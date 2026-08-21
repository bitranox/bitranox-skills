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
SET (merged on update). `bx:pin` is a WRITE-PERMISSION gate, not just render-ordering advice: an
ordinary `add` targeting an already-pinned slug raises `PinnedEntry` before any write (see
`add_or_update_entry`); the only way through is the separate `amend-pinned` verb. The movers (`move`,
`relocate`, `rename`) are unaffected - they carry pin through untouched, never refuse. All output is
ASCII (` - ` separators, never an em dash).

Pure standard library; cross-platform (pathlib, UTF-8, the O_EXCL lock in self_improve_signals).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import capture_constraints
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
    `<anchor>/.claude-memory/facts/<slug>.md`. `source` is the provenance set; `pin` marks it as one
    of the iron rules the dream must not silently archive/move/reword AND gates ordinary `add`
    against overwriting it (see `PinnedEntry`). A LEGACY entry (pre-pivot pointer) still reads its
    body from the old sharded uuid path until the migration moves it; the engine flips an entry to
    the current format the first time it is UPDATED (and archives the old body)."""

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


class EmptyBody(ValueError):
    """Raised when a NEW fact is given no body. The frame alone would ship an always-loaded pointer
    promising a rule with nothing behind it, and no integrity check reports an absent body - so it is
    refused at the one moment the content still exists to supply. An UPDATE may still omit the body:
    there, empty means "keep the stored one"."""

    def __init__(self, slug):
        self.slug = slug
        super().__init__("%r is new and its body is empty; a frame-only fact ships a hook with "
                         "nothing behind it. Pass --body/--body-file with the fact plus its "
                         "**Why:** and **How to apply:** lines" % slug)


class HookTooLong(ValueError):
    """Raised when an authored hook exceeds the always-loaded pointer line's hard cap. Refused rather
    than truncated, so no fact ever ships a line that reads complete while its tail is missing - the
    author moves the detail into the body, which is read on demand."""

    def __init__(self, length, limit=None):
        self.length = int(length)
        self.limit = us.HOOK_HARD_MAX if limit is None else int(limit)
        super().__init__("hook is %d chars, over the %d-char hard cap; move the detail into the body "
                         "and keep the hook one trigger-first directive" % (self.length, self.limit))


class PinnedEntry(ValueError):
    """Raised when an ordinary `add` targets a fact whose pointer line already carries `bx:pin`.
    `bx:pin` already marks exactly the facts that must not be silently touched (the iron rules); this
    turns that existing marker into a real write-permission gate instead of prose asking a model not
    to overwrite them. Raised BEFORE any write. The only way through is the separate `amend-pinned`
    verb (never a `--force` flag on `add` - a flag can be reached by accident or copied from an
    example `add` invocation; a distinct verb cannot). The movers (`move`, `relocate`, `rename`) are
    untouched by this gate: they carry `pin` through unchanged and never refuse on it."""

    def __init__(self, slug):
        self.slug = slug
        super().__init__("%s is pinned; report it for human review instead - a human runs "
                         "'amend-pinned --slug %s' to change it deliberately"
                         % (slug, slug))


class UnknownSlug(ValueError):
    """Raised when `amend-pinned` targets a slug this level has no pointer for. The verb carries no
    `--title` (it amends, it does not create), so there is nothing to attach a first write to; use
    `add --pin` to create the fact instead."""

    def __init__(self, slug):
        self.slug = slug
        super().__init__("%r has no existing entry at this level to amend; use "
                         "'add --pin' to create it first" % slug)


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


def _framed_body(slug, hook, type_, body):
    """Wrap a bare body in the native memory-entry frame (frontmatter; the capturer adds **Why:**
    and **How to apply:** in the prose). Probe-verified: bodies matching the genuine entry shape
    get APPLIED mid-reasoning far more reliably than bare prose (the model discounts bodies that
    do not look like real memory entries). A body that already starts with frontmatter passes
    through unchanged."""
    if (body or "").lstrip().startswith("---"):
        return body
    if not type_:
        head = (slug or "").split("-", 1)[0]
        type_ = head if head in us.TYPE_PREFIXES else "project"
    desc = " ".join((hook or "").split())
    return ("---\nname: %s\ndescription: %s\nmetadata:\n  type: %s\n---\n\n%s"
            % (slug, desc, type_, body or ""))


def add_or_update_entry(proj, title, hook, body="", type_=None, source=None, pin=False,
                        scope_default="", slug=None, allow_over_cap_hook=False,
                        allow_pinned_overwrite=False):
    """Upsert a curated fact into `<proj>`'s pointer block + the anchor's central store (the single write
    path). Merges the provenance `source` set on update, ensures the level's pointer block + scope, and
    writes under a lock, mtime-neutral. Returns the slug.

    An over-cap hook raises `HookTooLong` BEFORE anything is written, so a refusal never half-writes
    or clobbers the entry it was updating. `allow_over_cap_hook` exists for the movers only (rehome,
    migrate): they carry text that is ALREADY stored, and refusing there would strand the fact.

    Updating a target already marked `pin` raises `PinnedEntry` BEFORE any write UNLESS
    `allow_pinned_overwrite` is set - the escape hatch `amend_pinned_entry` uses deliberately, and
    nothing else should. Passing `pin=True` to newly PIN an unpinned (or new) entry is unaffected;
    the gate only fires when the entry found at `slug` is ALREADY pinned."""
    slug = slug or slugify(title, type_)
    hook = (hook or "").strip()
    if not allow_over_cap_hook and us.hook_over_hard_cap(hook):
        raise HookTooLong(len(hook))
    src = set(source or ())
    anchor = _anchor(proj)
    # An empty body is the documented UPDATE path ("keep the stored one"), but on a CREATE there is
    # nothing to keep: it writes the frontmatter frame and stops, leaving a convincing always-loaded
    # hook with nothing behind it. Nothing downstream reports that - heal normalizes grammar, --check
    # counts refs, --check-tree checks slug uniqueness, lint --tree looks for UNFRAMED bodies, not
    # absent ones - so the only signal is a reader walking up to an empty file. Refuse here, while
    # the content still exists to supply. Keyed on the body FILE, so a mover carrying stored text
    # (rehome/migrate, which pass no body) is unaffected.
    if not (body or "").strip() and not us.body_path(anchor, slug).is_file():
        raise EmptyBody(slug)
    store_dir = us.central_facts_dir(anchor).parent   # the `.claude-memory` store dir for this tree
    store_existed = store_dir.exists()
    lock_target = sig.claude_local_md_path(proj)
    with sig.memory_lock(lock_target):
        ensure_level(proj, scope_default=scope_default, _locked=True)
        scope, entries, bodies = read_store(proj)
        by_slug = {e.slug: e for e in entries}
        if slug not in by_slug and us.body_path(anchor, slug).is_file() \
                and not _slug_owned_elsewhere(anchor, proj, slug):
            # A DANGLING body (its pointer was lost - e.g. a formatter wrapped the line and a heal
            # round-trip then dropped it) is safe to ADOPT here rather than leave the fact stuck
            # (invisible, yet un-recreatable because the body registers the slug). Reconstruct its
            # Entry so the update path below re-attaches a pointer at this level.
            adopted = _entry_from_body(anchor, slug)
            if adopted is not None:
                entries.append(adopted)
                by_slug[slug] = adopted
        if slug in by_slug:
            e = by_slug[slug]
            # A pinned target refuses an ORDINARY add - the write-permission gate this function
            # exists to enforce for every caller (CLI, reconcile, the dream), not just the CLI layer.
            # The only way through is amend_pinned_entry (allow_pinned_overwrite).
            if e.pin and not allow_pinned_overwrite:
                raise PinnedEntry(slug)
            old_hook = e.hook
            e.title, e.hook = title, (hook or e.hook)
            if body:
                e.body = _framed_body(slug, e.hook, type_, body)
            elif e.hook != old_hook:
                e.body = _reframe_description(e.body, e.hook)   # keep body description in sync with the pointer
            e.source |= src
            e.pin = e.pin or pin
            if e.legacy:                             # first update flips a legacy entry: the body
                _archive_legacy_body(anchor, e)      # moves to the slug path, the old file archives
                e.legacy, e.uuid = False, ""
        else:
            # Tree-unique slugs: the body file is the registry. A body that exists while ANOTHER level
            # owns the slug (checked just above) is a real collision - refuse with a suggestion.
            if us.body_path(anchor, slug).is_file():
                raise SlugCollision(slug, _free_slug(anchor, slug))
            e = Entry(slug=slug, title=title, hook=hook,
                      body=_framed_body(slug, hook, type_, body), source=src, pin=pin)
            entries.append(e)
        bodies[slug] = e.body
        _commit_store(proj, scope or scope_default, entries, bodies)
    if not store_existed and store_dir.exists():      # this add created a brand-new store dir:
        sig.bump_stores_generation()                  # bust the cross-tree dir-cache so recall sees it
    _warn_dangling_wikilinks(anchor, "%s\n%s" % (e.hook or "", e.body or ""), slug)
    return slug


def amend_pinned_entry(proj, slug, hook=None, body=None, source=None):
    """The escape hatch for a pinned fact: the same upsert as `add`, with the pinned refusal skipped.
    Keeps the existing title (the CLI carries no `--title` to change it) and the existing pin state
    (this never unpins - `bx:pin` is untouched, only content changes); an empty/absent `hook` or
    `body` keeps the stored one, matching `add_or_update_entry`'s update semantics. Raises
    `UnknownSlug` when `slug` names no existing entry at this level - amending presumes a prior
    `add --pin`.

    `source` MERGES into the stored provenance set exactly as `add` does (never replaces it): with
    the pin gate in place this is the only remaining path that can record a new `bx:src` key or a
    bumped recurrence on an iron rule, and a pinned fact typically carries several merged keys that
    a replace would discard."""
    _scope, entries, _bodies = read_store(proj)
    by_slug = {e.slug: e for e in entries}
    if slug not in by_slug:
        raise UnknownSlug(slug)
    return add_or_update_entry(proj, title=by_slug[slug].title, hook=hook or "", body=body or "",
                               source=source, slug=slug, allow_pinned_overwrite=True)


def _slug_owned_elsewhere(anchor, proj, slug):
    """True when a level OTHER than `proj` in proj's altitude chain still points at `slug` (the slug is
    owned elsewhere, not a dangling body). Chain-scoped by design: a rare cross-sibling re-capture at
    worst makes a duplicate the dream merges - never corruption - and this stays off the hot path."""
    try:
        chain = sig.altitude_chain(proj)
    except Exception:                                # noqa: BLE001 - never block an add
        return False
    pnorm = Path(proj).resolve()
    for lvl in chain:
        try:
            if Path(lvl).resolve() == pnorm:
                continue
            _s, ptrs = us.parse_pointer_index(sig.claude_local_md_path(lvl).read_text(encoding="utf-8"))
        except OSError:
            continue
        if any(p.slug == slug for p in ptrs):
            return True
    return False


def _body_description(text):
    """The `description:` value (the hook) from a framed body's frontmatter, or '' if absent."""
    m = re.search(r"(?m)^description:[ \t]*(.*)$", text or "")
    return m.group(1).strip() if m else ""


