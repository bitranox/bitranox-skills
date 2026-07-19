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
    """True if any OTHER entry across the chain references `[[slug]]` - move/demotion safety.
    Delegates to the engine's scan (memory_engine.inbound_ref_sources is the single source)."""
    return ME.has_inbound_refs([str(d) for d in dirs], slug)


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
    """True when any OTHER curated level in the tree still has a pointer for `slug` - SIBLINGS and
    DESCENDANTS included, not just `level_dir`'s altitude chain. The archive guard depends on this:
    dropping a pointer at a HIGH level must not archive the body while a LOWER level still points at
    it (that leaves an orphan pointer). Scanning only the ancestor chain missed descendant levels."""
    qcanon = _canon(slug)
    for lvl in _all_curated_levels(anchor):
        if Path(lvl).resolve() == Path(level_dir).resolve():
            continue
        try:
            _s, ptrs = us.parse_pointer_index((Path(lvl) / "CLAUDE.local.md").read_text(encoding="utf-8"))
        except OSError:
            continue
        if any(_canon(x.slug) == qcanon for x in ptrs):
            return True
    return False


def archive_entry(level_dir, slug, archive_subdir=".archive", dry_run=False):
    """Forget a fact: drop its pointer line and move its central body to `<anchor>/.claude-memory/
    <archive_subdir>/`. With `dry_run`, report whether an entry WOULD be removed but write nothing.
    Returns True if an entry was (or, under dry_run, would be) removed."""
    d = Path(level_dir)
    scope, entries, bodies = ME.read_store(str(d))
    qcanon = _canon(slug)
    kept = [e for e in entries if _canon(e.slug) != qcanon]
    if len(kept) == len(entries):
        return False
    if dry_run:                                  # a dry run reports the outcome and writes NOTHING
        return True
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

def _all_curated_levels(anchor):
    """Every curated level dir under `anchor` (a `CLAUDE.local.md` with a managed pointer block).
    Delegates to the engine's `curated_levels_under` (the single tree-walk) so this tool and the
    engine's `lint --tree` never enumerate the tree differently."""
    return ME.curated_levels_under(anchor)


def find_dangling_bodies(anchor):
    """Central bodies (`.../facts/<slug>.md`) that NO curated level in the tree points at - the invisible
    orphans: loaded by nothing, yet the slug is 'taken' so a plain `add` used to refuse re-creating it.
    Returns a sorted list of slugs."""
    facts = us.central_facts_dir(Path(anchor))
    try:
        body_slugs = {p.stem for p in facts.glob("*.md")}
    except OSError:
        return []
    pointed = set()
    for lvl in _all_curated_levels(anchor):
        pointed |= {e.slug for e in ME.read_store(str(lvl))[1]}
    return sorted(body_slugs - pointed)


# An absolute POSIX path mentioned in a fact body. Deliberately conservative: a path is only
# evidence of subject when it is absolute and long enough to resolve to a tree.
_ABS_PATH_RX = re.compile(r"(/[\w.@+-]+(?:/[\w.@+-]+){2,})")


def find_misplaced(anchor):
    """Facts under `anchor` whose body is ABOUT a different tree - the wrong-dir capture, made visible.

    Capture routes by cwd, so a learning discovered about repo B while working in repo A lands in
    A's store. Cross-tree that used to be permanent (move refuses; only a duplicating copy existed),
    and it is invisible in A: nothing in A's own integrity checks knows the fact is foreign. The
    evidence is the body's own absolute paths - if they resolve into ANOTHER tree's anchor and none
    resolve into this one, the fact is filed in the wrong tree.

    Returns [{"level","slug","target_anchor","paths"}], the model's candidates to judge - a path
    mention is EVIDENCE, not proof (a fact can legitimately cite a neighbour), so this reports and
    never relocates on its own.
    """
    anchor_r = Path(anchor).resolve()
    out = []
    for lvl in ME.curated_levels_under(str(anchor_r)):
        _scope, entries, bodies = ME.read_store(lvl)
        for e in entries:
            body = bodies.get(e.slug) or ""
            foreign = {}
            own = 0
            for m in _ABS_PATH_RX.finditer(body):
                p = m.group(1)
                a = ME.us.resolve_anchor(p) or _existing_ancestor_anchor(p)
                if a is None:
                    continue
                a = Path(a).resolve()
                if a == anchor_r:
                    own += 1
                else:
                    foreign.setdefault(str(a), []).append(p)
            # only a fact pointing EXCLUSIVELY at one other tree is a candidate; a body citing both
            # its own tree and a neighbour is normal cross-reference, not a misfile
            if foreign and not own and len(foreign) == 1:
                target, paths = next(iter(foreign.items()))
                out.append({"level": lvl, "slug": e.slug, "target_anchor": target,
                            "paths": sorted(set(paths))})
    return out


