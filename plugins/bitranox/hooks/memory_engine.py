#!/usr/bin/env python3
"""The single write path for the curated memory store (UUID-native).

A fact's identity is its SLUG; its body lives exactly once in the central UUID store at
`<anchor>/.claude-memory/facts/<shard>/<uuid>.md` (uuid = `uuid_store.fact_uuid(altitude, slug)`, the
mount-independent body-file key). The always-loaded per-altitude index is a POINTER BLOCK inline in
`<altitude>/CLAUDE.local.md`: a scope descriptor + one `- [Title](uuid:X) - hook <!-- bx:src=.. bx:pin
bx:slug=s -->` line per fact. The model reads that block as cascade text; `uuid_store.resolve` reads the
bodies from cwd.

Every memory mutation (per-turn capture, migration, reconcile backfill) goes through here - NEVER
hand-write the pointer block or a central body via the Write/Edit tools, or the PostToolUse hooks
(tell-sweep, reformat-md-tables) fire and churn the mtime. This module writes files directly with
`Path.write_text`, mtime-neutral (a no-op write writes nothing). See `uuid_store.py` for the on-disk
format, sharding, anchor resolution, and the resolver.

Provenance is a `<!-- bx:src=<comma-list> [bx:pin] bx:slug=<slug> -->` comment on the pointer line;
`source` is a SET (merged on update) so migration idempotency + cross-tier de-double + two-slugs->same-
identity merge all key off it. All output is ASCII (` - ` separators, never an em dash).

Pure standard library; cross-platform (pathlib, UTF-8, the O_EXCL lock in self_improve_signals).
"""

import argparse
import re
import sys
from pathlib import Path

import self_improve_signals as sig
import uuid_store as us

SCOPE_BEGIN = sig.SCOPE_MARK_BEGIN          # <!-- bitranox:self-learning -->
SCOPE_END = sig.SCOPE_MARK_END              # <!-- /bitranox:self-learning -->

_TYPE_PREFIXES = ("project", "feedback", "reference", "user")
# Minimal marker written to a level's CLAUDE.md when the scaffold creates one (so every altitude up to
# the anchor is a real CLAUDE.md-bearing rung). Scope + fact pointers live in CLAUDE.local.md, bodies in
# the anchor's `.claude-memory/`; no `@`-token so it can never fire an import.
_ALTITUDE_MARKER = ("<!-- bitranox memory altitude: scope + fact pointers live in CLAUDE.local.md; "
                    "bodies in the anchor's .claude-memory/. -->\n")


def slugify(title, type_=None):
    """A stable, filesystem-safe slug from a title (+ optional type prefix), matching the native
    topic-file convention (e.g. 'feedback-no-em-dashes'). Lowercase, hyphen-separated, deduped."""
    base = re.sub(r"[^a-z0-9]+", "-", (title or "").strip().lower()).strip("-")
    base = base or "note"
    if type_ and type_ in _TYPE_PREFIXES and not base.startswith(type_ + "-"):
        base = "%s-%s" % (type_, base)
    return base


class Entry:
    """One curated fact. Identity is `slug`; `uuid` is the central body-file key (derived from the home
    altitude + slug via `uuid_store.fact_uuid`). `source` is the provenance set; `pin` protects it from
    cap-eviction. The body always lives centrally (there is no inline-vs-heavy split any more)."""

    __slots__ = ("slug", "title", "hook", "body", "source", "pin", "uuid")

    def __init__(self, slug, title, hook, body="", source=None, pin=False, uuid=""):
        self.slug = slug
        self.title = title
        self.hook = hook or ""
        self.body = body or ""
        self.source = set(source or ())
        self.pin = bool(pin)
        self.uuid = uuid or ""


# ---- store IO (pointer block in CLAUDE.local.md + central bodies), locked + mtime-neutral --------

def _anchor(proj):
    """The anchor dir for `proj` (holds the central `.claude-memory/` body-store). Falls back to `proj`
    itself when there is no CLAUDE.md-bearing ancestor to anchor to (bootstrap)."""
    return us.resolve_anchor(proj) or Path(proj)


def _write_if_changed(path, text):
    """Write only when content differs (mtime-neutral: a no-op write writes nothing). True if written."""
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


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
        try:
            body = us.body_path(anchor, p.uuid).read_text(encoding="utf-8").rstrip("\n")
        except OSError:
            body = ""
        entries.append(Entry(slug=p.slug, title=p.title, hook=p.hook, body=body,
                             source=p.source, pin=p.pin, uuid=p.uuid))
        bodies[p.slug] = body
    return scope, entries, bodies


