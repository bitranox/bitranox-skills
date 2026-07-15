#!/usr/bin/env python3
"""PreToolUse(Bash) guard against claiming success on a gate whose exit status a pipe ate.

The mistake, seen twice in one session on a rule that was already written down twice:

    cargo fmt -- --check 2>&1 | head -20 && echo "FMT-OK"
    cargo clippy -- -D warnings 2>&1 | grep -E "^error" ; git add -A && git commit -m ...

A pipeline's exit status is its LAST element's. Piping a gate into head/grep/tail
throws the gate's status away: `head` succeeds, so the `&&` fires and the `;`
sequences on regardless. The result is a printed "OK" while the gate was red, or a
commit of a red state - and the output scrolling past looks like it was checked.

This blocks exactly that shape and nothing else:
  - the command must run a recognised GATE (cargo/pytest/ruff/pyright/... );
  - that gate must sit in a pipeline where it is NOT the last element, so its
    status is masked;
  - and a LATER statement must claim success (an OK-ish echo) or commit/push.

A pipeline whose status is handled correctly is never blocked: `set -o pipefail`
and any `PIPESTATUS` reference are honoured as the fix and exit clean, as does
running the gate bare (no pipe) or ending the pipeline with the gate itself.

Pure standard library: no jq, no shell. Reads the PreToolUse event JSON on stdin.
Exit 2 blocks the call and shows stderr to the model; every other path (including
any error) exits 0, so a broken guard never wedges a turn.
"""

import json
import re
import sys

# Commands whose exit status is a quality verdict worth protecting.
GATE = re.compile(
    r"\b(?:"
    r"cargo\s+(?:fmt|clippy|test|build|check|xtask)"
    r"|pytest|ruff|pyright|mypy|tsc|bandit"
    r"|go\s+(?:test|vet)"
    r"|npm\s+(?:run\s+)?(?:test|lint)"
    r"|dotnet\s+test"
    r"|make\s+\S*(?:test|check|lint)"
    r")\b"
)

# Filters that swallow the upstream status by becoming the pipeline's exit code.
FILTER = re.compile(r"^\s*(?:head|tail|grep|egrep|wc|cut|awk|sed|sort|uniq|tee)\b")

# Statements that assert the gate passed, or act as though it did.
CONSUMER = re.compile(
    r"\bgit\s+(?:commit|push|tag)\b"
    r"|\becho\b[^|;&]*\b(?:OK|PASS|PASSED|GREEN|SUCCESS|CLEAN|ALL\s+GOOD)\b",
    re.IGNORECASE,
)

# The correct handlings - if any is present the author is not making this mistake.
HANDLED = re.compile(r"pipefail|PIPESTATUS")

# Split into statements on ; && || and newlines, keeping it simple and syntactic.
SPLIT = re.compile(r"\s*(?:;|&&|\|\||\n)\s*")


def masks_a_gate(statement: str) -> bool:
    """True when a gate runs in this pipeline but is not what sets its status."""
    if "|" not in statement:
        return False
    # Split on a single '|' that is not part of '||' (already handled by SPLIT).
    elements = [e for e in statement.split("|") if e.strip()]
    if len(elements) < 2:
        return False
    if not GATE.search(statement):
        return False
    # If the gate IS the last element, the pipeline's status is the gate's.
    if GATE.search(elements[-1]):
        return False
    # Only a swallowing filter actually masks it.
    return any(FILTER.match(e) for e in elements[1:])


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return 0

    # Fast path: nothing to protect if no gate runs here.
    if not GATE.search(cmd):
        return 0
    # The author already handles the pipe's status correctly.
    if HANDLED.search(cmd):
        return 0

    statements = SPLIT.split(cmd)
    masked_at = None
    for i, st in enumerate(statements):
        if masked_at is None:
            if masks_a_gate(st):
                masked_at = i
            continue
        if CONSUMER.search(st):
            gate = GATE.search(statements[masked_at])
            msg = [
                "BLOCKED: this claims success on a gate whose exit status the pipe threw away.",
                "",
                f"  gate      : {gate.group(0) if gate else '(gate)'}",
                f"  piped into: {statements[masked_at].strip()[:100]}",
                f"  then      : {st.strip()[:100]}",
                "",
                "A pipeline exits with its LAST element's status, so head/grep/tail succeed even",
                "when the gate failed - the && fires, the ; sequences on, and you print OK or",
                "commit a red state while the real failure scrolls past.",
                "",
                "Fix it one of these ways:",
                "  - run the gate bare and let it set the status:   <gate> || exit 1",
                "  - keep the pipe but check the gate:              ${PIPESTATUS[0]}",
                "  - make the pipe propagate:                       set -o pipefail",
                "  - redirect to a file, then grep it separately:   <gate> > out.log 2>&1 || { grep ... out.log; exit 1; }",
            ]
            print("\n".join(msg), file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
