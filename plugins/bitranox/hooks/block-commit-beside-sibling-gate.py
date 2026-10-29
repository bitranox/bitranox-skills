#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard: a commit or push sent beside the gate it depends on.

Tool calls in ONE assistant message do not wait for each other's verdict. They run one after
another, but a refusal, an error or a red result in one never stops the next: each was decided
before any of them ran. So a message holding a test run AND a `git commit` commits whatever the
test said, and nobody has read what it said.

The incident, 2026-10-12: a doc edit was followed by one message with two calls, the cooldown test
module and `git add -A && git commit`. block-masked-gate-exit refused the test call (it piped
pytest into `tail`); the commit ran anyway. That was the fourth recorded miss of the written rule
"gate in the same && chain as the action, or read the gate before acting" - and none of the
earlier guards could see it, because each judges one call alone.

So this refuses a call that PUBLISHES - a `git commit`, `git push` or `gh pr create`
(`shell_text.is_gated_command`) - when an EARLIER shell call of the same message runs a recognised
gate (`shell_text.GATE_RE`, or the gate.py jig). The two allowed shapes are the fix: put the gate in
the same call, chained with `&&` so a red gate stops the commit, or send the commit in the NEXT
message, after reading the gate's real exit code.

PRICED before shipping, by replaying 131,830 recorded shell calls with their real earlier siblings
(4,663 of them commit, push or PR): 19 refusals, about one call in 7,000. All 19 were read in full,
and every one had an earlier sibling that really ran a gate (`make test`, `pytest`, `ruff check`,
`pyright`, the gate.py jig) followed by a commit nobody had checked against it; four of the 19
were found by reading the siblings back, since a heredoc edit and a commit-message write sat in the
same calls. Each costs one retry in the next message. Whether those 19 gates were red was not
measured: the shape is refused because nothing in it can tell. These counts are REPLAY-derived: a
replay shows each call every earlier sibling already on disk, which the live hook did not see
before the sibling ledger of 9.13.0 (below). They are an upper bound on what the live hook could
refuse, not a measured live rate.

A commit sent BEFORE its gate in the same message is not caught: nothing of the gate has run or
been recorded yet. Data regions are masked first, so a gate or a commit named inside a heredoc body
or a quoted string is text, not a command.

The siblings come from `transcript_siblings` (shared with block-write-after-sibling-cd), which asks
`sibling_ledger` first and the transcript only as a fallback. Live on Claude Code 2.1.309 the
transcript does not yet hold the earlier siblings when this hook runs, so a probe commit beside
`ruff --version` went through on 9.12.0 and is refused once the ledger is read (probed 2026-10-23,
both arms in a throwaway session). A file EDIT that fails is invisible to every PreToolUse hook; the
PostToolBatch hook publish-after-failed-edit-note covers that case after the fact. BLOCKING: exit 2
with the reason on stderr. Fail-open on any error. ASCII only.
"""

import json
import sys

# `runs_a_gate` lives in shell_text beside the gate vocabulary, so block-masked-gate-exit reads the
# program word the same way when it asks whether a piped element is a gate.
import shell_text
from shell_text import is_gated_command, is_shell_tool, runs_a_gate
from transcript_siblings import siblings_for_event


def verdict(command, siblings, tool_name="Bash"):
    """The earlier sibling whose gate this publishing `command` would act on unread, or None."""
    if not is_gated_command(command, tool_name):
        return None
    return next((s for s in siblings if runs_a_gate(s, tool_name)), None)


def refusal(gate):
    first = (gate.strip().splitlines() or [""])[0][:120]
    return "\n".join([
        "BLOCKED: this call publishes (commit/push/PR) in the same message as a gate whose",
        "verdict nobody has read yet.",
        "",
        "  earlier sibling (the gate): " + first,
        "",
        "Calls in one message do not wait for each other's result: a refused, failed or red gate",
        "does not stop the call after it, so this would commit whatever the gate said.",
        "",
        "Do one of these instead:",
        "  - chain them in ONE call so a red gate stops the commit:  <gate> && git commit ...",
        "  - or send the commit in the next message, after reading the gate's real exit code.",
    ])


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    tool_name = event.get("tool_name")
    if not is_shell_tool(tool_name):
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if not is_gated_command(command, tool_name):
        return 0                                    # the common case never opens the transcript
    gate = verdict(command, siblings_for_event(event) or [], tool_name)
    if gate is None:
        return 0
    return shell_text.refuse(refusal(gate))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a guard must never wedge a turn
        sys.exit(0)
