#!/usr/bin/env python3
"""PreToolUse(Bash) guard against the pgrep/pkill self-match.

`pgrep -f` / `pkill -f` match against /proc/*/cmdline, which INCLUDES the command
line of the shell running the check. So the checker can match itself: pgrep
reports a false positive, or pkill kills its own shell mid-command (truncated
output). Over SSH it kills the ssh shell (exit 255); locally it kills the script.

Two shapes cause it, and this hook blocks both.

1. BRACKET LEAK.

       pgrep -f "[n]ginx"; echo "=== nginx running? ==="

   The bracket trick `[n]ginx` is meant to stop the pattern from matching the
   checker's own argv (the literal `[n]ginx` is not the regex `nginx`). But the
   SAME keyword printed verbatim in an echo/printf label (or a comment) in the
   same command re-introduces the literal, defeating the trick.

2. PLAIN LITERAL.

       ssh host 'pkill -f "iperf3 -s"'

   A `-f` pattern written as a plain literal ALWAYS self-matches: the shell's own
   cmdline contains that very literal. No bracket, no leak needed - the pattern
   itself is the leak.

Blocking is precise, so false positives stay near zero. Only commands that call
pgrep/pkill are inspected, and these forms are NOT blocked because they cannot
self-match or already handle it:
  - a pattern containing `$` (`pkill -f "$name"`): argv holds the UNEXPANDED text,
    so the expanded value is not in the shell's own cmdline;
  - a bracket-trick pattern whose literal does not appear elsewhere (shape 1 only
    fires on the actual leak);
  - `pgrep`/`pkill` WITHOUT `-f`: matches comm, not the full cmdline, so a shell
    named bash/sh cannot match a program-name pattern;
  - a command that already excludes the current shell (`grep -vw "$$"`).

Pure standard library: no jq, no shell. Reads the PreToolUse event JSON on stdin.
Exit 2 blocks the call and shows stderr to the model; every other path (including
any error) exits 0, so a broken guard never wedges a turn.
"""

import json
import re
import sys

from shell_text import strip_data_sink_statements

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

# `-f`, alone or bundled (e.g. -af) or in its long form (--full), followed by its pattern
# argument: a double-quoted, single-quoted, or bare token.
#
# The FLAG must start at a token boundary. Without that guard the `-` inside a hyphenated word
# matched: `nudge-detector-footguns reformat-md-tables` was read as the flag `-footguns` carrying
# the pattern `reformat-md-tables`, inventing an invocation out of two filenames. The dash RUN is
# `-{1,2}` rather than a single `-` because `--full` is a real self-matcher and is matched today;
# requiring one dash would have silently dropped it.
_DASH_F_PATTERN = re.compile(
    r"(?<![\w-])-{1,2}[a-zA-Z]*f[a-zA-Z]*\s+(?:\"([^\"]*)\"|'([^']*)'|(\S+))")

_BRACKET_TOKEN = re.compile(r"\[[^\]]\][A-Za-z0-9_./@:+-]+")

# A heredoc: `<<TAG` (optionally `<<-`, quoted tag) then its body up to a closing TAG line. The body
# is stdin DATA, never the shell's own argv, so a pgrep/pkill named in it cannot self-match.
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n[ \t]*\2\b", re.DOTALL)

# A `git commit` message argument (`-m`/`--message`, quoted or bare). git runs git, not pkill, so the
# message text cannot self-match a pgrep/pkill call; and a real pgrep pattern follows `-f`, never `-m`.
_COMMIT_MSG = re.compile(r"(?:-m|--message)(?:=|\s+)(?:\"[^\"]*\"|'[^']*'|\S+)")


def strip_data_bodies(cmd):
    """Blank out text that is DATA, not a command - heredoc bodies and commit-message args - before
    self-match scanning, so a commit that merely DISCUSSES `pkill -f` is not read as invoking it."""
    out = _HEREDOC.sub(lambda m: "<<" + m.group(2), cmd)
    out = _COMMIT_MSG.sub("-m X", out)
    return out


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
    # `haystack` drops only what the shell never puts in its own argv at all - a heredoc body and a
    # commit message. `commands` additionally blanks statements that merely PRINT or STORE their
    # argument, and is what the invocation search reads, so `echo \'pkill -f x\'` is no longer
    # mistaken for a call. The leak search deliberately keeps reading `haystack`: an echo label IS
    # the leak, so blanking it there would delete the finding rather than a false positive.
    haystack = strip_data_bodies(cmd)
    commands = strip_data_sink_statements(haystack, data.get("tool_name"))

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