def _reframe_description(text, hook):
    """Return `text` with its frontmatter `description:` reset to `hook` (whitespace collapsed), so a
    hook-only pointer update keeps the body's description in sync (spec: the body description IS the
    hook). An unframed body (no leading frontmatter) is returned unchanged. The replacement is a
    lambda: a hook can carry backslashes (Windows paths) that re.sub would otherwise treat as
    template escapes."""
    if not (text or "").lstrip().startswith("---"):
        return text
    desc = " ".join((hook or "").split())
    return re.sub(r"(?m)^(description:)[ \t]*.*$",
                  lambda m: "%s %s" % (m.group(1), desc), text, count=1)


def _entry_from_body(anchor, slug):
    """Reconstruct an Entry from a dangling central body so `add` can re-adopt it. The hook comes from
    the body's `description:` frontmatter; title/level are not stored in a body, so the caller's update
    supplies them. Returns None if the body is unreadable."""
    try:
        text = us.body_path(anchor, slug).read_text(encoding="utf-8").rstrip("\n")
    except OSError:
        return None
    return Entry(slug=slug, title=slug, hook=_body_description(text), body=text, source=set())


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


def dangling_wikilinks(text, existing):
    """[(target, closest-existing-or-None)] for each `[[ref]]` in `text` whose canonical slug is NOT
    in `existing`. PURE - the write-time catch for an invented-phrase link before it becomes a
    store-wide dangling ref a later `--check-tree` has to find. Deduped, order-preserving."""
    import difflib
    ex = {_canon_slug(s) for s in existing}
    out, seen = [], set()
    for m in _WIKILINK_RX.finditer(text or ""):
        target = _ref_slug(m.group(1))
        if not target or target in ex or target in seen:
            continue
        seen.add(target)
        near = difflib.get_close_matches(target, ex, n=1)
        out.append((target, near[0] if near else None))
    return out


def _existing_slugs(anchor):
    """Every slug pointed at anywhere in the tree (pointer blocks only - cheap, no body reads)."""
    slugs = set()
    for lvl in curated_levels_under(anchor):
        try:
            text = sig.claude_local_md_path(lvl).read_text(encoding="utf-8")
        except OSError:
            continue
        _scope, pointers = us.parse_pointer_index(text)
        slugs.update(p.slug for p in pointers)
    return slugs


