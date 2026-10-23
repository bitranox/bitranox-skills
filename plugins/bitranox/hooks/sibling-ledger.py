#!/usr/bin/env python3
"""Keep `sibling_ledger`'s record of the shell calls run in the current assistant message.

PreToolUse(Bash|PowerShell): append the call. PostToolBatch: the message's calls have all
resolved, so empty the record. UserPromptSubmit and Stop: empty it too, as backstops for a batch
that never resolved (an interrupt). The guards that judge a call against its same-message
siblings read the record through `transcript_siblings.siblings_for_event`; why the transcript
alone no longer serves is in `sibling_ledger`.

Never blocks and prints nothing: exit 0 on every path, including any error. ASCII only.
"""

import json
import sys

import sibling_ledger

_CLEARING_EVENTS = {"PostToolBatch", "UserPromptSubmit", "Stop"}


def handle(event):
    """Record or clear for one hook `event`; anything else is ignored."""
    name = event.get("hook_event_name")
    if name == "PreToolUse":
        sibling_ledger.record(event)
    elif name in _CLEARING_EVENTS:
        sibling_ledger.clear(event)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if isinstance(event, dict):
        handle(event)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a recorder must never wedge a turn
        sys.exit(0)
