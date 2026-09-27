#!/usr/bin/env python3
"""PostToolUse(Write|Edit|MultiEdit|NotebookEdit) recorder: which files has this session actually touched?

Capture is cwd-keyed (`memory_engine add --proj "<cwd>"`), so a learning ABOUT a repo you edited
from somewhere ELSE lands in the wrong store - and cross-tree the dream can never re-home it (a
`move` refuses to cross trees). Nothing in the capture path knew which repo a turn was really
working on; this hook records that EVIDENCE so the capture nudge can offer the right `--proj`.

It only appends the edited file's path to a per-session scratch file; `self_improve_signals.
subject_levels()` turns those paths into the levels that differ from cwd, and the Stop gate surfaces
them. This hook makes no routing decision and writes no memory.

The evidence is SESSION-cumulative, not per turn: nothing clears it between turns, so a repo edited
three turns ago is still listed. That is deliberate - a learning can be captured turns after the edit
it is about - but it means a reader of the list must not call it "this turn's" edits.

The path is `tool_input.file_path`, or `tool_input.notebook_path` for NotebookEdit, which names its
target differently. `file_path` and the session key (`session_id`) are probe-verified on the live
harness (`.plan/probes/probe_hook_events.py`); `notebook_path` is the field the sibling guards
(config-edit-guard, skill-edit-guard, store-edit-guard) already read for the same tool.

Pure standard library. Reads the event JSON on stdin. ALWAYS exits 0 (a recorder must never wedge
a turn); the file is capped so a long session cannot grow it without bound.
"""
import json
import sys

import self_improve_signals as sig

_MAX_LINES = 400          # cap: plenty for a session's distinct files, bounded for a long one


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return 0
    try:
        tool_input = event.get("tool_input") or {}
        # NotebookEdit names its target `notebook_path`; every other registered tool `file_path`.
        fp = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        session = event.get("session_id") or ""
        if not fp or not session:
            return 0
        sig.record_touched_path(session, fp, max_lines=_MAX_LINES)
    except Exception:                                     # noqa: BLE001 - fail open, always
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
