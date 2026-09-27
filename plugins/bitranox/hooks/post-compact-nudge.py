#!/usr/bin/env python3
"""PostCompact hook: after compaction, record that the consolidation pass is owed.

Compaction clears the model's CONTEXT - it does NOT delete the session transcript, which stays on
disk in full. So the pre-compaction stretch is still recoverable, but ONLY by a pass that reads the
FILE; a pass working from what the model "remembers" is working from the compacted summary and
silently loses the detail. Three deterministic pieces make that work:

  PreCompact   -> self-improve-audit.py salvages candidate learnings from the still-full transcript
                  into the per-project audit file (a hook has no model, so it can only pattern-match).
  PostCompact  -> this hook records that a nap is OWED, with the compacting session and transcript.
                  A hook cannot RUN a model pass, so the obligation is enforced by the Stop gate,
                  which refuses to stop while it stands and says why. Running the dream
                  (`dream_state.py done` -> mark_dream_done) discharges it.
  SessionStart -> fires again after a compaction (source "compact") and surfaces, then consumes,
                  the salvaged audit file.

WHY THIS HOOK PRINTS NOTHING. PostCompact is a side-effect-only event: Claude Code discards its
JSON output fields (no `additionalContext`, no `systemMessage`), writes plain stdout to the debug
log, and sends exit-0 stderr to the debug log too (code.claude.com/docs/en/hooks.md, "Decision
control": PostCompact - None; "Exit code 0"). A reminder printed here therefore reached nobody while
reading like a working nudge. The only visible route, exit 2, shows stderr to the user as an error
notice, which is the wrong reader for an instruction to the model. The model-facing text is the Stop
gate's block reason instead, and the salvage is SessionStart's to deliver - which is also why this
hook must not delete the audit file: it once did, after folding it into the discarded string, so
the channel that does deliver it found nothing.

Pure standard library. Every failure path exits 0 so a broken hook never disrupts a turn.
"""

import json
import os
import sys

from self_improve_signals import mark_nap_owed


def _read_event():
    """The event object, or {} for anything else - no stdin, invalid JSON, or a non-object value."""
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: fall back, never wedge
        return {}
    return event if isinstance(event, dict) else {}


def main():
    event = _read_event()
    proj = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:  # a hook cannot RUN the nap; record the obligation and let the Stop gate enforce it.
        # Record WHICH session compacted and where its transcript is: the flag is per-project and
        # outlives its session, so without these a nap in a LATER session clears an obligation whose
        # material it never opened.
        mark_nap_owed(proj, session_id=event.get("session_id"),
                      transcript_path=event.get("transcript_path"))
    except Exception:  # noqa: BLE001 - never disrupt a turn
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never disrupt a turn
        sys.exit(0)
