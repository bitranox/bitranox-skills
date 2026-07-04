#!/usr/bin/env python3
"""One-shot migration: uuid-sharded body files -> slug-named files, pointer lines uuid: -> mem:.

The 2026-07-05 retrieval experiment pivoted the store to slug-named flat bodies (see
`.plan/probe-retrieval-and-platform-20260705.md`). Stores written before the pivot carry
`- [Title](uuid:<uuid>) - hook <!-- ... bx:slug=<slug> -->` lines with bodies at
`facts/<2-hex>/<uuid>.md`. This tool converts a tree in place, atomically per fact (body move and
line flip happen in the same apply pass, never separately - a flipped line whose body did not move
would break resolution):

  * DRY-RUN (default): per level, report the lines to flip, the body moves, slug COLLISIONS
    (two legacy facts mapping to one slug in the tree - resolved by suffixing, reported), and
    missing old bodies. Writes nothing.
  * --apply: BACKUP first (every touched CLAUDE.local.md + the anchor's `.claude-memory/` copied to
    a timestamped dir under the anchor), then move each body `facts/<sh>/<uuid>.md` ->
    `facts/<slug>.md` and rewrite each pointer block (new fence, `mem:` lines, retrieval recipe,
    pinned-first sections). Idempotent: a second run finds nothing legacy.

Pure standard library; mtime-neutral writers; ASCII output.
"""
import argparse
import os
import shutil
import sys
import time
from pathlib import Path

import self_improve_signals as sig
import uuid_store as us


def find_pointer_files(root):
    """Every CLAUDE.local.md under `root` that carries a managed pointer block (either fence),
    pruning vendor/hidden/backup dirs and never descending into stores."""
    out = []
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            base = os.path.basename(dirpath)
            if base in (sig.MEMORY_DIRNAME, sig.CURATED_DIRNAME):
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames
                           if d not in sig.VENDOR_DIRNAMES and not d.startswith(".")
                           and ".bak-" not in d and not d.endswith(".bak")]
            if "CLAUDE.local.md" in filenames:
                p = Path(dirpath) / "CLAUDE.local.md"
                try:
                    text = p.read_text(encoding="utf-8")
                except OSError:
                    continue
                if us.INDEX_BEGIN in text or us.LEGACY_INDEX_BEGIN in text:
                    out.append(p)
    except OSError:
        pass
    return sorted(out)


def plan_level(local_path, taken_slugs):
    """Plan one level's migration. Returns a dict with the parsed block plus per-fact actions:
    [{slug, final_slug, uuid, old_body, new_body, collided, missing}]. `taken_slugs` is the
    tree-wide registry (slug -> owning old body path or None) used for collision detection."""
    level = local_path.parent
    anchor = us.resolve_anchor(str(level)) or level
    text = local_path.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    actions = []
    for p in pointers:
        if not p.legacy:
            if p.slug not in taken_slugs:
                taken_slugs[p.slug] = str(us.body_path(anchor, p.slug))
            continue
        final = p.slug
        old_body = us.legacy_body_path(anchor, p.uuid)
        collided = False
        if final in taken_slugs and taken_slugs[final] != str(old_body):
            n = 2
            while ("%s-%d" % (final, n)) in taken_slugs:
                n += 1
            final, collided = "%s-%d" % (p.slug, n), True
        taken_slugs[final] = str(old_body)
        actions.append({"slug": p.slug, "final_slug": final, "uuid": p.uuid,
                        "old_body": old_body, "new_body": us.body_path(anchor, final),
                        "collided": collided, "missing": not old_body.is_file(),
                        "pointer": p})
    return {"local": local_path, "level": level, "anchor": anchor, "scope": scope,
            "pointers": pointers, "actions": actions, "text": text}


def migrate(roots, apply=False):
    """Migrate every tree under `roots`. Returns a report dict."""
    report = {"files": 0, "legacy_lines": 0, "moved": 0, "collisions": 0, "missing": 0,
              "backups": [], "items": []}
    taken = {}
    plans = []
    for root in roots:
        for local in find_pointer_files(root):
            plan = plan_level(local, taken)
            plans.append(plan)
            report["files"] += 1
            for a in plan["actions"]:
                report["legacy_lines"] += 1
                report["collisions"] += 1 if a["collided"] else 0
                report["missing"] += 1 if a["missing"] else 0
                report["items"].append((str(plan["level"]), a["slug"], a["final_slug"],
                                        a["collided"], a["missing"]))
    if not apply:
        return report

    # backup: every touched CLAUDE.local.md + each anchor's .claude-memory, once per anchor
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backed_anchors = set()
    for plan in plans:
        if not plan["actions"]:
            continue
        bdir = Path(str(plan["anchor"])) / (".claude-memory-migration-backup-" + stamp)
        if str(plan["anchor"]) not in backed_anchors:
            try:
                store = Path(str(plan["anchor"])) / sig.MEMORY_DIRNAME
                if store.is_dir():
                    shutil.copytree(store, bdir / sig.MEMORY_DIRNAME)
                backed_anchors.add(str(plan["anchor"]))
                report["backups"].append(str(bdir))
            except OSError:
                pass
        try:
            bdir.mkdir(parents=True, exist_ok=True)
            rel = str(plan["local"]).replace("/", "_")
            shutil.copy2(plan["local"], bdir / rel)
        except OSError:
            pass

    for plan in plans:
        if not plan["actions"]:
            continue
        with sig.memory_lock(plan["local"]):
            for a in plan["actions"]:
                if a["missing"]:
                    continue                          # body gone: leave the line legacy, report only
                a["new_body"].parent.mkdir(parents=True, exist_ok=True)
                if not a["new_body"].exists():
                    shutil.move(str(a["old_body"]), str(a["new_body"]))
                p = a["pointer"]
                p.slug, p.legacy, p.uuid = a["final_slug"], False, ""
                report["moved"] += 1
            new_text = us.upsert_pointer_block(plan["text"], plan["scope"], plan["pointers"])
            us.write_if_changed(plan["local"], new_text)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Migrate uuid-sharded stores to the slug store.")
    ap.add_argument("--root", action="append", required=True, dest="roots",
                    help="tree root(s) to scan (repeatable)")
    ap.add_argument("--apply", action="store_true", help="write (default: DRY-RUN, writes nothing)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    rep = migrate(args.roots, apply=args.apply)
    tag = "APPLIED" if args.apply else "DRY-RUN"
    print("%s: %d pointer file(s); %d legacy line(s); %d body move(s); %d collision(s); %d missing"
          % (tag, rep["files"], rep["legacy_lines"], rep["moved"], rep["collisions"], rep["missing"]))
    for level, slug, final, collided, missing in rep["items"]:
        flag = " COLLISION->%s" % final if collided else (" MISSING-BODY" if missing else "")
        print("    %s [%s]%s" % (slug, level, flag))
    for b in rep["backups"]:
        print("    backup: %s" % b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
