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

# Both spellings: POSIX `sleep 300` / `sleep 10m`, and PowerShell `Start-Sleep -Seconds 300`.
# The plugin registers this hook on a Bash|PowerShell matcher, so knowing only one of them makes
# it run on Windows and find nothing, which is as silent as never firing at all.
_SLEEP = re.compile(
    r"\b(?:start-)?sleep\s+(?:-(?P<param>seconds|milliseconds|ms|s)\s+)?"
    r"(?P<n>\d+(?:\.\d+)?)(?P<unit>[smhd])?\b",
    re.IGNORECASE,
)

# A keyword counts only at a COMMAND POSITION - start of line, or after a separator. Matching the
# bare word anywhere silenced the nudge on `sleep 300 && echo done`, which is the exact shape this
# hook exists to catch, and left `/tmp/done` looking like a loop terminator.
_DO = re.compile(r"(?:^|[;&|\n(])\s*(do)\b")
_DONE = re.compile(r"(?:^|[;&|\n(])\s*(done)\b")

# PowerShell paces a poll with a brace BLOCK instead of do/done. Applied ONLY for the PowerShell
# tool: excluding `;` from the run before the brace is not enough on its own, because an awk or jq
# program pairs a loop word with a brace and is not a loop body at all.
_BRACE_LOOP = re.compile(r"\b(?:while|until|for|foreach|do)\b[^{;\n]*\{", re.IGNORECASE)

_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
# PowerShell names the unit as a parameter instead of a suffix; -Milliseconds is not seconds.
_PARAM_SCALE = {"milliseconds": 0.001, "ms": 0.001}

_NOTICE = (
    "ARBITRARY SLEEP: this waits on the CLOCK for %s seconds, not on the event. Wait on a "
    "concrete SIGNAL instead - a marker file, a status endpoint, a completion line in the log, or "
    "the worker process still existing - and check the worker is alive, because a flat derived "
    "signal cannot tell finished from aborted. If no signal exists, use a MEASURED duration plus "
    "1.3-1.5x, and stop and investigate at about 2x rather than waiting longer. A sleep pacing a "
    "polling loop is fine and is not what this is about."
)


def _seconds(match) -> float:
    param = (match.group("param") or "").lower()
    if param in _PARAM_SCALE:
        return float(match.group("n")) * _PARAM_SCALE[param]
    return float(match.group("n")) * _UNITS.get((match.group("unit") or "s").lower(), 1)


def _loop_body_spans(text):
    """Half-open spans covered by a `do ... done` loop body, honouring nesting.

    An unterminated `do` runs to the end of the text: a sleep after it is still inside the body as
    far as anything here can tell, and exempting it errs toward silence rather than a false nudge.
    """
    marks = [(m.start(1), 1) for m in _DO.finditer(text)]
    marks += [(m.start(1), -1) for m in _DONE.finditer(text)]
    marks.sort()
    spans, depth, opened = [], 0, None
    for pos, delta in marks:
        if delta == 1:
            if depth == 0:
                opened = pos
            depth += 1
        elif depth:
            depth -= 1
            if depth == 0 and opened is not None:
                spans.append((opened, pos))
                opened = None
    if depth and opened is not None:
        spans.append((opened, len(text)))
    return spans


def _brace_body_spans(text):
    """Half-open spans covered by a PowerShell loop's brace block."""
    spans = []
    for match in _BRACE_LOOP.finditer(text):
        opened = match.end() - 1
        depth = 0
        for index in range(opened, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    spans.append((opened, index))
                    break
        else:
            spans.append((opened, len(text)))
    return spans


def notice(command, tool_name="Bash"):
    """The nudge text when a long sleep waits on the clock outside a polling loop, else None.

    `tool_name` selects the loop syntax, because a brace block is a loop BODY only in PowerShell.
    In a shell command it is an awk or jq program, and `awk '/for/ { system("sleep 300") }'` really
    does wait on the clock - exempting it would be silent, which is the failure nobody reports. An
    unknown tool gets the stricter shell reading: for a nudge, a false nudge is cheaper than a
    false silence.
    """
    if not command or not isinstance(command, str):
        return None
    text = strip_heredoc_bodies(command)
    spans = _loop_body_spans(text)
    if tool_name == "PowerShell":
        spans += _brace_body_spans(text)
    longest = 0.0
    for match in _SLEEP.finditer(text):
        if any(start <= match.start() < end for start, end in spans):
            continue  # this sleep PACES a poll: the loop is the wait, not the clock
        longest = max(longest, _seconds(match))
    if longest < LONG_SLEEP_SECONDS:
        return None
    # Not int(): a long enough literal overflows float to inf, and int(inf) raises, which the
    # top-level fail-open would turn into a silently lost nudge.
    return _NOTICE % format(longest, ".0f")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    message = notice((event.get("tool_input") or {}).get("command"),
                     event.get("tool_name") or "Bash")
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
