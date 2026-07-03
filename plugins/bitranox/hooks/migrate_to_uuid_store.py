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


def _current_legacy_uuids(altitude):
    """The uuid set the altitude's CURRENT legacy facts SHOULD have (one per live slug)."""
    _scope, entries, _bodies = E.read_store(altitude)
    return {us.fact_uuid(altitude, e.slug) for e in entries}


def sync(root, prune):
    """Make the UUID store mirror the current legacy stores: (re)write every live fact (idempotent
    migrate), and when `prune`, drop pointers whose legacy fact is gone and delete central body files
    no pointer references any more. This keeps the projection faithful after a dream deletes/merges
    facts. Returns {'facts', 'written', 'pruned', 'bodies_deleted'}."""
    mig = migrate(root, dry_run=False)
    report = {"facts": mig["facts"], "written": mig["written"], "pruned": 0, "bodies_deleted": 0}
    altitudes = sorted(find_legacy_stores(root))
    referenced = set()                                # uuids still referenced by ANY altitude pointer
    for altitude in altitudes:
        keep = _current_legacy_uuids(altitude)
        local = sig.claude_local_md_path(altitude)
        with sig.memory_lock(local):
            try:
                text = local.read_text(encoding="utf-8")
            except OSError:
                continue
            scope, pointers = us.parse_pointer_index(text)
            kept = [p for p in pointers if p.uuid in keep]
            if prune and len(kept) != len(pointers):
                report["pruned"] += len(pointers) - len(kept)
                us.write_if_changed(local, us.upsert_pointer_block(text, scope, kept))
                pointers = kept
            referenced |= {p.uuid for p in pointers}
    if prune:                                         # delete central bodies nothing references
        for altitude in altitudes:
            anchor = us.resolve_anchor(altitude) or Path(altitude)
            facts_dir = us.central_facts_dir(anchor)
            if not facts_dir.is_dir():
                continue
            for body in facts_dir.glob("*/*.md"):
                if body.stem not in referenced:
                    try:
                        body.unlink()
                        report["bodies_deleted"] += 1
                    except OSError:
                        pass
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Copy/sync legacy curated facts into the central UUID store (additive).")
    ap.add_argument("--root", required=True, help="tree to scan for legacy .claude-bx-selflearning stores")
    ap.add_argument("--apply", action="store_true", help="actually write (default: DRY-RUN, writes nothing)")
    ap.add_argument("--sync", action="store_true",
                    help="mirror the UUID store to the current legacy stores AND prune orphans (implies --apply)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if args.sync:
        rep = sync(args.root, prune=True)
        print("SYNCED: %d fact(s) written, %d orphan pointer(s) pruned, %d orphan body(ies) deleted"
              % (rep["written"], rep["pruned"], rep["bodies_deleted"]))
        return 0
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
