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

# A pgrep/pkill invocation up to the next shell separator, so only the flags and
# pattern belonging to THIS call are read.
_INVOCATION = re.compile(r"\b(?:pgrep|pkill)\b[^|;&\n]*")

# `-f`, alone or bundled (e.g. -af), followed by its pattern argument: a
# double-quoted, single-quoted, or bare token.
_DASH_F_PATTERN = re.compile(r"-[a-zA-Z]*f[a-zA-Z]*\s+(?:\"([^\"]*)\"|'([^']*)'|(\S+))")

_BRACKET_TOKEN = re.compile(r"\[[^\]]\][A-Za-z0-9_./@:+-]+")


def bracket_leaks(cmd):
    """Shape 1: a de-bracketed literal appearing contiguously elsewhere in the command.

    A contiguous occurrence cannot come from the bracket form itself, so it is
    always a real label/comment leak.
    """
    leaked = []
    for tok in _BRACKET_TOKEN.findall(cmd):
        literal = tok[1] + tok[3:]  # drop the '[' and the ']'
        if literal in cmd:
            leaked.append(f"{tok} -> {literal}")
    return leaked


def plain_f_patterns(cmd):
    """Shape 2: `-f` patterns that are plain literals, so the shell's argv self-matches."""
    found = []
    for call in _INVOCATION.findall(cmd):
        for m in _DASH_F_PATTERN.finditer(call):
            pattern = next((g for g in m.groups() if g is not None), "")
            if not pattern:
                continue
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

    # Fast path: only guard commands that call pgrep/pkill.
    if not re.search(r"\b(pgrep|pkill)\b", cmd):
        return 0

    # An explicit self-exclusion means the caller already handled it.
    if re.search(r"grep\s+-vw\s+[\"']?\$\$", cmd):
        return 0

    leaked = bracket_leaks(cmd)
    plain = plain_f_patterns(cmd)
    if not leaked and not plain:
        return 0

    msg = ["BLOCKED: pgrep/pkill would match the shell running this very command."]
    if plain:
        msg += [
            "",
            "PLAIN `-f` PATTERN. `-f` matches /proc/*/cmdline, and this shell's own",
            "cmdline contains the pattern literal, so it always matches itself:",
        ]
        msg += [f"  -f {p}" for p in plain]
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
