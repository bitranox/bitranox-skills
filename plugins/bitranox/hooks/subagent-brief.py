#!/usr/bin/env python3
"""SubagentStart hook: give a subagent the two delivery facts nothing else tells it.

A subagent gets no standing bitranox context at all today. The standing-instruction skill
(`meta-using-bitranox-skills`) opens with a SUBAGENT-STOP block telling a dispatched subagent to
skip it and just do the task, which is the right call for that skill and leaves a gap: the two
facts below are about how a subagent's OUTPUT reaches anyone, and a subagent that does not know
them produces good work that is then thrown away.

Both are recorded in the store as things that actually happened, repeatedly:

  * the harness refuses a subagent's `Write` by FILENAME - `findings_batch1.md` and `report.md`
    were refused while `notes.txt` in the same directory was written fine. A subagent that plans to
    hand back a report file discovers this only after doing the work.
  * how a NAMED subagent's final text reaches the main session depends on the build. On Claude
    Code 2.1.268 (re-measured 2026-09-11) it did not: only a SendMessage reached it, and the main
    agent saw nothing but an idle notification. On 2.1.325 (measured 2026-11-17, 3 of 3 named
    agents with no SendMessage instruction) it arrived, in the idle notification's `result` field
    or as a Subagent hand-back. An UNNAMED subagent's final text arrives in the caller's
    completion notification on both.

WHY A HOOK AND NOT PROSE. Prose in a skill only works for a subagent that loads that skill, and the
one skill every session loads is the one that tells subagents to stop reading. `SubagentStart` puts
the text at the start of the subagent's OWN conversation, which is the only channel that reaches it
regardless of what it loads. This event did not exist when the store recorded that briefing a
subagent from a hook was impossible; it is possible now.

BASELINE PROBES ARE EXCLUDED, and this is the load-bearing part of the design rather than a detail.
`bitranox:baseline-probe` exists to answer a question from its prompt alone - it is how a RED
baseline is measured. Its inertness bounds TOOLS, not CONTEXT, and the store already records that a
RED can falsely pass because the environment fed the agent the answer. A hook that injects text
into every subagent would contaminate exactly the agent whose value is an uncontaminated context,
and the failure would be silent: the probe would simply start passing.

The exclusion can only key on `agent_type`, the one identity SubagentStart carries - the event has
no prompt and no `subagent_type`. For a NAMED dispatch that field CAN hold the NAME instead of the
type: measured 2026-10-05 on CLI 2.1.289, a named teammate-style dispatch recorded
`SubagentStart:<name>`, while a named general-purpose dispatch from the main session recorded
`SubagentStart:general-purpose`. Measured 2026-09-11, a named baseline-probe's hook record read
`SubagentStart:<name>` and the probe was briefed. A named probe therefore cannot be recognised
here, and subagent-probe-capability-gate refuses to dispatch one. A probe sent to an ordinary
agent type is briefed like any other agent.
An `agent_type` that is missing, blank or not a string gets silence: all 1213 recorded subagents
carried a non-empty type, so only a malformed event reaches that branch.

Cannot block: `SubagentStart` ignores the exit code (stderr surfaces in the subagent's own
transcript, and Claude does not see it). Emits `additionalContext` and exits 0, fail-open on any
error. Pure standard library, ASCII only; launched via run-python.sh so it works on Windows too.
"""

import json
import sys

# Agent types that must receive NOTHING. Matched case-insensitively against `agent_type`, both bare
# and plugin-scoped, because a dispatch may name either form.
#
# A substring test rather than an equality test is deliberate: a future `baseline-probe-strict` or a
# differently-scoped spelling must fail CLOSED (stay clean) rather than start receiving context. The
# cost of wrongly staying silent is one subagent that has to be told twice; the cost of wrongly
# speaking is a RED baseline that passes for the wrong reason and is believed.
CLEAN_ROOM_MARKERS = ("baseline-probe", "probe-effort")

BRIEF = (
    "Two facts about how this subagent's output reaches anyone, which are properties of the "
    "harness rather than of the task:\n"
    "1. A subagent's Write is refused by FILENAME. Names that read as a deliverable - report.md, "
    "findings_batch1.md - are refused, while an ordinary name such as notes.txt in the same "
    "directory is written normally. The final TEXT returned is the reliable channel, so results "
    "belong there rather than in a file the caller is told to open.\n"
    "2. If this subagent is NAMED, whether its final text reaches the main session depends on the "
    "Claude Code build: older builds deliver a named subagent's result only by SendMessage to the "
    "caller and show the main session a bare idle notification otherwise, while newer ones carry "
    "the final text along. When the brief asks for SendMessage, use it; an unnamed subagent's "
    "final text always arrives."
)


def is_clean_room(agent_type) -> bool:
    """True when this agent type must be left with an uncontaminated context. PURE.

    Case-insensitive substring match, so `bitranox:baseline-probe` and a bare `baseline-probe`
    both count and an unknown probe-shaped name errs toward silence.
    """
    return any(marker in str(agent_type or "").lower() for marker in CLEAN_ROOM_MARKERS)


def brief_for(agent_type):
    """The text to inject for this agent type, or None to stay silent. PURE.

    An agent type that is missing, blank or not a string is silent rather than briefed: without
    one the exclusion cannot tell a probe from anything else, and briefing a probe is the mistake
    that costs a believed baseline.
    """
    if not isinstance(agent_type, str) or not agent_type.strip():
        return None
    return None if is_clean_room(agent_type) else BRIEF


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    text = brief_for(event.get("agent_type"))
    if not text:
        return 0
    json.dump({"hookSpecificOutput": {"hookEventName": "SubagentStart",
                                      "additionalContext": text}}, sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a subagent
        sys.exit(0)