def _warn_dangling_wikilinks(anchor, text, self_slug):
    """Best-effort stderr warning (never raises) for each `[[ref]]` in a just-added fact that resolves
    to no slug in the tree - the write-time catch for invented-phrase links (the root cause of a
    dream's orphan refs)."""
    try:
        for target, near in dangling_wikilinks(text, _existing_slugs(anchor) | {self_slug}):
            hint = " (did you mean [[%s]]?)" % near if near else ""
            sys.stderr.write("~ warning: wikilink [[%s]] resolves to no slug in the tree%s\n" % (target, hint))
    except Exception:                                    # noqa: BLE001 - a warning must never break add
        pass


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


def _as_slug_list(slug):
    """The move's slug SET as an ordered, de-duplicated list. Accepts one slug or an iterable of
    them, so every existing single-slug caller keeps working untouched."""
    raw = [slug] if isinstance(slug, str) else list(slug or ())
    seen, out = set(), []
    for s in raw:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _dangling_inbound_after_move(src, dst, slugs):
    """[(level, citer, moved_slug)] for every inbound `[[ref]]` a DOWN-move of `slugs` (all sitting
    at `src`) to `dst` would push out of cascade reach.

    A citer is SAFE when it will sit AT or BELOW `dst` afterwards, and that includes a citer which
    is itself in the moving SET: its pointer lands at `dst` with the rest, so a mutually-citing
    cluster moving together dangles nothing. The exemption is keyed to the pointer AT `src` (the one
    that actually moves), never to the slug NAME - a stray duplicate pointer for a moving slug left
    at a higher level stays put and must still count. Pure read, and it takes the WHOLE set, so the
    answer cannot depend on the order the members are listed in."""
    chain = {str(Path(x).resolve()) for x in
             (sig.altitude_chain(str(src)) + sig.altitude_chain(str(dst)))}
    moving = {_canon_slug(s) for s in slugs}
    out = []
    for s in slugs:
        for lvl, citer in inbound_ref_sources(sorted(chain), s):
            here = Path(lvl).resolve()
            if here == src and _canon_slug(citer) in moving:
                continue                             # a co-mover: it lands at dst too
            if here == dst or dst in here.parents:
                continue                             # already at or below the new home
            out.append((lvl, citer, s))
    return out


def _dedup_pick(entry, dst_entry):
    """Forced dedup of a divergent duplicate pointer: keep the information-richer (LONGER) hook
    regardless of move DIRECTION, union provenance + pin. Direction-independent by construction, so
    it can never discard the richer hook the way a plain overwrite did. Returns ((title, hook,
    source, pin), warning)."""
    keep = entry if len(entry.hook or "") >= len(dst_entry.hook or "") else dst_entry
    fields = (keep.title, keep.hook,
              set(entry.source) | set(dst_entry.source), entry.pin or dst_entry.pin)
    warning = ("duplicate at target: kept the longer hook (%d vs %d chars), unioned provenance, "
               "dropped the shorter source line" % (len(keep.hook or ""),
                                                    min(len(entry.hook or ""), len(dst_entry.hook or ""))))
    return fields, warning


def move_entry(from_level, to_level, slug, force=False):
    """Relocate a fact's POINTER LINE - or a whole SET of them, together - between two levels of one
    tree (the body file never moves - the slug is the identity and the body is anchored centrally).

    `slug` is one slug OR an iterable of slugs. A set moves as ONE unit and the down-move ref guard
    judges every member by its POST-MOVE placement, so a member citing another member is not
    dangling. That is the only non-forced way to demote a MUTUALLY-CITING pair: each one's inbound
    ref is the other, so single-slug moves refuse in BOTH orders and the sole escape was `--force`,
    which is how a ref actually gets stranded. A citer OUTSIDE the set still refuses - the guard is
    made set-aware, not weakened.

    ATOMIC ON REFUSAL: the entire set is validated (present at the from-level, non-legacy, refs,
    duplicate pointers at the target) BEFORE anything is written, so a refusal leaves every pointer
    exactly where it was; a partial move would strand precisely the refs this protects. The write
    phase is per-slug ADD-THEN-REMOVE: the pointer is upserted at the target (merging provenance/pin
    - which also completes a crash-interrupted move), then dropped at the source. An interruption
    mid-set therefore leaves a visible duplicate pointer, never a lost fact, and re-running the SAME
    command completes it (both halves are idempotent); a write error is reported as a refusal naming
    how many pointers already moved, with that same re-run instruction.

    Returns {"slug","slugs","from","to","direction","moved","moved_slugs","refused","warnings"};
    `slug` is the comma-joined set, identical to the input for a single slug."""
    slugs = _as_slug_list(slug)
    rep = {"slug": ", ".join(slugs), "slugs": list(slugs),
           "from": str(from_level), "to": str(to_level),
           "direction": None, "moved": False, "moved_slugs": [], "refused": None, "warnings": []}
    if not slugs:
        rep["refused"] = "no slug given - name at least one fact to move"
        return rep
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
    by_slug = {e.slug: e for e in entries}
    moving = []
    for s in slugs:
        entry = by_slug.get(s)
        if entry is None:
            rep["refused"] = "slug %r not found at the from-level" % s
            return rep
        if entry.legacy:
            rep["refused"] = ("entry %r is an unmigrated legacy pointer - run "
                              "migrate_to_slug_store.py first" % s)
            return rep
        moving.append(entry)

    if rep["direction"] == "down":
        # a citing entry must sit AT or BELOW the new home, or its [[ref]] leaves cascade reach
        dangling = _dangling_inbound_after_move(src, dst, slugs)
        if dangling:
            # name WHICH member the citer blocks only when the set makes that ambiguous, so the
            # single-slug refusal reads exactly as it always has
            what = ", ".join("%s at %s%s" % (citer, lvl, " (cites %s)" % s if len(slugs) > 1 else "")
                             for lvl, citer, s in dangling)
            if not force:
                rep["refused"] = "down-move would dangle inbound [[refs]]: %s (use --force to move anyway)" % what
                return rep
            rep["warnings"].append("moved despite dangling inbound [[refs]]: %s" % what)

    # Duplicate-pointer handling (defect A): the target may ALREADY point at a moving slug - either a
    # crash-interrupted move (add succeeded, drop did not) or a real DIVERGENT duplicate from drift
    # (dedup is exactly when two levels point at one slug). A plain add_pointer overwrites the
    # target's title+hook with the source's, so a divergent duplicate is silent, direction-dependent
    # data loss - the hook is the always-loaded part, and which one survives would depend on move
    # DIRECTION, not on which hook is better. Decide it for EVERY member before the add-then-remove,
    # so a late member's duplicate can never surface after an earlier member was already written:
    _s2, dst_entries, _b2 = read_store(str(dst))
    dst_by_slug = {e.slug: e for e in dst_entries}
    plan, dedup_warnings = [], []
    for entry in moving:
        dst_entry = dst_by_slug.get(entry.slug)
        if dst_entry is not None and (dst_entry.title, dst_entry.hook) != (entry.title, entry.hook):
            if not force:
                # Name the field that ACTUALLY differs: the condition above compares the (title,
                # hook) TUPLE, so it fires on a title-only divergence too, and a message blaming
                # the hook then sends the reader to diff two identical hooks.
                differing = " and ".join(
                    part for part, differs in (("TITLE", dst_entry.title != entry.title),
                                               ("HOOK", (dst_entry.hook or "") != (entry.hook or "")))
                    if differs)
                rep["refused"] = (
                    "target already points at %r with a DIFFERENT %s (duplicate pointer); picking by "
                    "move direction would discard one - dedup deliberately with `add --slug %s` at the "
                    "surviving level, or --force to keep the LONGER hook (an exact tie keeps the "
                    "MOVING entry) and drop the other"
                    % (entry.slug, differing, entry.slug))
                return rep
            fields, warning = _dedup_pick(entry, dst_entry)
            dedup_warnings.append(warning)
        else:
            # No duplicate, or an IDENTICAL one (crash residue): the normal add-then-remove. An
            # identical duplicate merges provenance/pin and completes a crash-interrupted move.
            fields = (entry.title, entry.hook, entry.source, entry.pin)
        plan.append((entry.slug, fields))

    for s, (title, hook, source, pin) in plan:
        try:
            us.add_pointer(str(dst), slug=s, title=title, hook=hook, source=source, pin=pin)
            _drop_pointer(str(src), s)
        except OSError as exc:
            rep["refused"] = (
                "write failed on %r after %d of %d pointer(s) moved: %s - each move is an idempotent "
                "add-then-remove, so re-run the SAME command to complete the set"
                % (s, len(rep["moved_slugs"]), len(plan), exc))
            return rep
        rep["moved_slugs"].append(s)
    rep["warnings"].extend(dedup_warnings)
    rep["moved"] = True
    return rep



