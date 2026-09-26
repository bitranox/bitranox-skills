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

"Shown" means a non-assistant transcript record carried that exact 40-character string, which is
what separates a pasted or printed sha (the normal case) from a padded or invented one (the
padding case shows the short prefix and never the full form). Three kinds of record carry the
assistant's OWN text back and so do not count:

- the result of a file-writing tool (Write, Edit, MultiEdit, NotebookEdit), whose `toolUseResult`
  and snippet repeat what the assistant wrote;
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


def _asserted(statements, sha, tool_name):
    """True when some statement is a git command that proves THIS literal exists."""
    for argv in statements:
        found = _git_verb(argv, _ASSERTING_VERBS, tool_name)
        if found is None:
            continue
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


def _consumed_only_by_loud_git(statements, sha, tool_name):
    """True when every statement using `sha` resolves it as a revision of a loud git verb."""
    uses = [argv for argv in statements if any(_holds(token, sha) for token in argv)]
    if not uses:
        return False
    for argv in uses:
        found = _git_verb(argv, LOUD_GIT_VERBS, tool_name)
        if found is None:
            return False
        if not any(_holds(token, sha) for token in _revision_operands(*found)):
            return False
    return True


def shas_in(command, tool_name=None):
    """The bare full-sha literals this command uses without asserting them, in order."""
    if not command or not isinstance(command, str):
        return []
    executed = _executed_text(command, tool_name)
    statements = [argv_for_match(segment, tool_name or "Bash")
                  for _at, segment in iter_segments(executed, tool_name)]
    found = []
    for match in _SHA.finditer(executed):
        sha = match.group(0)
        if sha.isdigit() or sha in found:
            continue
        if _asserted(statements, sha, tool_name):
            continue
        if _consumed_only_by_loud_git(statements, sha, tool_name):
            continue
        found.append(sha)
    return found


def _parse(line):
    try:
        record = json.loads(line)
    except ValueError:
        return None
    return record if isinstance(record, dict) else None


def _file_tool_ids(record):
    """Ids of the file-writing tool calls in an assistant record."""
    content = (record.get("message") or {}).get("content")
    if not isinstance(content, list):
        return set()
    return {block.get("id") for block in content
            if isinstance(block, dict) and block.get("type") == "tool_use"
            and block.get("name") in _FILE_TOOLS}


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


def _shown_in(handle, wanted, relayed):
    seen = set()
    file_tools = set()
    for line in handle:
        if _FILE_TOOL_USE.search(line):
            record = _parse(line)
            if record is not None and record.get("type") == "assistant":
                file_tools |= _file_tool_ids(record)
        hits = {sha for sha in wanted - seen if sha in line}
        if not hits:
            continue
        record = _parse(line)
        if record is None:
            seen |= {m.group(0) for m in _SHA_IN_TEXT.finditer(line)} & hits
            continue
        if record.get("type") == "assistant":
            continue
        for text in _carried(record, file_tools, relayed):
            seen |= _unrefused(text) & hits
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
