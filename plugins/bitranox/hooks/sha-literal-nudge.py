#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge: a full git sha typed as a literal may have been invented.

An abbreviated sha is how one is DISPLAYED, so the 40-character form feels like something to
complete rather than something to look up - and a completion is plausible by construction, since
only the prefix is ever checked by eye. Measured five times: `fb3330b` printed, then
`fb3330b1d7b7...` typed into `ci_wait --sha`, where the real sha was `fb3330bd1ad7...`. Every
guard downstream checks SHAPE, not existence: `ci_wait`'s full-sha regex, a `headSha ==` filter
and `gh run list --commit` (which answers `[]` with exit 0) all pass a fabricated sha, so a wait
armed on one polls to its deadline. The prose rule was retrieved, restated and violated inside a
single session, which is why this is a hook.

What fires: a bare lowercase 40-hex literal, outside data regions (heredoc bodies, commit messages,
`echo`/`printf` operands - `Write-Host`/`Write-Output` under PowerShell - message-flag values,
comments), that the command does not ASSERT and that the session transcript never SHOWED.

Each literal is judged on its own. A command that derives a sha (`--sha $(git rev-parse HEAD)`)
has no literal to judge; one that also carries a literal says nothing about it by deriving
something else - `cd "$(git rev-parse --show-toplevel)" && ci_wait --sha <literal>` is the common
shape, and it derives a path. A literal is ASSERTED only when that same literal is an operand of
`git cat-file`, `git merge-base` or a `git rev-parse` that looks it up. `rev-parse` looks a full
sha up only through a suffix such as `^{commit}`: bare, `git rev-parse --verify <sha>` prints the
sha back with exit 0 whether or not the object exists. A comparison against a derived value
(`test "$SHA" = <literal>`) asserts nothing either: an invented literal just answers "not equal".

Every USE of the literal is judged. A use is checked when it is the assertion itself, a loud git
revision operand (below), or a statement that runs only because the assertion SUCCEEDED: joined to
it by `&&` (or through the edge of a `$(...)`), or inside the `then` block of an `if` whose
condition it is. `git cat-file -e <sha>^{commit}; gh run list --commit <sha>` fires - `;`, a
newline, `||` and `|` run the next statement whatever the check said - and so does an assertion
that comes after the use, or one negated with `!`. A literal assigned to a variable
(`I=<sha>`, `export I=<sha>`, PowerShell `$I = '<sha>'`) is used where `$I` / `${I}` is expanded,
not by the assignment. A literal inside a quoted command line another program runs
(`gate.py --gate 'git cat-file -e <sha>^{commit}'`, `ssh host 'git log -1 <sha>'`) is judged as
that command line.

"Shown" means a non-assistant transcript record carried that exact 40-character string, which is
what separates a pasted or printed sha (the normal case) from a padded or invented one (the
padding case shows the short prefix and never the full form). These records carry the
assistant's OWN text back and so do not count:

- the result of a file-writing tool (Write, Edit, MultiEdit, NotebookEdit), whose `toolUseResult`
  and snippet repeat what the assistant wrote;
- the result of a shell command that carried the literal without resolving it: `git rev-parse
  <sha>` prints any 40-hex string back, `echo` prints anything, and a command that merely passed
  it on cannot be told from one that confirmed it, so only a command that ASSERTED it or used it
  as a loud git revision vouches for it in its output;