def ensure_level(proj, scope_default="", _locked=False):
    """Ensure this level can carry curated memory: (1) its `CLAUDE.local.md` holds a managed pointer
    block with a scope descriptor (created if absent; an existing scope is kept, else a legacy scope
    harvested from `CLAUDE.md`, else `scope_default`), and (2) any LEGACY `<!-- bitranox:self-learning
    -->` scope block still sitting in `CLAUDE.md` is MOVED out into the pointer block (byte-safe outside
    the markers). Best-effort gitignore of `CLAUDE.local.md` + the anchor's `.claude-memory/` when not
    `track_private`. Idempotent + mtime-neutral. No `@import`, no `index.md`.

    REFUSES an excluded altitude (home, the system temp dir, the filesystem root): those dirs are
    never a memory level, and scaffolding them turns e.g. all of /tmp into a fake knowledge tree
    that pollutes recall (bitten twice on 2026-07-05)."""
    _lvl = Path(proj)
    if _lvl == Path(_lvl.anchor) or _lvl in sig._excluded_anchor_dirs():
        raise ValueError("refused: %s is an excluded altitude (home/tempdir/root)" % proj)
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


def _level_needs_heal(proj):
    """READ-ONLY probe: does this level need the (locked) repair pass? True when the CLAUDE.md
    marker or CLAUDE.local.md is missing, or the managed block is absent/non-canonical. The
    every-session heal calls this first so a healthy chain costs no lock and no write."""
    if not sig.claude_md_path(proj).is_file():
        return True
    local = sig.claude_local_md_path(proj)
    try:
        text = local.read_text(encoding="utf-8")
    except OSError:
        return True
    scope, pointers = us.parse_pointer_index(text)
    return us.upsert_pointer_block(text, scope, pointers) != text


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
            if _level_needs_heal(level):             # skip-fast: healthy level = no lock, no write
                _heal_level(level, report)
            anchor = _anchor(level)
            # orphan check by pointer-parse + stat only - bodies are never opened here
            try:
                text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
            except OSError:
                text = ""
            for ptr in us.parse_pointer_index(text)[1]:
                path = (us.legacy_body_path(anchor, ptr.uuid) if ptr.legacy
                        else us.body_path(anchor, ptr.slug))
                if not path.is_file():
                    report["orphans"].append((level, ptr.slug))
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
        facts_dir = us.central_facts_dir(_anchor(proj))
        store_existed = facts_dir.parent.exists()     # the `.claude-memory` store dir
        facts_dir.mkdir(parents=True, exist_ok=True)
        if not store_existed:                          # scaffolding created a brand-new store dir
            sig.bump_stores_generation()               # bust the cross-tree dir-cache
    except OSError:
        pass
    return created


# ---- tree-wide sweeps (curated-level walk shared by the engine + reconcile) ----------------------

