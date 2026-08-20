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
  * a NAMED background subagent's final text is NOT returned to the main session. Only a
    SendMessage reaches it; otherwise the report sits unread in the subagent's own transcript and
    the main agent sees nothing but an idle notification.

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

Cannot block: `SubagentStart` ignores the exit code (stderr surfaces in the subagent's own
transcript, and Claude does not see it). Emits `additionalContext` and exits 0, fail-open on any
error. Pure standard library, ASCII only; launched via run-python.sh so it works on Windows too.
"""
from __future__ import annotations

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
    "2. A named or backgrounded subagent's final text is not returned to the main session. It is "
    "delivered only by SendMessage to the caller; without that the report stays in this "
    "subagent's own transcript and the main session sees an idle notification and nothing else."
)


def is_clean_room(agent_type) -> bool:
    """True when this agent type must be left with an uncontaminated context. PURE.

    Case-insensitive substring match, so `bitranox:baseline-probe` and a bare `baseline-probe`
    both count and an unknown probe-shaped name errs toward silence.
    """
    return any(marker in str(agent_type or "").lower() for marker in CLEAN_ROOM_MARKERS)


def brief_for(agent_type):
    """The text to inject for this agent type, or None to stay silent. PURE."""
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