- a sha the assistant wrote down as DATA before anything showed it - a file-writing tool's input,
  a heredoc, an `echo` operand, a commit message - read back later by any tool (Read, `cat`,
  `git log --format=%B`); again only an asserting or loud git command's output, or a record that
  is not a tool result (the user's words), vouches for it afterwards;
- a refusal: a sha that follows `bad object`, `unknown revision`, `no such commit` and the like on
  the same output line is the tool naming the sha it could NOT find;
- inside a subagent, the brief (and any later message from the parent): the parent ASSISTANT
  wrote it. A sha there counts only if the parent's transcript showed it in a record of its own
  (a tool result, the user's text). The parent is the session file next to the subagent's
  `subagents/` directory; if it cannot be read the brief vouches for nothing and the literal is
  nudged. For a subagent started by another subagent the session file is the grandparent, so a sha
  only the middle agent's tools printed is nudged - the direction that costs a note, not a miss.

What does NOT fire, deliberately: a literal every one of whose uses is a REVISION operand of a
local git command that resolves it (`git show <sha>`, `git log -1 <sha>`, `git diff A <sha>`,
`git branch --contains <sha>`, `git update-ref ...`). Git refuses a nonexistent object LOUDLY
there, so the invented sha costs one round trip and cannot become a silent wait. The same verbs
do not resolve every operand: `git log --grep=<sha>` / `-S<sha>` / `--author=` match TEXT and
exit 0 on nothing, anything after `--` is a pathspec, and `git branch <sha>`, `git tag <sha>`,
`git checkout -b <sha>` create a ref of that NAME. Those fire, as do the other silent consumers -
`gh`, `ci_wait`, `grep`, a `test` comparison, a poll loop - that this exists for.

NON-BLOCKING: emits additionalContext and exits 0, because a sha legitimately arriving from outside
(a CI URL, a pasted commit) must stay usable. Fail-open on any error. ASCII only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from shell_text import (
    argv_for_match,
    git_verb_operands,
    is_shell_tool,
    iter_segments,
    mask_data_regions,
    strip_data_sink_statements,
    strip_heredoc_bodies,
)

__all__ = ["main", "notice", "shas_in", "shown_shas"]

# A full sha as git prints it: exactly 40 LOWERCASE hex characters, not part of a longer word. An
# uppercase run is a GPG fingerprint, a longer one a sha256 or a hash inside an identifier. A
# single-letter option glued to it is not an identifier: `git log -S<sha>` uses the literal.
_SHA = re.compile(
    r"(?:(?<![0-9A-Za-z_])|(?<=\s-[A-Za-z])|(?<=^-[A-Za-z]))[0-9a-f]{40}(?![0-9A-Za-z_])")

# The same shape in RAW transcript text, where a JSON escape can sit right before it (`\n<sha>`
# reads as `n<sha>`), so only an adjacent hex character disqualifies a hit there.
_SHA_IN_TEXT = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{40}(?![0-9a-fA-F])")

# Local git verbs that prove the object exists - or fail - for a literal among their operands.
# `merge-base --is-ancestor` refuses a nonexistent object too, so it is an assertion as well.
_ASSERTING_VERBS = frozenset({"rev-parse", "cat-file", "merge-base"})

# What must follow a full sha for `rev-parse` to look it up rather than echo it back (measured,
# git 2.x: `rev-parse --verify <40 hex>` exits 0 for a nonexistent object; `<sha>^{commit}` does
# not).
_LOOKUP_SUFFIX = frozenset("^~:")

# Flags whose VALUE is prose for a human, whatever program takes them.
_MESSAGE_FLAG = re.compile(
    r"(?:(?<=\s)|^)(?:-m|--message|--body|--title|--notes|--subject|--description)(?:=|\s+)")

# Local git verbs that RESOLVE their revision operands and fail loudly on a nonexistent object. A
# literal consumed only as a revision operand of one of these cannot turn into a silent wait.
LOUD_GIT_VERBS = frozenset({
    "show", "log", "diff", "checkout", "switch", "restore", "reset", "revert", "cherry-pick",
    "merge", "rebase", "update-ref", "branch", "tag", "push", "fetch", "rev-list", "describe",
    "name-rev", "format-patch", "worktree", "blame", "ls-tree", "diff-tree", "shortlog", "notes",
    "bisect", "range-diff", "archive",
})

# Options whose value IS a revision, resolved as loudly as a positional one.
_REVISION_OPTIONS = frozenset({
    "--contains", "--no-contains", "--merged", "--no-merged", "--points-at", "--onto", "--source",
    "--force-with-lease",
})

# Options whose separate VALUE is text, a pattern or a date - matched, never resolved.
_TEXT_OPTIONS = frozenset({
    "--grep", "--author", "--committer", "--format", "--pretty", "--since", "--until", "--after",
    "--before", "--output", "--exclude", "--glob", "--date",
})

# Per verb, because the same letter means a bare flag elsewhere: `git show -m <sha>` resolves the
# sha, `git tag -m <text>` does not, and `-S` is pickaxe TEXT for log but a signing flag for merge.
_PICKAXE = frozenset({"-S", "-G"})
_VERB_TEXT_OPTIONS = {
    "log": _PICKAXE, "show": _PICKAXE, "diff": _PICKAXE, "rev-list": _PICKAXE,
    "shortlog": _PICKAXE, "format-patch": _PICKAXE, "diff-tree": _PICKAXE,
    "tag": frozenset({"-m", "-F", "--message", "--file", "-u", "--local-user"}),
    "notes": frozenset({"-m", "-F", "--message", "--file"}),
    "merge": frozenset({"-m", "-F", "--message", "--file"}),
    # These take the NAME of a ref to create.
    "checkout": frozenset({"-b", "-B", "--orphan"}),
    "switch": frozenset({"-c", "-C", "--create", "--force-create", "--orphan"}),
    "worktree": frozenset({"-b", "-B"}),
}

# Verbs whose FIRST positional operand is a ref NAME (or a list pattern), never a revision:
# `git branch <sha>` and `git tag <sha>` exit 0 having created a ref called that.
_NAMING_VERBS = frozenset({"branch", "tag"})

# Programs whose result record repeats what the assistant itself wrote.
_FILE_TOOL_USE = re.compile(r'"name"\s*:\s*"(?:Write|Edit|MultiEdit|NotebookEdit)"')
_FILE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})