def _existing_ancestor_anchor(path):
    """Anchor for the nearest EXISTING ancestor of `path` (a body cites files, not just dirs)."""
    p = Path(path)
    for cand in [p] + list(p.parents):
        if cand.exists():
            return ME.us.resolve_anchor(str(cand))
    return None


def find_decoy_anchors(anchor):
    """Every `.claude-memory` store dir STRICTLY BELOW the tree top - a DECOY anchor. resolve_anchor
    always returns the TOPMOST ancestor carrying CLAUDE.md + a store, so any store dir deeper in the
    tree is dead to the engine, yet the `CLAUDE.local.md` walk-up retrieval text resolves a
    below-level slug to that NEARER store FIRST and reads a stale or empty-stub body. A migration
    that centralizes bodies to the top must delete the drained sub-stores; this flags one it left
    behind. Backup dirs (`<store>-*`, e.g. `-migration-backup-...`) and any store nested inside them
    are NOT decoys - they are in no level's ancestor chain - so descent prunes them. Returns sorted
    absolute paths; empty is the healthy answer (exactly one store per tree, at the top)."""
    import os
    import self_improve_signals as sig
    anchor = Path(anchor).resolve()
    found = []
    for root, dirs, _files in os.walk(str(anchor)):
        rootp = Path(root)
        for d in dirs:
            if d == us.STORE_DIRNAME and rootp.resolve() != anchor:
                found.append(str(rootp / d))
        # never descend into a store, a backup/variant dir (`<store>-*`), or a vendored dir
        dirs[:] = [d for d in dirs
                   if not d.startswith(us.STORE_DIRNAME) and d not in sig.VENDOR_DIRNAMES]
    return sorted(found)


