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
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    total_added = 0
    for d in args.dirs:
        rep = reconcile(d, dry_run=args.dry_run)
        _print_report(rep)
        total_added += len(rep["added"])
    print("TOTAL %s: %d" % ("would add" if args.dry_run else "added", total_added))
    return 0


if __name__ == "__main__":
    sys.exit(main())