# A tool naming the sha it could NOT find. Case-insensitive: git says "Not a valid object name",
# gh says "No commit found for SHA".
_REFUSAL = re.compile(
    r"bad object|bad revision|unknown revision|no such commit|not a valid (?:object|commit) name"
    r"|ambiguous argument|no commit found for sha", re.IGNORECASE)

_FILL = "\x00"

# Separators across which the next statement runs only if the one before it succeeded: `&&`, and
# the edges of a command substitution, whose status `X=$(...)` or a `test` comparison carries on.
_CHAINED = frozenset({"&&", "$(", ")", "`"})
_IF_HEADS = frozenset({"if", "elif"})
_BLOCK_ENDS = frozenset({"else", "elif", "fi"})

# Variable assignment: `NAME=value`, optionally after a declaring builtin, and PowerShell's
# `$name = value`.
_ASSIGNMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)\Z", re.DOTALL)
_DECLARERS = frozenset({"export", "local", "readonly", "declare", "typeset"})
_PS_VARIABLE = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*\Z")

# How deep a quoted command line inside a command line is judged as a command of its own.
_MAX_DEPTH = 2

_NOTICE = (
    "FULL SHA TYPED AS A LITERAL: {shas} {where}, and this command neither derives it nor checks "
    "it exists. A 40-character sha completed from a short one (or recalled) is invented: it "
    "passes every shape check, `gh run list --commit` answers [] with exit 0, and a wait armed on "
    "it polls to its deadline. Derive it in the same command (`--sha $(git rev-parse --verify -q "
    "HEAD)`), or prove it resolves first (`git cat-file -e <sha>^{{commit}}`). If you copied it "
    "from output you actually saw, ignore this."
)
_NOT_SHOWN = "does not appear in anything this session was shown (only a prefix, at most)"
_UNKNOWN = "could not be checked against the session transcript"


