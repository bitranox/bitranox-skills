#!/usr/bin/env python3
"""The pending-upstream-contribution queue CLI (the intent-to-ship, made durable).

A learning that warrants a SKILL or HOOK change reaches the marketplace only if the model authors the
self-PR before the session ends. Nothing recorded the INTENT, so it died with the context: the
private fact survived in the store, the "this should become a skill change" did not. No queue, no
marker, no state - just prose in `references/upstream-propagation.md` that a model may or may not act
on, and the only deterministic checkpoint (`repo-gate.py`'s version bump) sits at the DESTINATION,
downstream of every drop point.

This is that missing state. Queue an entry the moment a learning is judged shippable; SessionStart
surfaces the queue every session (without consuming it - a TODO must outlive being read), so the
intent survives a session end and gets picked up later. Draining is explicit and happens only after
the change actually ships.

Usage (cwd defaults to the current directory):
  contrib_queue.py add --what TEXT [--target T] [--why W] [--source S] [cwd]
  contrib_queue.py list [cwd]
  contrib_queue.py drain [cwd]      # ONLY after the contributions actually shipped

`--target` names where it goes, e.g. `skill:meta-dream-tree` or `hook:reconcile`. Entries dedup on
(what, target), so re-noticing the same gap is not a second TODO.

Pure standard library.
"""
import argparse
import os
import sys
from pathlib import Path

# self_improve_signals is the shared state layer, in the plugin's hooks dir
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import self_improve_signals as sig  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pending upstream-contribution queue (durable intent).")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="queue a pending skill/hook contribution")
    a.add_argument("--what", required=True, help="the change the learning warrants")
    a.add_argument("--target", default="", help="where it goes, e.g. skill:meta-dream-tree")
    a.add_argument("--why", default="", help="the evidence/reason it is shippable")
    a.add_argument("--source", default="", help="the fact slug or session it came from")
    a.add_argument("proj", nargs="?", default=None)
    ls = sub.add_parser("list", help="show the pending contributions (does NOT consume them)")
    ls.add_argument("proj", nargs="?", default=None)
    dr = sub.add_parser("drain", help="clear the queue - only after the changes actually shipped")
    dr.add_argument("proj", nargs="?", default=None)
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if not args.cmd:
        ap.print_help(sys.stderr)
        return 2
    proj = args.proj or os.getcwd()

    if args.cmd == "add":
        sig.add_contribution(proj, {"what": args.what, "target": args.target,
                                    "why": args.why, "source": args.source})
        print("queued: %s%s" % (args.what, " -> %s" % args.target if args.target else ""))
        return 0

    if args.cmd == "list":
        recs = sig.read_contributions(proj)
        if not recs:
            print("no pending upstream contributions for %s" % proj)
            return 0
        print("%d pending upstream contribution(s):" % len(recs))
        for r in recs:
            print("  - %s%s%s" % (r.get("what") or "",
                                  " -> %s" % r["target"] if r.get("target") else "",
                                  " (%s)" % r["why"] if r.get("why") else ""))
        return 0

    sig.drain_contributions(proj)                       # drain
    print("drained the pending-contribution queue for %s" % proj)
    return 0


if __name__ == "__main__":
    sys.exit(main())
