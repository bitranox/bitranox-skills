#!/usr/bin/env python3
"""Cadence marker CLI for the meta-dream skill.

Thin wrapper over self_improve_signals (the shared source of truth, in the plugin's hooks dir)
so the dream's "is a consolidation due?" / "mark this dream done" / "what mode?" logic lives in
ONE place and never drifts from the SessionStart nudge that uses the same functions.

Usage (cwd defaults to the current directory):
  dream_state.py due  [cwd]               print "due" or "not-due"
  dream_state.py done [cwd]               record that a dream just completed (silences the nudge)
  dream_state.py mode [cwd]               print the dream mode: off | auto | propose
  dream_state.py saw-promotable  S [cwd]  record a dream sighting of tree-top-promotion candidate S;
                                          print its dwell count (dreams it has appeared in)
  dream_state.py should-promote  S [cwd]  print "promote" or "hold" for a model-inferred candidate S
                                          (>= 2 dreams corroborates; read-only, does NOT count)
  dream_state.py promoted        S [cwd]  clear S's dwell count after it was promoted (no re-fire)
  dream_state.py session-review  [cwd]    print the session material the dream must consolidate,
                                          READ FROM DISK: the not-yet-reviewed transcript stretch +
                                          the buffered subagent learnings + the touched-path routing
                                          evidence. Incremental (a watermark per reviewer), so an
                                          already-consumed prefix is never re-fed to the model.
  dream_state.py session-reviewed [cwd]   advance the review watermark to the current end

The session-review pair is the compaction fix: compaction clears the model's CONTEXT but NOT the
transcript file, so the pre-compaction stretch is recoverable only by reading the FILE. A dream never
receives `transcript_path`; the Stop gate records it (record_session_meta) and this looks it up by cwd.

The corroboration gate backs the docs' ">= 2 dreams" claim: it is the dwell counter in
self_improve_signals (out-of-store, so counting never bumps the store mtime). saw-promotable/
promoted are the write verbs; should-promote is the read-only decision.

Pure standard library.
"""

import os
import sys
from pathlib import Path

# self_improve_signals lives in the plugin's hooks dir: skills/meta-dream -> skills -> bitranox -> hooks
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))

import self_improve_signals as sig  # noqa: E402


_PROMOTE_CMDS = ("saw-promotable", "should-promote", "promoted")
_REVIEWER = "dream"          # the dream's own watermark; the regex audit marks separately


def _session_review(proj):
    """Print the session material to consolidate, read FROM DISK and only the unreviewed part."""
    meta = sig.read_session_meta(proj)
    text, offset = sig.unreviewed_transcript_text(proj, _REVIEWER)
    session = meta.get("session_id") or ""
    subs = sig.read_subagent_learnings(session) if session else []
    touched = sig.subject_levels(sig.read_touched_paths(session), proj) if session else []

    if not (text or subs or touched):
        print("NOTHING NEW since the last review (transcript: %s)"
              % (meta.get("transcript_path") or "unknown"))
        return 0

    if subs:
        print("== SUBAGENT LEARNINGS (not in your transcript - they die unless captured) ==")
        for r in subs:
            print("  [%s] %s" % (r.get("agent_type") or "subagent", r.get("snippet") or ""))
        print()
    if touched:
        print("== ROUTING EVIDENCE (repos this session edited that are NOT the cwd) ==")
        for lv in touched:
            print("  %s%s" % (lv["level"], "  [DIFFERENT TREE - a misfile here is unrecoverable]"
                              if lv["cross_tree"] else "  [sibling project in this tree]"))
        print()
    if text:
        print("== UNREVIEWED TRANSCRIPT (from disk; %d bytes up to offset %d) ==" % (len(text), offset))
        print(text)
    else:
        print("== UNREVIEWED TRANSCRIPT == (none - already consumed)")
    print("\n-- when done, run: dream_state.py session-reviewed %s --" % proj)
    return 0


def _session_reviewed(proj):
    """Advance the dream's watermark to the transcript's current end."""
    meta = sig.read_session_meta(proj)
    tp = meta.get("transcript_path") or ""
    if not tp:
        print("no known transcript for %s - nothing to mark" % proj)
        return 0
    try:
        size = os.path.getsize(tp)
    except OSError:
        print("transcript unreadable: %s" % tp)
        return 0
    sig.set_watermark(proj, tp, _REVIEWER, size)
    print("review watermark advanced to %d for %s" % (size, tp))
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "due"
    if cmd in _PROMOTE_CMDS:
        if len(argv) < 2:
            print("usage: dream_state.py %s <slug> [cwd]" % cmd, file=sys.stderr)
            return 2
        slug = argv[1]
        proj = argv[2] if len(argv) > 2 else os.getcwd()
        if cmd == "saw-promotable":
            print(sig.note_promotion_candidate(proj, slug))          # dwell count after this sighting
        elif cmd == "should-promote":
            dwell = sig.promotion_dwell(proj, slug)                  # read-only, does not count
            print("promote" if sig.should_promote("inferred", dwell) else "hold")
        else:                                                        # promoted
            sig.clear_promotion_candidate(proj, slug)
            print("cleared dwell for %s" % slug)
        return 0
    proj = argv[1] if len(argv) > 1 else os.getcwd()
    if cmd == "session-review":
        return _session_review(proj)
    if cmd == "session-reviewed":
        return _session_reviewed(proj)
    if cmd == "due":
        print("due" if sig.dream_due(proj) else "not-due")
    elif cmd == "done":
        sig.mark_dream_done(proj)
        print("dream marked done for %s" % proj)
    elif cmd == "mode":
        print(sig.dream_mode(proj))
    else:
        print("usage: dream_state.py [due|done|mode|saw-promotable|should-promote|promoted] ...",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