def _executed_text(command, tool_name):
    """The command with every data region blanked, length preserved."""
    text = strip_data_sink_statements(strip_heredoc_bodies(command), tool_name)
    masked = mask_data_regions(text, _FILL, tool_name or "Bash")
    out = list(text)
    for index, char in enumerate(masked):
        # mask_data_regions turns a comment into spaces and a quoted region into the fill: a
        # non-space character that became a space was inside a comment.
        if char == " " and not text[index].isspace():
            out[index] = " "
    for flag in _MESSAGE_FLAG.finditer(masked):
        cursor = flag.end()
        while cursor < len(masked) and masked[cursor] == _FILL:
            out[cursor] = " "
            cursor += 1
    return "".join(out)


def _holds(token, sha):
    return any(match.group(0) == sha for match in _SHA.finditer(token))


def _git_verb(argv, verbs, tool_name):
    """(verb, operands) when `argv` is `git <global opts> <verb> ...` for one of `verbs`."""
    operands = git_verb_operands(argv, verbs, tool_name)
    if operands is None:
        return None
    return argv[len(argv) - len(operands) - 1], operands


def _revision_operands(verb, operands):
    """The operands `verb` RESOLVES as revisions: no option text, no pathspec, no new ref name."""
    text_options = _TEXT_OPTIONS | _VERB_TEXT_OPTIONS.get(verb, frozenset())
    resolved = []
    positional = 0
    tokens = iter(operands)
    for token in tokens:
        if token == "--":
            break                                   # everything after it is a pathspec
        if token.startswith("-") and len(token) > 1:
            name, has_value, value = token.partition("=")
            if name in _REVISION_OPTIONS:
                resolved.append(value if has_value else next(tokens, ""))
            elif name in text_options and not has_value:
                next(tokens, None)                  # its separate value is text, not a revision
            continue
        positional += 1
        if positional == 1 and verb in _NAMING_VERBS:
            continue
        resolved.append(token)
    return resolved


def _asserts(argv, sha, tool_name):
    """True when this statement is a git command that proves THIS literal exists."""
    found = _git_verb(argv, _ASSERTING_VERBS, tool_name)
    if found is None:
        return False
    verb, operands = found
    for token in _revision_operands(verb, operands):
        if not _holds(token, sha):
            continue
        if verb != "rev-parse":
            return True
        after = token[token.find(sha) + len(sha):][:1]
        if after and after in _LOOKUP_SUFFIX:
            return True
    return False


def _resolved_loudly(argv, sha, tool_name):
    """True when this statement resolves `sha` as a revision of a loud git verb."""
    found = _git_verb(argv, LOUD_GIT_VERBS, tool_name)
    return found is not None and any(_holds(token, sha) for token in _revision_operands(*found))


def _vetted_inside(argv, sha, tool_name, depth):
    """True when every token carrying `sha` is a command line of its own that does not misuse it.

    `gate.py --gate 'git cat-file -e <sha>^{commit}'` and `ssh host 'git log -1 <sha>'` hand the
    literal to a command another program runs; judged as that command, it is asserted or resolved.
    """
    holding = [token for token in argv if _holds(token, sha)]
    if not holding or depth >= _MAX_DEPTH:
        return False
    return all(any(char.isspace() for char in token)
               and sha not in _unverified(token, tool_name, depth + 1) for token in holding)


def _statements(executed, tool_name):
    """[(argv, separator after it)] for each statement, the separator stripped ("" at the end)."""
    segments = list(iter_segments(executed, tool_name))
    out = []
    for index, (at, segment) in enumerate(segments):
        end = segments[index + 1][0] if index + 1 < len(segments) else len(executed)
        out.append((argv_for_match(segment, tool_name or "Bash"),
                    executed[at + len(segment):end].strip()))
    return out


def _unquoted(word):
    if len(word) >= 2 and word[0] == word[-1] and word[0] in "'\"":
        return word[1:-1]
    return word


