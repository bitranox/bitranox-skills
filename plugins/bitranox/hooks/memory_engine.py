#!/usr/bin/env python3
"""The single write path for the curated memory store (slug-keyed).

A fact's identity is its SLUG, unique per knowledge TREE; its body lives exactly once at
`<anchor>/.claude-memory/facts/<slug>.md`. The always-loaded per-altitude index is a POINTER BLOCK
inline in `<altitude>/CLAUDE.local.md`: a scope descriptor, the retrieval RECIPE, and one
`- [Title](mem:<slug>) - hook <!-- bx:src=.. bx:pin -->` line per fact. The model reads the block as
cascade text and fetches bodies per the recipe; `uuid_store.resolve` is the programmatic resolver.

Every memory mutation (per-turn capture, migration, reconcile) goes through here - NEVER hand-write
the pointer block or a central body via the Write/Edit tools (the store-edit-guard denies it; this
module writes directly with `Path.write_text`, mtime-neutral). See `uuid_store.py` for the on-disk
format, anchor resolution, the resolver, and the legacy-line transition rules.

Provenance is a `<!-- bx:src=<comma-list> [bx:pin] -->` comment on the pointer line; `source` is a
SET (merged on update). All output is ASCII (` - ` separators, never an em dash).

Pure standard library; cross-platform (pathlib, UTF-8, the O_EXCL lock in self_improve_signals).
"""

import argparse
import json
import re
import sys
from pathlib import Path

import self_improve_signals as sig
import uuid_store as us

SCOPE_BEGIN = sig.SCOPE_MARK_BEGIN          # <!-- bitranox:self-learning -->
SCOPE_END = sig.SCOPE_MARK_END              # <!-- /bitranox:self-learning -->

# The slug algorithm + type prefixes live in uuid_store (single source); aliased here because the
# capture procedure and the migration tools call them via this module.
slugify = us.slugify
_TYPE_PREFIXES = us.TYPE_PREFIXES

# Minimal marker written to a level's CLAUDE.md when the scaffold creates one (so every altitude up to
# the anchor is a real CLAUDE.md-bearing rung). Scope + fact pointers live in CLAUDE.local.md, bodies in
# the anchor's `.claude-memory/`; no `@`-token so it can never fire an import.
_ALTITUDE_MARKER = ("<!-- bitranox memory altitude: scope + fact pointers live in CLAUDE.local.md; "
                    "bodies in the anchor's .claude-memory/. -->\n")


class Entry:
    """One curated fact. Identity is `slug` (unique per TREE); the body lives centrally at
    `<anchor>/.claude-memory/facts/<slug>.md`. `source` is the provenance set; `pin` protects it
    from eviction. A LEGACY entry (pre-pivot pointer) still reads its body from the old sharded
    uuid path until the migration moves it; the engine flips an entry to the current format the
    first time it is UPDATED (and archives the old body)."""

    __slots__ = ("slug", "title", "hook", "body", "source", "pin", "uuid", "legacy")

    def __init__(self, slug, title, hook, body="", source=None, pin=False, uuid="", legacy=False):
        self.slug = slug
        self.title = title
        self.hook = hook or ""
        self.body = body or ""
        self.source = set(source or ())
        self.pin = bool(pin)
        self.uuid = uuid or ""
        self.legacy = bool(legacy)


class SlugCollision(ValueError):
    """Raised when a NEW fact wants a slug that already exists elsewhere in the tree (slugs are
    tree-unique: the body file is the registry). Carries a suggested free slug."""

    def __init__(self, slug, suggestion):
        super().__init__("slug %r already exists in this tree; suggested: %r" % (slug, suggestion))
        self.slug, self.suggestion = slug, suggestion


# ---- store IO (pointer block in CLAUDE.local.md + central bodies), locked + mtime-neutral --------