def _commit_store(proj, scope, entries, bodies):
    """Write each entry's central body + the pointer block in `CLAUDE.local.md`; mtime-neutral. Returns
    True if anything changed."""
    anchor = _anchor(proj)
    changed = False
    pointers = []
    for e in entries:
        uid = e.uuid or us.fact_uuid(proj, e.slug)
        e.uuid = uid
        changed |= us.put_body(str(anchor), uid, bodies.get(e.slug, e.body))
        pointers.append(us.Pointer(uuid=uid, title=e.title, hook=e.hook,
                                   source=e.source, pin=e.pin, slug=e.slug))
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
        else:
            e = Entry(slug=slug, title=title, hook=hook, body=body, source=src, pin=pin)
            entries.append(e)
        bodies[slug] = e.body
        _commit_store(proj, scope or scope_default, entries, bodies)
    return slug


def add_uuid_entry(altitude, title, hook, body="", type_=None, source=None, pin=False,
                   scope_default="", slug=None):
    """Upsert a fact and return its UUID (thin wrapper over `add_or_update_entry`; the slug is the
    logical identity, the uuid is the central body-file key). Kept as the `add-uuid` CLI entry point."""
    slug = slug or slugify(title, type_)
    add_or_update_entry(altitude, title=title, hook=hook, body=body, type_=type_,
                        source=source, pin=pin, scope_default=scope_default, slug=slug)
    return us.fact_uuid(altitude, slug)


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
        levels = [store.parent for store in sig.altitude_chain(proj)]
    except Exception:                                # noqa: BLE001 - self-heal must never raise
        return report
    for level in levels:
        report["levels"] += 1
        level = str(level)
        try:
            _heal_level(level, report)
            anchor = _anchor(level)
            for e in read_store(level)[1]:
                if not us.body_path(anchor, e.uuid).is_file():
                    report["orphans"].append((level, e.slug))
        except Exception:                            # noqa: BLE001 - one bad level never blocks the rest
            continue
    return report


def scaffold(proj):
    """Create every MISSING CLAUDE.md (marker) + CLAUDE.local.md (pointer block) from `proj` up to the
    anchor, and the anchor's `.claude-memory/` body-store. Idempotent; returns the created paths."""
    created = []
    try:
        levels = [store.parent for store in sig.altitude_chain(proj)]
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
    au = sub.add_parser("add-uuid", help="upsert one fact and print its uuid (alias of add)")
    au.add_argument("--proj", required=True, help="the altitude (home level) to capture the fact at")
    au.add_argument("--title", required=True)
    au.add_argument("--hook", required=True, help="one-line hook (what makes the fact present)")
    au.add_argument("--type", dest="type_", default=None,
                    choices=[None, "feedback", "project", "reference", "user"])
    au.add_argument("--body", default="", help="the fact body (written to the central sharded store)")
    au.add_argument("--body-file", default=None, help="read the body from a file (multi-line safe)")
    au.add_argument("--source", default="", help="comma-separated provenance keys")
    au.add_argument("--pin", action="store_true", help="force-keep in the always-loaded pointer index")
    au.add_argument("--scope", default="", help="scope descriptor for this level (set if absent)")
    h = sub.add_parser("heal", help="self-heal missing/malformed pointer blocks/markers across the chain")
    h.add_argument("--proj", required=True, help="project cwd (heals its whole altitude chain)")
    s = sub.add_parser("set-scope", help="upsert (overwrite) a level's pointer-block scope descriptor")
    s.add_argument("--proj", required=True, help="the altitude dir whose scope to set")
    s.add_argument("--scope", required=True, help="the scope-descriptor text (what this level is about)")
    m = sub.add_parser("ensure-memory-structure",
                       help="create missing CLAUDE.md/CLAUDE.local.md/pointer blocks up to the anchor")
    m.add_argument("--proj", required=True, help="the current project dir; the chain is derived from it")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

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

    if args.cmd in ("add", "add-uuid"):
        body = args.body
        if args.body_file:
            body = Path(args.body_file).read_text(encoding="utf-8")
        source = [x.strip() for x in args.source.split(",") if x.strip()]
        if args.cmd == "add-uuid":
            print(add_uuid_entry(args.proj, title=args.title, hook=args.hook, body=body,
                                 type_=args.type_, source=source, pin=args.pin, scope_default=args.scope))
        else:
            print(add_or_update_entry(args.proj, title=args.title, hook=args.hook, body=body,
                                      type_=args.type_, source=source, pin=args.pin,
                                      scope_default=args.scope))
        return 0
    ap.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