def _assignments(argv, tool_name):
    """{name: value} when the statement does nothing but assign variables, else None."""
    if tool_name == "PowerShell":
        if len(argv) == 3 and argv[1] == "=" and _PS_VARIABLE.match(argv[0]):
            return {argv[0][1:].lower(): _unquoted(argv[2])}
        return None
    words = argv[1:] if argv[:1] and argv[0] in _DECLARERS else argv
    found = {}
    for word in words:
        match = _ASSIGNMENT.match(word)
        if match is None:
            return None
        found[match.group(1)] = _unquoted(match.group(2))
    return found or None


def _expanded(argv, variables, tool_name):
    """`argv` with every `$NAME` / `${NAME}` of a variable holding a full sha replaced by it."""
    if not variables:
        return argv
    flags = re.IGNORECASE if tool_name == "PowerShell" else 0
    out = []
    for token in argv:
        for name, value in variables.items():
            token = re.sub(r"\$(?:\{%s\}|%s(?![A-Za-z0-9_]))" % (name, name),
                           lambda _m, value=value: value, token, flags=flags)
        out.append(token)
    return out


def _with_variables(statements, tool_name):
    """The statements with sha-holding variables expanded; a pure assignment becomes None.

    `I=<sha>; git merge-base --is-ancestor HEAD $I` uses the literal where `$I` is expanded, and
    the assignment itself consumes nothing.
    """
    variables = {}
    out = []
    for argv, separator in statements:
        assigned = _assignments(argv, tool_name)
        argv = _expanded(argv, variables, tool_name)
        if assigned is None:
            out.append((argv, separator))
            continue
        for name, value in assigned.items():
            if tool_name == "PowerShell":
                name = name.lower()
            if _SHA.search(value):
                variables[name] = value
            else:
                variables.pop(name, None)
        out.append((None, separator))
    return out


def _head_word(argv):
    return argv[0] if argv else ""


def _then_block(statements, start):
    """Indexes of the `then` block opening at `start`, up to its `else`/`elif`/`fi`."""
    block = set()
    depth = 0
    for index in range(start, len(statements)):
        word = _head_word(statements[index][0])
        if index > start and depth == 0 and word in _BLOCK_ENDS:
            break
        if word == "if":
            depth += 1
        elif word == "fi" and depth:
            depth -= 1
        block.add(index)
    return block


def _runs_only_after(statements, index):
    """Indexes of the statements that run only if statement `index` succeeded.

    `&&` passes success on, and so does the edge of a command substitution, whose status an
    assignment or a comparison carries; `;`, a newline, `||`, `|` and `&` do not. A condition of
    `if`/`elif` made only of such links guards its `then` block.
    """
    guarded = set()
    last = index
    while last + 1 < len(statements) and statements[last][1] in _CHAINED:
        last += 1
        guarded.add(last)
    head = index
    while head > 0 and statements[head - 1][1] in _CHAINED:
        head -= 1
    opens = _head_word(statements[head][0]) in _IF_HEADS
    if opens and last + 1 < len(statements) and _head_word(statements[last + 1][0]) == "then":
        guarded |= _then_block(statements, last + 1)
    return guarded


def _negated(argv):
    """True when a `!` before the program inverts the statement's status."""
    return "!" in argv[:argv.index("git")] if "git" in argv else "!" in argv


def _vouched(statements, sha, tool_name, depth):
    """True when every use of `sha` is checked: asserted, loudly resolved, or run after a check."""
    uses = [index for index, (argv, _sep) in enumerate(statements)
            if argv and any(_holds(token, sha) for token in argv)]
    if not uses:
        return False
    asserting = [index for index in uses if _asserts(statements[index][0], sha, tool_name)]
    guarded = set()
    for index in asserting:
        if not _negated(statements[index][0]):
            guarded |= _runs_only_after(statements, index)
    for index in uses:
        argv = statements[index][0]
        if index in asserting or index in guarded or _resolved_loudly(argv, sha, tool_name):
            continue
        if not _vetted_inside(argv, sha, tool_name, depth):
            return False
    return True