def _anchor(proj):
    """The anchor dir for `proj` (holds the central `.claude-memory/` body-store). Falls back to `proj`
    itself when there is no CLAUDE.md-bearing ancestor to anchor to (bootstrap)."""
    return us.resolve_anchor(proj) or Path(proj)


# mtime-neutral writer: one implementation, in uuid_store.
_write_if_changed = us.write_if_changed


def read_store(proj):
    """Return (scope, [Entry], {slug: body}) for a level's curated store: the pointer block in its
    `CLAUDE.local.md` + each body from the anchor's central store. Missing/empty -> ("", [], {})."""
    anchor = _anchor(proj)
    try:
        text = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    except OSError:
        text = ""
    scope, pointers = us.parse_pointer_index(text)
    entries, bodies = [], {}
    for p in pointers:
        path = us.legacy_body_path(anchor, p.uuid) if p.legacy else us.body_path(anchor, p.slug)
        try:
            body = path.read_text(encoding="utf-8").rstrip("\n")
        except OSError:
            body = ""
        entries.append(Entry(slug=p.slug, title=p.title, hook=p.hook, body=body,
                             source=p.source, pin=p.pin, uuid=p.uuid, legacy=p.legacy))
        bodies[p.slug] = body
    return scope, entries, bodies


def _commit_store(proj, scope, entries, bodies):
    """Write each entry's central body + the pointer block in `CLAUDE.local.md`; mtime-neutral. Returns
    True if anything changed."""
    anchor = _anchor(proj)
    changed = False
    pointers = []
    for e in entries:
        if not e.legacy:                             # a legacy body stays at its old path until the
            changed |= us.put_body(str(anchor), e.slug, bodies.get(e.slug, e.body))  # migration moves it
        pointers.append(us.Pointer(slug=e.slug, title=e.title, hook=e.hook,
                                   source=e.source, pin=e.pin, uuid=e.uuid, legacy=e.legacy))
    local = sig.claude_local_md_path(proj)
    try:
        text = local.read_text(encoding="utf-8")
    except OSError:
        text = ""
    changed |= us.write_if_changed(local, us.upsert_pointer_block(text, scope or "", pointers))
    return changed


def add_or_update_entry(proj, title, hook, body="", type_=None, source=None, pin=False,
                        scope_default="", slug=None):
    """Upsert a curated fact into `<proj>`'s pointer block + the anchor's central store (the single write
    path). Merges the provenance `source` set on update, ensures the level's pointer block + scope, and
    writes under a lock, mtime-neutral. Returns the slug."""
    slug = slug or slugify(title, type_)
    src = set(source or ())
    anchor = _anchor(proj)
    lock_target = sig.claude_local_md_path(proj)
    with sig.memory_lock(lock_target):
        ensure_level(proj, scope_default=scope_default, _locked=True)
        scope, entries, bodies = read_store(proj)
        by_slug = {e.slug: e for e in entries}
        if slug in by_slug:
            e = by_slug[slug]
            e.title, e.hook = title, (hook or e.hook)
            if body:
                e.body = body
            e.source |= src
            e.pin = e.pin or pin
            if e.legacy:                             # first update flips a legacy entry: the body
                _archive_legacy_body(anchor, e)      # moves to the slug path, the old file archives
                e.legacy, e.uuid = False, ""
        else:
            # Tree-unique slugs: the body file is the registry. A file that exists while THIS level
            # has no pointer for it means another level owns the slug - refuse with a suggestion.
            if us.body_path(anchor, slug).is_file():
                raise SlugCollision(slug, _free_slug(anchor, slug))
            e = Entry(slug=slug, title=title, hook=hook, body=body, source=src, pin=pin)
            entries.append(e)
        bodies[slug] = e.body
        _commit_store(proj, scope or scope_default, entries, bodies)
    return slug


def _free_slug(anchor, slug):
    """The first free `<slug>-N` variant in this tree (the collision suggestion)."""
    n = 2
    while us.body_path(anchor, "%s-%d" % (slug, n)).is_file():
        n += 1
    return "%s-%d" % (slug, n)


