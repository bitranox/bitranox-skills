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
