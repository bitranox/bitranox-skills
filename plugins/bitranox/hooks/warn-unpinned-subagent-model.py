#!/usr/bin/env python3
"""PreToolUse(Task|Agent) guard: WARN when a subagent is dispatched without an explicit model.

Dispatching a subagent with no `model` makes it inherit the session's model - usually the most
capable and most expensive tier (often opus) - which silently defeats per-role model tiering.
bitranox:process-agents-subagent-driven-development ("Concrete tiers") requires pinning the tier
explicitly: `haiku` (mechanical / scan), `sonnet` (default fan-out / bounded judgment), `opus`
(deep reasoning where being wrong is costly). This is a NON-BLOCKING reminder, not a block, because
some dispatches legitimately inherit: a `fork` always inherits the parent model by design, and
sometimes the session model is genuinely the right choice.

Contract: reads a PreToolUse event JSON on stdin. WARN (exit 0, stderr) when tool_name is a
subagent-dispatch tool (Task / Agent), the dispatch is not a `fork`, and `model` is absent or blank.
Every other path exits 0. Fail-open: any parse/IO error -> exit 0 (a broken guard must never wedge a
turn). Pure standard library; launched via run-python.sh so it works on Windows too. ASCII only.
"""
import json
import sys

SUBAGENT_TOOLS = {"Task", "Agent"}

_MESSAGE = (
    "Subagent dispatched without an explicit `model`. Pin the tier per "
    "bitranox:process-agents-subagent-driven-development (Concrete tiers): "
    "`haiku` = mechanical / transcription / scan, `sonnet` = default fan-out and bounded judgment, "
    "`opus` = deep reasoning where being wrong is costly (architecture, synthesis, adversarial verify). "
    "An omitted model inherits the session model - often opus, the priciest - and silently defeats tiering."
)


def assess(tool_name, tool_input):
    """Pure: return (action, message).

    action is 'warn' only when a subagent-dispatch tool is invoked, the dispatch is not a `fork`,
    and no non-blank `model` is set; otherwise (None, "").
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
    return ("warn", _MESSAGE)


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    action, message = assess(event.get("tool_name"), event.get("tool_input") or {})
    if action == "warn":
        sys.stderr.write("SUBAGENT-MODEL GUARD (warning): " + message + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        sys.exit(0)
