#!/usr/bin/env python3
"""PreToolUse(Bash) nudge: a long bare `sleep` waits on the CLOCK, not on the event.

Waiting a fixed span for something whose real duration you have not measured is how a run either
returns before the work finished or sits idle long after it did. The rule is to wait on a concrete
SIGNAL (a marker file, a status endpoint, a completion line, the worker process still existing),
or on a measured duration plus a small margin, and to stop and INVESTIGATE at roughly twice the
expected time rather than waiting longer.

A sleep INSIDE a polling loop is the opposite of this mistake - that is waiting on the signal, with
the sleep merely pacing the checks - so `until ... do sleep N; done` and friends are left alone
however long the pause. Short pauses are left alone too: a couple of seconds to let a service
settle is not a wait on an event.

NON-BLOCKING: emits additionalContext and exits 0. Fail-open on any error. ASCII only.
"""
from __future__ import annotations

import json
import re
import sys

from shell_text import is_shell_tool, strip_heredoc_bodies

# Below this a sleep is a settle pause, not a wait on an event.
LONG_SLEEP_SECONDS = 60

_SLEEP = re.compile(r"\bsleep\s+(?P<n>\d+(?:\.\d+)?)(?P<unit>[smhd])?\b")
# A sleep that PACES a poll: the loop is the wait, the sleep is just the interval.
_POLLING = re.compile(r"\b(?:until|while)\b|\bfor\s+\w+\s+in\b|\bdone\b")

_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

_NOTICE = (
    "ARBITRARY SLEEP: this waits on the CLOCK for %s seconds, not on the event. Wait on a "
    "concrete SIGNAL instead - a marker file, a status endpoint, a completion line in the log, or "
    "the worker process still existing - and check the worker is alive, because a flat derived "
    "signal cannot tell finished from aborted. If no signal exists, use a MEASURED duration plus "
    "1.3-1.5x, and stop and investigate at about 2x rather than waiting longer. A sleep pacing a "
    "polling loop is fine and is not what this is about."
)


def _seconds(match) -> float:
    return float(match.group("n")) * _UNITS.get(match.group("unit") or "s", 1)


def notice(command):
    """The nudge text when a long sleep waits on the clock outside a polling loop, else None."""
    if not command or not isinstance(command, str):
        return None
    text = strip_heredoc_bodies(command)
    if _POLLING.search(text):
        return None
    longest = 0.0
    for match in _SLEEP.finditer(text):
        longest = max(longest, _seconds(match))
    if longest < LONG_SLEEP_SECONDS:
        return None
    return _NOTICE % int(longest)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    message = notice((event.get("tool_input") or {}).get("command"))
    if message:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
