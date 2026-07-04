#!/usr/bin/env python3
"""Migrate the legacy `.claude-bx-selflearning/` curated stores into the central UUID store.

The engine is now UUID-native, so this one-shot tool carries its OWN reader for the retired legacy
format (`index.md` scope + `- [Title](facts/<slug>.md|#slug) - hook <!-- bx:src=.. bx:pin -->` lines,
tiny bodies inlined, heavy bodies in `facts/<slug>.md`). For every legacy fact it writes:
  * the deterministic uuid5 identity `uuid_store.fact_uuid(<altitude>, <slug>)` (idempotent),
  * its body once to `<anchor>/.claude-memory/facts/<shard>/<uuid>.md`,
  * a `uuid:` pointer line carrying the REAL legacy slug as `bx:slug=` into the altitude's
    `CLAUDE.local.md`.

NOTHING in the legacy store is deleted or rewritten - the two coexist until the cutover is verified live
and the legacy stores are removed in a separate, gated step. `--sync` additionally prunes pointers whose
legacy fact is gone + central bodies nothing references. Default is a DRY-RUN; `--apply` writes. Pure
standard library; mtime-neutral writers.
"""
import argparse
import os
import re
import sys
from pathlib import Path

import self_improve_signals as sig
import uuid_store as us

# legacy index.md entry line: `- [Title](facts/slug.md|#slug) - hook <!-- bx:src=a,b bx:pin -->`
_LEGACY_ENTRY = re.compile(r"^- \[(?P<title>[^\]]*)\]\((?P<target>[^)]+)\) - (?P<hook>.*?)"
                           r"(?:\s*<!--\s*(?P<meta>bx:[^>]*?)\s*-->)?\s*$")


def _parse_legacy_meta(meta):
    source, pin = set(), False
    for tok in (meta or "").split():
        if tok == "bx:pin":
            pin = True
        elif tok.startswith("bx:src="):
            source |= {s for s in tok[len("bx:src="):].split(",") if s}
    return source, pin


def read_legacy_store(store_dir):
    """Parse a legacy `.claude-bx-selflearning/` store dir -> (scope, [fact dict]). Each fact:
    {slug, title, hook, body, source, pin}. Tiny bodies are inlined under an `(#slug)` entry; heavy
    bodies live in `facts/<slug>.md`. Missing store -> ("", [])."""
    store = Path(store_dir)
    try:
        text = (store / sig.CURATED_INDEX).read_text(encoding="utf-8")
    except OSError:
        return "", []
    scope = sig.read_scope_block(text) or ""
    facts, cur = [], None
    for raw in text.splitlines():
        m = _LEGACY_ENTRY.match(raw)
        if m:
            source, pin = _parse_legacy_meta(m.group("meta"))
            target = m.group("target")
            heavy = target.endswith(".md")
            slug = target.rsplit("/", 1)[-1][:-3] if heavy else target.lstrip("#")
            cur = {"slug": slug, "title": m.group("title"), "hook": m.group("hook"),
                   "body": "", "source": source, "pin": pin, "heavy": heavy}
            facts.append(cur)
            continue
        if cur is not None and not cur["heavy"] and (raw.startswith("  ") or not raw.strip()):
            cur["body"] = (cur["body"] + "\n" + raw[2:]) if cur["body"] else raw[2:]
        else:
            cur = None
    for f in facts:
        f["body"] = f["body"].rstrip("\n")
        if f["heavy"]:
            try:
                f["body"] = (store / "facts" / (f["slug"] + ".md")).read_text(encoding="utf-8").rstrip("\n")
            except OSError:
                f["body"] = ""
    return scope, facts


