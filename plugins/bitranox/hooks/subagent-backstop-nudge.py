#!/usr/bin/env python3
"""PreToolUse(Task|Agent) nudge: at every subagent dispatch, remind the main agent to bound
the subagent with an expected-duration ceiling and arm its OWN backstop re-check.

A hook cannot set a timer, poll, or re-invoke the loop; only the main agent can re-check a
subagent (a run_in_background poll of the real target state, or ScheduleWakeup). So this hook
does the one thing a PreToolUse hook can: it injects a reminder next to the dispatch via
hookSpecificOutput.additionalContext (verified to reach the model as a system-reminder on
Claude Code 2.1.206), telling the main agent to estimate the duration and arm a bounded
backstop instead of passively waiting on the subagent's completion notification - which a
subagent stuck in a wait-loop may never fire, hanging the wait forever. Operationalizes the
bitranox memory 'subagent-bound-and-backstop'.

Non-blocking by design: emits additionalContext only, never a permissionDecision, so the
dispatch proceeds through normal permission handling and the sibling subagent-model-gate.

Contract: reads a PreToolUse event JSON on stdin. Fail-open: any parse/IO error -> exit 0 (a
broken hook must never wedge a turn). Pure standard library; launched via run-python.sh so it
works on Windows too. ASCII only.
"""
import json
import sys

SUBAGENT_TOOLS = {"Task", "Agent"}

_REMINDER = (
    "Subagent dispatched. If this subagent runs in the BACKGROUND (named, detached, "
    "isolation=remote/worktree) rather than blocking until it returns, arm your OWN "
    "time-bounded backstop BEFORE moving on: estimate its expected duration, then start a "
    "run_in_background poll of the subagent's real target state (or a ScheduleWakeup) with a "
    "deadline about 1.5x to 2x that estimate. Do NOT rely on the subagent's completion "
    "notification alone - a subagent stuck in a wait-loop may never fire it, so passive "
    "waiting can hang forever. On timeout, investigate or take over the remaining (usually "
    "mechanical) steps yourself. Poll ground truth, not the subagent's self-report."
)

_DELIVERY_WARNING = (
    " ALSO: this dispatch is NAMED, so it runs in the background and its final text is NOT "
    "returned to you - only an idle/completion notification arrives. Its prompt does not "
    "mention SendMessage, so its report will sit unread in its own transcript and you will "
    "have to ping every agent for it. Add to the prompt: 'deliver your result by calling "
    "SendMessage to \"main\" - your plain text is not visible to me'. And treat a bare idle "
    "notification as 'report NOT sent', never as 'done and reported'."
)


def _needs_delivery_warning(tool_input):
    """Pure: True when a NAMED dispatch's prompt never mentions SendMessage.

    `name` is the background tell: a named agent is addressable via the mailbox and its final
    message is not returned as the tool result, whereas an unnamed dispatch blocks and does
    return it - so warning on an unnamed one would be a false positive. If the prompt already
    says SendMessage the instruction is present and repeating it is noise.
    """
    if not isinstance(tool_input, dict):
        return False
    if not (tool_input.get("name") or ""):
        return False
    prompt = str(tool_input.get("prompt") or "")
    return "sendmessage" not in prompt.lower()


def assess(tool_name, tool_input=None):
    """Pure: return the reminder string for a subagent dispatch, else None.

    Fires on EVERY Task/Agent dispatch (including a fork - a fork can hang in a wait-loop
    too). A NAMED dispatch whose prompt never mentions SendMessage also gets the delivery
    warning appended: observed twice (2026-07 roster review, 9 of 9 silent; 2026-07-15 bmk
    review, 8 of 9 silent) that such agents finish, go idle, and deliver nothing.
    """
    if tool_name not in SUBAGENT_TOOLS:
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
