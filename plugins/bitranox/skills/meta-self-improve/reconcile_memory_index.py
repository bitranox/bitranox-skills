#!/usr/bin/env python3
"""Reference-check + reconcile a curated memory altitude (UUID-native).

A curated altitude is a level dir whose `CLAUDE.local.md` holds a managed pointer block
(`- [Title](mem:<slug>) - hook <!-- bx:src=.. bx:pin -->`); the fact bodies live centrally at
`<anchor>/.claude-memory/facts/<slug>.md`. Slug is the identity, unique per tree. This tool:
  * `--check`: verifies `[[wikilink]]` integrity across an ordered altitude chain (upward-only, no
    dangling), and emits an ADVISORY warning when a level's always-loaded pointer block grows large;
  * default (reconcile): reports orphan pointers whose central body is missing (a raw body carries no
    title/hook/slug, so a pointer can NOT be reconstructed from a body - orphans are reported, never
    fabricated; unreferenced bodies are pruned by `migrate_to_uuid_store.py --sync`).
  * `archive_entry` forgets a fact: drop its pointer line + move its central body to `.archive/`.

`parse_frontmatter`/`derive_title`/`derive_hook` are kept for the NATIVE `~/.claude` tier (its topic
files still carry `name`/`description` frontmatter); `migrate_memory.py` imports them.

Pure standard library; cross-platform; ASCII output only.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

# reuse the UUID-native engine (single source of truth for the on-disk format) from the hooks dir
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import memory_engine as ME  # noqa: E402
import uuid_store as us  # noqa: E402

_HOOK_MAX = 160
_TYPE_PREFIXES = us.TYPE_PREFIXES
_WIKILINK_RX = re.compile(r"\[\[([^\]]+)\]\]")
_WARN_BYTES = 50_000             # SOFT: warn (never fail) when a level's pointer block grows past this
_NON_ENTRY = {"claude.md", "claude.local.md"}


# ---- frontmatter parsing (the NATIVE tier's topic files still carry name/description) ------------

def parse_frontmatter(text):
    """Return (meta, body). meta has 'name'/'description' when present (stdlib, no YAML dep)."""
    meta = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return meta, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return meta, text
    block, body = lines[1:end], "\n".join(lines[end + 1:])
    i = 0
    while i < len(block):
        line = block[i]
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2)
        if val in (">", "|", ">-", "|-", ">+", "|+"):
            chunk = []
            i += 1
            while i < len(block) and (block[i].startswith((" ", "\t")) or not block[i].strip()):
                chunk.append(block[i].strip())
                i += 1
            meta[key] = " ".join(c for c in chunk if c).strip()
            continue
        if val.startswith('"') and not (val.endswith('"') and len(val) > 1):
            chunk = [val[1:]]
            i += 1
            while i < len(block) and '"' not in block[i]:
                chunk.append(block[i].strip())
                i += 1
            if i < len(block):
                chunk.append(block[i].split('"')[0].strip())
                i += 1
            meta[key] = " ".join(chunk).strip()
            continue
        meta[key] = val.strip().strip('"').strip("'")
        i += 1
    return meta, body


def _collapse(text):
    return " ".join((text or "").split())


def derive_title(meta, body, filename):
    """A human-ish title: first body heading, else de-slugified name, else the filename stem."""
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return _collapse(s[2:])
    name = meta.get("name") or Path(filename).stem
    parts = re.split(r"[_-]", name)
    if len(parts) > 1 and parts[0].lower() in _TYPE_PREFIXES:
        parts = parts[1:]
    title = " ".join(p for p in parts if p).strip()
    return title[:1].upper() + title[1:] if title else Path(filename).stem


def derive_hook(meta, body):
    """One-line hook: the frontmatter description, else the first body sentence; capped."""
    hook = _collapse(meta.get("description", ""))
    if not hook:
        para = _collapse(body)
        hook = re.split(r"(?<=[.!?])\s", para)[0] if para else ""
    if len(hook) > _HOOK_MAX:
        hook = hook[: _HOOK_MAX - 3].rstrip() + "..."
    return hook


# ---- altitude model (pointer block + central bodies) -------------------------------------------

def _canon(s):
    """Canonical slug for MATCHING: lowercase, treat `-` and `_` as the same separator."""
    return s.strip().lower().replace("_", "-")


def _ref_slug(token):
    """Normalize a wiki-link token to a bare canonical slug: '[[global:fleet_ssh]]' -> 'fleet-ssh'."""
    return _canon(token.split(":")[-1])


def is_curated(d):
    """A dir is CURATED when its `CLAUDE.local.md` holds a managed pointer block."""
    try:
        text = (Path(d) / "CLAUDE.local.md").read_text(encoding="utf-8")
        return us.INDEX_BEGIN in text or us.LEGACY_INDEX_BEGIN in text
    except OSError:
        return False


def altitude_targets(d):
    """Every canonical slug a curated altitude offers as a `[[wikilink]]` target: each pointer's slug.
    A NON-curated level contributes nothing (it is a plain project dir, not a memory store - never
    rglob its subtree, which would scan docs/code and manufacture false refs)."""
    d = Path(d)
    if not is_curated(d):
        return set()
    _scope, entries, _bodies = ME.read_store(str(d))
    return {_canon(e.slug) for e in entries}


def altitude_sources(d):
    """[(source_slug, text)] to scan for `[[wikilinks]]` at a curated altitude - one source PER pointer
    (its hook + central body). A NON-curated level contributes nothing."""
    d = Path(d)
    if not is_curated(d):
        return []
    _scope, entries, bodies = ME.read_store(str(d))
    return [(_canon(e.slug), e.hook + "\n" + bodies.get(e.slug, "")) for e in entries]


def check_references(dirs):
    """Verify `[[ref]]` integrity across an ordered altitude chain (narrow -> broad). Returns
    {checked, orphans, downward}: `orphans` refs resolve nowhere in the chain; `downward` refs resolve
    only at a NARROWER altitude than the source. Both are (source_slug, ref_slug) pairs."""
    dirs = [Path(d) for d in dirs]
    targets = {}                                  # slug -> set of altitude positions offering it
    for pos, d in enumerate(dirs):
        for s in altitude_targets(d):
            targets.setdefault(s, set()).add(pos)

    orphans, downward, checked = [], [], 0
    for pos, d in enumerate(dirs):
        for label, text in altitude_sources(d):
            for m in _WIKILINK_RX.finditer(text):
                ref = _ref_slug(m.group(1))
                if not ref or ref == label:
                    continue
                checked += 1
                where = targets.get(ref)
                if not where:
                    orphans.append((label, ref))
                elif max(where) < pos:
                    downward.append((label, ref))
    return {"checked": checked, "orphans": sorted(set(orphans)), "downward": sorted(set(downward))}


def has_inbound_refs(dirs, slug):
    """True if any OTHER entry across the chain references `[[slug]]` (or `[[x:slug]]`) - demotion
    safety: never demote a target that lower entries still point UP at. Slug IS the identity now
    (no frontmatter name aliases)."""
    qcanon = _canon(slug)
    for d in [Path(x) for x in dirs]:
        for label, text in altitude_sources(d):
            if _canon(label) == qcanon:               # the target's own body - skip
                continue
            for m in _WIKILINK_RX.finditer(text):
                if _ref_slug(m.group(1)) == qcanon:
                    return True
    return False


# ---- advisory size probe on the always-loaded pointer block ------------------------------------

def over_cap(level_dir, max_bytes=_WARN_BYTES):
    """(within, lines, bytes) for a level's always-loaded pointer block (the managed span in its
    CLAUDE.local.md). NOT hard-capped: `within` is False only to raise an ADVISORY warning when the
    block grows large; the remedy is to let the dream lift/dedup/promote. Bodies are central (not in
    the block), so only the pointer lines count toward the always-loaded budget."""
    try:
        text = (Path(level_dir) / "CLAUDE.local.md").read_text(encoding="utf-8")
    except OSError:
        return True, 0, 0
    b = text.find(us.INDEX_BEGIN)
    endm = us.INDEX_END
    if b < 0:
        b = text.find(us.LEGACY_INDEX_BEGIN)
        endm = us.LEGACY_INDEX_END
    if b < 0:
        return True, 0, 0
    e = text.find(endm, b)
    block = text[b:(len(text) if e < 0 else e + len(endm))]
    raw = block.encode("utf-8")
    lines = block.count("\n") + (1 if block and not block.endswith("\n") else 0)
    return len(raw) <= max_bytes, lines, len(raw)


# ---- reconcile (report orphan pointers) + archive ----------------------------------------------

def reconcile(level_dir, dry_run=False):
    """Report pointers at `level_dir` whose central body is missing (unreconstructable - a raw body
    carries no title/hook/slug). Additive/idempotent: it writes nothing (there is no backfill in the
    UUID model; the engine writes pointer + body atomically). Returns a report dict."""
    d = Path(level_dir)
    _scope, entries, _bodies = ME.read_store(str(d))
    anchor = ME._anchor(str(d))
    orphans = sorted(
        _canon(e.slug) for e in entries
        if not (us.legacy_body_path(anchor, e.uuid) if e.legacy else us.body_path(anchor, e.slug)).is_file())
    return {"dir": str(d), "facts": len(entries), "already_indexed": len(entries),
            "added": [], "orphans": orphans, "dry_run": dry_run}


def _other_levels_pointing(anchor, level_dir, slug):
    """True when any OTHER level between anchor and its subtree that we can see (the level's own
    chain) still has a pointer for `slug`. Conservative: checks every CLAUDE.local.md under the
    anchor one level deep plus the chain of `level_dir`."""
    qcanon = _canon(slug)
    seen = set()
    try:
        import self_improve_signals as sig_mod
        chain = sig_mod.altitude_chain(str(level_dir))
    except Exception:  # noqa: BLE001
        chain = []
    for lvl in chain:
        if Path(lvl) == Path(level_dir):
            continue
        try:
            _s, ptrs = us.parse_pointer_index((Path(lvl) / "CLAUDE.local.md").read_text(encoding="utf-8"))
        except OSError:
            continue
        if any(_canon(x.slug) == qcanon for x in ptrs):
            return True
    return False


def archive_entry(level_dir, slug, archive_subdir=".archive"):
    """Forget a fact: drop its pointer line and move its central body to `<anchor>/.claude-memory/
    <archive_subdir>/`. Returns True if an entry was removed."""
    d = Path(level_dir)
    scope, entries, bodies = ME.read_store(str(d))
    qcanon = _canon(slug)
    kept = [e for e in entries if _canon(e.slug) != qcanon]
    if len(kept) == len(entries):
        return False
    anchor = ME._anchor(str(d))
    for e in entries:
        if _canon(e.slug) == qcanon:
            src = us.legacy_body_path(anchor, e.uuid) if e.legacy else us.body_path(anchor, e.slug)
            # archive the body ONLY when no other level in the tree still points at this slug
            others = _other_levels_pointing(anchor, d, e.slug)
            if src.is_file() and not others:
                archive = us.central_facts_dir(anchor).parent / archive_subdir
                try:
                    archive.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(archive / (src.name)))
                except OSError:
                    pass
    ME._commit_store(str(d), scope, kept, {e.slug: bodies.get(e.slug, "") for e in kept})
    return True


# ---- CLI ---------------------------------------------------------------------------------------

def _print_report(rep):
    print("curated dir: %s" % rep["dir"])
    print("  facts: %d | orphan pointers (no central body): %d" % (rep["facts"], len(rep["orphans"])))
    for slug in rep["orphans"]:
        print("    ! orphan (pointer line, no central body): %s" % slug)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Reference-check / reconcile a curated memory altitude.")
    ap.add_argument("dirs", nargs="+", help="level dir(s) to reconcile, or an altitude chain for --check")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    ap.add_argument("--check", action="store_true",
                    help="treat dirs as an ordered altitude chain (narrow->broad) and verify reference "
                         "integrity (upward-only, no orphans) + emit advisory pointer-block size "
                         "warnings; exit 1 only on reference-integrity issues")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if args.check:
        refs = check_references(args.dirs)
        problems = 0
        print("reference integrity: %d ref(s) checked" % refs["checked"])
        for src, ref in refs["orphans"]:
            print("    ! orphan ref: [[%s]] in %s -> no such entry in the chain" % (ref, src))
            problems += 1
        for src, ref in refs["downward"]:
            print("    ! downward ref: %s -> [[%s]] points to a NARROWER altitude" % (src, ref))
            problems += 1
        warnings = 0
        for d in args.dirs:
            if is_curated(d):
                within, lines, nbytes = over_cap(d)
                if not within:
                    print("    ~ warning: %s pointer block is %d bytes / %d lines - large always-loaded "
                          "index; let the dream lift/dedup/promote, else it loads only for this project"
                          % (d, nbytes, lines))
                    warnings += 1
        print("TOTAL problems: %d" % problems)
        if warnings:
            print("TOTAL warnings: %d (advisory, not failures)" % warnings)
        return 1 if problems else 0

    total_orphans = 0
    for d in args.dirs:
        rep = reconcile(d, dry_run=args.dry_run)
        _print_report(rep)
        total_orphans += len(rep["orphans"])
    print("TOTAL orphan pointers: %d" % total_orphans)
    return 0


if __name__ == "__main__":
    sys.exit(main())
