#!/usr/bin/env python3
"""One-shot backfill: wrap bare-prose fact bodies in the native memory-entry frame.

The 2026-07-05 probes measured that a fact body matching the GENUINE memory-entry shape
(frontmatter with name/description/metadata.type) gets APPLIED mid-reasoning far more reliably
than bare prose - the model discounts bodies that do not look like real memory entries. The
engine now frames new captures (`memory_engine._framed_body`); this tool retrofits the frame
onto every existing body across the given trees. The existing prose is NEVER touched - the frame
is prepended verbatim (frontmatter derives from the pointer line: slug, hook, type prefix).

  * DRY-RUN (default): report per tree which bodies would be framed / are already framed /
    are missing. Writes nothing.
  * --apply: frame them (mtime-neutral writer; a re-run finds nothing to do).

Pure standard library; ASCII output.
"""
import argparse
import sys
from pathlib import Path

import memory_engine as me
import migrate_to_slug_store as ms
import uuid_store as us


def backfill(roots, apply=False):
    """Frame every bare body reachable from `roots`. Returns a report dict."""
    report = {"files": 0, "framed": 0, "already": 0, "missing": 0, "items": []}
    seen = set()
    for root in roots:
        for local in ms.find_pointer_files(root):
            report["files"] += 1
            level = local.parent
            anchor = us.resolve_anchor(str(level)) or level
            _scope, pointers = us.parse_pointer_index(local.read_text(encoding="utf-8"))
            for p in pointers:
                if p.legacy:
                    continue                          # unmigrated line: the migration tool owns it
                bp = us.body_path(anchor, p.slug)
                if str(bp) in seen:
                    continue                          # one body may be pointed at from many levels
                seen.add(str(bp))
                try:
                    body = bp.read_text(encoding="utf-8")
                except OSError:
                    report["missing"] += 1
                    report["items"].append(("MISSING", p.slug, str(level)))
                    continue
                if body.lstrip().startswith("---"):
                    report["already"] += 1
                    continue
                report["framed"] += 1
                report["items"].append(("FRAME", p.slug, str(level)))
                if apply:
                    us.write_if_changed(bp, me._framed_body(p.slug, p.hook, None, body).rstrip("\n") + "\n")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Frame bare fact bodies as native memory entries.")
    ap.add_argument("--root", action="append", required=True, dest="roots",
                    help="tree root(s) to scan (repeatable)")
    ap.add_argument("--apply", action="store_true", help="write (default: DRY-RUN, writes nothing)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    rep = backfill(args.roots, apply=args.apply)
    tag = "APPLIED" if args.apply else "DRY-RUN"
    print("%s: %d pointer file(s); %d body(ies) framed; %d already framed; %d missing"
          % (tag, rep["files"], rep["framed"], rep["already"], rep["missing"]))
    for kind, slug, level in rep["items"]:
        print("    %s %s [%s]" % (kind, slug, level))
    return 0


if __name__ == "__main__":
    sys.exit(main())
