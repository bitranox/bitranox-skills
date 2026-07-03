#!/usr/bin/env python3
"""Migrate the legacy `.claude-bx-selflearning/` curated stores into the central UUID store, ADDITIVELY.

For every legacy store under a root, each fact is copied into the new mount-independent layout:
  * its deterministic uuid5 identity is `uuid_store.fact_uuid(<altitude>, <slug>)` (idempotent, so a
    re-run never duplicates),
  * its body is written once to the anchor's central sharded store
    (`<anchor>/.claude-memory/facts/<shard>/<uuid>.md`),
  * a `uuid:` pointer line (title + hook + provenance + pin) is upserted into the altitude's
    `CLAUDE.local.md`.

NOTHING in the legacy store is deleted or rewritten - the two layouts coexist until the new code is
shipped, reloaded, and verified live (only THEN are the legacy stores removed, in a separate step). The
default mode is a DRY-RUN; pass `--apply` to write. Pure standard library; mtime-neutral writers.
"""
import argparse
import os
import sys
from pathlib import Path

import memory_engine as E
import self_improve_signals as sig
import uuid_store as us


def find_legacy_stores(root):
    """Every dir under `root` that OWNS a legacy `.claude-bx-selflearning/index.md` store (returns the
    owning altitude dirs - the store parents - not the store dirs). Skips backup dirs (`.bak`)."""
    out = []
    try:
        for dirpath, dirnames, _files in os.walk(root):
            if os.path.basename(dirpath) == sig.CURATED_DIRNAME:
                if (Path(dirpath) / sig.CURATED_INDEX).is_file():
                    out.append(str(Path(dirpath).parent))
                dirnames[:] = []                      # do not descend into a store
                continue
            dirnames[:] = [d for d in dirnames if ".bak-" not in d and not d.endswith(".bak")]
    except OSError:
        pass
    return out


def migrate_store(altitude, dry_run):
    """Migrate one altitude's legacy store into the central UUID store. Returns a list of
    (uuid, slug, written_bool) for every fact. `dry_run` writes nothing."""
    scope, entries, bodies = E.read_store(altitude)
    anchor = us.resolve_anchor(altitude) or Path(altitude)
    results = []
    for e in entries:
        uid = us.fact_uuid(altitude, e.slug)
        body = bodies.get(e.slug, "") if e.heavy else e.body
        written = False
        if not dry_run:
            us.put_body(str(anchor), uid, body)
            us.add_pointer(altitude, uuid=uid, title=e.title, hook=e.hook,
                           source=e.source, pin=e.pin, scope_default=scope)
            written = True
        results.append((uid, e.slug, written))
    return results


def migrate(root, dry_run):
    """Migrate every legacy store under `root`. Returns {'stores', 'facts', 'written', 'items':[...]}."""
    report = {"stores": 0, "facts": 0, "written": 0, "items": []}
    for altitude in sorted(find_legacy_stores(root)):
        report["stores"] += 1
        for uid, slug, written in migrate_store(altitude, dry_run):
            report["facts"] += 1
            report["written"] += 1 if written else 0
            report["items"].append((altitude, slug, uid, written))
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Copy legacy curated facts into the central UUID store (additive).")
    ap.add_argument("--root", required=True, help="tree to scan for legacy .claude-bx-selflearning stores")
    ap.add_argument("--apply", action="store_true", help="actually write (default: DRY-RUN, writes nothing)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    dry_run = not args.apply
    rep = migrate(args.root, dry_run=dry_run)
    tag = "DRY-RUN" if dry_run else "APPLIED"
    print("%s: %d fact(s) across %d store(s); %d body+pointer written"
          % (tag, rep["facts"], rep["stores"], rep["written"]))
    for altitude, slug, uid, written in rep["items"]:
        print("    %s %s -> %s  [%s]" % ("+" if written else ".", slug, uid, altitude))
    return 0


if __name__ == "__main__":
    sys.exit(main())
