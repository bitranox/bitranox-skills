#!/usr/bin/env python3
"""One-shot migration: uuid-sharded body files -> slug-named files, pointer lines uuid: -> mem:.

The 2026-07-05 retrieval experiment pivoted the store to slug-named flat bodies (see
`.plan/probe-retrieval-and-platform-20260705.md`). Stores written before the pivot carry
`- [Title](uuid:<uuid>) - hook <!-- ... bx:slug=<slug> -->` lines with bodies at
`facts/<2-hex>/<uuid>.md`. This tool converts a tree in place, atomically per fact (body move and
line flip happen in the same apply pass, never separately - a flipped line whose body did not move
would break resolution):

  * DRY-RUN (default): per level, report the lines to flip, the body moves, slug COLLISIONS, and
    missing old bodies. Writes nothing. A slug is taken when, in the same tree, a migrated pointer
    already owns it, another legacy fact claimed it first, or a body file already sits at its path;
    a collision is resolved by suffixing (`-2`, `-3`, ...) and reported. A `CLAUDE.local.md` that
    cannot be read or decoded is reported as UNREADABLE and left alone.
  * --apply: BACKUP first (every touched CLAUDE.local.md + the anchor's `.claude-memory/` copied to
    a timestamped dir under the anchor, with a `manifest.txt` mapping each copy back to its file),
    then move each body `facts/<sh>/<uuid>.md` -> `facts/<slug>.md` and rewrite each pointer block
    (new fence, `mem:` lines, retrieval recipe, pinned-first sections). When any backup step fails
    the apply stops before touching anything and the CLI exits 1. Idempotent: a second run finds
    nothing legacy.

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

__all__ = ["BACKUP_PREFIX", "backup_rel", "find_pointer_files", "main", "migrate", "plan_level"]

BACKUP_PREFIX = ".claude-memory-migration-backup-"


def _is_pruned(name):
    """True for a dir the walk never enters: vendored/build/VCS dirs, a store, or a backup."""
    return (name in sig.VENDOR_DIRNAMES or name in (sig.MEMORY_DIRNAME, sig.CURATED_DIRNAME)
            or name.startswith(BACKUP_PREFIX) or ".bak-" in name or name.endswith(".bak"))


def find_pointer_files(root, unreadable=None):
    """Every CLAUDE.local.md under `root` that carries a managed pointer block (either fence).

    Hidden dirs ARE walked: a tree checked out under `.claude/worktrees/` is a tree like any other.
    Pruned: vendor/build/VCS dirs, stores, backups, and the machine-local audit dir (by resolved
    path), whose dream backups hold copies of pointer blocks that are snapshots, not live levels.
    A file that cannot be read or decoded is appended to `unreadable` (when given) and skipped.
    """
    audit_root = sig._audit_dir().resolve()
    out = []
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            if os.path.basename(dirpath) in (sig.MEMORY_DIRNAME, sig.CURATED_DIRNAME):
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames
                           if not _is_pruned(d) and Path(dirpath, d).resolve() != audit_root]
            if "CLAUDE.local.md" not in filenames:
                continue
            p = Path(dirpath) / "CLAUDE.local.md"
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                if unreadable is not None:
                    unreadable.append(str(p))
                continue
            if us.INDEX_BEGIN in text or us.LEGACY_INDEX_BEGIN in text:
                out.append(p)
    except OSError:
        pass
    return sorted(out)


def _read_level(local_path):
    """One pointer file parsed: its level, its tree's anchor (absolute), scope and pointers."""
    level = Path(os.path.abspath(local_path)).parent
    anchor = Path(os.path.abspath(us.resolve_anchor(str(level)) or level))
    text = Path(local_path).read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    return {"local": Path(local_path), "level": level, "anchor": anchor, "scope": scope,
            "pointers": pointers, "text": text, "actions": []}


def _seed_taken(levels):
    """{(anchor, slug): owning body path} for every slug a MIGRATED pointer already holds.

    Seeded from every file before any legacy line is planned, so which file the walk reaches first
    cannot decide whether a legacy fact is handed a slug that a migrated fact already owns.
    Keyed per tree: slugs are unique within a tree, never across trees.
    """
    taken = {}
    for lv in levels:
        for p in lv["pointers"]:
            if not p.legacy:
                taken.setdefault((str(lv["anchor"]), p.slug), str(us.body_path(lv["anchor"], p.slug)))
    return taken


def _slug_busy(anchor, slug, old_body, taken):
    """True when `slug` in `anchor`'s tree belongs to something other than the fact at `old_body`."""
    owner = taken.get((str(anchor), slug))
    if owner is not None:
        return owner != str(old_body)
    return us.body_path(anchor, slug).exists()          # a dangling body still belongs to a fact


def _free_slug(anchor, slug, old_body, taken):
    """(slug to migrate to, collided) - `slug` itself when free, else the first free suffix."""
    if not _slug_busy(anchor, slug, old_body, taken):
        return slug, False
    n = 2
    while _slug_busy(anchor, "%s-%d" % (slug, n), old_body, taken):
        n += 1
    return "%s-%d" % (slug, n), True