def _archive_legacy_body(anchor, entry):
    """Move a flipped legacy entry's old sharded body to `.claude-memory/.archive/` (best-effort;
    the new slug-named body is written by the commit that follows)."""
    try:
        old = us.legacy_body_path(anchor, entry.uuid)
        if old.is_file():
            dest = us.central_facts_dir(anchor).parent / ".archive"
            dest.mkdir(parents=True, exist_ok=True)
            old.rename(dest / old.name)
    except OSError:
        pass


# ---- move: the dream's re-leveling primitive -----------------------------------------------------

_WIKILINK_RX = re.compile(r"\[\[([^\]]+)\]\]")


def _canon_slug(s):
    """Separator-insensitive canonical slug form (matches reconcile's semantics)."""
    return re.sub(r"[\s_]+", "-", (s or "").strip().lower())


def _ref_slug(raw):
    """The slug inside a [[ref]]; tolerates a `type:` prefix and a `|label` suffix."""
    core = raw.split("|", 1)[0].split(":", 1)[-1]
    return _canon_slug(core)


def inbound_ref_sources(levels, slug):
    """[(level, source_slug)] of every OTHER curated entry across `levels` whose hook or body
    contains a `[[slug]]` reference. THE inbound-ref scan (reconcile delegates here); the dream's
    move safety check keys off it."""
    qcanon = _canon_slug(slug)
    out = []
    for level in levels:
        _scope, entries, bodies = read_store(str(level))
        for e in entries:
            if _canon_slug(e.slug) == qcanon:
                continue                             # the target's own line/body does not count
            text = "%s\n%s" % (e.hook, bodies.get(e.slug, ""))
            if any(_ref_slug(m.group(1)) == qcanon for m in _WIKILINK_RX.finditer(text)):
                out.append((str(level), e.slug))
    return out


def has_inbound_refs(levels, slug):
    """True when any other entry across `levels` references `[[slug]]`."""
    return bool(inbound_ref_sources(levels, slug))


def _drop_pointer(level, slug):
    """Remove one pointer line (by slug) from a level's block, under lock, mtime-neutral."""
    local = sig.claude_local_md_path(level)
    with sig.memory_lock(local):
        try:
            text = local.read_text(encoding="utf-8")
        except OSError:
            return False
        scope, pointers = us.parse_pointer_index(text)
        kept = [p for p in pointers if p.slug != slug]
        if len(kept) == len(pointers):
            return False
        us.write_if_changed(local, us.upsert_pointer_block(text, scope, kept))
    return True


