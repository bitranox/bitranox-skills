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
  contrib_queue.py ship --match TEXT [--note WHERE] [cwd]  # this one DELIVERED
  contrib_queue.py drop --match TEXT [--reason WHY] [cwd]  # this one is wrong or stale
  contrib_queue.py shipped | rejected [cwd]
  contrib_queue.py drain [cwd]      # ONLY after the contributions actually shipped

`--target` names where it goes, e.g. `skill:meta-dream-tree` or `hook:reconcile`. Entries dedup on
(what, target), so re-noticing the same gap is not a second TODO.

An intent leaves the queue by one of two OUTCOMES, and they are not interchangeable: `ship` for
what was delivered, `drop` for what turned out wrong or stale. Both block a re-queue; only the
outcome recorded differs, and recording a delivered contribution as rejected misleads every later
reader about whether the work was done. `drain` closes the WHOLE queue at once and so fits only a
sweep where every entry shipped - to close one entry, use `ship`.

Select the entry with `--match TEXT` (unique text from its `what`/`target`) rather than `--index`:
an index comes from a listing and SHIFTS under the previous close, so closing two entries by the
indices of one listing hits the wrong second entry and destroys a contribution that was meant to
stay queued. `--match` refuses on no match or an ambiguous one instead of guessing.

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
    sh = sub.add_parser("ship", help="close ONE intent that DELIVERED - it is never re-queued")
    sh.add_argument("--index", type=int, help="1-based index from `list` (shifts after a close)")
    sh.add_argument("--match", default="", help="unique text from its what/target - order-proof")
    sh.add_argument("--note", default="", help="where it landed, e.g. a version or commit")
    sh.add_argument("proj", nargs="?", default=None)
    dp = sub.add_parser("drop", help="remove ONE disproven/stale intent - it is never re-queued")
    dp.add_argument("--index", type=int, help="1-based index from `list` (shifts after a close)")
    dp.add_argument("--match", default="", help="unique text from its what/target - order-proof")
    dp.add_argument("--reason", default="", help="why it is wrong or stale (kept in the tombstone)")
    dp.add_argument("proj", nargs="?", default=None)
    rj = sub.add_parser("rejected", help="show the dropped intents and why")
    rj.add_argument("proj", nargs="?", default=None)
    sl = sub.add_parser("shipped", help="show the intents that delivered, and where")
    sl.add_argument("proj", nargs="?", default=None)
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if not args.cmd:
        ap.print_help(sys.stderr)
        return 2
    proj = args.proj or os.getcwd()

    if args.cmd == "add":
        queued = sig.add_contribution(proj, {"what": args.what, "target": args.target,
                                             "why": args.why, "source": args.source})
        if not queued:
            # already queued, or CLOSED earlier - either way not a new TODO. Name the outcome that
            # closed it: "rejected" for work that was already DONE would send the reader to redo it.
            key = (args.what, args.target)
            closed = {(r.get("what"), r.get("target") or ""): r.get("outcome") for r in sig.read_closed(proj)}
            why = {sig.SHIPPED: "shipped earlier", sig.REJECTED: "rejected earlier"}.get(
                closed.get(key), "already queued")
            print("not queued (%s): %s" % (why, args.what))
            return 0
        print("queued: %s%s" % (args.what, " -> %s" % args.target if args.target else ""))
        return 0

    if args.cmd == "list":
        recs = sig.read_contributions(proj)
        if not recs:
            print("no pending upstream contributions for %s" % proj)
            return 0
        print("%d pending upstream contribution(s):" % len(recs))
        for i, r in enumerate(recs, 1):                 # numbered so `drop --index` can target one
            print("  %d. %s%s%s" % (i, r.get("what") or "",
                                    " -> %s" % r["target"] if r.get("target") else "",
                                    " (%s)" % r["why"] if r.get("why") else ""))
        return 0

    if args.cmd in ("drop", "ship"):
        shipping = args.cmd == "ship"
        note = args.note if shipping else args.reason
        close = sig.ship_contribution if shipping else sig.drop_contribution
        if bool(args.index) == bool(args.match):        # exactly one selector, never a guess
            print("! refused: pass EITHER --index N OR --match TEXT (--match is order-proof)",
                  file=sys.stderr)
            return 2
        try:
            rec = close(proj, args.index, note, match=args.match)
        except IndexError as exc:
            print("! refused: %s" % exc, file=sys.stderr)
            return 2
        print("%s: %s%s%s" % ("shipped" if shipping else "dropped", rec.get("what") or "",
                              " -> %s" % rec["target"] if rec.get("target") else "",
                              " (%s)" % note if note else ""))
        print("  it will NOT be re-queued by a later dream.")
        return 0

    if args.cmd in ("rejected", "shipped"):
        shipping = args.cmd == "shipped"
        recs = sig.read_shipped(proj) if shipping else sig.read_rejected(proj)
        label, field = ("shipped", "note") if shipping else ("dropped", "reason")
        if not recs:
            print("no %s contributions for %s" % (label, proj))
            return 0
        print("%d %s contribution(s):" % (len(recs), label))
        for r in recs:
            print("  - %s%s%s" % (r.get("what") or "",
                                  " -> %s" % r["target"] if r.get("target") else "",
                                  " (%s)" % r[field] if r.get(field) else ""))
        return 0

    sig.drain_contributions(proj)                       # drain
    print("drained the pending-contribution queue for %s" % proj)
    return 0


if __name__ == "__main__":
    sys.exit(main())
