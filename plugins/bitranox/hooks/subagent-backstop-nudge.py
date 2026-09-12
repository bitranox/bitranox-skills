#!/usr/bin/env python3
"""PreToolUse(Task|Agent) nudge: at every subagent dispatch, remind the main agent to bound
the subagent with an expected-duration ceiling and arm its OWN backstop re-check.

A hook cannot set a timer, poll, or re-invoke the loop; only the main agent can re-check a
subagent (a run_in_background poll of the real target state, or ScheduleWakeup). So this hook
does the one thing a PreToolUse hook can: it injects a reminder next to the dispatch via
hookSpecificOutput.additionalContext (verified to reach the model as a system-reminder on
Claude Code 2.1.206), telling the main agent to estimate the duration and arm a bounded
backstop instead of passively waiting for the subagent to report - which a subagent stuck in a
wait-loop never does, hanging the wait forever. Operationalizes the bitranox memory
'subagent-bound-and-backstop'.

Non-blocking by design: emits additionalContext only, never a permissionDecision, so the
dispatch proceeds through normal permission handling and the sibling subagent-model-gate.

Contract: reads a PreToolUse event JSON on stdin. Fail-open: any parse/IO error -> exit 0 (a
broken hook must never wedge a turn). Pure standard library; launched via run-python.sh so it
works on Windows too. ASCII only.
"""
import json
import sys

SUBAGENT_TOOLS = {"Task", "Agent"}

# What every hook that decides "is this a probe" matches on. Kept character-identical to the copies
# in subagent-brief and subagent-probe-capability-gate, which a shared test pins: these are
# standalone hook scripts with hyphenated filenames and cannot import one another, so the constant
# is duplicated on purpose and the test is what keeps the three from drifting.
#
# It decides one thing here: the probe gate refuses a NAMED probe outright, so delivery advice
# beside that refusal is noise - and for an inert probe it asks for a tool the type does not have.
# Matched as a substring, because the refusal covers every probe-shaped type; an exact two-name set
# left the `-strict` and `probe-effort-` variants being told to call SendMessage.
CLEAN_ROOM_MARKERS = ("baseline-probe", "probe-effort")


def is_clean_room(agent_type) -> bool:
    """True when this agent type is a probe. PURE."""
    return any(marker in str(agent_type or "").lower() for marker in CLEAN_ROOM_MARKERS)

_REMINDER = (
    "Subagent dispatched. A subagent stuck in a wait-loop never reports back, whether its result "
    "is due as the tool result or in a completion notification, so arm your OWN time-bounded "
    "backstop BEFORE moving on: estimate its expected duration, then start a run_in_background "
    "poll of the subagent's real target state (or a ScheduleWakeup) with a deadline about 1.5x "
    "to 2x that estimate. Do NOT rely on the subagent's completion notification alone - passive "
    "waiting can hang forever. On timeout, investigate or take over the remaining (usually "
    "mechanical) steps yourself. Poll ground truth, not the subagent's self-report."
)

_DELIVERY_WARNING = (
    " ALSO: this dispatch is NAMED, so its final text is NOT returned to you - only an idle "
    "notification arrives. Its prompt does not mention SendMessage, so its report will sit unread "
    "in its own transcript and you will have to ping every agent for it. Add to the prompt: "
    "'deliver your result by calling SendMessage to \"main\" - your plain text is not visible to "
    "me'. And treat a bare idle notification as 'report NOT sent', never as 'done and reported'."
)


def _needs_delivery_warning(tool_input):
    """Pure: True when a NAMED dispatch of an agent able to SendMessage never mentions it.

    `name` is the delivery tell. An unnamed dispatch's final text reaches the caller in its
    completion notification; a named one's stays in its own transcript, so only SendMessage
    carries it (re-measured 2026-09-11 on Claude Code 2.1.268: the unnamed probe's reply arrived
    within 6 s, the named probe's never arrived). A prompt that already says SendMessage needs no
    repeat. A PROBE is never told to, whether or not it holds the tool: the probe gate refuses a
    named dispatch of one outright, and that refusal is the message that applies.
    """
    if not isinstance(tool_input, dict):
        return False
    if not str(tool_input.get("name") or "").strip():
        return False
    if is_clean_room(tool_input.get("subagent_type")):
        return False
    prompt = str(tool_input.get("prompt") or "")
    return "sendmessage" not in prompt.lower()


def assess(tool_name, tool_input=None):
    """Pure: return the reminder string for a subagent dispatch, else None.

    Fires on EVERY Task/Agent dispatch (including a fork - a fork can hang in a wait-loop
    too). A NAMED dispatch whose prompt never mentions SendMessage also gets the delivery
    warning appended: observed twice (2026-07 roster review, 9 of 9 silent; 2026-07-15 bmk
    review, 8 of 9 silent) that such agents finish, go idle, and deliver nothing. A tool name
    that is not a string is a malformed event, and testing it against the set would raise.
    """
    if not isinstance(tool_name, str) or tool_name not in SUBAGENT_TOOLS:
        return None
    if _needs_delivery_warning(tool_input):
        return _REMINDER + _DELIVERY_WARNING
    return _REMINDER


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    message = assess(event.get("tool_name"), event.get("tool_input"))
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
