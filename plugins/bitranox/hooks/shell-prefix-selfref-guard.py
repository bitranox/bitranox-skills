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

# Shared with the other command-scanning guards: a heredoc body is DATA, and scanning it makes a
# guard fire on prose that merely mentions the footgun it guards. Re-exported so callers and tests
# can keep reaching it as `shell_prefix_selfref_guard.strip_heredoc_bodies`.
from shell_text import strip_heredoc_bodies  # noqa: F401

# Statement separators. A prefix assignment dies at the end of ITS command, so a
# reference after one of these is a deliberate use of the shell's own variable.
SEP = re.compile(r"&&|\|\||[;\n|]")

# NAME=value at a command position. The value is optional (`VAR= cmd` is legal).
ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")


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


# Flags whose argument is SELF-AUTHORED PROSE: a commit subject, a memory hook, a queue reason.
# Prose is the case where a shell metacharacter is certainly not meant as one.
TEXT_FLAGS = (
    "-m", "--message", "--hook", "--title", "--body", "--descr", "--description",
    "--why", "--what", "--reason", "--note", "--summary", "--subject",
)
# A double-quoted argument to one of those flags. Single quotes are NOT this bug: the outer shell
# does not expand them, which is why the single-quoted form is the documented workaround.
_TEXT_ARG_RX = re.compile(
    r"(?<![\w-])(?:%s)\s+\"([^\"]*)\"" % "|".join(re.escape(f) for f in TEXT_FLAGS)
)
_SUBSTITUTION_RX = re.compile(r"`[^`]*`|\$\(")


def substitutes_inside_text_arg(command: str) -> bool:
    """Return whether self-authored PROSE carries a command substitution the shell will run.

    Bash evaluates backticks and `$(...)` inside a double-quoted argument BEFORE the program sees
    the string, so the words are not stored - they are EXECUTED. Measured 2026-07-12: a memory
    `--hook` describing a fix wrapped the word shutdown in backticks; the dev box ran the real
    shutdown and survived only because polkit denied it. Every occurrence had exited zero.

    Scoped to prose-carrying flags on purpose. `$(...)` is legitimate nearly everywhere else, so a
    blanket rule would block ordinary work - and a guard that blocks ordinary work gets disabled.
    """
    return any(_SUBSTITUTION_RX.search(arg)
               for arg in _TEXT_ARG_RX.findall(strip_heredoc_bodies(command)))


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
    if substitutes_inside_text_arg(command):
        sys.stderr.write(
            "Self-authored PROSE carries a command substitution, so the shell will RUN it.\n"
            "Backticks and $(...) inside a double-quoted argument are evaluated BEFORE the\n"
            "program sees the string, so the words are not stored - they execute. A memory hook\n"
            "describing a fix once wrapped `shutdown -r now` in backticks and the dev box ran it;\n"
            "it survived only because polkit refused. Every occurrence exited 0.\n"
            "Fix: write the text to a FILE and hand the program the path (git commit -F,\n"
            "--body-file), or single-quote it - the outer shell does not expand single quotes.\n"
            "Then READ THE RESULT BACK before pushing.\n"
        )
        return 2
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
