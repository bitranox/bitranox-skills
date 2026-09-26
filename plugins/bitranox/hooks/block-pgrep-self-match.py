#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard against the pgrep/pkill self-match.

`pgrep -f` / `pkill -f` match against /proc/*/cmdline, which INCLUDES the command
line of the shell running the check. So the checker can match itself: pgrep
reports a false positive, or pkill kills its own shell mid-command (truncated
output). Over SSH it kills the ssh shell (exit 255); locally it kills the script.

Two shapes cause it, and this hook blocks both. Both are read only inside a
`pgrep`/`pkill` call that carries `-f` (alone or bundled, as in `-af`) or `--full`.

1. BRACKET LEAK.

       pgrep -f "[n]ginx"; echo "=== nginx running? ==="

   The bracket trick `[n]ginx` is meant to stop the pattern from matching the
   checker's own argv (the literal `[n]ginx` is not the regex `nginx`). But the
   SAME keyword appearing verbatim anywhere else in the command - an echo/printf
   label, a comment, a commit message, a heredoc body - re-introduces the literal,
   because the whole command string is the shell's own cmdline.

2. PLAIN LITERAL.

       ssh host 'pkill -f "iperf3 -s"'

   A `-f` pattern written as a plain literal ALWAYS self-matches: the shell's own
   cmdline contains that very literal. No bracket, no leak needed - the pattern
   itself is the leak.

A call is looked for only in text the shell will EXECUTE: heredoc bodies, `#`
comments, plain commit-message text, and the operands of echo/printf and the other
sinks `shell_text.strip_data_sink_statements` lists are blanked first. A `$(...)`
or backtick substitution inside a message still runs, so it is kept.

These forms are NOT blocked because they cannot self-match or already handle it:
  - a pattern containing `$` (`pkill -f "$name"`): argv holds the UNEXPANDED text,
    so the expanded value is not in the shell's own cmdline;
  - a bracket-trick pattern whose literal does not appear elsewhere (shape 1 only
    fires on the actual leak);
  - `pgrep`/`pkill` WITHOUT `-f`/`--full`, bracketed or not: matches comm, not the
    full cmdline, so a shell named bash/sh cannot match a program-name pattern.
    `-F`/`--pidfile` and `-L`/`--logpidfile` are not `-f` either;
  - a command that already excludes the current shell (`grep -vw "$$"`).

A pgrep/pkill named inside a quoted argument of a program NOT on that sink list -
`grep -rn "pkill -f x"` - still reads as a call; bracket its first letter to pass.

Pure standard library: no jq, no shell. Reads the PreToolUse event JSON on stdin.
Exit 2 blocks the call and shows stderr to the model; every other path (including
any error) exits 0, so a broken guard never wedges a turn.
"""

import json
import re
import sys

from shell_text import (
    mask_data_regions,
    strip_data_sink_statements,
    strip_heredoc_bodies,
)

# A pgrep/pkill invocation up to the next shell separator, so only the flags and
# pattern belonging to THIS call are read.
#
# The program name must be a whole TOKEN, not a substring. `\b` is not that test: a hyphen is a
# word boundary, so `\bpgrep\b` matched the FILENAME `block-pgrep-self-match` and the guard then
# read the rest of the line as that call's arguments. A leading `/` is allowed because
# `/usr/bin/pgrep` is a real invocation; a trailing `-`, `.` or word character is not, because
# `pgrep-self-match` and `pkill-notes.md` name files, not programs.
_PROGRAM = r"(?<![\w-])(?:pgrep|pkill)(?![\w.-])"
_INVOCATION = re.compile(_PROGRAM + r"[^|;&\n]*")

# `-f`, alone or bundled (e.g. -af), or its exact long form `--full`.
#
# The FLAG must start at a token boundary. Without that guard the `-` inside a hyphenated word
# matched: `nudge-detector-footguns reformat-md-tables` was read as the flag `-footguns` carrying
# the pattern `reformat-md-tables`, inventing an invocation out of two filenames.
#
# The long form is spelled out rather than "any long option containing an f": that reading took
# `--pidfile` and `--logpidfile` for `-f`, and both read PIDs from a file and match no command line.
# A bundle is letters only, and pgrep's only lowercase-f short option is -f itself.
_DASH_F_FLAG = r"(?<![\w-])(?:-[a-zA-Z]*f[a-zA-Z]*|--full)"
_HAS_DASH_F = re.compile(_DASH_F_FLAG + r"(?=\s|$)")

# The flag followed by its pattern argument: a double-quoted, single-quoted, or bare token.
_DASH_F_PATTERN = re.compile(_DASH_F_FLAG + r"\s+(?:\"([^\"]*)\"|'([^']*)'|(\S+))")

_BRACKET_TOKEN = re.compile(r"\[[^\]]\][A-Za-z0-9_./@:+-]+")

# A `git commit` message argument (`-m`/`--message`, quoted or bare). Its TEXT is stored, never run.
# Kept beside the shared sink stripper because that one stops at `git -C <dir> commit` - the `-C`
# value is not a flag, so the statement is not recognised as a commit there.
_COMMIT_MSG = re.compile(r"(?:-m|--message)(?:=|\s+)(?:\"[^\"]*\"|'[^']*'|\S+)")

# `$(` and a backtick RUN what they enclose, even inside a double-quoted message, so a message that
# carries one is left for the invocation search: `git commit -m "$(pgrep -f x | wc -l) up"` runs a
# real pgrep. A substitution inside SINGLE quotes runs nothing and is kept too, which errs toward a
# visible false block rather than a silent miss.
_RUNS_SUBSTITUTION = re.compile(r"\$\(|`")


def _blank_comments(text, tool_name):
    """`text` with every `#` comment turned into spaces, length preserved.

    `mask_data_regions` already decides which `#` starts a comment (not one inside quotes, not one
    mid-word) and masks exactly those to SPACES, while everything else it masks becomes filler. So
    a space in the mask where the text has none is a comment character, and nothing else changes.
    """
    masked = mask_data_regions(text, tool_name=tool_name or "Bash")
    return "".join(" " if mask == " " else char for char, mask in zip(text, masked))


def strip_data_bodies(cmd, tool_name=None):
    """Remove text the shell will not EXECUTE - heredoc bodies, comments, plain commit messages - so a
    command that merely DISCUSSES `pkill -f` is not read as invoking it.

    Heredoc bodies go through the shared `strip_heredoc_bodies`, which ends a body only at a line that
    IS the delimiter, as bash does; a body line merely starting with the tag stays body.
    """
    out = strip_heredoc_bodies(cmd)
    out = _blank_comments(out, tool_name)
    return _COMMIT_MSG.sub(
        lambda m: m.group(0) if _RUNS_SUBSTITUTION.search(m.group(0)) else "-m X", out)


def bracket_leaks(cmd, haystack=None):
    """Shape 1: a de-bracketed literal appearing contiguously elsewhere in the command.

    A contiguous occurrence cannot come from the bracket form itself, so it is
    always a real label/comment leak.

    TWO texts, and they must not be the same one. `cmd` is where INVOCATIONS are read, so it may
    have inert statements blanked - a pgrep merely named inside an `echo` is not a call. `haystack`
    is where the LEAKED LITERAL is searched for, and there the echo must survive, because an echo
    label is precisely what re-introduces the literal into the shell's own argv, which is what
    `pgrep -f` matches. Blanking it in both places deletes the finding: measured, it took down
    `pgrep -f "[n]ginx"; echo "=== nginx running? ==="`, this hook's own motivating case.

    Defaulting `haystack` to `cmd` keeps the single-argument form meaningful for a caller that has
    only one text.
    """
    haystack = cmd if haystack is None else haystack
    # Only patterns belonging to a real pgrep/pkill invocation can self-match. Scanning the whole
    # command reported ANOTHER command's bracket trick as a leak - `grep "[s]shd"` is grep's own
    # search pattern, and the bracket form there is correct usage, not a footgun.
    leaked = []
    for call in _INVOCATION.findall(cmd):
        # Without -f/--full the call matches comm, the program name, never a command line, so no
        # literal elsewhere in the command can make it match the shell.
        if not _HAS_DASH_F.search(call):
            continue
        for tok in _BRACKET_TOKEN.findall(call):
            literal = tok[1] + tok[3:]  # drop the '[' and the ']'
            if literal in haystack:
                entry = f"{tok} -> {literal}"
                if entry not in leaked:
                    leaked.append(entry)
    return leaked


def plain_f_patterns(cmd):
    """Shape 2: `-f` patterns that are plain literals, so the shell's argv self-matches."""
    found = []
    for call in _INVOCATION.findall(cmd):
        for m in _DASH_F_PATTERN.finditer(call):
            pattern = next((g for g in m.groups() if g is not None), "")
            # An EMPTY pattern is not "no pattern" - it is the worst one there is, matching every
            # command line on the box including this shell's. The regex requires one of its three
            # alternatives to match, so a match always has exactly one non-None group and the ""
            # default is unreachable; the old `if not pattern: continue` therefore skipped nothing
            # BUT the explicitly-empty quoted form. A `-f` with no pattern at all does not match
            # the regex in the first place, so it never reaches here.
            if "$" in pattern:
                continue  # variable: argv holds the unexpanded text, cannot self-match
            if _BRACKET_TOKEN.search(pattern):
                continue  # bracket trick: shape 1 owns the leak case
            found.append(pattern)
    return found


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return 0

    # Two views of the command, because the two halves of this guard ask different questions.
    #
    # `haystack` is where a leaked literal is searched for, and it is the RAW command: the shell is
    # started with the whole command string, heredoc bodies, comments and commit messages included,
    # so all of it is in the cmdline `pgrep -f` matches. `commands` is what the invocation search
    # reads, and it keeps only what EXECUTES, so `echo \'pkill -f x\'` is not mistaken for a call.
    tool_name = data.get("tool_name")
    haystack = cmd
    commands = strip_data_sink_statements(strip_data_bodies(cmd, tool_name), tool_name)

    # Fast path: only guard commands that call pgrep/pkill.
    if not re.search(_PROGRAM, commands):
        return 0

    # An explicit self-exclusion means the caller already handled it.
    if re.search(r"grep\s+-vw\s+[\"']?\$\$", commands):
        return 0

    leaked = bracket_leaks(commands, haystack)
    plain = plain_f_patterns(commands)
    if not leaked and not plain:
        return 0

    msg = ["BLOCKED: pgrep/pkill would match the shell running this very command."]
    if plain:
        msg += [
            "",
            "PLAIN `-f` PATTERN. `-f` matches /proc/*/cmdline, and this shell's own",
            "cmdline contains the pattern literal, so it always matches itself:",
        ]
        msg += [f"  -f {p}" if p else
                '  -f ""   <- EMPTY pattern: matches EVERY process, including this shell'
                for p in plain]
    if leaked:
        msg += [
            "",
            "BRACKET TRICK DEFEATED by the same literal appearing contiguously elsewhere",
            "(usually an echo/printf label or comment), so the shell's own argv",
            "self-matches and pgrep returns a false positive (or pkill kills its shell):",
        ]
        msg += [f"  {x}" for x in leaked]
    msg += [
        "",
        "Fix, best first:",
        "  - do not match on a command line at all - use a signal that cannot:",
        "    systemctl is-active <unit> | a pidfile + kill -0 <pid> |",
        "    a listening port via ss -ltnH | grep -c :PORT | readlink /proc/<pid>/exe;",
        "  - kill by PID, or use `pkill -x <name>` / `pgrep -x <name>` (matches comm,",
        "    not the full cmdline, so this shell cannot match);",
        "  - if you must use -f: bracket the first char ([n]ginx) AND keep that keyword",
        '    out of every echo/printf label in the same command; or add | grep -vw "$$".',
    ]
    print("\n".join(msg), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