def _unverified(command, tool_name, depth):
    executed = _executed_text(command, tool_name)
    statements = _with_variables(_statements(executed, tool_name), tool_name)
    found = []
    for match in _SHA.finditer(executed):
        sha = match.group(0)
        if sha.isdigit() or sha in found:
            continue
        if not _vouched(statements, sha, tool_name, depth):
            found.append(sha)
    return found


def shas_in(command, tool_name=None):
    """The bare full-sha literals this command uses without asserting them, in order."""
    if not command or not isinstance(command, str):
        return []
    return _unverified(command, tool_name, 0)


def _parse(line):
    try:
        record = json.loads(line)
    except ValueError:
        return None
    return record if isinstance(record, dict) else None


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _content_strings(content, file_tools, authored):
    """Message content, minus file-tool echoes, minus the text another assistant authored."""
    if isinstance(content, str):
        if not authored:
            yield content
        return
    if not isinstance(content, list):
        yield from _strings(content)
        return
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            if block.get("tool_use_id") not in file_tools:
                yield from _strings(block)
        elif not authored:
            yield from _strings(block)


def _carried(record, file_tools, relayed):
    """Every string a non-assistant record carries that the assistant did not write itself."""
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    echoes = isinstance(content, list) and any(
        isinstance(block, dict) and block.get("tool_use_id") in file_tools for block in content)
    # In a subagent's own file the non-meta user TEXT is the parent assistant's brief or message.
    authored = relayed and record.get("type") == "user" and not record.get("isMeta")
    for key, value in record.items():
        if key == "toolUseResult" and echoes:
            continue
        if key == "message" and isinstance(value, dict):
            for inner, item in value.items():
                if inner == "content":
                    yield from _content_strings(item, file_tools, authored)
                else:
                    yield from _strings(item)
            continue
        yield from _strings(value)


def _unrefused(text):
    """The shas in `text`, except one a tool names on the same line as refusing it."""
    found = set()
    for match in _SHA_IN_TEXT.finditer(text):
        line_start = text.rfind("\n", 0, match.start()) + 1
        if not _REFUSAL.search(text, line_start, match.start()):
            found.add(match.group(0))
    return found


class _Calls:
    """What the assistant's own tool calls did with each candidate sha, in transcript order.

    `echoes[id]`: the shas a shell call carried without resolving them - its output repeating one
    is the assistant's word coming back (`git rev-parse <sha>` prints any 40-hex string, `echo`
    prints anything). `resolves[id]`: the shas a shell call resolved, so its output naming one is
    evidence. `authored`: shas the assistant wrote down as DATA - a file-writing tool's input, a
    heredoc, an `echo` operand, a commit message - before anything showed them.
    """

    def __init__(self):
        self.file_tools = set()
        self.echoes = {}
        self.resolves = {}
        self.authored = set()

    def record(self, record, wanted, seen):
        content = (record.get("message") or {}).get("content")
        if not isinstance(content, list):
            return
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name, call_id, input_ = block.get("name"), block.get("id"), block.get("input")
            if name in _FILE_TOOLS:
                self.file_tools.add(call_id)
                written = {sha for text in _strings(input_) for sha in wanted if sha in text}
                self.authored |= written - seen
            elif is_shell_tool(name) and isinstance(input_, dict):
                self._shell(call_id, name, input_.get("command"), wanted, seen)

    def _shell(self, call_id, name, command, wanted, seen):
        if not isinstance(command, str):
            return
        carried = {sha for sha in wanted if sha in command}
        if not carried:
            return
        executed = {match.group(0) for match in _SHA.finditer(_executed_text(command, name))}
        resolved = (carried & executed) - set(shas_in(command, name))
        self.resolves[call_id] = resolved
        self.echoes[call_id] = carried - resolved
        self.authored |= (carried - executed) - seen

    def discounted(self, record):
        """The shas a TOOL record's output may not vouch for: echoes of the call's own literal,
        and what the assistant wrote down, unless this call resolved it."""
        content = (record.get("message") or {}).get("content")
        ids = {block.get("tool_use_id") for block in content if isinstance(block, dict)
               and block.get("type") == "tool_result"} if isinstance(content, list) else set()
        if not ids and "toolUseResult" not in record:
            return set()                                # a user's words, an attachment
        echoed = set().union(*(self.echoes.get(call_id, ()) for call_id in ids))
        resolved = set().union(*(self.resolves.get(call_id, ()) for call_id in ids))
        return echoed | (self.authored - resolved)