def plan_level(level, taken):
    """Plan one parsed level's migration (from `_read_level`), filling `level["actions"]` with
    [{slug, final_slug, uuid, old_body, new_body, collided, missing, pointer}]. `taken` is the
    per-tree registry from `_seed_taken`, extended with every slug planned here."""
    anchor = level["anchor"]
    for p in level["pointers"]:
        if not p.legacy:
            continue
        old_body = us.legacy_body_path(anchor, p.uuid)
        final, collided = _free_slug(anchor, p.slug, old_body, taken)
        taken[(str(anchor), final)] = str(old_body)
        level["actions"].append({"slug": p.slug, "final_slug": final, "uuid": p.uuid,
                                 "old_body": old_body, "new_body": us.body_path(anchor, final),
                                 "collided": collided, "missing": not old_body.is_file(),
                                 "pointer": p})
    return level


def backup_rel(local, anchor):
    """Where the copy of pointer file `local` goes, relative to the backup dir. PURE.

    Its path relative to `anchor`, so the copy keeps the level's layout and two levels cannot
    overwrite each other. Outside the anchor, the whole path is flattened into one name with every
    separator and drive colon replaced: joining an absolute path onto the backup dir yields the
    absolute path itself, which on Windows made the "copy" the source file.
    """
    try:
        return local.relative_to(anchor)
    except ValueError:
        parts = [part.strip("\\/").replace(":", "") for part in local.parts]
        return type(local)("_".join(part for part in parts if part))


def _backup(plans, stamp):
    """Copy each tree's store and every touched pointer file; returns the backup dirs.
    Raises OSError on any failure - the caller must not migrate without a backup."""
    dirs = []
    for plan in plans:
        if not plan["actions"]:
            continue
        anchor = plan["anchor"]
        bdir = anchor / (BACKUP_PREFIX + stamp)
        if str(bdir) not in dirs:
            bdir.mkdir(parents=True, exist_ok=True)
            store = anchor / sig.MEMORY_DIRNAME
            if store.is_dir():
                shutil.copytree(store, bdir / sig.MEMORY_DIRNAME)
            dirs.append(str(bdir))
        rel = Path("levels") / backup_rel(Path(os.path.abspath(plan["local"])), anchor)
        (bdir / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plan["local"], bdir / rel)
        with (bdir / "manifest.txt").open("a", encoding="utf-8") as mf:
            mf.write("%s\t%s\n" % (rel.as_posix(), plan["local"]))     # reversible mapping
    return dirs


def _apply(plans, report):
    for plan in plans:
        if not plan["actions"]:
            continue
        with sig.memory_lock(plan["local"]):
            for a in plan["actions"]:
                if a["missing"]:
                    continue                          # body gone: leave the line legacy, report only
                a["new_body"].parent.mkdir(parents=True, exist_ok=True)
                if not a["new_body"].exists():        # a second pointer to the same legacy body
                    shutil.move(str(a["old_body"]), str(a["new_body"]))
                p = a["pointer"]
                p.slug, p.legacy, p.uuid = a["final_slug"], False, ""
                report["moved"] += 1
            new_text = us.upsert_pointer_block(plan["text"], plan["scope"], plan["pointers"])
            us.write_if_changed(plan["local"], new_text)


def migrate(roots, apply=False):
    """Migrate every tree under `roots`. Returns a report dict; `backup_failed` is set (and nothing
    was written) when --apply could not back up first."""
    report = {"files": 0, "legacy_lines": 0, "moved": 0, "collisions": 0, "missing": 0,
              "backups": [], "items": [], "unreadable": [], "backup_failed": None}
    levels = []
    for root in roots:
        for local in find_pointer_files(root, report["unreadable"]):
            try:
                levels.append(_read_level(local))
            except (OSError, UnicodeDecodeError):
                report["unreadable"].append(str(local))
    taken = _seed_taken(levels)
    for level in levels:
        plan_level(level, taken)
        report["files"] += 1
        for a in level["actions"]:
            report["legacy_lines"] += 1
            report["collisions"] += 1 if a["collided"] else 0
            report["missing"] += 1 if a["missing"] else 0
            report["items"].append((str(level["level"]), a["slug"], a["final_slug"],
                                    a["collided"], a["missing"]))
    if not apply:
        return report
    try:
        report["backups"] = _backup(levels, time.strftime("%Y%m%d-%H%M%S"))
    except OSError as exc:
        report["backup_failed"] = str(exc)
        return report
    _apply(levels, report)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Migrate uuid-sharded stores to the slug store.")
    ap.add_argument("--root", action="append", required=True, dest="roots",
                    help="tree root(s) to scan (repeatable)")
    ap.add_argument("--apply", action="store_true", help="write (default: DRY-RUN, writes nothing)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    rep = migrate(args.roots, apply=args.apply)
    if rep["backup_failed"]:
        print("ABORTED: backup failed, nothing was moved or rewritten: %s" % rep["backup_failed"],
              file=sys.stderr)
        return 1
    tag = "APPLIED" if args.apply else "DRY-RUN"
    print("%s: %d pointer file(s); %d legacy line(s); %d body move(s); %d collision(s); %d missing;"
          " %d unreadable"
          % (tag, rep["files"], rep["legacy_lines"], rep["moved"], rep["collisions"], rep["missing"],
             len(rep["unreadable"])))
    for level, slug, final, collided, missing in rep["items"]:
        flag = " COLLISION->%s" % final if collided else (" MISSING-BODY" if missing else "")
        print("    %s [%s]%s" % (slug, level, flag))
    for path in rep["unreadable"]:
        print("    UNREADABLE (not scanned): %s" % path)
    for b in rep["backups"]:
        print("    backup: %s" % b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