def check_tree(anchor):
    """Tree-wide integrity over EVERY curated level under `anchor` (SIBLINGS included) - the checks
    the chain-scoped `--check` structurally cannot make: a slug pointed at from more than one level
    (slugs are TREE-unique, so any duplicate is a violation heal never sees), a pointer whose central
    body is missing, a `[[ref]]` that resolves NOWHERE in the tree, and central bodies no level points
    at. Only levels anchored at THIS anchor count (a nested independent tree is separate). Returns a
    report dict; `duplicates`/`orphan_pointers`/`orphan_refs` are the HARD problems."""
    anchor = ME._anchor(str(anchor))
    anchor_res = Path(anchor).resolve()
    levels = [lvl for lvl in _all_curated_levels(anchor)
              if Path(ME._anchor(lvl)).resolve() == anchor_res]
    slug_levels = {}                            # canonical slug -> [level dirs pointing at it]
    orphan_pointers = []                        # (level, slug) whose central body is missing
    all_targets = set()                         # every slug offered anywhere in the tree
    ref_sources = []                            # (level, source_slug, ref_slug)
    for lvl in levels:
        _scope, entries, bodies = ME.read_store(lvl)
        for e in entries:
            cslug = _canon(e.slug)
            slug_levels.setdefault(cslug, []).append(lvl)
            all_targets.add(cslug)
            body_p = us.legacy_body_path(anchor, e.uuid) if e.legacy else us.body_path(anchor, e.slug)
            if not body_p.is_file():
                orphan_pointers.append((lvl, e.slug))
            for m in _WIKILINK_RX.finditer(e.hook + "\n" + bodies.get(e.slug, "")):
                ref = _ref_slug(m.group(1))
                if ref and ref != cslug:
                    ref_sources.append((lvl, e.slug, ref))
    duplicates = {s: sorted(lv) for s, lv in slug_levels.items() if len(lv) > 1}
    orphan_refs = sorted(set((lvl, s, r) for (lvl, s, r) in ref_sources if r not in all_targets))

    # Downward/sideways refs: the target EXISTS in the tree but at NO level on the citing fact's
    # ancestor-or-self path, so the ref resolves "somewhere" (not an orphan) yet dangles for the
    # citing level's cascade - a fact citing a sibling subtree's slug, or a broad fact citing a
    # slug that lives below it. `[[refs]]` are upward-only; the chain-only `--check` catches these
    # per chain, but tree-wide `--check-tree` must too (it saw only the nowhere-resolving orphans).
    def _reachable(ref_canon, citing_level):
        cl = Path(citing_level).resolve()
        for t in slug_levels.get(ref_canon, ()):
            tr = Path(t).resolve()
            if tr == cl or tr in cl.parents:            # target at-or-above the citer -> upward, OK
                return True
        return False
    sideways_refs = sorted(set((lvl, s, r) for (lvl, s, r) in ref_sources
                               if r in all_targets and not _reachable(r, lvl)))
    return {"anchor": str(anchor), "levels": len(levels), "duplicates": duplicates,
            "orphan_pointers": sorted(orphan_pointers), "orphan_refs": orphan_refs,
            "sideways_refs": sideways_refs, "danglers": find_dangling_bodies(anchor),
            "decoy_anchors": find_decoy_anchors(anchor)}