def find_legacy_stores(root):
    """Every dir under `root` that OWNS a legacy `.claude-bx-selflearning/index.md` store (returns the
    owning altitude dirs - the store parents). Skips backup dirs (`.bak`)."""
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
    """Migrate one altitude's legacy store into the central SLUG store. Returns a list of
    (slug, written_bool, collided_bool) for every fact; a cross-level slug collision gets a
    suffixed slug (reported). `dry_run` writes nothing."""
    scope, facts = read_legacy_store(sig.claude_memory_dir(altitude))
    anchor = us.resolve_anchor(altitude) or Path(altitude)
    results = []
    for f in facts:
        slug, collided = f["slug"], False
        target = us.body_path(str(anchor), slug)
        if target.is_file() and target.read_text(encoding="utf-8").rstrip("\n") != f["body"].rstrip("\n"):
            # a DIFFERENT fact in this tree already owns the slug (slugs are tree-unique now)
            n = 2
            while us.body_path(str(anchor), "%s-%d" % (slug, n)).is_file():
                n += 1
            slug, collided = "%s-%d" % (slug, n), True
        written = False
        if not dry_run:
            us.put_body(str(anchor), slug, f["body"])
            us.add_pointer(altitude, slug=slug, title=f["title"], hook=f["hook"],
                           source=f["source"], pin=f["pin"], scope_default=scope)
            written = True
        results.append((slug, written, collided))
    return results


def migrate(root, dry_run):
    """Migrate every legacy store under `root`. Returns {'stores', 'facts', 'written', 'items':[...]}."""
    report = {"stores": 0, "facts": 0, "written": 0, "collisions": 0, "items": []}
    for altitude in sorted(find_legacy_stores(root)):
        report["stores"] += 1
        for slug, written, collided in migrate_store(altitude, dry_run):
            report["facts"] += 1
            report["written"] += 1 if written else 0
            report["collisions"] += 1 if collided else 0
            report["items"].append((altitude, slug, written))
    return report


def _current_legacy_slugs(altitude):
    """The slug set the altitude's CURRENT legacy facts carry."""
    _scope, facts = read_legacy_store(sig.claude_memory_dir(altitude))
    return {f["slug"] for f in facts}


def sync(root, prune):
    """Make the UUID store mirror the current legacy stores: (re)write every live fact (idempotent
    migrate), and when `prune`, drop pointers whose legacy fact is gone and delete central body files no
    pointer references any more. Returns {'facts', 'written', 'pruned', 'bodies_deleted'}."""
    mig = migrate(root, dry_run=False)
    report = {"facts": mig["facts"], "written": mig["written"], "pruned": 0, "bodies_deleted": 0}
    altitudes = sorted(find_legacy_stores(root))
    referenced = set()                                # slugs still referenced by ANY altitude pointer
    for altitude in altitudes:
        keep = _current_legacy_slugs(altitude)
        local = sig.claude_local_md_path(altitude)
        with sig.memory_lock(local):
            try:
                text = local.read_text(encoding="utf-8")
            except OSError:
                continue
            scope, pointers = us.parse_pointer_index(text)
            kept = [p for p in pointers if p.slug in keep or p.slug.rsplit("-", 1)[0] in keep]
            if prune and len(kept) != len(pointers):
                report["pruned"] += len(pointers) - len(kept)
                us.write_if_changed(local, us.upsert_pointer_block(text, scope, kept))
                pointers = kept
            referenced |= {p.slug for p in pointers}
    if prune:                                         # delete central bodies nothing references
        for altitude in altitudes:
            anchor = us.resolve_anchor(altitude) or Path(altitude)
            facts_dir = us.central_facts_dir(anchor)
            if not facts_dir.is_dir():
                continue
            for body in list(facts_dir.glob("*.md")):
                if body.stem not in referenced:
                    try:
                        body.unlink()
                        report["bodies_deleted"] += 1
                    except OSError:
                        pass
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Copy/sync legacy curated facts into the central UUID store.")
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
    print("%s: %d fact(s) across %d store(s); %d body+pointer written; %d slug collision(s)"
          % (tag, rep["facts"], rep["stores"], rep["written"], rep["collisions"]))
    for altitude, slug, written in rep["items"]:
        print("    %s %s  [%s]" % ("+" if written else ".", slug, altitude))
    return 0


if __name__ == "__main__":
    sys.exit(main())
