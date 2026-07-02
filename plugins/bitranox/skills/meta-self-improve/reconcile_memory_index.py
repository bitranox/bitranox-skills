#!/usr/bin/env python3
"""Reconcile + reference-check a curated `.claude-bx-selflearning/` store (and the loose global tier).

The curated store is `index.md` (the @imported index: a scope block + one markdown-link line per
fact, tiny bodies inlined) + `facts/<slug>.md` (heavy bodies). This tool:
  * BACKFILLS `index.md` from any `facts/<slug>.md` that has no index line (additive/idempotent),
    and reports orphan heavy entries whose `facts/` file is missing;
  * with `--check`, verifies `[[wikilink]]` integrity across an ordered altitude chain (upward-only,
    no dangling), where BOTH an inline `#slug` entry AND a heavy `facts/<slug>.md` are valid link
    targets (so a ref to an inlined fact is never a false orphan), and the always-loaded `index.md`
    is within the cap (with a separate bounded budget for pinned entries).

It is FORMAT-AWARE: a dir holding `index.md`/`facts/` is CURATED; any other dir (e.g. a legacy loose
whole-loaded rules layer) is scanned as `*.md` files. All bitranox altitudes are now curated stores,
including the global one at `~/.claude/.claude-bx-selflearning/`; the loose branch is kept only for a
foreign/legacy layer. `archive_entry` forgets a fact (move its body to `.archive/`, drop its index line).

Pure standard library; cross-platform; ASCII output only.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

# reuse the index.md grammar (single source of truth) from the plugin's hooks dir
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import memory_engine as ME  # noqa: E402

_HOOK_MAX = 160
_TYPE_PREFIXES = ("project", "feedback", "reference", "user")
_WIKILINK_RX = re.compile(r"\[\[([^\]]+)\]\]")
_CAP_LINES = 200
_CAP_BYTES = 25_000
_PIN_CAP_BYTES = 8_000            # pinned inline bodies get their own bounded budget within the cap
_NON_ENTRY = {ME.sig.CURATED_INDEX, "claude.md", "claude.local.md"}


# ---- frontmatter parsing (facts/ bodies still carry name/description frontmatter) ---------------

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


# ---- shape-aware altitude model ----------------------------------------------------------------

def _canon(s):
    """Canonical slug for MATCHING: lowercase, treat `-` and `_` as the same separator."""
    return s.strip().lower().replace("_", "-")


def _ref_slug(token):
    """Normalize a wiki-link token to a bare canonical slug: '[[global:fleet_ssh]]' -> 'fleet-ssh'."""
    return _canon(token.split(":")[-1])


def is_curated(d):
    """A dir is CURATED when it holds the curated store (`index.md` and/or a `facts/` subdir)."""
    d = Path(d)
    try:
        return (d / ME.sig.CURATED_INDEX).is_file() or (d / "facts").is_dir() or d.name == ME.sig.CURATED_DIRNAME
    except OSError:
        return False


def _facts_frontmatter_slugs(facts_dir):
    """{canonical slug -> frontmatter name slug too} for facts/*.md (so a ref by declared name resolves)."""
    out = {}
    try:
        for p in facts_dir.glob("*.md"):
            slugs = {_canon(p.stem)}
            try:
                meta, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
                if meta.get("name"):
                    slugs.add(_canon(meta["name"]))
            except OSError:
                pass
            for s in slugs:
                out[s] = slugs
    except OSError:
        pass
    return out


def altitude_targets(d):
    """Every canonical slug an altitude offers as a `[[wikilink]]` target.
    CURATED: each entry's slug (inline `#slug` AND heavy `facts/<slug>.md`) + facts/ frontmatter names.
    LOOSE (legacy/foreign): each `*.md` stem + frontmatter name (recursive)."""
    d = Path(d)
    slugs = set()
    if is_curated(d):
        try:
            _, entries = ME.parse((d / ME.sig.CURATED_INDEX).read_text(encoding="utf-8"))
        except OSError:
            entries = []
        for e in entries:
            slugs.add(_canon(e.slug))
        for s in _facts_frontmatter_slugs(d / "facts"):
            slugs.add(s)
    else:
        try:
            for p in d.rglob("*.md"):
                if p.name.lower() in _NON_ENTRY:
                    continue
                slugs.add(_canon(p.stem))
                try:
                    meta, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
                    if meta.get("name"):
                        slugs.add(_canon(meta["name"]))
                except OSError:
                    pass
        except OSError:
            pass
    return slugs


def altitude_sources(d):
    """[(source_slug, text)] to scan for `[[wikilinks]]` at an altitude - one source PER ENTRY so a
    ref is attributed to the entry that made it (not the whole file).
    CURATED: each index.md entry -> its hook + inline body; plus each `facts/<slug>.md` body -> slug.
    LOOSE: each `*.md` file's text -> stem."""
    d = Path(d)
    out = []
    if is_curated(d):
        try:
            _, entries = ME.parse((d / ME.sig.CURATED_INDEX).read_text(encoding="utf-8"))
        except OSError:
            entries = []
        for e in entries:
            text = e.hook if e.heavy else (e.hook + "\n" + e.body)
            out.append((_canon(e.slug), text))
        try:
            for p in (d / "facts").glob("*.md"):
                try:
                    out.append((_canon(p.stem), p.read_text(encoding="utf-8")))
                except OSError:
                    continue
        except OSError:
            pass
    else:
        try:
            for p in d.rglob("*.md"):
                if p.name.lower() in _NON_ENTRY:
                    continue
                try:
                    out.append((_canon(p.stem), p.read_text(encoding="utf-8")))
                except OSError:
                    continue
        except OSError:
            pass
    return out


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
    safety: never demote a target that lower entries still point UP at. Matches by the target's own
    slug set (its `#slug` / filename stem / frontmatter name)."""
    qcanon = _canon(slug)
    dirs = [Path(x) for x in dirs]
    target_slugs = {qcanon}
    for d in dirs:                                # expand to every slug the target answers to
        fm = _facts_frontmatter_slugs(Path(d) / "facts")
        if qcanon in fm:
            target_slugs |= fm[qcanon]
    for d in dirs:
        for label, text in altitude_sources(d):
            if _canon(label) in target_slugs:     # the target's own body - skip
                continue
            for m in _WIKILINK_RX.finditer(text):
                if _ref_slug(m.group(1)) in target_slugs:
                    return True
    return False


# ---- cap / pinned budget on the always-loaded index.md -----------------------------------------

def over_cap(index_md_path, max_lines=_CAP_LINES, max_bytes=_CAP_BYTES, max_pin_bytes=_PIN_CAP_BYTES):
    """(ok, lines, bytes, pin_bytes) for an `index.md` against the always-loaded window. ok is False
    when the file exceeds the line/byte cap OR the pinned inline bodies alone exceed their budget
    (route overflow: move non-pinned inline bodies out to `facts/`; a pinned overflow fails LOUD)."""
    p = Path(index_md_path)
    try:
        raw = p.read_bytes()
    except OSError:
        return True, 0, 0, 0
    lines = raw.count(b"\n") + (1 if raw and not raw.endswith(b"\n") else 0)
    nbytes = len(raw)
    pin_bytes = 0
    try:
        _, entries = ME.parse(raw.decode("utf-8", "replace"))
        pin_bytes = sum(len(e.body.encode("utf-8")) for e in entries if e.pin and not e.heavy)
    except (ValueError, UnicodeError):
        pass
    ok = lines <= max_lines and nbytes <= max_bytes and pin_bytes <= max_pin_bytes
    return ok, lines, nbytes, pin_bytes


# ---- reconcile (backfill index.md from orphan facts/ files) ------------------------------------

def reconcile(curated_dir, dry_run=False):
    """Backfill `index.md` index lines for any `facts/<slug>.md` lacking one (additive/idempotent),
    deriving title/hook from the file's frontmatter. Report orphan heavy entries whose facts file is
    missing (never removed here). Returns a report dict."""
    d = Path(curated_dir)
    mem = d / ME.sig.CURATED_INDEX
    facts = d / "facts"
    try:
        scope, entries = ME.parse(mem.read_text(encoding="utf-8"))
    except OSError:
        scope, entries = "", []
    have = {_canon(e.slug) for e in entries}

    fact_files = sorted(facts.glob("*.md")) if facts.is_dir() else []
    missing = [p for p in fact_files if _canon(p.stem) not in have]
    fact_slugs = {_canon(p.stem) for p in fact_files}
    orphans = sorted(_canon(e.slug) for e in entries if e.heavy and _canon(e.slug) not in fact_slugs)

    added = []
    for p in missing:
        try:
            meta, body = parse_frontmatter(p.read_text(encoding="utf-8"))
        except OSError:
            continue
        entries.append(ME.Entry(slug=p.stem, title=derive_title(meta, body, p.name),
                                hook=derive_hook(meta, body), heavy=True,
                                source=[s for s in [meta.get("name")] if s]))
        added.append(p.name)

    if added and not dry_run:
        ME._write_if_changed(mem, ME.render(scope, entries))

    return {"dir": str(d), "facts": len(fact_files), "already_indexed": len(fact_files) - len(missing),
            "added": added, "orphans": orphans, "dry_run": dry_run}


def archive_entry(curated_dir, slug, archive_subdir=".archive"):
    """Forget a fact: drop its `index.md` index line and (if heavy) move `facts/<slug>.md` to
    `.archive/`. Returns True if an entry was removed. Inline bodies are dropped with the line."""
    d = Path(curated_dir)
    mem = d / ME.sig.CURATED_INDEX
    try:
        scope, entries = ME.parse(mem.read_text(encoding="utf-8"))
    except OSError:
        return False
    qcanon = _canon(slug)
    kept = [e for e in entries if _canon(e.slug) != qcanon]
    if len(kept) == len(entries):
        return False
    src = d / "facts" / (slug + ".md")
    if src.is_file():
        archive = d / archive_subdir
        try:
            archive.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(archive / (slug + ".md")))
        except OSError:
            pass
    ME._write_if_changed(mem, ME.render(scope, kept))
    return True


# ---- CLI ---------------------------------------------------------------------------------------

def _print_report(rep):
    print("curated dir: %s" % rep["dir"])
    print("  facts: %d | already indexed: %d | %s: %d | orphan heavy entries: %d"
          % (rep["facts"], rep["already_indexed"],
             "would add" if rep["dry_run"] else "added", len(rep["added"]), len(rep["orphans"])))
    for name in rep["added"]:
        print("    + %s" % name)
    for slug in rep["orphans"]:
        print("    ! orphan (index line, no facts file): %s" % slug)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Backfill/check a curated .claude-bx-selflearning store.")
    ap.add_argument("dirs", nargs="+", help="curated dir(s) to reconcile, or an altitude chain for --check")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    ap.add_argument("--check", action="store_true",
                    help="treat dirs as an ordered altitude chain (narrow->broad) and verify reference "
                         "integrity (upward-only, no orphans) + over-cap; exit 1 on issues")
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
            if is_curated(d):
                ok, lines, nbytes, pin_bytes = over_cap(Path(d) / ME.sig.CURATED_INDEX)
                if not ok:
                    print("    ! over-cap: %s/%s is %d lines / %d bytes (pinned %d) - route overflow"
                          % (d, ME.sig.CURATED_INDEX, lines, nbytes, pin_bytes))
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
