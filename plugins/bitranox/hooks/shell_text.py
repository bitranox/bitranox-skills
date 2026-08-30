#!/usr/bin/env python3
"""Shared shell-command text handling for the command-scanning guards.

A guard that inspects a Bash command must judge COMMANDS, not data. A heredoc body is data: it is
text being written to a file or piped to a program, not something the shell will execute. Scanning
it makes a guard fire on prose that merely MENTIONS the footgun it guards - which blocks you from
writing the documentation, memory entry, or commit message that warns about that very footgun. This
repo has shipped that failure before, in more than one guard.

It lives here rather than in each guard because two copies had already drifted apart in wording and
would eventually drift in behaviour: a guard learning about a new heredoc form must teach every
other guard at the same time, and a copy that misses the lesson silently blocks something the
others allow.

Import it directly (`import shell_text`); the hooks directory is on `sys.path` for both the
`run-python.sh` launch and the test conftest.
"""
from __future__ import annotations

import re
import shlex
from pathlib import PurePosixPath, PureWindowsPath

# The opener forms bash accepts: `<<WORD`, `<<-WORD`, `<< WORD`, `<<'WORD'`, `<<"WORD"`. The
# backreference keeps the quoting symmetric, so `<<'EOF"` is not read as a quoted delimiter.
HEREDOC_OPEN = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# The tools whose `tool_input.command` is a shell command string. Claude Code routes the model's
# shell commands through the `PowerShell` tool on Windows where that tool is enabled, and on a
# Windows box without Git Bash it registers no `Bash` tool at all. So a guard that compares
# `tool_name` against "Bash" alone simply never runs there, while still reading - in hooks.json, in
# its docstring, and in its own passing tests - exactly like a guard that is switched on. A hook
# that never fires and one that fires and finds nothing are both silent.
SHELL_TOOLS = ("Bash", "PowerShell")

# Statement separators, and the three shapes that mean "a change is leaving this machine".
SEP = re.compile(r"&&|\|\||[;\n|]")
# A statement can also begin INSIDE a command substitution, and what is in there is a real
# command. Anchoring a match at a segment start is what makes `git commit` appearing as DATA not
# count - but without that, anchoring also silently drops `A=$(git commit ...)`, which the older
# match-anywhere regexes did see. Measured as a regression when the walk replaced them.
#
# Which of these separators actually separates depends on QUOTING, which a regex cannot carry, so
# the spellings live in the walk below rather than in a pattern of their own.