def move_entry(from_level, to_level, slug, force=False):
    """Relocate a fact's POINTER LINE between two levels of one tree (the body file never moves -
    the slug is the identity and the body is anchored centrally). ADD-THEN-REMOVE: the pointer is
    upserted at the target (merging provenance/pin - which also completes a crash-interrupted
    move), then dropped at the source; a crash between the two leaves a visible duplicate pointer,
    never a lost fact. Returns {"slug","from","to","direction","moved","refused","warnings"}."""
    rep = {"slug": slug, "from": str(from_level), "to": str(to_level),
           "direction": None, "moved": False, "refused": None, "warnings": []}
    src = Path(from_level).resolve()
    dst = Path(to_level).resolve()
    a_from, a_to = us.resolve_anchor(str(src)), us.resolve_anchor(str(dst))
    if a_from is None or a_to is None or a_from != a_to:
        rep["refused"] = "cross-tree move (or no anchor) - a move stays within one tree; use a lift/copy for cross-tree"
        return rep
    if src == dst:
        rep["refused"] = "same level - nothing to move"
        return rep
    if dst in src.parents:
        rep["direction"] = "up"
    elif src in dst.parents:
        rep["direction"] = "down"
    else:
        rep["refused"] = "sibling levels - a move follows the altitude chain (ancestor <-> descendant only)"
        return rep

    _scope, entries, _bodies = read_store(str(src))
    entry = next((e for e in entries if e.slug == slug), None)
    if entry is None:
        rep["refused"] = "slug %r not found at the from-level" % slug
        return rep
    if entry.legacy:
        rep["refused"] = "entry is an unmigrated legacy pointer - run migrate_to_slug_store.py first"
        return rep

    if rep["direction"] == "down":
        # a citing entry must sit AT or BELOW the new home, or its [[ref]] leaves cascade reach
        chain = {str(Path(x).resolve()) for x in
                 (sig.altitude_chain(str(src)) + sig.altitude_chain(str(dst)))}
        dangling = [(lvl, s) for lvl, s in inbound_ref_sources(sorted(chain), slug)
                    if not (Path(lvl).resolve() == dst or dst in Path(lvl).resolve().parents)]
        if dangling:
            what = ", ".join("%s at %s" % (s, lvl) for lvl, s in dangling)
            if not force:
                rep["refused"] = "down-move would dangle inbound [[refs]]: %s (use --force to move anyway)" % what
                return rep
            rep["warnings"].append("moved despite dangling inbound [[refs]]: %s" % what)

    us.add_pointer(str(dst), slug=slug, title=entry.title, hook=entry.hook,
                   source=entry.source, pin=entry.pin)
    _drop_pointer(str(src), slug)
    rep["moved"] = True
    return rep



def ensure_level(proj, scope_default="", _locked=False):
    """Ensure this level can carry curated memory: (1) its `CLAUDE.local.md` holds a managed pointer
    block with a scope descriptor (created if absent; an existing scope is kept, else a legacy scope
    harvested from `CLAUDE.md`, else `scope_default`), and (2) any LEGACY `<!-- bitranox:self-learning
    -->` scope block still sitting in `CLAUDE.md` is MOVED out into the pointer block (byte-safe outside
    the markers). Best-effort gitignore of `CLAUDE.local.md` + the anchor's `.claude-memory/` when not
    `track_private`. Idempotent + mtime-neutral. No `@import`, no `index.md`."""
    def _do():
        md_path = sig.claude_md_path(proj)
        try:
            md = md_path.read_text(encoding="utf-8")
        except OSError:
            md = ""
        legacy_scope = sig.read_scope_block(md)             # a scope block left in CLAUDE.md (migration)
        if legacy_scope is not None:
            _write_if_changed(md_path, _strip_scope_block(md))
        local = sig.claude_local_md_path(proj)
        try:
            text = local.read_text(encoding="utf-8")
        except OSError:
            text = ""
        scope, pointers = us.parse_pointer_index(text)
        want_scope = scope or (legacy_scope or scope_default or "").strip()
        if us.INDEX_BEGIN not in text or want_scope != scope:
            us.write_if_changed(local, us.upsert_pointer_block(text, want_scope, pointers))
        if not sig.load_config().get("track_private"):     # keep local wiring + central store unpushed
            sig.ensure_gitignored(proj, "CLAUDE.local.md")
            sig.ensure_gitignored(str(_anchor(proj)), us.STORE_DIRNAME + "/")

    if _locked:
        _do()
    else:
        with sig.memory_lock(sig.claude_local_md_path(proj)):
            _do()


def _strip_scope_block(text):
    """Remove a marked `<!-- bitranox:self-learning -->...<!-- /... -->` block from CLAUDE.md text,
    leaving everything else byte-identical (used to relocate a legacy scope block into the pointer
    block)."""
    b = text.find(SCOPE_BEGIN)
    if b < 0:
        return text
    e = text.find(SCOPE_END, b)
    if e < 0:
        return text
    e += len(SCOPE_END)
    head = text[:b].rstrip("\n")
    tail = text[e:].lstrip("\n")
    if head and tail:
        return head + "\n\n" + tail
    return (head or tail) + ("\n" if (head or tail) else "")