def rehome_dangling_bodies(anchor, to_level=None, dry_run=False):
    """Re-attach a pointer for each dangling body at `to_level` (default: the anchor top) so it becomes
    visible + loadable again; a later dream re-levels it. The hook is read from the body frontmatter; the
    title is derived from the slug (a body stores no title). Returns the rehomed slugs."""
    anchor = Path(anchor)
    to_level = str(to_level or anchor)
    done = []
    for slug in find_dangling_bodies(anchor):
        try:
            text = us.body_path(anchor, slug).read_text(encoding="utf-8")
        except OSError:
            continue
        if not dry_run:
            # add with no body keeps the existing central body; Fix A re-adopts the dangling slug.
            ME.add_or_update_entry(to_level, title=slug.replace("-", " "),
                                   hook=ME._body_description(text), slug=slug)
        done.append(slug)
    return done


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
                         "integrity (upward-only, no orphans) + report dangling bodies + emit advisory "
                         "pointer-block size warnings; exit 1 only on reference-integrity issues")
    ap.add_argument("--rehome", action="store_true",
                    help="re-attach every dangling body (a central body no level points at) so it is "
                         "visible + loadable again; a later dream re-levels it. Default target is the "
                         "tree top - use --rehome-to for a subtree so a subtree's danglers are not "
                         "over-promoted to the whole tree")
    ap.add_argument("--rehome-to", metavar="LEVEL", default=None, dest="rehome_to",
                    help="with --rehome: re-attach the dangling bodies at LEVEL (a dir in the tree) "
                         "instead of the tree top - so a subtree's orphaned bodies land in that subtree")
    ap.add_argument("--archive", metavar="SLUG", default=None,
                    help="forget a fact: drop its pointer line at the given level (the positional dir) "
                         "and move its central body to .archive/ (only when no other level still "
                         "points at it)")
    ap.add_argument("--check-tree", action="store_true", dest="check_tree",
                    help="TREE-WIDE integrity from any dir in the tree (resolved to its anchor): flags a "
                         "slug pointed at from >1 level (tree-unique violation), orphan pointers, refs "
                         "resolving nowhere, and dangling bodies - the cross-sibling problems --check "
                         "(chain-only) cannot see; exit 1 on any hard problem")
    ap.add_argument("--check-misplaced", action="store_true", dest="check_misplaced",
                    help="TREE-WIDE wrong-tree audit: facts whose body cites ONLY another tree's "
                         "paths, i.e. captured in the wrong store (capture routes by cwd). Reports "
                         "candidates + the relocate command; never moves anything. Exit 1 if any")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if args.check_misplaced:
        anchor = ME._anchor(args.dirs[0])
        rows = find_misplaced(anchor)
        print("misplacement audit: %s" % anchor)
        for r in rows:
            print("    ? %s [%s]" % (r["slug"], r["level"]))
            print("      body cites ONLY: %s" % r["target_anchor"])
            print("      evidence: %s" % ", ".join(r["paths"][:3]))
            print("      if it IS about that tree: bash <plugin>/hooks/run-python.sh "
                  "<plugin>/hooks/memory_engine.py relocate \\")
            print("        --from-level %s --to-level <level in that tree> --slug %s"
                  % (r["level"], r["slug"]))
        print("TOTAL misplaced: %d" % len(rows))
        if rows:
            print("A path mention is EVIDENCE, not proof - a fact may legitimately cite a "
                  "neighbour. JUDGE each one before relocating.")
        return 1 if rows else 0

    if args.archive:
        level = args.dirs[0]
        if archive_entry(level, args.archive, dry_run=args.dry_run):
            if args.dry_run:
                print("would archive %s (pointer would be dropped at %s) - dry run, nothing written"
                      % (args.archive, level))
            else:
                print("archived %s (pointer dropped at %s)" % (args.archive, level))
            return 0
        print("! no such entry: %s at %s (nothing archived)" % (args.archive, level))
        return 1

    if args.check_tree:
        rep = check_tree(ME._anchor(args.dirs[0]))
        problems = 0
        print("tree integrity: %d curated level(s) under %s" % (rep["levels"], rep["anchor"]))
        for slug, lvls in sorted(rep["duplicates"].items()):
            print("    ! duplicate pointer: %s at %d levels -> %s"
                  % (slug, len(lvls), ", ".join(lvls)))
            problems += 1
        for lvl, slug in rep["orphan_pointers"]:
            print("    ! orphan pointer (no central body): %s [%s]" % (slug, lvl))
            problems += 1
        for lvl, src, ref in rep["orphan_refs"]:
            print("    ! orphan ref: [[%s]] in %s (%s) -> no such entry anywhere in the tree"
                  % (ref, src, lvl))
            problems += 1
        for lvl, src, ref in rep["sideways_refs"]:
            print("    ! sideways/downward ref: [[%s]] in %s (%s) -> target exists but not on this "
                  "level's ancestor chain (dangles here; refs are upward-only)" % (ref, src, lvl))
            problems += 1
        for store in rep["decoy_anchors"]:
            print("    ! decoy anchor (orphan .claude-memory below the tree top; shadows the "
                  "walk-up retrieval path with stale/stub bodies): %s" % store)
            problems += 1
        for slug in rep["danglers"]:
            print("    ~ dangling body (no pointer at any level): %s" % slug)
        print("TOTAL tree problems: %d" % problems)
        if rep["danglers"]:
            print("TOTAL dangling bodies: %d (advisory - run with --rehome to re-attach them)"
                  % len(rep["danglers"]))
        return 1 if problems else 0

    if args.rehome:
        anchor = ME._anchor(args.dirs[0])
        done = rehome_dangling_bodies(anchor, to_level=args.rehome_to, dry_run=args.dry_run)
        for slug in done:
            print("%s: %s" % ("would re-home" if args.dry_run else "re-homed", slug))
        print("TOTAL re-homed: %d" % len(done))
        return 0

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
        danglers = find_dangling_bodies(ME._anchor(args.dirs[0]))
        for slug in danglers:
            print("    ~ dangling body (no pointer at any level): %s" % slug)
        print("TOTAL problems: %d" % problems)
        if warnings:
            print("TOTAL warnings: %d (advisory, not failures)" % warnings)
        if danglers:
            print("TOTAL dangling bodies: %d (advisory - run with --rehome to re-attach them)"
                  % len(danglers))
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
