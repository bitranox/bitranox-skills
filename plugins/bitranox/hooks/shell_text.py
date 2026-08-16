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

# The opener forms bash accepts: `<<WORD`, `<<-WORD`, `<< WORD`, `<<'WORD'`, `<<"WORD"`. The
# backreference keeps the quoting symmetric, so `<<'EOF"` is not read as a quoted delimiter.
HEREDOC_OPEN = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# Statement separators, and the three shapes that mean "a change is leaving this machine".
SEP = re.compile(r"&&|\|\||[;\n|]")
COMMIT_RE = re.compile(r"^(?:\w+=\S+\s+)*git\b(?:\s+-C\s+\S+|\s+--?\S+)*\s+commit\b")
PR_RE = re.compile(r"^(?:\w+=\S+\s+)*gh\b.*\bpr\b.*\bcreate\b")
PUSH_RE = re.compile(r"^(?:\w+=\S+\s+)*git\b(?:\s+-C\s+\S+|\s+--?\S+)*\s+push\b")


def is_gated_command(command):
    """True when a statement in `command` is a git commit, a git push, or a gh pr create.

    Match per statement, anchored at its start, so "git commit"/"git push" embedded in a quoted
    string or heredoc body does not count - only an actual command does. Over-matching is not
    harmless here: the repo gate blocks on it, and a CHANGELOG line ABOUT committing would then
    block the commit that adds it.

    It lives in this module rather than in the gate that first needed it because a second consumer
    now asks the same question for its own reason - a commit is the moment work concludes, which is
    when the decision-review nudge fires. Two copies of this regex set would drift, and the drift
    would be silent in both directions: a shape one recognises and the other does not.
    """
    for seg in SEP.split(command or ""):
        seg = seg.strip().lstrip("(").strip()
        if COMMIT_RE.match(seg) or PR_RE.match(seg) or PUSH_RE.match(seg):
            return True
    return False


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
        opener = HEREDOC_OPEN.search(lines[index])
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
    - `${...}` parameter expansion, whose braces are a word, not a brace GROUP;
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
            closing = command.find(char, index + 1)
            stop = size if closing == -1 else closing + 1  # unterminated quote runs to the end
            out.append(fill * (stop - index))
            index = stop
        elif char == "`":
            closing = command.find("`", index + 1)
            stop = size if closing == -1 else closing + 1
            out.append(fill * (stop - index))
            index = stop
        elif command.startswith("${", index):
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
