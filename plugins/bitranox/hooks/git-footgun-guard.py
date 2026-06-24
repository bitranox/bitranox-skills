#!/usr/bin/env python3
"""PreToolUse(Bash) guard against a known-always-broken git invocation:
`git rev-parse --short` with two or more revisions.

`--short` abbreviates a SINGLE revision; passing two or more makes git fail with
`fatal: needed a single commit` (exit 128), a confusing error that is easy to
dismiss as a transient quirk. It is deterministic: drop `--short` to print full
hashes for multiple revs, or call rev-parse once per rev. This guard blocks the
broken form before it runs and names the fix, so the error never has to be
re-diagnosed.

Pure standard library. Reads the PreToolUse event JSON on stdin. Exit 2 blocks the
call and shows stderr to the model; every other path (including any error) exits 0
so a broken guard never wedges a turn.
"""
import json
import re
import sys

# Split a command line into statements so a rev-parse in one segment is judged
# on its own operands, not tokens from a neighbouring command.
SEP = re.compile(r"&&|\|\||[;\n|]")


def broken_revparse(command: str) -> bool:
    for segment in SEP.split(command):
        toks = segment.split()
        if "git" not in toks or "rev-parse" not in toks:
            continue
        rest = toks[toks.index("rev-parse") + 1 :]
        if not any(t == "--short" or t.startswith("--short=") for t in rest):
            continue
        # Operands are the non-option tokens after rev-parse (the revisions).
        operands = [t for t in rest if not t.startswith("-")]
        if len(operands) >= 2:
            return True
    return False


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if not broken_revparse(command):
        return 0
    sys.stderr.write(
        "git rev-parse --short takes a SINGLE revision; with 2+ revs it fails "
        "`fatal: needed a single commit` (exit 128).\n"
        "Fix: drop --short to print full hashes for multiple revs, or run "
        "rev-parse once per rev. Deterministic, not a transient quirk.\n"
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