def _iter_separators(text, tool_name=None):
    """(start, end) of every separator in `text` that genuinely begins a new statement.

    Quoting decides this, and it decides it DIFFERENTLY for the two kinds of separator, which
    is why one "is it quoted" flag is not enough:

    * inside SINGLE quotes nothing is special - `echo '$(git commit)'` runs no git at all;
    * inside DOUBLE quotes a command substitution STILL runs, while `;` `|` `&&` are literal.

    Neither is expressible as a pattern, because quoting is state carried across the string, so
    this walks it. The stack matters as much as the flags: when `$(` opens, the quoting in force
    outside it must be restored at the matching `)`, or the closing `"` of `echo "$(date)"` reads
    as an OPENING one and every separator on the rest of the line looks quoted - turning a false
    block into a silent miss, which is the worse direction.

    `tool_name` decides which character escapes, and the two shells are mirror images of each
    other, so guessing is wrong in both directions at once. Under Bash `\\` escapes and a backtick
    opens a substitution; under PowerShell a BACKTICK escapes and `\\` is a PATH SEPARATOR. Reading
    `\\` as an escape under PowerShell eats the separator behind a Windows path, so
    `cd C:\\; git commit` stops being seen at all - the same tool-versus-host confusion that
    `split_for_tool` exists to prevent, one function further down.
    """
    # An UNKNOWN tool escapes NOTHING. The two readings are not symmetric: the Bash one enables
    # backslash escaping, which is the reading that can swallow a separator and hide a command, so
    # defaulting an unrecognised tool to it puts the silent miss in the fallback. Escaping nothing
    # errs toward MORE separators - a false block, which is visible and recoverable. Same rule as
    # `split_for_tool` one function down: an unknown tool takes the stricter reading.
    escape, substitutes = {
        "Bash": ("\\", True),
        "PowerShell": ("`", False),
    }.get(tool_name, ("", True))
    depth: list[tuple[str, bool, bool]] = []   # (closer, saved_single, saved_double)
    in_single = in_double = False
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == escape and not in_single:
            i += 2                             # an escaped character is data, whatever it is
            continue
        if in_single:
            in_single = ch != "'"
            i += 1
            continue
        if ch == "'" and not in_double:
            in_single = True
            i += 1
            continue
        if ch == '"':
            in_double = not in_double
            i += 1
            continue
        if depth and not in_double and ch == depth[-1][0]:
            # The closer ENDS the substitution's statement. Without this the rest of the line
            # stays glued to it, so `foo=$(ls) git commit -m x` yields one segment `ls) git
            # commit -m x` whose start is `ls)` - and a gate that anchors at the start cannot
            # see the commit at all. It also drops the stray `)` off the last operand token.
            yield i, i + 1
            _closer, in_single, in_double = depth.pop()
            i += 1
            continue
        two = text[i:i + 2]
        # A substitution runs a command even inside double quotes. Process substitution does
        # NOT happen there, so only `$(` and a backtick survive the in_double test.
        if two == "$(" or (substitutes and not in_double and two in ("<(", ">(")):
            yield i, i + 2
            depth.append((")", in_single, in_double))
            in_single = in_double = False
            i += 2
            continue
        if ch == "`" and substitutes:
            yield i, i + 1
            depth.append(("`", in_single, in_double))
            in_single = in_double = False
            i += 1
            continue
        if in_double:
            i += 1                             # a plain separator is literal in double quotes
            continue
        if two in ("&&", "||"):
            yield i, i + 2
            i += 2
            continue
        if ch in ";\n|":
            yield i, i + 1
            i += 1
            continue
        i += 1


COMMIT_RE = re.compile(r"^(?:\w+=\S+\s+)*git\b(?:\s+-C\s+\S+|\s+--?\S+)*\s+commit\b")
PR_RE = re.compile(r"^(?:\w+=\S+\s+)*gh\b.*\bpr\b.*\bcreate\b")
_GATED_GIT_VERBS = frozenset({"commit", "push"})
PUSH_RE = re.compile(r"^(?:\w+=\S+\s+)*git\b(?:\s+-C\s+\S+|\s+--?\S+)*\s+push\b")


# git global options that consume a SEPARATE following token, so a subcommand search never
# mistakes their VALUE for the verb. Lifted here from `git-footgun-guard`, which had the only
# correct implementation of this in the plugin while three other callers each got it wrong in
# their own way - two blind to any option at all, and the regex pair above wrong in BOTH
# directions (see `git_verb_operands`).
GIT_VALUE_OPTS = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
)


def git_verb_operands(tokens, verbs, tool_name="Bash"):
    r"""Tokens after git's SUBCOMMAND when this really is `git <global opts> <verb>`; else None.

    The single answer to "what git command is this?", because asking it with a regex is wrong in
    both directions and every caller here had drifted:

    * UNDER-matching, which the 2026-08-28 audit found in two nudges: `\bgit\s+rev-parse\b`
      requires the verb to sit adjacent to `git`, so any global option between them silences the
      hook - and `git -C <path>` is the shape the rev-parse nudge's own advice steers people
      toward, so the one reader who half-learned the lesson got nothing.
    * OVER-matching, found while checking the shared module for the same class of gap: the old
      `COMMIT_RE` treats `-C` as a bare flag, so `git -C commit status` read `-C`'s VALUE as the
      verb and the repo gate BLOCKED a status command run in a directory named `commit`. In the
      other direction `git -c key=value commit` was not gated at all, because `key=value` does
      not start with `-` and ended the option run early. A commit that the gate cannot see is a
      commit it cannot gate.

    Leading `VAR=value` environment assignments are skipped, and the program name is taken with
    `basename_for_tool`, so `/usr/bin/git` and `git.exe` both count.
    """
    idx = 0
    while idx < len(tokens) and "=" in tokens[idx] and not tokens[idx].startswith("-"):
        idx += 1                                  # leading VAR=value environment assignments
    if idx >= len(tokens) or basename_for_tool(tokens[idx], tool_name) != "git":
        return None
    idx += 1
    while idx < len(tokens) and tokens[idx].startswith("-"):
        if tokens[idx] in GIT_VALUE_OPTS:
            idx += 1                              # this option's VALUE is a separate token
        idx += 1
    if idx >= len(tokens) or tokens[idx] not in verbs:
        return None
    return tokens[idx + 1:]