def relocate_entry(from_level, to_level, slug, force=False):
    """Relocate a fact to another level, INCLUDING across knowledge trees.

    `move_entry` cannot cross trees: the body is anchored per tree, so moving only the pointer
    would strand it. The only cross-tree path was a COPY, which leaves the stale original behind -
    so a learning captured in the wrong tree could never be fully re-homed and the misplacement was
    permanent. This verb makes the cross-tree move real: the body FILE is copied into the target
    tree's central store, the pointer is created there, then the source pointer is dropped and the
    source body ARCHIVED. Exactly one live copy afterwards, and the old one stays recoverable.

    Same-tree calls delegate to `move_entry` (the body already sits at the right anchor, so it is a
    pointer move and nothing should touch the body).
    Returns {"slug","from","to","cross_tree","relocated","refused","warnings"}.
    """
    rep = {"slug": slug, "from": str(from_level), "to": str(to_level),
           "cross_tree": False, "relocated": False, "refused": None, "warnings": []}
    src, dst = Path(from_level).resolve(), Path(to_level).resolve()
    a_from, a_to = us.resolve_anchor(str(src)), us.resolve_anchor(str(dst))
    if a_from is None or a_to is None:
        rep["refused"] = "no anchor for the source or the target level"
        return rep
    if Path(a_from).resolve() == Path(a_to).resolve():
        m = move_entry(from_level, to_level, slug, force=force)
        rep.update(relocated=m["moved"], refused=m["refused"], warnings=m["warnings"])
        return rep
    rep["cross_tree"] = True

    _scope, entries, _bodies = read_store(str(src))
    entry = next((e for e in entries if e.slug == slug), None)
    if entry is None:
        rep["refused"] = "slug %r not found at the from-level" % slug
        return rep
    if entry.legacy:
        rep["refused"] = "entry is an unmigrated legacy pointer - run migrate_to_slug_store.py first"
        return rep

    # Slugs are TREE-unique, so a divergent slug already in the target tree is a different fact.
    # Landing on it would destroy it silently; never pick a winner here (dedup is a decision).
    _s2, dst_entries, _b2 = read_store(str(dst))
    dst_entry = next((e for e in dst_entries if e.slug == slug), None)
    if dst_entry is not None and (dst_entry.title, dst_entry.hook) != (entry.title, entry.hook):
        rep["refused"] = ("target tree already has slug %r with a DIFFERENT hook - relocating would "
                          "overwrite that fact; dedup deliberately or rename one first" % slug)
        return rep

    # The fact LEAVES this tree entirely, so EVERY inbound [[ref]] in the source tree dangles -
    # including one at the source level itself. A cross-tree ref is never an allowed substitute.
    dangling = inbound_ref_sources(curated_levels_under(a_from), slug)
    if dangling:
        what = ", ".join("%s at %s" % (s, lvl) for lvl, s in dangling)
        if not force:
            rep["refused"] = ("relocating out of this tree would dangle inbound [[refs]]: %s "
                              "(fix the citers, or --force to relocate anyway)" % what)
            return rep
        rep["warnings"].append("relocated despite dangling inbound [[refs]]: %s" % what)

    # COPY-THEN-DROP (same crash-safety direction as move_entry): a crash between the two leaves a
    # visible duplicate, never a lost fact. The body file is copied VERBATIM - it is already framed,
    # and re-writing it through add_or_update_entry would double-wrap the frontmatter.
    src_body, dst_body = us.body_path(a_from, slug), us.body_path(a_to, slug)
    try:
        text = src_body.read_text(encoding="utf-8") if src_body.is_file() else ""
        dst_body.parent.mkdir(parents=True, exist_ok=True)
        dst_body.write_text(text, encoding="utf-8")
    except OSError as exc:
        rep["refused"] = "could not write the body into the target tree: %s" % exc
        return rep
    us.add_pointer(str(dst), slug=slug, title=entry.title, hook=entry.hook,
                   source=set(entry.source) | {"relocated-cross-tree"}, pin=entry.pin)
    _drop_pointer(str(src), slug)

    # Archive the source body only once nothing in the source tree points at the slug any more.
    if not _other_levels_pointing_in(a_from, slug):
        try:
            archive = us.central_facts_dir(a_from).parent / ".archive"
            archive.mkdir(parents=True, exist_ok=True)
            if src_body.is_file():
                src_body.replace(archive / (slug + ".md"))
        except OSError as exc:
            rep["warnings"].append("source body left in place (archive failed: %s)" % exc)
    else:
        rep["warnings"].append("source body kept: another level in the source tree still points at it")
    rep["relocated"] = True
    return rep


def _retarget_refs(text, canon_old, new_slug):
    """Repoint every `[[ref]]` whose target canonicalises to `canon_old`, keeping its own wording.

    A ref may carry a `type:` prefix and a `|label` suffix; both belong to the CITER, not to the
    target's identity, so a rename must preserve them - rewriting `[[reference:x|see here]]` into a
    bare `[[y]]` would silently edit someone else's sentence.
    """
    def repl(match):
        inner = match.group(1)
        if _ref_slug(inner) != canon_old:
            return match.group(0)
        head, sep, label = inner.partition("|")
        parts = head.split(":", 1)                   # mirrors _ref_slug's split, so the two agree
        prefix = parts[0] + ":" if len(parts) == 2 else ""
        return "[[%s%s%s%s]]" % (prefix, new_slug, sep, label)
    return _WIKILINK_RX.sub(repl, text or "")