def _shown_in(handle, wanted, relayed):
    seen = set()
    calls = _Calls()
    for line in handle:
        hits = {sha for sha in wanted - seen if sha in line}
        if not hits and not _FILE_TOOL_USE.search(line):
            continue
        record = _parse(line)
        if record is None:
            seen |= {m.group(0) for m in _SHA_IN_TEXT.finditer(line)} & hits
            continue
        if record.get("type") == "assistant":
            calls.record(record, wanted - seen, seen)
            continue
        if not hits:
            continue
        found = set()
        for text in _carried(record, calls.file_tools, relayed):
            found |= _unrefused(text) & hits
        seen |= found - calls.discounted(record)
    return seen


def shown_shas(paths, shas, relayed=()):
    """The subset of `shas` that some NON-assistant transcript record carried verbatim.

    None when no transcript could be read: "not shown" is a claim about a transcript that was
    read, so an unreadable one leaves the question open rather than answering it.

    `relayed` are transcripts whose user TEXT another assistant wrote - a subagent's own file,
    whose brief is the parent's words - so there only tool results and harness records count.

    Only lines holding a candidate are parsed (plus assistant lines naming a file-writing tool),
    so a large transcript costs one substring scan. The assistant's own records do not count: its
    earlier tool call carrying the sha is the invention, not evidence against it - and neither do
    the records that merely repeat it (see the module docstring).
    """
    wanted = set(shas)
    seen = set()
    readable = False
    for path, is_relayed in [(p, False) for p in paths] + [(p, True) for p in relayed]:
        if not wanted - seen:
            break
        try:
            handle = open(path, encoding="utf-8", errors="ignore")
        except OSError:
            continue
        readable = True
        with handle:
            seen |= _shown_in(handle, wanted - seen, is_relayed)
    return seen if readable else None


def notice(command, tool_name=None, shown=None):
    """The nudge text for unverified full-sha literals, else None.

    `shown` is the set of shas the transcript carried, or None when it could not be read; a sha in
    it was copied from real output and is left alone.
    """
    shas = shas_in(command, tool_name)
    if shown is not None:
        shas = [sha for sha in shas if sha not in shown]
    if not shas:
        return None
    listed = ", ".join(sha[:12] + "..." for sha in shas)
    return _NOTICE.format(shas=listed, where=_UNKNOWN if shown is None else _NOT_SHOWN)


def _transcripts(event):
    """(own, relayed): the session transcripts that vouch for a sha, and a subagent's own file.

    Inside a subagent `transcript_path` is the MAIN session's and `agent_id` names the subagent,
    whose file sits at `<session>/subagents/agent-<id>.jsonl`. A `transcript_path` that already
    names such a file is read the same way, with the session file beside its directory as parent.
    """
    main_path = event.get("transcript_path")
    if not main_path:
        return [], []
    path = Path(main_path)
    if path.parent.name == "subagents" and path.name.startswith("agent-"):
        session_dir = path.parent.parent
        return [session_dir.parent / (session_dir.name + ".jsonl")], [path]
    agent = event.get("agent_id")
    if agent:
        return [path], [path.with_suffix("") / "subagents" / ("agent-%s.jsonl" % agent)]
    return [path], []


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    command = (event.get("tool_input") or {}).get("command")
    tool_name = event.get("tool_name")
    candidates = shas_in(command, tool_name)
    if not candidates:
        return 0
    paths, relayed = _transcripts(event)
    shown = shown_shas(paths, candidates, relayed)
    message = notice(command, tool_name, shown)
    if message:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