def is_git_verb(segment, verbs, tool_name="Bash"):
    """True when `segment` is a `git <global opts> <verb>` command for one of `verbs`."""
    return git_verb_operands(segment.split(), verbs, tool_name) is not None


def iter_segments(text, tool_name=None):
    """(offset, segment) for each statement in `text`, offsets into `text` itself.

    `SEP.split` throws the positions away, which is fine for a yes/no question and not fine for a
    caller that must know whether a write happened BEFORE the gated verb. Without this such a
    caller keeps its own second splitter, and the two drift on exactly the shapes that matter.
    """
    pos = 0
    for start, end in _iter_separators(text, tool_name):
        yield pos, text[pos:start]
        pos = end
    yield pos, text[pos:]



def _windows_command_argv(command):
    r"""Split a Windows command line by the documented C-runtime rules.

    Pure Python rather than `CommandLineToArgvW`, unlike the copy in `harness_checks`: that one
    parses a command line THIS MACHINE will run, so a Windows-only path is fine there. This one
    parses the PowerShell TOOL's string, which can reach a hook on any host - pwsh runs on Linux -
    and a ctypes path would also be untestable on the platform most of this suite runs on.

    The backslash rules only bite around a quote: 2n backslashes before one are n backslashes and
    the quote still toggles, 2n+1 are n backslashes and a LITERAL quote, and a run with no quote
    after it is literal throughout. That last rule is the one that matters here - it is what keeps
    `C:\dir\file.txt` intact.
    """
    args, cur, in_quotes, started, i, n = [], [], False, False, 0, len(command)
    while i < n:
        ch = command[i]
        if ch == "\\":
            j = i
            while j < n and command[j] == "\\":
                j += 1
            slashes = j - i
            if j < n and command[j] == '"':
                cur.append("\\" * (slashes // 2))
                if slashes % 2:
                    cur.append('"')
                else:
                    in_quotes = not in_quotes
                started, i = True, j + 1
            else:
                cur.append("\\" * slashes)
                started, i = True, j
            continue
        if ch == '"':
            in_quotes, started, i = not in_quotes, True, i + 1
            continue
        if ch in " \t" and not in_quotes:
            if started:
                args.append("".join(cur))
                cur, started = [], False
            i += 1
            continue
        cur.append(ch)
        started, i = True, i + 1
    if started:
        args.append("".join(cur))
    return args


def split_for_tool(command, tool_name="Bash", comments=False):
    r"""Split a tool's `tool_input.command` into argv, by the TOOL's language, never the host OS.

    A hook on a `Bash|PowerShell` matcher receives two different languages. The Bash tool is a
    POSIX command line even on Windows, because Claude Code runs it through Git Bash - verified
    against real bash, which mangles an unquoted `C:\Users\me\f.txt` to `C:Usersmef.txt` exactly
    as `shlex` does, so shlex is not merely tolerable there, it is what the tool actually does.
    The PowerShell tool is a Windows command line, where that same backslash is a PATH SEPARATOR
    and eating it hands the caller a path that opens nothing.

    That matters only where a guard RESOLVES the token - opens, stats or executes it - because the
    read then fails and a fail-open approves what the guard exists to block. Tokens merely compared
    or name-matched survive mangling.

    `comments` reaches the POSIX arm only, where shlex knows `#`. The Windows arm has no comment
    concept at all - the C runtime hands `#` to the program like any other character - so passing
    it does not silently mean something different there, it means nothing.

    Do NOT reach for `harness_checks.split_command_line` instead: it keys on `os.name`, which is
    right for a command this machine will run and wrong here - on a Windows host it would hand the
    Bash tool's POSIX string to the Windows parser. An unknown tool takes the Bash reading, which
    is the one that cannot invent separators that were never in the string.
    """
    if tool_name == "PowerShell":
        return _windows_command_argv(command)
    return shlex.split(command, comments=comments)


def basename_for_tool(token, tool_name="Bash"):
    r"""The program name from a token that may carry a path, by the TOOL's separator rules.

    A guard asking "is this command `sed`?" has to strip the path first, and which characters
    separate a path is the tool's question, not the host's. `C:\bin\sed.exe` is a path in
    PowerShell and one long filename under POSIX rules - so a basename taken on `/` alone returns
    the whole string and never matches, which is a guard silently declining to fire.

    This is the SECOND half of the same defect as `split_for_tool`, and either half alone leaves
    the guard off: split correctly and the basename still fails, fix the basename and the split
    has already eaten the separators.

    `.exe` is dropped on BOTH arms, because it is about how a program is NAMED and not about
    separators at all - Git Bash on Windows runs `sed.exe`, and every command allowlist in this
    plugin is spelled without the suffix. Stripping it only on the PowerShell arm left
    `sed.exe -i config.json` unblocked under the tool that carries nearly all the traffic.
    """
    name = (PureWindowsPath(token) if tool_name == "PowerShell" else PurePosixPath(token)).name
    return name[:-4] if name.lower().endswith(".exe") else name

def is_shell_tool(tool_name) -> bool:
    """True when `tool_name` is a tool that carries a shell command in `tool_input.command`.

    Use this in place of a literal `tool_name == "Bash"` check, and pair it with a
    `Bash|PowerShell` matcher in hooks.json - the matcher decides whether the hook runs at all, so
    widening only one of the two leaves the guard off on the platform it was widened for.
    """
    return tool_name in SHELL_TOOLS


def is_gated_command(command, tool_name=None):
    """True when a statement in `command` is a git commit, a git push, or a gh pr create.

    Heredoc bodies are dropped first, then each remaining statement is matched anchored at its
    start, so "git commit"/"git push" appearing as DATA does not count - only an actual command
    does. Over-matching is not harmless here: the repo gate blocks on it, and a CHANGELOG line
    ABOUT committing would then block the commit that adds it.

    Anchoring alone does NOT cover a heredoc body, which is why the strip is needed and not merely
    tidy. The body is split on the same separators as the surrounding command, so a line such as
    `for cmd in ("git checkout -- f && git commit -m x",)` yields a segment beginning with a
    real-looking command. Measured 2026-08-20: writing the tests for `gated-prep-nudge` was blocked
    by the repo gate, because the test data named the very shapes under test - a guard refusing to
    let its own documentation be written.

    It lives in this module rather than in the gate that first needed it because a second consumer
    now asks the same question for its own reason - a commit is the moment work concludes, which is
    when the decision-review nudge fires. Two copies of this regex set would drift, and the drift
    would be silent in both directions: a shape one recognises and the other does not.
    """
    for _at, seg in iter_segments(strip_heredoc_bodies(command or ""), tool_name):
        seg = seg.strip().lstrip("(").strip()
        if is_git_verb(seg, _GATED_GIT_VERBS) or PR_RE.match(seg):
            return True
    return False


def commands_only(command: str) -> str:
    """`command` with every DATA region removed, leaving only text the shell will EXECUTE.

    The pairing every command-scanning guard needs, in one call. Each half alone leaves a hole the
    other closes, and both holes have shipped: `mask_data_regions` cannot see a heredoc BODY,
    because a body is not quoted, so a `git -C /elsewhere` written into a runbook read as the repo
    the command acts on; `strip_heredoc_bodies` cannot see a quoted ARGUMENT, so `echo 'pgrep -f x'`
    read as an invocation. A guard that calls only one is not half-safe, it is wrong in whichever
    direction it skipped - and which half was skipped is invisible at the call site, which is why
    this exists instead of the two-call idiom.

    Offsets do NOT survive: the heredoc strip removes lines. A caller that needs POSITIONS (to tell
    a write before the verb from one after it) must use `mask_data_regions` and handle heredocs
    itself - `gated-prep-nudge` is the one that does.

    NOT for every guard, and the exception is not an edge case. A quoted string is data to the
    LOCAL shell and a COMMAND to a remote one, so a guard whose subject is `ssh host \'...\'`,
    `bash -c \'...\'` or any other execute-this-string form must NOT mask quotes - that deletes
    exactly what it is looking for. Measured: routing `warn-inline-powershell` through this made
    `ssh host \'powershell -command "x"\'` stop firing and took six tests with it. Those guards
    want `strip_heredoc_bodies` alone. Ask what the guard's subject IS before reaching for this.
    """
    return mask_data_regions(strip_heredoc_bodies(command or ""))


def strip_heredoc_bodies(command: str) -> str:
    """Drop heredoc bodies, keeping the command lines around them.

    The opener line is KEPT, because it is a real command (`cat <<EOF > file.txt` still redirects,
    and `cmd <<EOF | grep x` still pipes). Only the body and its terminator are removed.

    An unterminated heredoc consumes the rest of the input, which is the safe direction: the shell
    would treat those lines as data too, so a guard must not judge them as commands.
    """
    out: list[str] = []
    lines = command.split("\n")
    index = 0
    while index < len(lines):
        out.append(lines[index])
        # `<<EOF` inside a quoted ARGUMENT opens nothing: `git commit -m "docs: explain <<EOF
        # heredocs"` was read as an opener, so the strip swallowed the rest of the command and
        # every guard downstream went SILENT on a real `git push` after it.
        #
        # The test is whether the `<<` ITSELF is quoted, not whether the line contains quotes.
        # Searching the masked line instead is wrong and was measured so: `mask_data_regions`
        # masks the delimiter's own quotes in the standard `<<'EOF'` form, which is heredoc
        # SYNTAX rather than a string, and 23 tests went red. The mask is length-preserving, so
        # the raw match offset indexes it directly.
        opener = HEREDOC_OPEN.search(lines[index])
        if opener and mask_data_regions(lines[index])[opener.start():opener.start() + 2] != "<<":
            opener = None
        index += 1
        if not opener:
            continue
        delimiter = opener.group(2)
        # The terminator is the first line that is exactly the delimiter; bash allows leading
        # whitespace with the `<<-` form, so the comparison is made on the stripped line.
        while index < len(lines) and lines[index].strip() != delimiter:
            index += 1
        index += 1                                    # drop the terminator line itself
    return "\n".join(out)


def blank_unexpanded_text(command: str) -> str:
    """Blank the regions the shell will neither execute nor expand, keeping structure intact.

    A heredoc is not the only data region in a command. These three are just as inert, and a guard
    that scans them fires on text merely DESCRIBING a footgun:

    - a BACKSLASH-ESCAPED character (`\\$?`), which bash passes through literally;
    - a SINGLE-quoted string, where no expansion happens at all;
    - a `#` comment, which is never executed.

    A DOUBLE-quoted string is deliberately left alone: `$?` expands there, so `echo "rc=$?"` is a
    genuine status read. That also means prose inside double quotes remains indistinguishable from
    the real thing - the two are identical to the shell, so no scanner can separate them.

    A caller asking about STATEMENT STRUCTURE rather than expansions wants the opposite treatment
    of the same characters, and `mask_data_regions` below is that function - not a flag here.

    Blanking to spaces rather than deleting keeps offsets, line structure and every pipe, `;` and
    `&&` outside the quotes, so callers that split on those still see the same command shape.
    """
    out: list[str] = []
    index, size = 0, len(command)
    in_single = in_double = False
    while index < size:
        char = command[index]
        if in_single:
            out.append(char if char in "'\n" else " ")
            in_single = char != "'"
            index += 1
        elif char == "\\" and index + 1 < size and not in_double:
            out.append("  " if command[index + 1] != "\n" else " \n")
            index += 2
        elif in_double:
            if char == "\\" and index + 1 < size:
                out.append("  " if command[index + 1] != "\n" else " \n")
                index += 2
                continue
            in_double = char != '"'
            out.append(char)
            index += 1
        elif char == "'":
            in_single = True
            out.append(char)
            index += 1
        elif char == '"':
            in_double = True
            out.append(char)
            index += 1
        elif char == "#" and (not out or out[-1].isspace()):
            while index < size and command[index] != "\n":
                out.append(" ")
                index += 1
        else:
            out.append(char)
            index += 1
    return "".join(out)


def mask_data_regions(command: str, fill: str = "Q") -> str:
    """Replace every region that cannot affect STATEMENT STRUCTURE with a filler character.

    `blank_unexpanded_text` above answers "will the shell expand this?" and therefore must leave
    double-quoted text intact. A guard reading statement structure asks a different question, and
    for it the answer is unambiguous: whatever the shell does with `$?` inside
    `git commit -m "wip; git push"`, that `;` is not a separator and those words are not a command.

    Four regions are masked, each including its own delimiters:

    - single- and double-quoted strings;
    - `$(...)` command substitution and `$((...))` arithmetic, depth-counted so nesting survives;
    - `${...}` parameter expansion and `@{...}` revspecs, whose braces are a word, not a
      brace GROUP - `git rev-list @{u}...HEAD` must not read as shell structure;
    - backtick substitution;
    - `#` comments (masked to spaces, since a comment genuinely ends the line).

    Delimiters are masked TOO, which is the difference that matters. Blanking only the content
    leaves the quote characters behind, and `"$MAIN"` then splits into two bare `"` tokens - so a
    parser walking `git -C "$MAIN" commit` reads the option value as `"`, loses the subcommand, and
    silently concludes the statement is not a git command at all. Masking the whole region keeps it
    one token, which is exactly what the shell passes.

    Length is preserved so offsets still line up. Newlines INSIDE a masked region are replaced as
    well: a newline in a quoted commit message is not a statement separator, and leaving it would
    manufacture one.
    """
    out: list[str] = []
    index, size = 0, len(command)
    while index < size:
        char = command[index]
        if char == "\\" and index + 1 < size:
            # A backslash-NEWLINE is a line continuation: it must become whitespace, not filler,
            # or the two tokens it joins fuse into one word that no longer reads as a command.
            out.append("  " if command[index + 1] == "\n" else fill * 2)
            index += 2
        elif char in "'\"":
            # Scan for the CLOSING quote rather than the next one: inside a double-quoted region
            # `\"` is an escaped quote, and `find` would stop there, leaving the rest of a commit
            # message to be scanned as shell. Single quotes have no escape, so only `"` looks.
            cursor = index + 1
            while cursor < size:
                if char == '"' and command[cursor] == "\\" and cursor + 1 < size:
                    cursor += 2
                    continue
                if command[cursor] == char:
                    cursor += 1
                    break
                cursor += 1
            out.append(fill * (cursor - index))       # unterminated quote runs to the end
            index = cursor
        elif char == "`":
            closing = command.find("`", index + 1)
            stop = size if closing == -1 else closing + 1
            out.append(fill * (stop - index))
            index = stop
        elif command.startswith("${", index) or command.startswith("@{", index):
            closing = command.find("}", index + 2)
            stop = size if closing == -1 else closing + 1
            out.append(fill * (stop - index))
            index = stop
        elif command.startswith("$(", index):
            depth, cursor = 0, index
            while cursor < size:
                if command.startswith("$(", cursor):
                    depth += 1
                    cursor += 2
                    continue
                if command[cursor] == "(":
                    depth += 1                    # arithmetic `$(( ))` and nested subshells
                    cursor += 1
                    continue
                if command[cursor] == ")":
                    depth -= 1
                    cursor += 1
                    if depth == 0:
                        break
                    continue
                cursor += 1
            out.append(fill * (cursor - index))
            index = cursor
        elif char == "#" and (not out or out[-1].isspace()):
            while index < size and command[index] != "\n":
                out.append(" ")
                index += 1
        else:
            out.append(char)
            index += 1
    return "".join(out)