def _retarget_body_name(text, new_slug):
    """Point a body's frontmatter `name:` at the new slug, which it mirrors.

    Left stale, the body asserts one identity while the pointer asserts another, and a later reader
    has no way to tell which is real.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            break
        if lines[i].startswith("name:"):
            lines[i] = "name: %s\n" % new_slug
            break
    return "".join(lines)


def _rewrite_inbound_refs(anchor, old_slug, new_slug):
    """Repoint every citation of `old_slug` across the tree, in pointer hooks AND bodies.

    Rewriting rather than merely reporting is the whole point of rename: citations that survive it
    are what separate a rename from capturing a new fact and orphaning the old one.
    Returns [(level, citing_slug, "hook"|"body")].
    """
    canon_old = _canon_slug(old_slug)
    touched = []
    for level in curated_levels_under(anchor):
        _scope, entries, _bodies = read_store(str(level))
        for e in entries:
            hook = _retarget_refs(e.hook, canon_old, new_slug)
            if hook != e.hook:
                us.add_pointer(str(level), slug=e.slug, title=e.title, hook=hook,
                               source=set(e.source), pin=e.pin)
                touched.append((str(level), e.slug, "hook"))
            body = us.body_path(anchor, e.slug)
            try:
                text = body.read_text(encoding="utf-8") if body.is_file() else ""
            except OSError:
                continue
            if text:
                retargeted = _retarget_refs(text, canon_old, new_slug)
                if retargeted != text:
                    us.write_if_changed(body, retargeted)
                    touched.append((str(level), e.slug, "body"))
    return touched


def rename_entry(level, slug, to_slug):
    """Rename one fact's SLUG in place, rewriting every `[[ref]]` that cites it.

    The slug is the fact's identity: it names the body file, the pointer's `mem:` target, and every
    wikilink aimed at it. `move` and `relocate` change a fact's LEVEL and never its NAME, so a slug
    whose words have gone wrong - one stating a premise that later turned out false - had no
    correction path. Capturing under a better slug leaves the stale fact live beside the new one,
    and hand-editing the store is exactly what the store-edit guard exists to prevent. The wrong
    name then keeps asserting its false premise from the always-loaded pointer index, which is the
    one place a wrong word is read most often and questioned least.

    Same level, same tree, body CONTENT untouched: only the name moves, along with the body's
    frontmatter `name:` and every inbound citation.
    Returns {"slug","to_slug","level","renamed","refs_rewritten","refused","warnings"}.
    """
    rep = {"slug": slug, "to_slug": to_slug, "level": str(level), "renamed": False,
           "refs_rewritten": [], "refused": None, "warnings": []}
    lvl = Path(level).resolve()
    anchor = us.resolve_anchor(str(lvl))
    if anchor is None:
        rep["refused"] = "no anchor for this level"
        return rep

    canon_new = _canon_slug(to_slug)
    if not canon_new:
        rep["refused"] = "the new slug is empty"
        return rep
    if canon_new != to_slug:
        rep["warnings"].append("new slug normalised to %r" % canon_new)
        to_slug = canon_new
        rep["to_slug"] = to_slug
    if _canon_slug(slug) == canon_new:
        rep["refused"] = "the new slug is the same as the old one"
        return rep

    _scope, entries, _bodies = read_store(str(lvl))
    entry = next((e for e in entries if e.slug == slug), None)
    if entry is None:
        rep["refused"] = "slug %r not found at this level" % slug
        return rep
    if entry.legacy:
        rep["refused"] = "entry is an unmigrated legacy pointer - run migrate_to_slug_store.py first"
        return rep

    # Slugs are TREE-unique, so an existing one names a DIFFERENT fact. Landing on it would destroy
    # that fact silently; never pick a winner here, deduping is a decision.
    for other in curated_levels_under(anchor):
        _s, oentries, _b = read_store(str(other))
        if any(e.slug == to_slug for e in oentries):
            rep["refused"] = ("slug %r already exists at %s - slugs are tree-unique; dedup "
                              "deliberately instead of renaming onto it" % (to_slug, other))
            return rep

    # COPY-THEN-DROP, the same crash-safety direction as move/relocate: a crash between the two
    # leaves a visible duplicate, never a lost fact.
    src_body, dst_body = us.body_path(anchor, slug), us.body_path(anchor, to_slug)
    if dst_body.exists():
        rep["refused"] = "a body file already sits at %s" % dst_body
        return rep
    try:
        if src_body.is_file():
            dst_body.parent.mkdir(parents=True, exist_ok=True)
            dst_body.write_text(_retarget_body_name(src_body.read_text(encoding="utf-8"), to_slug),
                                encoding="utf-8")
        else:
            rep["warnings"].append("no body file at the old slug; renaming the pointer only")
    except OSError as exc:
        rep["refused"] = "could not write the body under the new slug: %s" % exc
        return rep

    us.add_pointer(str(lvl), slug=to_slug, title=entry.title, hook=entry.hook,
                   source=set(entry.source) | {"renamed"}, pin=entry.pin)
    _drop_pointer(str(lvl), slug)

    # A slug carried by more than one level is a pre-existing violation (`heal` and the chain-only
    # `--check` both miss it), but a rename must not LEAVE one behind: dropping only the named
    # level's pointer turns every other one into an orphan aimed at a body that no longer answers to
    # that name. Renaming them too keeps the fact reachable from exactly where it was, and the
    # warning surfaces the duplicate instead of quietly propagating it under a new name.
    for other in curated_levels_under(anchor):
        if Path(other).resolve() == lvl:
            continue
        _s, oentries, _b = read_store(str(other))
        dup = next((e for e in oentries if e.slug == slug), None)
        if dup is None:
            continue
        us.add_pointer(str(other), slug=to_slug, title=dup.title, hook=dup.hook,
                       source=set(dup.source) | {"renamed"}, pin=dup.pin)
        _drop_pointer(str(other), slug)
        rep["warnings"].append("slug was ALSO pointed at from %s - a pre-existing duplicate; "
                               "renamed there too, dedup it deliberately" % other)

    # After the pointer swaps, so the renamed fact's OWN body already sits at the new path and a
    # self-reference is repointed along with everyone else's.
    rep["refs_rewritten"] = _rewrite_inbound_refs(anchor, slug, to_slug)

    try:
        if src_body.is_file():
            archive = us.central_facts_dir(anchor).parent / ".archive"
            archive.mkdir(parents=True, exist_ok=True)
            src_body.replace(archive / (slug + ".md"))
    except OSError as exc:
        rep["warnings"].append("old body left in place (archive failed: %s)" % exc)
    rep["renamed"] = True
    return rep


def _other_levels_pointing_in(anchor, slug):
    """True when any curated level under `anchor` still carries a pointer for `slug`."""
    for lvl in curated_levels_under(anchor):
        _s, entries, _b = read_store(lvl)
        if any(e.slug == slug for e in entries):
            return True
    return False


def curated_levels_under(anchor):
    """Every curated level dir under `anchor` (a `CLAUDE.local.md` carrying a managed pointer block),
    pruning vendored/build/cache dirs and the dream's own backup root - a bounded os.walk of the
    whole subtree, SIBLINGS included.
    THE single tree-walk (reconcile's `_all_curated_levels` delegates here) so the two never drift.

    Backups go under `~/.claude/self-improve-audit/` so a snapshot is never re-read as live memory.
    That holds for a tree on another mount, but `~/.claude` is itself an anchor (it carries a
    `CLAUDE.md`, and `~` is an excluded anchor so the walk stops there), putting the backup root
    INSIDE that tree - every backed-up pointer block then reads as a live level (measured: 6028
    spurious problems from `--check-tree ~/.claude`). Prune by RESOLVED PATH, never by dirname, so a
    project that happens to own a `self-improve-audit/` dir is still walked."""
    audit_root = sig._audit_dir().resolve()
    out = []
    for root, dirs, files in os.walk(str(anchor)):
        dirs[:] = [d for d in dirs if d not in sig.VENDOR_DIRNAMES
                   and Path(root, d).resolve() != audit_root]
        if "CLAUDE.local.md" not in files:
            continue
        try:
            text = sig.claude_local_md_path(root).read_text(encoding="utf-8")
        except OSError:
            continue
        if us.INDEX_BEGIN in text or us.LEGACY_INDEX_BEGIN in text:
            out.append(root)
    return out


def _body_unframed(body):
    """True when a fact body lacks the native-entry reasoning frame (either the `**Why:**` or the
    `**How to apply:**` line) - the shape the model discounts (~5x lower application)."""
    return "**Why:**" not in (body or "") or "**How to apply:**" not in (body or "")


def lint_tree(anchor):
    """READ-ONLY voice/frame sweep over every curated level under `anchor` (defect J - the store had
    no sweep verb, so the debt was rediscovered every dream). Reports: hooks over the HARD cap
    (the write path refuses one, so any that exist are hand-edited or legacy), hooks missing a
    trigger phrase (never fire during
    reasoning), and bodies missing the `**Why:**`/`**How to apply:**` frame. Advisory: a tracked
    backlog number, never a failure. Returns a report dict."""
    anchor = _anchor(str(anchor))
    over_cap, no_trigger, unframed = [], [], []
    for lvl in curated_levels_under(anchor):
        _scope, entries, bodies = read_store(lvl)
        for e in entries:
            if len(e.hook or "") > us.HOOK_HARD_MAX:
                over_cap.append((lvl, e.slug, len(e.hook)))
            if us.hook_missing_trigger(e.hook):
                no_trigger.append((lvl, e.slug))
            if _body_unframed(bodies.get(e.slug, "")):
                unframed.append((lvl, e.slug))
    return {"anchor": str(anchor), "over_cap": over_cap, "no_trigger": no_trigger, "unframed": unframed}


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


def _text_from_flag_or_file(inline, path, inline_flag, file_flag):
    """Resolve a text argument given inline or as a file path -> (text, error_message).

    The file variant exists because a hook (up to 500 chars) and a scope descriptor (multi-line)
    are too long to type inline comfortably, and the shell workaround - `--hook "$(cat f)"` - is a
    command substitution the shell EXECUTES, which the plugin's own guard denies. The file wins when
    both are given, matching --body/--body-file.
    """
    if path:
        try:
            return Path(path).read_text(encoding="utf-8"), None
        except OSError as exc:
            return None, "! refused: cannot read %s (%s)" % (path, exc.strerror or exc)
    if inline is None:
        return None, "! refused: pass %s or %s" % (inline_flag, file_flag)
    return inline, None


# ---- CLI: the capture procedure invokes this (never hand-writes memory files) ------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Curated memory write engine (the single write path).")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="upsert one curated fact (pointer + central body)")
    a.add_argument("--proj", required=True,
                   help="the level to capture at - the fact's SUBJECT repo, usually the cwd but NOT "
                        "when the learning is about another repo you edited (the Stop gate surfaces "
                        "the routing evidence; a cross-tree misfile can never be re-homed)")
    a.add_argument("--title", required=True)
    a.add_argument("--hook", default=None, help="one-line hook (what makes the fact present)")
    a.add_argument("--hook-file", default=None,
                   help="read the hook from a file - use this instead of --hook \"$(cat f)\", which "
                        "is a shell command substitution in self-authored prose")
    a.add_argument("--type", dest="type_", default=None,
                   choices=[None, "feedback", "project", "reference", "user"])
    a.add_argument("--body", default="", help="the fact body (stored in the central sharded store)")
    a.add_argument("--body-file", default=None, help="read the body from a file (multi-line safe)")
    a.add_argument("--source", default="", help="comma-separated provenance keys")
    a.add_argument("--pin", action="store_true",
                   help="force-keep in the always-loaded pointer index; once set, an ordinary add "
                        "refuses to overwrite this fact - use amend-pinned to change it deliberately")
    a.add_argument("--scope", default="", help="scope descriptor for this level (set if absent)")
    a.add_argument("--scope-file", default=None,
                   help="read the scope descriptor from a file - same reason as --hook-file: a "
                        "multi-line descriptor via --scope \"$(cat f)\" is a shell command "
                        "substitution the guard denies. Unlike set-scope, this stays OPTIONAL: "
                        "passing neither --scope nor --scope-file is not an error")
    a.add_argument("--slug", default=None,
                   help="target an existing identity explicitly (title can then change freely)")
    ap_ = sub.add_parser("amend-pinned",
                         help="deliberately change a pinned fact (human use only; "
                              "no autonomous pass invokes this)")
    ap_.add_argument("--proj", required=True)
    ap_.add_argument("--slug", required=True)
    ap_.add_argument("--hook", default=None)
    ap_.add_argument("--hook-file", default=None,
                     help="read the hook from a file - same reason as on add: a 500-char hook via "
                          "--hook \"$(cat f)\" is a shell command substitution the guard denies")
    ap_.add_argument("--body-file", default=None)
    ap_.add_argument("--source", default="",
                     help="comma-separated provenance keys, MERGED into the stored set (never "
                          "replacing it) - with the pin gate this is the only path that can record "
                          "a new bx:src key or a bumped recurrence on an iron rule")
    h = sub.add_parser("heal", help="self-heal missing/malformed pointer blocks/markers across the chain")
    h.add_argument("--proj", required=True, help="project cwd (heals its whole altitude chain)")
    s = sub.add_parser("set-scope", help="upsert (overwrite) a level's pointer-block scope descriptor")
    s.add_argument("--proj", required=True, help="the altitude dir whose scope to set")
    s.add_argument("--scope", default=None, help="the scope-descriptor text (what this level is about)")
    s.add_argument("--scope-file", default=None,
                   help="read the scope descriptor from a file - a descriptor is multi-line, so this "
                        "avoids a shell command substitution")
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
    ln = sub.add_parser("lint", help="tree-wide voice/frame sweep (advisory backlog, read-only)")
    ln.add_argument("--tree", required=True, dest="tree",
                    help="any dir in the tree (resolved to its anchor); sweeps every curated level")
    mv = sub.add_parser("move", help="re-level one fact (or a set that moves together): relocate "
                                     "the pointer line(s) within the tree")
    mv.add_argument("--from-level", required=True, dest="from_level")
    mv.add_argument("--to-level", required=True, dest="to_level")
    mv.add_argument("--slug", required=True, action="append", nargs="+", metavar="SLUG",
                    help="the fact to move; name SEVERAL (repeat --slug, or list them after one "
                         "--slug) to move a SET as one unit - the ref guard then judges each member "
                         "by where the WHOLE set lands, which is the only way to demote a "
                         "mutually-citing pair without --force. All or nothing: one bad member "
                         "refuses the whole set and writes nothing")
    mv.add_argument("--force", action="store_true",
                    help="down-move even when inbound [[refs]] would dangle, OR dedup a divergent "
                         "duplicate-target pointer by keeping the longer hook (warning instead of refusal)")

    rl = sub.add_parser("relocate",
                        help="re-home one fact to another level, INCLUDING across trees (moves the "
                             "body too, then archives the source - no duplicate left behind)")
    rl.add_argument("--from-level", required=True, dest="from_level")
    rl.add_argument("--to-level", required=True, dest="to_level")
    rl.add_argument("--slug", required=True)
    rl.add_argument("--force", action="store_true",
                    help="relocate even when inbound [[refs]] in the source tree would dangle")

    rn = sub.add_parser("rename",
                        help="rename one fact's SLUG in place, rewriting every [[ref]] that cites "
                             "it (same level, same tree, body content untouched)")
    rn.add_argument("--level", required=True,
                    help="the level whose pointer block carries the fact")
    rn.add_argument("--slug", required=True, help="the current slug")
    rn.add_argument("--to-slug", required=True, dest="to_slug",
                    help="the new slug (normalised to canonical form)")
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

    if args.cmd == "lint":
        rep = lint_tree(args.tree)
        print("voice/frame lint: %s" % rep["anchor"])
        for lvl, slug, n in rep["over_cap"]:
            print("    ! hook over HARD cap (%d chars, hand-edited past the refusal): %s [%s]"
                  % (n, slug, lvl))
        for lvl, slug in rep["no_trigger"]:
            print("    ~ hook missing trigger: %s [%s]" % (slug, lvl))
        for lvl, slug in rep["unframed"]:
            print("    ~ body missing **Why:**/**How to apply:** frame: %s [%s]" % (slug, lvl))
        print("TOTAL over-cap hooks: %d | trigger-less hooks: %d | unframed bodies: %d (advisory)"
              % (len(rep["over_cap"]), len(rep["no_trigger"]), len(rep["unframed"])))
        return 0

    if args.cmd == "move":
        # `--slug a --slug b` and `--slug a b` both land as a list of groups; flatten to the set
        slugs = [s for group in args.slug for s in group]
        rep = move_entry(args.from_level, args.to_level, slugs, force=args.force)
        if rep["refused"]:
            print("! refused: %s" % rep["refused"])
            return 1
        for w in rep["warnings"]:
            print("~ warning: %s" % w)
        print("moved %s: %s -> %s (%s)" % (rep["slug"], rep["from"], rep["to"], rep["direction"]))
        return 0

    if args.cmd == "relocate":
        rep = relocate_entry(args.from_level, args.to_level, args.slug, force=args.force)
        if rep["refused"]:
            print("! refused: %s" % rep["refused"])
            return 1
        for w in rep["warnings"]:
            print("~ warning: %s" % w)
        print("relocated %s: %s -> %s (%s)" % (
            rep["slug"], rep["from"], rep["to"],
            "CROSS-TREE: body moved + source archived" if rep["cross_tree"]
            else "same tree: pointer move, body untouched"))
        return 0

    if args.cmd == "rename":
        rep = rename_entry(args.level, args.slug, args.to_slug)
        if rep["refused"]:
            print("! refused: %s" % rep["refused"])
            return 1
        for w in rep["warnings"]:
            print("~ warning: %s" % w)
        print("renamed %s -> %s at %s" % (rep["slug"], rep["to_slug"], rep["level"]))
        for lvl, citer, where in rep["refs_rewritten"]:
            print("    ref repointed: %s (%s) [%s]" % (citer, where, lvl))
        return 0

    if args.cmd == "ensure-memory-structure":
        created = scaffold(args.proj)
        print("ensure-memory-structure: created %d file(s) up the chain" % len(created))
        for p in created:
            print("    +", p)
        return 0

    if args.cmd == "set-scope":
        # Resolve BEFORE ensure_level: a refused call must not leave a level scaffolded behind it.
        scope, err = _text_from_flag_or_file(args.scope, args.scope_file, "--scope", "--scope-file")
        if err:
            print(err)
            return 1
        ensure_level(args.proj)                       # make sure the pointer block exists first
        local = sig.claude_local_md_path(args.proj)
        text = _read_text(local)
        _scope, pointers = us.parse_pointer_index(text)
        changed = us.write_if_changed(local, us.upsert_pointer_block(text, scope.strip(), pointers))
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
        hook, err = _text_from_flag_or_file(args.hook, args.hook_file, "--hook", "--hook-file")
        if err:
            print(err)
            return 1
        hook = hook.strip()
        body = args.body
        if args.body_file:
            body = Path(args.body_file).read_text(encoding="utf-8")
        # Unlike --hook/--hook-file, a scope flag on `add` is OPTIONAL - essentially every capture
        # passes neither. So this is a GUARDED call: `_text_from_flag_or_file` only runs when
        # --scope-file was actually given (it reads the file, or refuses cleanly if it cannot);
        # with no --scope-file, args.scope (default "") is used as-is and the helper's "pass one or
        # the other" refusal is never reached. Routing this unconditionally through the helper is
        # the trap - it turns every ordinary `add` into a refusal the moment anyone tightens
        # --scope's default to match set-scope's mandatory one.
        scope_default = args.scope
        if args.scope_file:
            scope_default, err = _text_from_flag_or_file(args.scope, args.scope_file,
                                                          "--scope", "--scope-file")
            if err:
                print(err)
                return 1
        source = [x.strip() for x in args.source.split(",") if x.strip()]
        try:
            slug = add_or_update_entry(args.proj, title=args.title, hook=hook, body=body,
                                       type_=args.type_, source=source, pin=args.pin,
                                       scope_default=scope_default, slug=args.slug)
        except (SlugCollision, HookTooLong, EmptyBody, PinnedEntry) as c:
            print("! refused: %s" % c)
            return 1
        print(slug)
        if us.hook_over_budget(hook):
            print("~ warning: hook is %d chars (soft cap %d, advisory - fine up to the %d-char hard "
                  "cap; keep it self-sufficient, do not trim load-bearing detail to silence this)"
                  % (len(hook), us.HOOK_SOFT_MAX, us.HOOK_HARD_MAX))
        if us.hook_missing_trigger(hook):
            print("~ warning: hook has no trigger phrase - lead with WHEN it applies "
                  "('When <situation>, <directive>'), or it will not fire during reasoning")
        # `hook`, never `args.hook`: the two are only the same when the caller chose the inline
        # flag, and reading the raw namespace here would silently skip every advisory on a
        # `--hook-file` call (advise() coerces None to "", so it stays green and says nothing).
        for _advice in capture_constraints.advise(hook, body):
            print(f"~ warning: {_advice}")
        # The recurrence count is the one durable "this was already written and did not hold"
        # signal, and this is the moment it is in hand. Naming BOTH ladders is deliberate: the
        # body cannot say whether a repeat is a rule being skipped or work being re-done, and
        # the counter living only in the rule ladder is what kept sending readers to a guard
        # while the jig was never proposed.
        seen = us.recurrence_count(body)
        if seen is not None and seen >= us.RECURRENCE_ESCALATE_AT:
            print("~ warning: this body records recurrence %d - prose has already failed %d times, "
                  "so do NOT just reword it. Escalate and PROPOSE it to the user in THIS turn: a "
                  "deterministic GUARD if a rule keeps being skipped, a JIG (toolbox tool) if the "
                  "same multi-step work keeps being re-done by hand - and BOTH when it is both."
                  % (seen, seen))
        return 0

    if args.cmd == "amend-pinned":
        # The hook is OPTIONAL here (a body-only or source-only amend keeps the stored hook), so
        # neither form being present is not an error - resolve only when one of them was passed,
        # and use the resolved local downstream, never args.hook.
        hook = None
        if args.hook is not None or args.hook_file:
            hook, err = _text_from_flag_or_file(args.hook, args.hook_file, "--hook", "--hook-file")
            if err:
                print(err)
                return 1
            hook = hook.strip()
        body = None
        if args.body_file:
            body = Path(args.body_file).read_text(encoding="utf-8")
        source = [x.strip() for x in args.source.split(",") if x.strip()]
        try:
            slug = amend_pinned_entry(args.proj, slug=args.slug, hook=hook, body=body,
                                      source=source)
        except (SlugCollision, HookTooLong, EmptyBody, UnknownSlug) as c:
            print("! refused: %s" % c)
            return 1
        print(slug)
        return 0
    ap.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
