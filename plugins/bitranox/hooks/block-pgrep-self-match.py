#!/usr/bin/env python3
"""PreToolUse(Bash) guard against the pgrep/pkill bracket-trick self-match.

A common shell-hygiene mistake when checking or killing a process by name:

    pgrep -f "[n]ginx"; echo "=== nginx running? ==="

The bracket trick `[n]ginx` is meant to stop the pattern from matching the
checker's own command line (the literal `[n]ginx` in argv is not the regex
`nginx`). But the SAME keyword printed verbatim in an echo/printf label (or a
comment) in the same command re-introduces the literal `nginx` into the shell's
argv, which defeats the trick. The shell then self-matches: `pgrep` reports a
false positive, or `pkill -f` kills its own shell mid-command (truncated output).
Over SSH it kills the ssh shell; locally it kills the running script.

This hook blocks exactly that case and nothing else, so false positives are near
zero:
  - only commands that actually call pgrep/pkill are inspected;
  - it blocks only when a de-bracketed literal (`[n]ginx` -> `nginx`) appears as a
    contiguous substring elsewhere in the command. A contiguous occurrence cannot
    come from the bracket form itself, so it is always a real label/comment leak.

Pure standard library: no jq, no shell. Reads the PreToolUse event JSON on stdin.
Exit 2 blocks the call and shows stderr to the model; every other path (including
any error) exits 0, so a broken guard never wedges a turn.
"""
import json
import re
import sys


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

    # Find bracket-trick tokens [X]rest and reconstruct the literal Xrest. If that
    # literal also appears contiguously elsewhere, the bracket trick is defeated.
    leaked = []
    for tok in re.findall(r"\[[^\]]\][A-Za-z0-9_./@:+-]+", cmd):
        literal = tok[1] + tok[3:]  # drop the '[' and the ']'
        if literal in cmd:
            leaked.append(f"{tok} -> {literal}")

    if not leaked:
        return 0

    msg = [
        "BLOCKED: pgrep/pkill bracket trick defeated by a verbatim keyword in the same command.",
        "These bracketed patterns have their literal appearing contiguously elsewhere",
        "(usually an echo/printf label or comment), so the shell's own argv self-matches",
        "and pgrep returns a false positive (or pkill kills its own shell):",
    ]
    msg += [f"  {x}" for x in leaked]
    msg += [
        "",
        "Fix: keep the searched keyword OUT of echo/printf labels and comments in the",
        "same command (use a label that does not repeat the word). Better, do not grep",
        "process names at all - use a signal that cannot match a command line:",
        "  systemctl is-active <unit> | a pidfile + kill -0 <pid> |",
        "  a listening port via ss -ltnH | grep -c :PORT | readlink /proc/<pid>/exe.",
        'If you must pgrep/pkill -f, also exclude the current shell: ... | grep -vw "$$".',
    ]
    print("\n".join(msg), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
