#!/usr/bin/env python3
"""PreToolUse(Bash) guard against a prefix assignment referenced on the same line.

`VAR=value cmd ... "$VAR"` never does what it looks like. A prefix assignment
binds the variable in the COMMAND's environment, but `$VAR` on the same line is
expanded by the CURRENT shell before that command runs, and the current shell has
not been assigned. The reference expands to the shell's own value - usually empty
- and the command runs with a silently missing argument, exit 0.

Measured cost: a release commit whose message had been composed correctly and
written to a file was delivered with `MSG="$(cat f)" make push MSG="$MSG"`. The
program received an empty string, committed a fallback subject, and pushed it
before anyone could see. This is the same family as writing self-authored prose
through the shell at all - the file was right, the delivery lost it.

Single quotes are NOT this bug: `FOO=bar sh -c 'echo $FOO'` leaves the expansion
to the child shell, which does have the variable. Only a reference the OUTER
shell expands (unquoted or double-quoted) is flagged.

Pure standard library. Reads the PreToolUse event JSON on stdin. Exit 2 blocks the
call and shows stderr to the model; every other path (including any error) exits 0
so a broken guard never wedges a turn.
"""

from __future__ import annotations

import json
import re
import sys

# Statement separators. A prefix assignment dies at the end of ITS command, so a
# reference after one of these is a deliberate use of the shell's own variable.
SEP = re.compile(r"&&|\|\||[;\n|]")

# A heredoc BODY is data, not a command. Without this the guard fires on prose
# that merely MENTIONS the pattern, which would block documenting the footgun it
# guards - a failure this repo has shipped before.
HEREDOC_OPEN = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# NAME=value at a command position. The value is optional (`VAR= cmd` is legal).
ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")


def strip_heredoc_bodies(command: str) -> str:
    """Drop heredoc bodies, keeping the command lines around them."""

    out: list[str] = []
    lines = command.split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        out.append(line)
        opener = HEREDOC_OPEN.search(line)
        index += 1
        if not opener:
            continue
        delimiter = opener.group(2)
        while index < len(lines) and lines[index].strip() != delimiter:
            index += 1
        index += 1  # drop the terminator line itself
    return "\n".join(out)


def strip_single_quoted(segment: str) -> str:
    """Blank out single-quoted spans, which the outer shell never expands."""

    return re.sub(r"'[^']*'", "''", segment)


def _prefix_names(segment: str) -> list[str]:
    """Return the variables assigned as a PREFIX to this segment's command.

    Only leading `NAME=...` tokens count. A `[ "$X" = "y" ]` test is not a prefix
    assignment, and neither is an `export` (its variable outlives the command,
    so referencing it later is correct).
    """

    names: list[str] = []
    for token in segment.split():
        match = ASSIGNMENT.match(token)
        if not match:
            break
        names.append(match.group(1))
    return names


def self_referencing_prefix(command: str) -> bool:
    """Return whether any segment references a variable it assigns as a prefix."""

    for segment in SEP.split(strip_heredoc_bodies(command)):
        names = _prefix_names(segment)
        if not names:
            continue
        # Everything after the prefix tokens is where a reference would sit.
        rest = segment.split(None, len(names))[len(names) :]
        expandable = strip_single_quoted(" ".join(rest))
        for name in names:
            if re.search(r"\$\{?" + re.escape(name) + r"\}?(?![A-Za-z0-9_])", expandable):
                return True
    return False


def main() -> int:
    """Block the call when a prefix assignment is referenced on its own line."""

    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if not self_referencing_prefix(command):
        return 0
    sys.stderr.write(
        "A prefix assignment is referenced on the same command line, so it expands EMPTY.\n"
        'VAR=value cmd "$VAR" binds VAR in the command\'s environment, but the CURRENT shell\n'
        "expands $VAR first and has no such variable - the program gets an empty argument and\n"
        "exits 0. This shipped a release commit with a fallback subject once already.\n"
        'Fix: assign first, then use it - export VAR="$(cat f)"; cmd "$VAR" - or substitute\n'
        'directly at the use site: cmd MSG="$(cat f)". Then READ THE RESULT BACK.\n'
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