# ---- self-heal: repair missing/malformed pointer blocks + markers across the chain -------------

def _ensure_claude_md(proj):
    """Create a minimal marker CLAUDE.md at `proj` when absent (every altitude up to the anchor is a
    CLAUDE.md rung). Returns the created path, or None. Never overwrites an existing CLAUDE.md."""
    md = sig.claude_md_path(proj)
    if md.exists():
        return None
    try:
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(_ALTITUDE_MARKER, encoding="utf-8")
        return str(md)
    except OSError:
        return None


def _heal_level(proj, report):
    """Repair one altitude in place (locked): ensure the CLAUDE.md marker + the CLAUDE.local.md pointer
    block + scope exist, and re-render the pointer block to canonical (heals a malformed SCOPE block or
    drifted grammar). Idempotent + mtime-neutral."""
    with sig.memory_lock(sig.claude_local_md_path(proj)):
        made = _ensure_claude_md(proj)
        if made:
            report["healed"].append(made)
        ensure_level(proj, _locked=True)
        local = sig.claude_local_md_path(proj)
        try:
            text = local.read_text(encoding="utf-8")
        except OSError:
            text = ""
        scope, pointers = us.parse_pointer_index(text)
        canonical = us.upsert_pointer_block(text, scope, pointers)     # round-trip -> canonical grammar
        if canonical != text and _write_if_changed(local, canonical):
            report["healed"].append(str(local))


def heal(proj):
    """Self-heal the WHOLE altitude chain for `proj`: (re)create any missing `CLAUDE.md`,
    `CLAUDE.local.md`, or managed pointer block, NORMALIZE a malformed SCOPE/pointer block to canonical.
    A pointer whose central body is missing is REPORTED (never fabricated). Idempotent, mtime-neutral,
    FAIL-OPEN (never raises). Returns {'healed': [paths], 'orphans': [(level, slug)], 'levels': n}."""
    report = {"healed": [], "orphans": [], "levels": 0}
    try:
        levels = sig.altitude_chain(proj)            # level dirs, narrowest -> the tree's anchor
    except Exception:                                # noqa: BLE001 - self-heal must never raise
        return report
    for level in levels:
        report["levels"] += 1
        level = str(level)
        try:
            _heal_level(level, report)
            anchor = _anchor(level)
            for e in read_store(level)[1]:
                path = us.legacy_body_path(anchor, e.uuid) if e.legacy else us.body_path(anchor, e.slug)
                if not path.is_file():
                    report["orphans"].append((level, e.slug))
        except Exception:                            # noqa: BLE001 - one bad level never blocks the rest
            continue
    return report


def scaffold(proj):
    """Create every MISSING CLAUDE.md (marker) + CLAUDE.local.md (pointer block) from `proj` up to the
    anchor, and the anchor's `.claude-memory/` body-store. Idempotent; returns the created paths."""
    created = []
    try:
        levels = sig.altitude_chain(proj)            # level dirs, narrowest -> the tree's anchor
    except (TypeError, ValueError):
        return created
    for level in levels:
        level = str(level)
        try:
            made = _ensure_claude_md(level)
            if made:
                created.append(made)
            local_before = sig.claude_local_md_path(level).exists()
            ensure_level(level)
            if not local_before and sig.claude_local_md_path(level).exists():
                created.append(str(sig.claude_local_md_path(level)))
        except OSError:
            continue
    try:
        us.central_facts_dir(_anchor(proj)).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return created


# ---- multi-tree: whole-machine discovery + scaffolding -------------------------------------------

def tree_top(proj):
    """{'top', 'store', 'bootstrap'} for `proj`'s knowledge tree: the top dir, its central store
    path, and whether the tree is still BOOTSTRAP (top has no store yet - the first engine write
    creates it). For the model: `tree-top --proj <dir> [--json]`."""
    top = us.resolve_anchor(str(proj))
    if top is None:
        top = Path(proj)
    store = Path(top) / sig.MEMORY_DIRNAME
    return {"top": str(top), "store": str(store), "bootstrap": not store.is_dir()}


