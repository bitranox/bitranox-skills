#!/usr/bin/env python3
"""Reconcile a Claude Code Auto-memory dir's MEMORY.md index with its topic files.

A learning is only "present" if its one-line entry is in MEMORY.md (the file Claude Code
auto-loads each session). Topic files created out-of-band (e.g. written through a memory MCP)
leave a body on disk with no MEMORY.md index line, so they are never loaded. This tool
backfills the missing index lines from each topic file's frontmatter, making every body
present again. It is additive and idempotent: it only APPENDS missing lines and never edits
or deletes existing ones. Orphan index lines (pointing at a missing file) are reported, not
removed.

Usage:
    python reconcile_memory_index.py <memory-dir> [<memory-dir> ...] [--dry-run]

A <memory-dir> is a `.../memory/` folder holding MEMORY.md + topic `*.md` files.

Pure standard library; cross-platform (pathlib, UTF-8). ASCII output only.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

MEMORY_INDEX = "MEMORY.md"
_HEADING = "# Memory index"
_LINK_RX = re.compile(r"\]\(([^)]+\.md)\)")  # the (filename.md) in a markdown link
_HOOK_MAX = 160
_TYPE_PREFIXES = ("project", "feedback", "reference", "user")


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
        if val in (">", "|", ">-", "|-", ">+", "|+"):  # block scalar: gather indented lines
            chunk = []
            i += 1
            while i < len(block) and (block[i].startswith((" ", "\t")) or not block[i].strip()):
                chunk.append(block[i].strip())
                i += 1
            meta[key] = " ".join(c for c in chunk if c).strip()
            continue
        if val.startswith('"') and not (val.endswith('"') and len(val) > 1):  # multi-line quote
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


def referenced_files(memory_md_text):
    return {m.group(1) for m in _LINK_RX.finditer(memory_md_text)}


# ---- cross-altitude reference integrity (normalization safety) -----------------------
# Entries may carry `[[name]]` / `[[altitude:name]]` wiki-links to a generalized rule one or
# more altitudes UP. Two invariants keep that safe (see the plan's normalization section):
#   * the target must EXIST (no dangling pointer), and
#   * it must sit at the SAME or a HIGHER altitude (upward only), so deleting a lower project
#     never orphans a higher entry. A reference pointing DOWN is reported.
# An altitude CHAIN is a list of dirs ordered narrowest -> broadest (see
# self_improve_signals.altitude_chain): e.g. [project memory, ...ancestors..., global rules].

_WIKILINK_RX = re.compile(r"\[\[([^\]]+)\]\]")
_CAP_LINES = 200
_CAP_BYTES = 25_000


def _ref_slug(token):
    """Normalize a wiki-link token to a bare slug: '[[global:fleet-ssh]]' -> 'fleet-ssh'."""
    return token.split(":")[-1].strip().lower()


_NON_ENTRY = {MEMORY_INDEX.lower(), "claude.md", "claude.local.md"}


def _entry_md_files(d, recursive=False):
    """Slugged memory/rule entry `*.md` directly in an altitude dir. Excludes the MEMORY.md index AND
    `CLAUDE.md`/`CLAUDE.local.md` (hand-written prose/code, not memory entries - scanning them for
    `[[ ]]` matches things like `Callable[[...]]` in code, a false positive). `recursive=True` ONLY
    for the whole-loaded global tier (it may nest); everything else NON-recursively so an ancestor
    altitude never triggers a walk of the whole project tree under it."""
    try:
        it = d.rglob("*.md") if recursive else d.glob("*.md")
        return [p for p in it if p.name.lower() not in _NON_ENTRY]
    except OSError:
        return []


def _altitude_entries(pos, last, d):
    """Slugged ref entries at an altitude. ONLY the project memory dir (pos 0, flat) and the global
    layer (last, recursive) hold slugged entries. MIDDLE positions are ancestor CLAUDE.md altitudes -
    real repo/filesystem dirs whose other `*.md` (CHANGELOG/README/docs) are NOT memory entries - so
    they contribute nothing to reference scanning (their CLAUDE.md is a descriptor, not a ref target)."""
    if pos == 0:
        return _entry_md_files(d, recursive=False)
    if pos == last:
        return _entry_md_files(d, recursive=True)
    return []


def check_references(dirs):
    """Verify `[[ref]]` integrity across an ordered altitude chain (narrow -> broad): the first dir is
    the project memory, the last is the global layer (recursive), the middle ones are ancestor CLAUDE.md
    altitudes (scanned for nothing). See `_altitude_entries`.

    Returns {checked, orphans, downward}: `orphans` are refs whose target exists nowhere in the
    chain; `downward` are refs whose target lives only at a NARROWER altitude than the source.
    Both are (source_slug, ref_slug) pairs. A clean store yields empty lists.
    """
    dirs = [Path(d) for d in dirs]
    last = len(dirs) - 1
    # target slug -> set of altitude positions where an entry by that slug exists
    targets = {}
    for pos, d in enumerate(dirs):
        for p in _altitude_entries(pos, last, d):
            targets.setdefault(p.stem.lower(), set()).add(pos)

    orphans, downward, checked = [], [], 0
    for pos, d in enumerate(dirs):
        sources = _altitude_entries(pos, last, d) + ([d / MEMORY_INDEX] if pos == 0 else [])
        for p in sources:
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            for m in _WIKILINK_RX.finditer(text):
                ref = _ref_slug(m.group(1))
                if not ref or ref == p.stem.lower():
                    continue
                checked += 1
                where = targets.get(ref)
                if not where:
                    orphans.append((p.stem.lower(), ref))
                elif max(where) < pos:           # every target is strictly below the source
                    downward.append((p.stem.lower(), ref))
    return {"checked": checked, "orphans": sorted(set(orphans)), "downward": sorted(set(downward))}


def has_inbound_refs(dirs, slug):
    """True if any OTHER entry across the altitude chain references `[[slug]]` (or `[[x:slug]]`).
    Demotion safety: never demote a higher entry that lower entries still point UP at."""
    slug = slug.lower()
    dirs = [Path(x) for x in dirs]
    last = len(dirs) - 1
    for pos, d in enumerate(dirs):
        for p in _altitude_entries(pos, last, d) + ([d / MEMORY_INDEX] if pos == 0 else []):
            if p.stem.lower() == slug:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            for m in _WIKILINK_RX.finditer(text):
                if _ref_slug(m.group(1)) == slug:
                    return True
    return False


def archive_entry(memory_dir, filename, archive_subdir=".archive"):
    """Forget a NON-must-always entry: move its body to a cold archive subdir (disk, free; not
    always-present) and drop its `MEMORY.md` index line. Returns True if archived. The caller
    decides WHAT to archive (idle + not must-always); this just does the mechanical move."""
    memory_dir = Path(memory_dir)
    src = memory_dir / filename
    if not src.is_file() or filename == MEMORY_INDEX:
        return False
    archive = memory_dir / archive_subdir
    try:
        archive.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(archive / filename))
    except OSError:
        return False
    index_path = memory_dir / MEMORY_INDEX
    try:
        if index_path.is_file():
            kept = [ln for ln in index_path.read_text(encoding="utf-8").splitlines()
                    if filename not in referenced_files(ln)]
            index_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    except OSError:
        pass
    return True


def over_cap(memory_md_path, max_lines=_CAP_LINES, max_bytes=_CAP_BYTES):
    """(ok, lines, bytes) for a MEMORY.md against the native always-present window. ok is False
    when content would silently truncate out of presence (route overflow per the plan)."""
    p = Path(memory_md_path)
    try:
        raw = p.read_bytes()
    except OSError:
        return True, 0, 0
    lines = raw.count(b"\n") + (1 if raw and not raw.endswith(b"\n") else 0)
    nbytes = len(raw)
    return (lines <= max_lines and nbytes <= max_bytes), lines, nbytes


def index_line(filename, title, hook):
    return "- [%s](%s) - %s" % (title, filename, hook) if hook else "- [%s](%s)" % (title, filename)


def reconcile(memory_dir, dry_run=False):
    """Backfill missing MEMORY.md index lines for topic files. Returns a report dict."""
    memory_dir = Path(memory_dir)
    index_path = memory_dir / MEMORY_INDEX
    existing = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    referenced = referenced_files(existing)

    topics = sorted(
        p for p in memory_dir.glob("*.md")
        if p.name != MEMORY_INDEX
    )
    topic_names = {p.name for p in topics}

    missing = [p for p in topics if p.name not in referenced]
    orphans = sorted(referenced - topic_names)

    new_lines = []
    for p in missing:
        try:
            meta, body = parse_frontmatter(p.read_text(encoding="utf-8"))
        except OSError:
            continue
        new_lines.append(index_line(p.name, derive_title(meta, body, p.name), derive_hook(meta, body)))

    if new_lines and not dry_run:
        if existing.strip():
            block = existing.rstrip("\n") + "\n" + "\n".join(new_lines) + "\n"
        else:
            block = _HEADING + "\n\n" + "\n".join(new_lines) + "\n"
        index_path.write_text(block, encoding="utf-8")

    return {
        "dir": str(memory_dir),
        "topics": len(topics),
        "already_indexed": len(topics) - len(missing),
        "added": [p.name for p in missing],
        "orphans": orphans,
        "dry_run": dry_run,
    }


def _print_report(rep):
    print("memory dir: %s" % rep["dir"])
    print("  topics: %d | already indexed: %d | %s: %d | orphan index lines: %d"
          % (rep["topics"], rep["already_indexed"],
             "would add" if rep["dry_run"] else "added", len(rep["added"]), len(rep["orphans"])))
    for name in rep["added"]:
        print("    + %s" % name)
    for name in rep["orphans"]:
        print("    ! orphan (index line, no file): %s" % name)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Backfill MEMORY.md index lines from topic files.")
    ap.add_argument("dirs", nargs="+", help="one or more .../memory/ directories")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    ap.add_argument("--check", action="store_true",
                    help="treat dirs as an ordered altitude chain (narrow->broad) and verify "
                         "reference integrity (upward-only, no orphans) + over-cap; exit 1 on issues")
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
        for d in args.dirs:
            ok, lines, nbytes = over_cap(Path(d) / MEMORY_INDEX)
            if not ok:
                print("    ! over-cap: %s/MEMORY.md is %d lines / %d bytes (route overflow)"
                      % (d, lines, nbytes))
                problems += 1
        print("TOTAL problems: %d" % problems)
        return 1 if problems else 0

    total_added = 0
    for d in args.dirs:
        rep = reconcile(d, dry_run=args.dry_run)
        _print_report(rep)
        total_added += len(rep["added"])
    print("TOTAL %s: %d" % ("would add" if args.dry_run else "added", total_added))
    return 0


if __name__ == "__main__":
    sys.exit(main())
