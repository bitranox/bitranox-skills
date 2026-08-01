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
