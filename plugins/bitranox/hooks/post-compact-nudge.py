#!/usr/bin/env python3
"""PostCompact hook: after compaction, nudge the model to capture/consolidate before continuing.

Compaction discards raw transcript detail. The PreCompact hook (self-improve-audit.py) already
SALVAGED candidate learnings from the still-full transcript into the per-project audit file; this
PostCompact hook injects (PostCompact can inject context the model acts on) a reminder to run
meta-dream-nap on those candidates (the quick CHAIN-ONLY consolidation - built for exactly this
moment) so nothing is lost; a due full consolidation stays meta-dream-tree's job. It surfaces and
consumes the salvaged audit.

Pure standard library. Every failure path exits 0 so a broken hook never disrupts a turn.
"""

import json
import os
import sys
from pathlib import Path

from self_improve_signals import audit_file, dream_due


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

    msg = ("Context was just compacted; the raw transcript detail is now gone. Before continuing, "
           "run bitranox:meta-dream-nap - the quick CHAIN-ONLY consolidation built for this moment "
           "(it captures uncaptured learnings first, then tidies the cwd's chain in minutes)")
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