def ensure_all_trees(roots=None, apply=False):
    """Discover EVERY knowledge tree under `roots` (default: the configured discovery_roots) and
    scaffold each member's altitude chain (CLAUDE.md marker + CLAUDE.local.md pointer block on every
    rung between the deepest CLAUDE.md and the tree top) - so even completely independent trees
    (a marketing company and a bakery) each come out fully prefilled.

    BOOTSTRAP TIE-BREAK (mis-anchoring protection): a group whose top has NO store yet is scaffolded
    ONLY when no other group's top lies strictly beneath it; otherwise it is reported `ambiguous`
    ("a stray top CLAUDE.md above store-bearing trees; scaffolding would merge them") and skipped -
    never auto-merged. Default is a DRY-RUN report; `apply=True` writes."""
    roots = [str(r) for r in (roots or sig.discovery_roots())]
    groups = sig.tree_groups(sig.find_claude_md_dirs(roots))
    tops = list(groups)
    report = {"roots": roots, "trees": []}
    for top, members in sorted(groups.items(), key=lambda kv: str(kv[0])):
        store = Path(top) / sig.MEMORY_DIRNAME
        entry = {"top": str(top), "store_exists": store.is_dir(),
                 "members": [str(m) for m in members], "status": "ok", "created": []}
        if not store.is_dir():
            beneath = [str(o) for o in tops if o != top and top in o.parents]
            if beneath:
                entry["status"] = "ambiguous"
                entry["why"] = ("stray top CLAUDE.md above %d store-bearing tree(s) (%s); "
                                "scaffolding would merge them" % (len(beneath), ", ".join(sorted(beneath))))
        if entry["status"] == "ok" and apply:
            for m in members:
                entry["created"] += [str(c) for c in scaffold(str(m))]
        report["trees"].append(entry)
    return report



def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


