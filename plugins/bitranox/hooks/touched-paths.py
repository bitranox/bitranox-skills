#!/usr/bin/env python3
"""PostToolUse(Write|Edit|MultiEdit) recorder: which files did this turn actually touch?

Capture is cwd-keyed (`memory_engine add --proj "<cwd>"`), so a learning ABOUT a repo you edited
from somewhere ELSE lands in the wrong store - and cross-tree the dream can never re-home it (a
`move` refuses to cross trees). Nothing in the capture path knew which repo a turn was really
working on; this hook records that EVIDENCE so the capture nudge can offer the right `--proj`.

It only appends the edited file's path to a per-session scratch file; `self_improve_signals.
subject_levels()` turns those paths into the levels that differ from cwd, and the Stop gate surfaces
them. This hook makes no routing decision and writes no memory.

The path comes from the PostToolUse event's `tool_input.file_path` and the session key from
`session_id` - both probe-verified on the live harness (`.plan/probes/probe_hook_events.py`).

Pure standard library. Reads the event JSON on stdin. ALWAYS exits 0 (a recorder must never wedge
a turn); the file is capped so a long session cannot grow it without bound.
"""
import json
import sys

import self_improve_signals as sig

_MAX_LINES = 400          # cap: plenty for a turn's distinct dirs, bounded for a long session


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return 0
    try:
        fp = (event.get("tool_input") or {}).get("file_path") or ""
        session = event.get("session_id") or ""
        if not fp or not session:
            return 0
        sig.record_touched_path(session, fp, max_lines=_MAX_LINES)
    except Exception:                                     # noqa: BLE001 - fail open, always
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
