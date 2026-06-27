#!/usr/bin/env python3
"""Cadence marker CLI for the meta-dream skill.

Thin wrapper over self_improve_signals (the shared source of truth, in the plugin's hooks dir)
so the dream's "is a consolidation due?" / "mark this dream done" / "what mode?" logic lives in
ONE place and never drifts from the SessionStart nudge that uses the same functions.

Usage (cwd defaults to the current directory):
  dream_state.py due  [cwd]   print "due" or "not-due"
  dream_state.py done [cwd]   record that a dream just completed (silences the nudge)
  dream_state.py mode [cwd]   print the dream mode: off | auto | propose

Pure standard library.
"""

import os
import sys
from pathlib import Path

# self_improve_signals lives in the plugin's hooks dir: skills/meta-dream -> skills -> bitranox -> hooks
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))

import self_improve_signals as sig  # noqa: E402


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "due"
    proj = argv[1] if len(argv) > 1 else os.getcwd()
    if cmd == "due":
        print("due" if sig.dream_due(proj) else "not-due")
    elif cmd == "done":
        sig.mark_dream_done(proj)
        print("dream marked done for %s" % proj)
    elif cmd == "mode":
        print(sig.dream_mode(proj))
    else:
        print("usage: dream_state.py [due|done|mode] [cwd]", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
