#!/usr/bin/env python3
"""PostCompact hook: after compaction, require the consolidation pass before continuing.

Compaction clears the model's CONTEXT - it does NOT delete the session transcript, which stays on
disk in full. So the pre-compaction stretch is still recoverable, but ONLY by a pass that reads the
FILE; a pass working from what the model "remembers" is working from the compacted summary and
silently loses the detail. Two deterministic halves make that work:

  PreCompact  -> self-improve-audit.py salvages candidate learnings from the still-full transcript
                 into the per-project audit file (a hook has no model, so it can only pattern-match).
  PostCompact -> this hook injects the reminder AND records that a nap is OWED. A hook cannot RUN a
                 model pass, so the obligation is enforced by the Stop gate, which refuses to stop
                 while it stands (the same proven block the capture nudge uses). Running the dream
                 (`dream_state.py done` -> mark_dream_done) discharges it.

It also surfaces and consumes the salvaged audit.

Pure standard library. Every failure path exits 0 so a broken hook never disrupts a turn.
"""

import json
import os
import sys

from self_improve_signals import audit_file, dream_due, mark_nap_owed


def _read_event():
    try:
        return json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: fall back, never wedge
        return {}


def main():
    event = _read_event()
    proj = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    try:
        due = dream_due(proj)
    except Exception:  # noqa: BLE001
        due = False

    try:  # a hook cannot RUN the nap; record the obligation and let the Stop gate enforce it
        mark_nap_owed(proj)
    except Exception:  # noqa: BLE001 - never disrupt a turn
        pass

    msg = ("Context was just compacted. Your CONTEXT was cleared - the session transcript is NOT "
           "gone, it is still on DISK in full. Before continuing, run bitranox:meta-dream-nap - the "
           "quick CHAIN-ONLY consolidation built for this moment (it captures uncaptured learnings "
           "first, then tidies the cwd's chain in minutes). Read the pre-compaction stretch from the "
           "FILE (dream_state.py session-review), NOT from what you still remember - what you "
           "remember is the summary, and reading the file is the only way the detail survives. It is "
           "incremental: only the part no reviewer has consumed yet comes back")
    if due:
        msg += "; a FULL consolidation (bitranox:meta-dream-tree) is also due"
    msg += "."
    parts = [msg]

    try:  # surface (and consume) the candidate learnings the PreCompact hook salvaged
        af = audit_file(proj)
        if af.is_file():
            txt = af.read_text(encoding="utf-8").strip()
            if txt:
                parts.append("Salvaged candidate learnings from before compaction:\n" + txt)
            af.unlink()
    except Exception:  # noqa: BLE001 - unreadable/undeletable: skip
        pass

    out = {"hookSpecificOutput": {"hookEventName": "PostCompact",
                                  "additionalContext": "\n\n".join(parts)}}
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never disrupt a turn
        sys.exit(0)
