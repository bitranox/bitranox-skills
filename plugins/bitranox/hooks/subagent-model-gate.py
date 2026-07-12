#!/usr/bin/env python3
"""PreToolUse(Task|Agent) gate: subagents must carry an explicit model tier.

Dispatching a subagent with no `model` makes it inherit the session's model - usually the most
capable and most expensive tier - which silently defeats per-role model tiering.
bitranox:process-agents-subagent-driven-development ("Concrete tiers") requires pinning the tier
explicitly: `haiku` (mechanical / scan), `sonnet` (default fan-out / bounded judgment), `opus`
(deep reasoning where being wrong is costly). Reasoning EFFORT is not a per-dispatch field - it
rides the agent-type definition or a Workflow agent() call - so picking the tier (plus the right
agent type) is also how effort is chosen.

Two enforcement levels:
- Normally: WARN (additionalContext on stdout, exit 0) - some dispatches legitimately inherit
  (a `fork` always inherits by design, and sometimes the session model is genuinely right). The
  warn rides `hookSpecificOutput.additionalContext` (no `permissionDecision`), which reaches the
  model as a system-reminder without blocking the dispatch; exit-0 stderr would not reach it.
- While a PLAN EXECUTION is armed (a fresh `plan-execution` receipt written by
  `skill_receipt.py start plan-execution` - the plan-execution skills arm it at their step 0 and
  disarm with `skill_receipt.py end plan-execution` when the plan completes): DENY the dispatch
  with a reason, so no plan task runs on an unpinned model.

Contract: reads a PreToolUse event JSON on stdin. Fail-open: any parse/IO error -> exit 0 (a
broken gate must never wedge a turn). Pure standard library; launched via run-python.sh so it
works on Windows too. ASCII only.
"""
import json
import sys

import skill_receipt

SUBAGENT_TOOLS = {"Task", "Agent"}
PLAN_RECEIPT = "plan-execution"

_TIERS = (
    "Pin the tier per bitranox:process-agents-subagent-driven-development (Concrete tiers): "
    "`haiku` = mechanical / transcription / scan, `sonnet` = default fan-out and bounded judgment, "
    "`opus` = deep reasoning where being wrong is costly (architecture, synthesis, adversarial "
    "verify). Effort rides the agent type or a Workflow agent() call, not the dispatch - the tier "
    "(plus the right agent type) is how effort is chosen."
)

_WARN_MESSAGE = (
    "Subagent dispatched without an explicit `model`. " + _TIERS +
    " An omitted model inherits the session model - often the priciest - and silently defeats tiering."
)

_DENY_MESSAGE = (
    "DENIED: a plan execution is armed (fresh `plan-execution` receipt), and every dispatched "
    "subagent MUST pin `model`. " + _TIERS +
    " Re-dispatch with `model` set. When the plan is complete, disarm with "
    "`skill_receipt.py end plan-execution`."
)


def assess(tool_name, tool_input, plan_armed=False):
    """Pure: return (action, message) with action in {'deny', 'warn', None}.

    A missing/blank `model` on a non-fork subagent dispatch warns - or denies while a plan
    execution is armed. Everything else passes silently.
    """
    if tool_name not in SUBAGENT_TOOLS:
        return (None, "")
    if not isinstance(tool_input, dict):
        return (None, "")
    subagent_type = str(tool_input.get("subagent_type") or "").strip().lower()
    if subagent_type == "fork":  # a fork always inherits the parent model by design
        return (None, "")
    model = tool_input.get("model")
    if isinstance(model, str) and model.strip():
        return (None, "")  # explicitly pinned - good
    if plan_armed:
        return ("deny", _DENY_MESSAGE)
    return ("warn", _WARN_MESSAGE)


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    try:
        plan_armed = skill_receipt.is_fresh(PLAN_RECEIPT)
    except Exception:  # noqa: BLE001 - receipt trouble must not wedge a turn
        plan_armed = False
    action, message = assess(event.get("tool_name"), event.get("tool_input") or {}, plan_armed)
    if action == "deny":
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        }}) + "\n")
    elif action == "warn":
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "SUBAGENT-MODEL GATE: " + message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken gate must never wedge a turn
        sys.exit(0)
