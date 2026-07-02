#!/usr/bin/env python3
"""Migrate native Auto-memory stores into the curated `.claude-bx-selflearning/` model (Phase 2).

For each `~/.claude/projects/<slug>/memory/` store: resolve the slug back to its project directory,
curate its `MEMORY.md` + topic files into that project's curated store via the write engine, back up
out-of-tree first, and write a receipt so a re-run is idempotent and a crash resumes. Never deletes
the native store (it stays as the raw tier); never auto-commits any repo.

The slug encoding maps BOTH `/` and `.` to `-` (verified: `.../skills/.claude/worktrees` ->
`...-skills--claude-worktrees`), so reversing a slug is ambiguous. `resolve_slug` walks the filesystem,
trying each `-` as `/` (descend), `.`, or literal `-`, and keeps only candidates that EXIST. A unique
existing candidate resolves; ambiguous/none is PARKED and reported - never guessed.

Usage:
    migrate_memory.py --dry-run [--slug <s> ...]   # report the full touch-list, write nothing
    migrate_memory.py --apply   [--slug <s> ...]   # back up + migrate (idempotent via receipts)

Pure standard library; ASCII output.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import self_improve_signals as sig       # noqa: E402
import memory_engine as ME               # noqa: E402
import reconcile_memory_index as R       # noqa: E402

def _projects_dir():
    return Path.home() / ".claude" / "projects"


def _backups_dir():
    return Path.home() / ".claude" / "self-improve-audit" / "backups"


def _parked_dir():
    return Path.home() / ".claude" / "self-improve-audit" / "migration-unresolved"


# ---- slug -> path resolution (filesystem-guided; `/` and `.` both encode to `-`) ---------------

def _children(d):
    try:
        return set(os.listdir(d))
    except OSError:
        return set()


def resolve_slug(slug, max_candidates=8):
    """Every existing directory a `<slug>` could decode to. The slug starts with `-` (leading `/`);
    each subsequent `-` is `/` (descend), `.`, or literal `-`. DFS with filesystem pruning: a `/`
    only descends into a real child; a `.`/`-` continuation only survives if a child STARTS with the
    partial component. Returns a de-duplicated list of absolute dir paths (realpath), capped."""
    if not slug.startswith("-"):
        return []
    tokens = slug[1:].split("-")
    if not tokens:
        return []
    out = []

    def dfs(idx, base, comp):
        # `comp` is a partial name of a child of `base`; `tokens[idx]` is the next token to attach.
        if len(out) >= max_candidates:
            return
        if idx == len(tokens):
            full = os.path.join(base, comp)
            if os.path.isdir(full):
                out.append(str(Path(full).resolve()))
            return
        kids = _children(base)
        tok = tokens[idx]
        # option "/": `comp` is a complete child -> descend, start a new component with `tok`
        if comp in kids and os.path.isdir(os.path.join(base, comp)):
            dfs(idx + 1, os.path.join(base, comp), tok)
        # options "." / "-" / "_": extend the component (Claude encodes `/`, `.`, `_` all to `-`, and a
        # literal `-` stays `-`, so a slug `-` is any of the four); prune unless a child matches the prefix
        for sep in (".", "-", "_"):
            new_comp = comp + sep + tok
            if any(k.startswith(new_comp) for k in kids):
                dfs(idx + 1, base, new_comp)

    dfs(1, "/", tokens[0])
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def resolve_one(slug):
    """A single resolved project dir for `slug`, or None if ambiguous/unresolved. Disambiguate ties by
    preferring a candidate that looks like a project root (`.git` or `CLAUDE.md` present)."""
    cands = resolve_slug(slug)
    if len(cands) == 1:
        return cands[0]
    if not cands:
        return None
    marked = [c for c in cands if (Path(c) / ".git").exists() or (Path(c) / "CLAUDE.md").is_file()]
    return marked[0] if len(marked) == 1 else None


# roots that resolve but are NOT real projects to seed a curated store into (transient / the home dir)
_EXCLUDE_PREFIXES = ("/tmp",)


def is_excluded(path):
    """True for a resolved path we should NOT create a curated store in: `$HOME` itself, or anything
    under a transient root (`/tmp`). Such native stores are skipped (not migrated, not parked)."""
    if not path:
        return False
    try:
        p = str(Path(path).resolve())
    except OSError:
        return False
    if p == str(Path.home().resolve()):
        return True
    return any(p == pref or p.startswith(pref + "/") for pref in _EXCLUDE_PREFIXES)


# ---- reading a native store --------------------------------------------------------------------

def read_native_entries(memdir):
    """[(name, title, hook, body, source_slug)] for each native topic `*.md` (excluding MEMORY.md)."""
    out = []
    memdir = Path(memdir)
    try:
        topics = sorted(p for p in memdir.glob("*.md") if p.name != "MEMORY.md")
    except OSError:
        topics = []
    for p in topics:
        try:
            meta, body = R.parse_frontmatter(p.read_text(encoding="utf-8"))
        except OSError:
            continue
        title = R.derive_title(meta, body, p.name)
        hook = R.derive_hook(meta, body)
        src = meta.get("name") or p.stem
        type_ = None
        for t in ("feedback", "project", "reference", "user"):
            if str(meta.get("name", p.stem)).startswith(t) or str(meta.get("type", "")) == t \
               or str((meta.get("metadata") or "")).find(t) >= 0:
                type_ = t
                break
        out.append({"name": p.stem, "title": title, "hook": hook, "body": body.strip(),
                    "source": src, "type": type_})
    return out


# ---- receipts (idempotency + resume) -----------------------------------------------------------

def _receipt_path(proj):
    return sig.curated_state_dir(proj) / "migration-receipt.json"


def _load_receipt(proj):
    try:
        return json.loads(_receipt_path(proj).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"placed": [], "sources": [], "slugs": []}


def _save_receipt(proj, rec):
    p = _receipt_path(proj)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


# ---- gitignore safety (R11): keep the curated store out of git unless the user opts to track it ---

def _git(proj, *args):
    try:
        r = subprocess.run(["git", "-C", str(proj), *args], capture_output=True, text=True, timeout=15)
        return r.returncode, r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def ensure_gitignore(proj):
    """Ensure `.claude-bx-selflearning/` AND `CLAUDE.local.md` (the untracked memory wiring) are
    gitignored in the repo owning `proj`. Honors `track_private` (if set, the user WANTS it tracked ->
    do nothing). R11 checks: non-git dir -> skip; already ignored -> no-op; the store already TRACKED
    -> WARN (a possible existing leak) and do NOT append; else append the ignore lines to the repo-root
    `.gitignore`. Returns a status string. Fail-open."""
    if sig.load_config().get("track_private"):
        return "track_private: left tracked"
    rc, top = _git(proj, "rev-parse", "--show-toplevel")
    if rc != 0 or not top:
        return "not a git repo: skipped"
    root = Path(top)
    if _git(proj, "ls-files", "--error-unmatch", sig.CURATED_DIRNAME + "/")[0] == 0:
        return "WARNING: .claude-bx-selflearning is TRACKED (possible existing leak) - not modifying .gitignore"
    gi = root / ".gitignore"
    try:
        cur = gi.read_text(encoding="utf-8") if gi.is_file() else ""
        have = set(cur.splitlines())
        wanted = [sig.CURATED_DIRNAME + "/", "CLAUDE.local.md"]
        add = [w for w in wanted if w not in have and w.rstrip("/") not in have]
        if not add:
            return "already ignored"
        gi.write_text((cur.rstrip("\n") + "\n" if cur.strip() else "")
                      + "# bitranox curated self-learning memory (local; CLAUDE.local.md @imports it)\n"
                      + "\n".join(add) + "\n", encoding="utf-8")
        return "gitignored"
    except OSError:
        return "gitignore write failed"


# ---- migrate one store -------------------------------------------------------------------------

def migrate_store(slug, dry_run=True, scope_default="", redirect=None):
    """Migrate one native store. Returns a report dict. On apply: backs up out-of-tree, curates each
    native entry into the resolved (or `redirect`-forced) project's curated store via the engine,
    records a receipt. Idempotent (receipt-skipped). Unresolved -> parked; an excluded target
    (`/tmp`, `$HOME`) -> skipped, not migrated. `redirect` forces the target for a renamed/moved slug."""
    memdir = _projects_dir() / slug / "memory"
    entries = read_native_entries(memdir)
    proj = redirect or resolve_one(slug)
    rep = {"slug": slug, "resolved": proj, "in": len(entries), "placed": 0, "skipped": 0,
           "parked": False, "excluded": False, "redirected": bool(redirect), "dry_run": dry_run}
    if proj and is_excluded(proj):
        rep["excluded"] = True
        return rep
    if proj is None:
        rep["parked"] = True
        if not dry_run and entries:
            try:
                dst = _parked_dir() / slug
                dst.mkdir(parents=True, exist_ok=True)
                shutil.copytree(memdir, dst / "memory", dirs_exist_ok=True)
            except OSError:
                pass
        return rep
    if dry_run:
        rec = _load_receipt(proj)
        done = set(rec.get("sources", []))
        rep["placed"] = sum(1 for e in entries if e["source"] not in done)
        rep["skipped"] = len(entries) - rep["placed"]
        return rep

    # apply: back up both the native store and any existing curated store, out of tree
    key = sig.proj_key(proj)
    stamp = _backups_dir() / ("%s-%d" % (key, int(time.time())))
    try:
        stamp.mkdir(parents=True, exist_ok=True)
        shutil.copytree(memdir, stamp / "native", dirs_exist_ok=True)
        cur = sig.claude_memory_dir(proj)
        if cur.exists():
            shutil.copytree(cur, stamp / "curated", dirs_exist_ok=True)
    except OSError:
        pass

    rec = _load_receipt(proj)
    done = set(rec.get("sources", []))
    for e in entries:
        if e["source"] in done:
            rep["skipped"] += 1
            continue
        ME.add_or_update_entry(proj, title=e["title"], hook=e["hook"], body=e["body"],
                               type_=e["type"], source=[e["source"]], scope_default=scope_default)
        done.add(e["source"])
        rep["placed"] += 1
    rec["sources"] = sorted(done)
    rec["slugs"] = sorted(set(rec.get("slugs", []) + [slug]))
    _save_receipt(proj, rec)
    rep["gitignore"] = ensure_gitignore(proj)   # keep the curated store out of git (R11)
    return rep


def enumerate_slugs():
    try:
        return sorted(p.name for p in _projects_dir().glob("*") if (p / "memory").is_dir())
    except OSError:
        return []


def _parse_redirects(items):
    """Parse `--redirect SLUG=TARGET` items into {slug: target_path}. TARGET must be an existing dir."""
    out = {}
    for it in (items or []):
        if "=" not in it:
            continue
        slug, target = it.split("=", 1)
        out[slug.strip()] = target.strip()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Migrate native memory stores into the curated model.")
    ap.add_argument("--apply", action="store_true", help="write (default is dry-run/report-only)")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing (default)")
    ap.add_argument("--slug", action="append", default=None,
                    help="limit to specific slug(s); slugs start with '-', so use the =form: --slug=-media-...")
    ap.add_argument("--redirect", action="append", default=None,
                    help="force a renamed/moved slug into a target dir: --redirect=<slug>=<target-path>")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    dry = not args.apply
    redirects = _parse_redirects(args.redirect)

    slugs = args.slug if args.slug else enumerate_slugs()
    total_in = total_placed = total_parked = total_excluded = 0
    parked = []
    print("%s %d store(s)%s" % ("DRY-RUN over" if dry else "MIGRATING", len(slugs),
                                "" if dry else " (writing)"))
    for slug in slugs:
        rep = migrate_store(slug, dry_run=dry, redirect=redirects.get(slug))
        total_in += rep["in"]
        total_placed += rep["placed"]
        if rep["excluded"]:
            total_excluded += rep["in"]
            if rep["in"]:
                print("  - excluded (transient/home): %s -> %s (%d entries skipped)"
                      % (slug, rep["resolved"], rep["in"]))
        elif rep["parked"]:
            total_parked += rep["in"]
            parked.append(slug)
            print("  ! PARKED (unresolved): %s (%d entries)" % (slug, rep["in"]))
        elif rep["in"] or rep["redirected"]:            # suppress 0-entry no-op noise
            print("  %s%s -> %s : in=%d %s=%d skip=%d"
                  % ("[redirect] " if rep["redirected"] else "", slug, rep["resolved"], rep["in"],
                     "would-place" if dry else "placed", rep["placed"], rep["skipped"]))
    print("TOTAL in=%d %s=%d parked=%d excluded=%d (in == placed+skipped+parked+excluded)"
          % (total_in, "would-place" if dry else "placed", total_placed, total_parked, total_excluded))
    if parked:
        print("PARKED slugs (redirect with --redirect=<slug>=<path>, or resolve manually): %s"
              % ", ".join(parked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