# ---- CLI: the capture procedure invokes this (never hand-writes memory files) ------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Curated memory write engine (the single write path).")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="upsert one curated fact (pointer + central body)")
    a.add_argument("--proj", required=True, help="project cwd (the level to capture at)")
    a.add_argument("--title", required=True)
    a.add_argument("--hook", required=True, help="one-line hook (what makes the fact present)")
    a.add_argument("--type", dest="type_", default=None,
                   choices=[None, "feedback", "project", "reference", "user"])
    a.add_argument("--body", default="", help="the fact body (stored in the central sharded store)")
    a.add_argument("--body-file", default=None, help="read the body from a file (multi-line safe)")
    a.add_argument("--source", default="", help="comma-separated provenance keys")
    a.add_argument("--pin", action="store_true", help="force-keep in the always-loaded pointer index")
    a.add_argument("--scope", default="", help="scope descriptor for this level (set if absent)")
    h = sub.add_parser("heal", help="self-heal missing/malformed pointer blocks/markers across the chain")
    h.add_argument("--proj", required=True, help="project cwd (heals its whole altitude chain)")
    s = sub.add_parser("set-scope", help="upsert (overwrite) a level's pointer-block scope descriptor")
    s.add_argument("--proj", required=True, help="the altitude dir whose scope to set")
    s.add_argument("--scope", required=True, help="the scope-descriptor text (what this level is about)")
    m = sub.add_parser("ensure-memory-structure",
                       help="create missing CLAUDE.md/CLAUDE.local.md/pointer blocks up to the anchor")
    m.add_argument("--proj", required=True, help="the current project dir; the chain is derived from it")
    tt = sub.add_parser("tree-top", help="print the tree top / store / bootstrap flag for a dir")
    tt.add_argument("--proj", required=True)
    tt.add_argument("--json", action="store_true", dest="as_json")
    et = sub.add_parser("ensure-all-trees",
                        help="discover every knowledge tree under the roots and scaffold each (dry-run by default)")
    et.add_argument("--roots", nargs="*", default=None, help="override the configured discovery_roots")
    et.add_argument("--apply", action="store_true", help="write (default: dry-run report)")
    mv = sub.add_parser("move", help="re-level one fact: relocate its pointer line within the tree")
    mv.add_argument("--from-level", required=True, dest="from_level")
    mv.add_argument("--to-level", required=True, dest="to_level")
    mv.add_argument("--slug", required=True)
    mv.add_argument("--force", action="store_true",
                    help="down-move even when inbound [[refs]] would dangle (warning instead)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if args.cmd == "tree-top":
        info = tree_top(args.proj)
        if args.as_json:
            print(json.dumps(info))
        else:
            print("top: %s" % info["top"])
            print("store: %s%s" % (info["store"], "  (bootstrap: not created yet)" if info["bootstrap"] else ""))
        return 0

    if args.cmd == "ensure-all-trees":
        rep = ensure_all_trees(roots=args.roots or None, apply=args.apply)
        tag = "APPLIED" if args.apply else "DRY-RUN"
        print("%s: %d tree(s) under %s" % (tag, len(rep["trees"]), ", ".join(rep["roots"])))
        for tr in rep["trees"]:
            flag = "" if tr["store_exists"] else " [bootstrap]"
            print("  tree %s%s - %d member(s) - %s" % (tr["top"], flag, len(tr["members"]), tr["status"]))
            if tr["status"] == "ambiguous":
                print("    ! %s" % tr["why"])
            for c in tr["created"]:
                print("    + %s" % c)
        return 0

    if args.cmd == "move":
        rep = move_entry(args.from_level, args.to_level, args.slug, force=args.force)
        if rep["refused"]:
            print("! refused: %s" % rep["refused"])
            return 1
        for w in rep["warnings"]:
            print("~ warning: %s" % w)
        print("moved %s: %s -> %s (%s)" % (rep["slug"], rep["from"], rep["to"], rep["direction"]))
        return 0

    if args.cmd == "ensure-memory-structure":
        created = scaffold(args.proj)
        print("ensure-memory-structure: created %d file(s) up the chain" % len(created))
        for p in created:
            print("    +", p)
        return 0

    if args.cmd == "set-scope":
        ensure_level(args.proj)                       # make sure the pointer block exists first
        local = sig.claude_local_md_path(args.proj)
        text = _read_text(local)
        _scope, pointers = us.parse_pointer_index(text)
        changed = us.write_if_changed(local, us.upsert_pointer_block(text, args.scope.strip(), pointers))
        print("scope %s: %s" % ("updated" if changed else "unchanged", local))
        return 0

    if args.cmd == "heal":
        rep = heal(args.proj)
        print("healed %d file(s) across %d level(s)" % (len(rep["healed"]), rep["levels"]))
        for p in rep["healed"]:
            print("    ~ repaired: %s" % p)
        for level, slug in rep["orphans"]:
            print("    ! missing central body (not fabricated): %s [%s]" % (slug, level))
        return 0

    if args.cmd == "add":
        body = args.body
        if args.body_file:
            body = Path(args.body_file).read_text(encoding="utf-8")
        source = [x.strip() for x in args.source.split(",") if x.strip()]
        try:
            slug = add_or_update_entry(args.proj, title=args.title, hook=args.hook, body=body,
                                       type_=args.type_, source=source, pin=args.pin,
                                       scope_default=args.scope)
        except SlugCollision as c:
            print("! refused: %s" % c)
            return 1
        print(slug)
        if us.hook_over_budget(args.hook):
            print("~ warning: hook is %d chars (soft cap %d): rewrite as 1-3 directive sentences"
                  % (len(args.hook), us.HOOK_SOFT_MAX))
        return 0
    ap.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
