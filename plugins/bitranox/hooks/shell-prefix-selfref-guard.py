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
from shell_text import HEREDOC_OPEN, mask_data_regions, strip_heredoc_bodies  # noqa: F401

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

# Inside a heredoc body an opening backtick is enough: the closing one may sit on a later line,
# so the paired form above would miss a multi-line span. Only the SUBSTITUTING forms are listed.
# A bare `$VAR` also expands in a bare heredoc, but templating a value in is ordinary work, and a
# guard that fires on ordinary work gets disabled rather than obeyed.
_HEREDOC_SUBSTITUTION_RX = re.compile(r"`|\$\(")

# Inside a BARE heredoc, a backslash still escapes `, $ and \ - so `\`` is a literal backtick that
# runs nothing, and an author who wrote it already knew the delimiter was unquoted. Adjudicating
# the firings against their source transcripts, this was 9 of 12: every one of them correctly
# escaped. Blanking the escaped pairs before the search is what separates prose that WILL run from
# prose that was already made safe.
_HEREDOC_ESCAPED_RX = re.compile(r"\\[`$\\]")


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


def substitutes_inside_unquoted_heredoc(command: str) -> bool:
    """Return whether a BARE heredoc body carries a substitution the shell will run.

    Bash performs parameter expansion, command substitution and arithmetic expansion in the body
    of `<<EOF`, and NONE of it in `<<'EOF'`. So self-authored prose written through a bare heredoc
    is executed before the program ever sees it. Measured 2026-08-27: composing a memory body that
    way turned 4 KB of prose into 3.4 MB of shell output, exit 0, nothing logged.

    The argument-position half of this rule has been guarded since 5.161.0, and this position had
    not been - which is why the same fact was violated here twice. `strip_heredoc_bodies` cannot
    serve the check: it hides EVERY heredoc body from every command-scanning guard, which is right
    for a quoted delimiter and wrong for a bare one. It is left alone; 16 hooks depend on it.

    Openers are located on MASKED lines so a heredoc merely MENTIONED inside a quoted string is
    not read as opening one - priced against real history, that was the guard's only false
    positive, and it is the shape that makes a guard block its own documentation. The BODY is read
    from the original line, because masking would erase the very substitution being looked for.
    `mask_data_regions` preserves length, so the two line up; the delimiter and its quoting are
    re-read from the original, since masking a quoted delimiter would otherwise make `<<'EOF'`
    read as a bare one.

    Backslash-escaped forms are blanked before the search: a bare heredoc still honours `\\``, so
    an author who escaped had already made the text safe. That was 9 of the 12 firings this rule
    produced over 66,220 real commands, and dropping them is what takes it to every firing being
    a real one.
    """

    lines = (command or "").split("\n")
    masked = [mask_data_regions(line) for line in lines]
    index = 0
    while index < len(lines):
        found = HEREDOC_OPEN.search(masked[index])
        index += 1
        if found is None:
            continue
        opener = HEREDOC_OPEN.search(lines[index - 1], found.start())
        if opener is None:
            # Masking manufactured the opener, so there is no heredoc here and no body to skip.
            continue
        delimiter = opener.group(2)
        body: list[str] = []
        while index < len(lines) and lines[index].strip() != delimiter:
            body.append(lines[index])
            index += 1
        index += 1
        raw = _HEREDOC_ESCAPED_RX.sub("", "\n".join(body))
        if not opener.group(1) and _HEREDOC_SUBSTITUTION_RX.search(raw):
            return True
    return False


def main() -> int:
    """Block the call when a prefix assignment is referenced on its own line."""

    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if substitutes_inside_unquoted_heredoc(command):
        sys.stderr.write(
            "An UNQUOTED heredoc body carries a command substitution, so the shell will RUN it.\n"
            "Bash expands backticks and $(...) inside <<EOF and expands NOTHING inside <<'EOF'.\n"
            "Self-authored prose written through a bare heredoc is executed before the program\n"
            "sees it: composing a memory body this way once turned 4 KB of prose into 3.4 MB of\n"
            "shell output, exit 0, nothing logged.\n"
            "Fix: quote the delimiter - write <<'EOF', not <<EOF - and pass any varying path in\n"
            "through sys.argv instead of interpolating it into the text. Then READ THE RESULT\n"
            "BACK: a byte count or a tail of the composed file catches this in one line.\n"
        )
        return 2
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
