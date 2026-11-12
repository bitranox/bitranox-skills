#!/usr/bin/env python3
"""The single write path for the curated memory store (slug-keyed).

A fact's identity is its SLUG, unique per knowledge TREE; its body lives exactly once at
`<anchor>/.claude-memory/facts/<slug>.md`. The always-loaded per-altitude index is a POINTER BLOCK
inline in `<altitude>/CLAUDE.local.md`: a scope descriptor, the retrieval RECIPE, and one
`- [Title](mem:<slug>) - hook <!-- bx:pin -->` line per fact. The model reads the block as
cascade text and fetches bodies per the recipe; `uuid_store.resolve` is the programmatic resolver.

Every memory mutation (per-turn capture, migration, reconcile) goes through here - NEVER hand-write
the pointer block or a central body via the Write/Edit tools (the store-edit-guard denies it; this
module writes directly with `Path.write_text`, mtime-neutral). See `uuid_store.py` for the on-disk
format, anchor resolution, the resolver, and the legacy-line transition rules.

The meta comment on a pointer line carries `bx:pin` ONLY. Provenance (`bx:src`) was removed in
5.300.0: nothing read the value and it cost about 15 percent of the always-loaded cascade. An older
line's token is still parsed, then discarded, so a store written by an earlier version loads
without error until the next re-render of that level drops it.

`bx:pin` is a WRITE-PERMISSION gate, not just render-ordering advice: an
ordinary `add` targeting an already-pinned slug raises `PinnedEntry` before any write (see
`upsert_entry`); the only way through is the separate `amend-pinned` verb. The movers (`move`,
`relocate`, `rename`) are unaffected - they carry pin through untouched, never refuse. All output is
ASCII (` - ` separators, never an em dash).

The pin gate's recorded decision (the rejected `bx:owner=human` partition it replaced) is in the
`Decisions` block of `upsert_entry`'s docstring.

Pure standard library; cross-platform (pathlib, UTF-8, the O_EXCL lock in self_improve_signals).
"""

import argparse
import contextlib
import json
import os
import re
import sys
import time
from pathlib import Path

import capture_constraints
import self_improve_signals as sig
import tell_chars
import topic_placement as tp
import topic_store
import uuid_store as us

WRITE_VERBS = frozenset({"add", "amend-pinned", "move", "relocate", "rename", "retitle", "set-scope",
                         "heal", "ensure-memory-structure", "ensure-all-trees", "topics-set-list",
                         "set-topics", "set-level-topics", "set-top-topics", "render-topics"})
"""CLI verbs that write the store or a pointer block; refused under BITRANOX_MEMORY_WRITES=off."""

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
    `<anchor>/.claude-memory/facts/<slug>.md`. `pin` marks it as one
    of the iron rules the dream must not silently archive/move/reword AND gates ordinary `add`
    against overwriting it (see `PinnedEntry`). A LEGACY entry (pre-pivot pointer) still reads its
    body from the old sharded uuid path until the migration moves it; the engine flips an entry to
    the current format the first time it is UPDATED (and archives the old body)."""

    __slots__ = ("slug", "title", "hook", "body", "pin", "uuid", "legacy")

    def __init__(self, slug, title, hook, body="", pin=False, uuid="", legacy=False):
        self.slug = slug
        self.title = title
        self.hook = hook or ""
        self.body = body or ""
        self.pin = bool(pin)
        self.uuid = uuid or ""
        self.legacy = bool(legacy)


class SlugCollision(ValueError):
    """Raised when a NEW fact wants a slug that already exists elsewhere in the tree (slugs are
    tree-unique: the body file is the registry). Carries a suggested free slug."""

    def __init__(self, slug, suggestion):
        super().__init__("slug %r already exists in this tree; suggested: %r" % (slug, suggestion))
        self.slug, self.suggestion = slug, suggestion


_ENGINE_ROUTE = "hooks/memory_engine.py"


class PlacedElsewhere(SlugCollision):
    """Raised when `add` names a fact that is placed by topic from a level holding none of its
    lines. Adopting it there would add a line the placement does not have; the write goes to a
    level that holds one. A SlugCollision, so every caller that reports a collision reports this."""

    def __init__(self, slug, levels):
        # level order (sorted parts: the top first, a parent before its children, siblings by
        # name), so the message and the level it suggests do not follow the walk's listing order
        levels = sorted(levels, key=lambda level: Path(os.path.abspath(str(level))).parts)
        ValueError.__init__(self, "slug %r is placed by topic and has no line at this level; it is "
                                  "read at %s. Write it from one of those levels (%s add --proj "
                                  "%s --slug %s ...), or change where it is read with set-topics"
                            % (slug, ", ".join(str(level) for level in levels), _ENGINE_ROUTE,
                               levels[0], slug))
        self.slug, self.suggestion, self.levels = slug, None, levels


def _copies_of(anchor, slug):
    """[(level dir, Pointer)] for every line of `slug` in the tree, from one walk over its levels."""
    out = []
    for level in curated_levels_under(anchor):
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            if ptr.slug == slug:
                out.append((level, ptr))
    return out


def _placed_slugs(anchor, slugs):
    """The members of `slugs` whose facts are placed by topic: what the renderer manages, a body
    bound to at least one topic that a line can be built from (`title:` and `description:`),
    with a line at some level and no line of it pinned or legacy (`uuid:`) at any level (see
    `_unplaceable_slugs`). A bound fact the renderer
    does not manage stays where its lines are, so the verbs that place lines by hand still take
    it, and the refusals of render-topics and set-topics offer to move exactly those lines.
    Reads one body head per slug; walks the tree's levels once, and only when a body is
    managed. Holds one small record per managed slug."""
    managed = set()
    for slug in slugs:
        head = _read_body_head(us.body_path(anchor, slug))
        if head is not None and _managed_topics(slug, head, ()) is not None:
            managed.add(slug)
    if not managed:
        return set()
    seen, fixed = set(), set()
    for level in curated_levels_under(anchor):
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            if ptr.slug in managed:
                seen.add(ptr.slug)
                if _keeps_in_place(ptr):
                    fixed.add(ptr.slug)
    return seen - fixed


def _placed_copies(anchor, slug):
    """[(level dir, Pointer)] for every line of `slug` when its fact is placed by topic (see
    `_placed_slugs`), else []. One body head; one walk over the levels for a managed body."""
    head = _read_body_head(us.body_path(anchor, slug))
    if head is None or _managed_topics(slug, head, ()) is None:
        return []
    copies = _copies_of(anchor, slug)
    return [] if any(_keeps_in_place(ptr) for _level, ptr in copies) else copies


def _keeps_in_place(ptr):
    """True when the line `ptr` keeps its fact from being placed by topic, wherever it is: a
    pinned line (an always-loaded rule stays where it was put) or a legacy `uuid:` line (the
    renderer builds a line from the body alone and never drops a legacy one, so a tree render
    would add lines no render or check could account for beside it)."""
    return ptr.pin or ptr.legacy


def _same_level(a, b):
    return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


_PLACED_BY_TOPIC = ("%r is placed by topic: where it is read follows its topics and the levels' "
                    "(set-topics, set-level-topics, then render-topics). To place it by hand, "
                    "un-bind it first: " + _ENGINE_ROUTE + " set-topics --proj %s --slug %s "
                    "--clear (its lines collapse to one at the tree top, where a move or "
                    "relocate takes it)")


# A slug that is not a plain filename (`uuid_store.is_valid_slug`). Defined by the store, whose path
# builder raises it too, so the engine's up-front refusal and the store's last line of defence are
# one exception type.
InvalidSlug = us.InvalidSlug
_require_valid_slug = us.require_valid_slug


def _require_known_type(type_):
    """Raise ValueError for a kind outside `TYPE_PREFIXES`; None/empty means 'not given'. The kind is
    written into the body's frontmatter, so an unchecked string would be stored as a fact's type."""
    if type_ and type_ not in _TYPE_PREFIXES:
        raise ValueError("unknown type %r - use one of %s" % (type_, ", ".join(_TYPE_PREFIXES)))


# A skill name as the Skill tool takes it: `name` or `plugin:name`, lower case. Checked with fullmatch
# on [a-z0-9] classes (never `$`, which also matches before a trailing newline) because the value is
# written as a frontmatter line: a newline in it would inject a second key.
_SKILL_RX = re.compile(r"[a-z0-9][a-z0-9._-]*(?::[a-z0-9][a-z0-9._-]*)?")
_SKILL_MAX = 128


class InvalidSkill(ValueError):
    """Raised for a `skill` value that is not a plain skill name (`name` or `plugin:name`)."""

    def __init__(self, skill):
        super().__init__("invalid skill %r - use a skill name as the Skill tool takes it, e.g. "
                         "bitranox:compuse-git (lower case, at most %d chars)" % (skill, _SKILL_MAX))
        self.skill = skill


def _require_valid_skill(skill):
    """Raise `InvalidSkill` unless `skill` is None/empty (not given) or a plain skill name. A
    non-string (the mod bridge passes JSON through) is refused, not handed to the regex."""
    if skill is None or skill == "":
        return
    if not isinstance(skill, str) or len(skill) > _SKILL_MAX or not _SKILL_RX.fullmatch(skill):
        raise InvalidSkill(skill)


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


class TopicsOnCreate(ValueError):
    """Raised when a NEW fact's body brings a frontmatter `topics:` line. Only `set-topics` changes
    a fact's topics: it checks each name against the tree's closed list and records the tagging,
    while a create would store the line unchecked - a name off the list, a line that does not
    parse, a tagging from another tree's list. An UPDATE is unaffected: there the stored line wins
    over whatever the new frame says."""

    def __init__(self, slug):
        self.slug = slug
        super().__init__("%r has no body file yet and the body given carries a frontmatter topics: "
                         "line; topics change only through set-topics. Write the fact without the "
                         "line, then run set-topics on it" % slug)


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


class ExcludedLevel(ValueError):
    """Raised when a write targets HOME, the system temp dir or the filesystem root: those dirs are
    never a memory level (see `ensure_level`). A ValueError subclass, so an in-process caller that
    catches ValueError still does; the CLI maps it to exit 2 rather than letting it escape as a
    traceback."""

    def __init__(self, proj):
        self.proj = proj
        super().__init__("%s is an excluded altitude (home/tempdir/root)" % proj)


class NonLevelDir(ExcludedLevel):
    """Raised, before any write, when `add`, `set-scope`, `move` or `relocate` targets a level
    whose path below the tree's anchor crosses a directory every walk over the tree's levels
    prunes (`uuid_store.is_non_level_dirname`: a virtualenv, a vendored, build or cache dir, the
    store). No walk reads a level there, so a line written there would be read by nobody and its
    body reported dangling by every check. An ExcludedLevel, so every caller that reports an
    excluded altitude reports this. `route` is the verb's own call with `{level}` where the level
    outside the pruned dir goes; `add`'s by default."""

    def __init__(self, proj, name, outside, route=_ENGINE_ROUTE + " add --proj {level} ..."):
        ValueError.__init__(self, "%s is no memory level: its path crosses %r, a directory every "
                                  "walk over the tree's levels prunes (a virtualenv, a vendored, "
                                  "build or cache dir, or the store), so a fact written there "
                                  "would be read by no walk and its body reported dangling. Write "
                                  "it at a level outside it, e.g. %s"
                            % (proj, name, route.replace("{level}", str(outside))))
        self.proj, self.name, self.outside = proj, name, outside


def _pruned_part(anchor, proj):
    """(name, the dir holding it) for the first directory on the way from `anchor` down to `proj`
    that the level walk prunes, else None. Lexical, like the walk's own names; the anchor itself
    is never pruned (the walk starts there), and a `proj` outside it has nothing to cross."""
    top = Path(os.path.abspath(str(anchor)))
    try:
        rel = Path(os.path.abspath(str(proj))).relative_to(top)
    except ValueError:
        return None
    for name in rel.parts:
        if us.is_non_level_dirname(name):
            return name, str(top)
        top = top / name
    return None


def _pruned_refusal(anchor, level, route):
    """The `NonLevelDir` text when `level` crosses a directory the level walk prunes below
    `anchor`, else None; `route` as `NonLevelDir` takes it. For the verbs that report a refusal
    rather than raise one."""
    pruned = _pruned_part(anchor, level)
    return None if pruned is None else str(NonLevelDir(str(level), *pruned, route=route))


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


# ---- the placement lock: one per tree, held by everything that changes where a line is read ---
#
# A level lock covers one level's file, and a render, a set-topics and a write to a placed fact
# each touch several levels plus a body: a peer landing between two of their steps saw half a
# change and acted on it (a render's REMOVE dropping every line of a fact its ADD never placed; a
# render putting back the lines a --clear collapse had just dropped). So each of them holds this
# lock across ALL of its reads and writes: `render_topics` (a real run, both scopes, census to
# last drop), `set_fact_topics` (checks, collapse lines and bodies), `upsert_entry` of a fact
# bound to a topic, and `retitle_entry`, `rename_entry` and reconcile's archive of any fact in a
# tree with a topic list. Dry runs and read-only checks take none (see `_write_lock`).
#
# Lock order, which keeps this deadlock-free by construction: the placement lock is taken FIRST,
# before any level lock, and never while one is held. Every holder above takes it as its first
# lock and takes level locks (one at a time) only inside it; nothing that holds a level lock
# calls any of them.
#
# The mechanism is the level locks' own: `sig.memory_lock`, an O_EXCL `<target>.lock` file,
# reclaimed when its mtime is older than `sig._LOCK_STALE_S` (a crashed holder). A long holder
# keeps it from looking stale with a heartbeat (`_placement_heartbeat`): a render refreshes the
# lock file's mtime once per level it walks in each pass, and set-topics once per row, so only a
# holder that stops walking (crashed or hung) ages past the reclaim.

PLACEMENT_LOCK_TIMEOUT_S = 30.0
"""How long a verb waits for the placement lock before refusing with PlacementLockBusy: longer than
a level lock's 5 s, because the holder may be a whole-tree render."""


def _placement_target(anchor):
    """The path `sig.memory_lock` locks for `anchor`'s tree: `<anchor>/.claude-memory/placement`."""
    return us.central_facts_dir(anchor).parent / "placement"


def placement_lock_path(anchor):
    """The file whose existence IS the tree's placement lock: `<store>/placement.lock`."""
    return Path(str(_placement_target(anchor)) + ".lock")


class PlacementLockBusy(TimeoutError):
    """The placement lock stayed held past the wait. A TimeoutError with only a message (strerror
    None), so the CLI prints it as `! error: <message>` and exits 2 like any lock contention."""

    def __init__(self, anchor, verb, waited):
        super().__init__(
            "%s waited %g s for the placement lock of the tree %s (%s): another render-topics, "
            "set-topics, or write to a fact placed by topic holds it. Run %s again once that one "
            "finishes; a lock left by a holder that crashed is reclaimed once it is %d s old"
            % (verb, waited, anchor, placement_lock_path(anchor), verb, int(sig._LOCK_STALE_S)))


_HEARTBEAT_AFTER_S = sig._LOCK_STALE_S / 4
"""How old the held placement lock's mtime may get before a heartbeat refreshes it: well inside
the reclaim age, so a holder that beats at least once per this many seconds never looks stale,
and one stat per beat is all a fresh lock costs."""

_HELD_PLACEMENT_LOCKS = []
"""The lock files of the placement locks this process holds now, innermost last."""


def _placement_heartbeat():
    """Refresh the mtime of every placement lock this process holds once it is older than
    _HEARTBEAT_AFTER_S. The long holders call it once per level they walk in each pass (render)
    and once per row (set-topics), so a holder that is still working never ages past
    `sig._LOCK_STALE_S` and has its lock reclaimed by a waiter. A lock file gone (a peer
    reclaimed it) is left alone: refreshing would not give the lock back."""
    for lock in _HELD_PLACEMENT_LOCKS:
        try:
            if time.time() - lock.stat().st_mtime > _HEARTBEAT_AFTER_S:
                os.utime(lock)
        except OSError:
            continue


@contextlib.contextmanager
def placement_lock(anchor, verb, timeout=PLACEMENT_LOCK_TIMEOUT_S):
    """Hold `anchor`'s placement lock for the block; `verb` names the caller in a timeout's
    PlacementLockBusy. Take it before any level lock (see the section comment). While it is held,
    `_placement_heartbeat` keeps its mtime fresh."""
    with contextlib.ExitStack() as held:
        try:
            held.enter_context(sig.memory_lock(_placement_target(anchor), timeout=timeout))
        except TimeoutError as exc:
            raise PlacementLockBusy(anchor, verb, timeout) from exc
        _HELD_PLACEMENT_LOCKS.append(placement_lock_path(anchor))
        try:
            yield
        finally:
            _HELD_PLACEMENT_LOCKS.pop()


def _placement_lock_if_bound(anchor, slug, verb):
    """`add`'s placement lock: held when `slug`'s body is bound to a topic, else none.

    Read without the lock, as a superset of "placed by topic": `add` then decides placed under
    the lock. `add` writes the fact at ONE level, under that level's lock, so a fact bound and
    placed by peers after this read meets an `add` that either finds its line there (and updates
    it, a line the next render refreshes) or finds it gone and refuses as a collision; it can
    neither drop a line elsewhere nor put one back. `add` is also the per-turn capture path, so it
    does not wait behind a render for a fact no render manages."""
    if not us.is_valid_slug(slug) or not read_body_topics(us.body_path(anchor, slug)):
        return contextlib.nullcontext()
    return placement_lock(anchor, verb)


def placement_lock_if_listed(anchor, verb):
    """The placement lock for a verb that walks EVERY level holding a fact's line (`rename`,
    `retitle`, reconcile's archive): held whenever `anchor`'s tree has a topic list, else none.
    Such a verb reads a level, then writes it, level after level; a fact bound, placed and
    un-bound by peers between two of those steps would get a line put back where a collapse had
    dropped it. Holding the lock for any fact of a tree that places by topic rules that out; a
    tree without a list places nothing, and nothing there takes it."""
    if anchor is None or not topic_store.store_path(anchor).is_file():
        return contextlib.nullcontext()
    return placement_lock(anchor, verb)


# mtime-neutral writer: one implementation, in uuid_store.
_write_if_changed = us.write_if_changed

# The strict store reader and its error: one implementation, in uuid_store, so a read that
# add_pointer makes there fails with the class this module's CLI maps to exit 2.
TreeWalkError = us.TreeWalkError
read_store_text = us.read_store_text


def read_store(proj):
    """Return (scope, [Entry], {slug: body}) for a level's curated store: the pointer block in its
    `CLAUDE.local.md` + each body from the anchor's central store. Missing/empty -> ("", [], {}); a
    missing body reads as "". Raises TreeWalkError when the level file or a body exists but cannot
    be read or is not UTF-8: every writer builds on this answer, and an entry read as bodiless or a
    level read as empty is one it would then rewrite."""
    anchor = _anchor(proj)
    text = read_store_text(sig.claude_local_md_path(proj))
    scope, pointers = us.parse_pointer_index(text)
    entries, bodies = [], {}
    for p in pointers:
        path = us.legacy_body_path(anchor, p.uuid) if p.legacy else us.body_path(anchor, p.slug)
        body = read_store_text(path).rstrip("\n")
        entries.append(Entry(slug=p.slug, title=p.title, hook=p.hook, body=body,
                             pin=p.pin, uuid=p.uuid, legacy=p.legacy))
        bodies[p.slug] = body
    return scope, entries, bodies


def _commit_store(proj, scope, entries, bodies):
    """Write each entry's central body + the pointer block in `CLAUDE.local.md`; mtime-neutral. Returns
    True if anything changed. Refuses first under BITRANOX_MEMORY_WRITES=off: reconcile's archive
    commits a pointer block through here without going through `upsert_entry`."""
    sig.refuse_if_memory_writes_off()
    anchor = _anchor(proj)
    changed = False
    pointers = []
    for e in entries:
        if not e.legacy:                             # a legacy body stays at its old path until the
            changed |= us.put_body(str(anchor), e.slug, bodies.get(e.slug, e.body))  # migration moves it
        pointers.append(us.Pointer(slug=e.slug, title=e.title, hook=e.hook,
                                   pin=e.pin, uuid=e.uuid, legacy=e.legacy))
    local = sig.claude_local_md_path(proj)
    text = read_store_text(local)
    _warn_dropped_invalid_pointers(local, text)
    changed |= us.write_if_changed(local, us.upsert_pointer_block(text, scope or "", pointers))
    return changed


def _warn_dropped_invalid_pointers(local, text):
    """Name, on stderr, each pointer line the canonical re-render about to happen will drop because
    its slug or legacy uuid is not a plain store name. The parser already refuses to follow such a
    line; this keeps its removal from being silent."""
    for raw in us.invalid_pointer_lines(text):
        print("memory_engine: dropping a pointer whose slug is not a plain filename (%s): %s"
              % (local, raw), file=sys.stderr)


_FRONTMATTER_BLOCK_RX = re.compile(r"---[ \t]*\r?\n(.*?\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.S)


def _frontmatter(body):
    """(head, match): `body` without leading whitespace, and the match of its leading frontmatter
    block - None unless the block is CLOSED and carries a `name:` key. `match.group(1)` is the text
    between the delimiters, ending in its line break.

    The one test of "is this frontmatter" for every reader and rewriter of a body: a body that
    merely opens with a markdown horizontal rule has no frame, and a helper asking only
    `startswith("---")` wrote a `metadata:` block onto the end of such a body's prose."""
    head = (body or "").lstrip()
    m = _FRONTMATTER_BLOCK_RX.match(head)
    if m and re.search(r"(?m)^name:", m.group(1) or ""):
        return head, m
    return head, None


def _has_prose(body):
    """True when `body` holds text below its frontmatter frame (or any text, unframed). A blank
    body and a frame-only body both say nothing, and either one, taken as a body, replaced a stored
    fact's prose with an empty frame."""
    head, m = _frontmatter(body)
    return bool((head[m.end():] if m else head).strip())


def _has_frontmatter(body):
    """True when `body` opens with a closed frontmatter block that carries a `name:` key."""
    return _frontmatter(body)[1] is not None


def _framed_body(slug, hook, type_, body):
    """Wrap a bare body in the native memory-entry frame (frontmatter; the capturer adds **Why:**
    and **How to apply:** in the prose). Probe-verified: bodies matching the genuine entry shape
    get APPLIED mid-reasoning far more reliably than bare prose (the model discounts bodies that
    do not look like real memory entries). A body that already starts with frontmatter passes
    through unchanged - REAL frontmatter only (a closing `---` line and a `name:` key): a body
    that merely opens with a markdown horizontal rule used to pass through as-is, and was stored
    with no name, description or type."""
    if _has_frontmatter(body):
        return body
    if not type_:
        head = (slug or "").split("-", 1)[0]
        type_ = head if head in us.TYPE_PREFIXES else "project"
    desc = " ".join((hook or "").split())
    # The frame ends in ONE blank line; a body file that opens with its own blank line(s) would
    # otherwise double it, and a read-back-and-write round trip would grow the gap every time.
    prose = _LEADING_BLANK_LINES_RX.sub("", body or "")
    return ("---\nname: %s\ndescription: %s\nmetadata:\n  type: %s\n---\n\n%s"
            % (slug, desc, type_, prose))


# Whole blank lines only: the first CONTENT line keeps its indentation (an indented code block).
_LEADING_BLANK_LINES_RX = re.compile(r"\A(?:[ \t]*\r?\n)+")


def _synced_frame(slug, hook, type_, text):
    """Return framed `text` with its frame agreeing with this write: `name:` is the slug,
    `description:` the hook, and an EXPLICIT `type_` replaces the kind the frame records.

    A caller that hands back a body it read (the text `factedit.py show --body` prints, or a stored
    body file) brings the OLD frame with it. `_framed_body` passes such a body through, so without
    this its `description:` kept the previous hook while the pointer took the new one, and an
    explicit --type was dropped in silence. The prose below the frame is never touched. An unframed
    `text` is returned unchanged."""
    head, m = _frontmatter(text)
    if m is None:
        return text
    inner = m.group(1)
    inner, _n = re.subn(r"(?m)^(name:)[ \t]*[^\r\n]*", lambda d: "%s %s" % (d.group(1), slug),
                        inner, count=1)
    text = _reframe_description(_with_frame(head, m, inner), hook)
    if type_ and _body_type(text) != type_:
        text = _retype_body(slug, hook, type_, text)
    return text


def add_or_update_entry(proj, title, hook, body="", type_=None, pin=False,
                        scope_default="", slug=None, allow_over_cap_hook=False,
                        allow_pinned_overwrite=False, skill=None):
    """`upsert_entry` returning only the slug: the single write path for every caller that does not
    need to know whether the fact was new."""
    return upsert_entry(proj, title, hook, body=body, type_=type_, pin=pin,
                        scope_default=scope_default, slug=slug,
                        allow_over_cap_hook=allow_over_cap_hook,
                        allow_pinned_overwrite=allow_pinned_overwrite, skill=skill)[0]


def upsert_entry(proj, title, hook, body="", type_=None, pin=False,
                 scope_default="", slug=None, allow_over_cap_hook=False,
                 allow_pinned_overwrite=False, skill=None):
    """Upsert a curated fact into `<proj>`'s pointer block + the anchor's central store (the single write
    path). Ensures the level's pointer block + scope, and writes under a lock, mtime-neutral.
    Returns (slug, created): `created` is True when this call made a new fact, decided under the
    lock from the store it read, False when it updated one (a dangling body adopted back counts as
    an update).

    An over-cap hook raises `HookTooLong` BEFORE anything is written, so a refusal never half-writes
    or clobbers the entry it was updating. `allow_over_cap_hook` exists for the movers only (rehome,
    migrate): they carry text that is ALREADY stored, and refusing there would strand the fact.

    Updating a target already marked `pin` raises `PinnedEntry` BEFORE any write UNLESS
    `allow_pinned_overwrite` is set - the escape hatch `amend_pinned_entry` uses deliberately, and
    nothing else should. Passing `pin=True` to newly PIN an unpinned (or new) entry is unaffected;
    the gate only fires when the entry found at `slug` is ALREADY pinned.

    A slug that is not a plain filename raises `InvalidSlug`, and a `type_` outside the four kinds
    raises ValueError, both BEFORE any write. On an UPDATE, a `type_` with no body re-types the
    stored body in place (its prose untouched). A relative `proj` is taken relative to the cwd.

    A fact placed by topic (see `_placed_slugs`) is written only from a level holding one of its
    lines, else `PlacedElsewhere`; the write then refreshes its other lines too. Pinning one raises
    TopicRefusal. A level whose path below the anchor crosses a directory the level walk prunes
    raises `NonLevelDir`. All three before any write. A fact whose body is bound to a topic is
    decided and written under the tree's placement lock (`_placement_lock_if_bound`), so its
    lines change with no render or set-topics half done; PlacementLockBusy when it stays held.

    `skill` ties the fact to the skill it belongs with (`metadata: skill:`); it follows the same
    rules as `type_` - kept on an update that does not name it, set in place by one with no body -
    and an invalid name raises `InvalidSkill` before any write.

    Under BITRANOX_MEMORY_WRITES=off it raises `sig.MemoryWritesOff` as its first statement, before
    the lock is taken and before anything is read: this is the entry write path the skill scripts
    (reconcile, migrate) call directly, so a guard on the CLI verbs alone left it open.

    Decisions:
        - Rejected: a `bx:owner=human` partition on the pointer line, refusing an autonomous
          overwrite of a "human-owned" fact (53c54a85, reverted c59cb953). Why: every fact in the
          store is written by a model, so "human-owned" only ever labelled the model's own write,
          and `bx:pin` already marks exactly the facts that need protecting; the pin gate above
          replaced it (f1278a93). Evidence: argued: the review recorded in f1278a93, which also
          found the movers silently stripped the owner marker. Reopen if: facts start being
          written by a person rather than a model, and a pin cannot express which of them must
          not be overwritten.
          Pinned by: tests/test_memory_pin_gate.py::test_add_refuses_a_pinned_target_and_leaves_the_original_hook_on_disk"""
    sig.refuse_if_memory_writes_off()
    proj = os.path.abspath(str(proj))
    _require_known_type(type_)
    _require_valid_skill(skill)
    slug = slug or slugify(title, type_)
    _require_valid_slug(slug)
    hook = (hook or "").strip()
    if not allow_over_cap_hook and us.hook_over_hard_cap(hook):
        raise HookTooLong(len(hook))
    anchor = _anchor(proj)
    pruned = _pruned_part(anchor, proj)
    if pruned is not None:
        raise NonLevelDir(proj, *pruned)
    # An empty body is the documented UPDATE path ("keep the stored one"), but on a CREATE there is
    # nothing to keep: it writes the frontmatter frame and stops, leaving a convincing always-loaded
    # hook with nothing behind it. Nothing downstream reports that - heal normalizes grammar, --check
    # counts refs, --check-tree checks slug uniqueness, lint --tree looks for UNLABELLED bodies, not
    # absent ones - so the only signal is a reader walking up to an empty file. Refuse here, while
    # the content still exists to supply. Keyed on the body FILE, so a mover carrying stored text
    # (rehome/migrate, which pass no body) is unaffected.
    if not _has_prose(body) and not us.body_path(anchor, slug).is_file():
        raise EmptyBody(slug)
    # Same key, same moment: a create (no body file yet) whose framed body brings a `topics:` line
    # would store a tagging set-topics never checked. Refused before the level is scaffolded, so
    # the refusal writes nothing at all.
    if _body_topics_line(body) is not None and not us.body_path(anchor, slug).is_file():
        raise TopicsOnCreate(slug)
    # A write to a fact bound to a topic holds the tree's placement lock from here on, so the
    # placed decision below and every line it rewrites see no render or set-topics half done.
    with _placement_lock_if_bound(anchor, slug, "add"):
        return _upsert_checked(proj, anchor, slug, title, hook, body, type_, pin, scope_default,
                               allow_pinned_overwrite, skill)


def _upsert_checked(proj, anchor, slug, title, hook, body, type_, pin, scope_default,
                    allow_pinned_overwrite, skill):
    """The writing half of `upsert_entry`, from the placed-by-topic checks on: its caller has
    validated every argument and holds the placement lock when the fact is bound."""
    # A fact placed by topic (see `_placed_slugs`) has a line at each level its topics place it
    # at. Checked here, before the level is scaffolded, so each refusal writes nothing: it is not
    # pinned (a pinned fact is never placed by topic), and it is written from a level that holds
    # one of its lines (adopting it elsewhere would add a line the placement lacks). One tree
    # walk, and only for a body the renderer manages; a new fact has no body and skips it.
    copies = _placed_copies(anchor, slug)
    placed = bool(copies)
    if placed and pin:
        raise TopicRefusal(["%s is bound to topics, and a pinned fact is never placed by topic; "
                            "un-bind it first (%s set-topics --proj %s --slug %s --clear), then "
                            "pin it" % (slug, _ENGINE_ROUTE, anchor, slug)])
    if placed and not any(_same_level(level, proj) for level, _ptr in copies):
        raise PlacedElsewhere(slug, [level for level, _ptr in copies])
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
        created = slug not in by_slug
        if slug in by_slug:
            e = by_slug[slug]
            # A pinned target refuses an ORDINARY add - the write-permission gate this function
            # exists to enforce for every caller (CLI, reconcile, the dream), not just the CLI layer.
            # The only way through is amend_pinned_entry (allow_pinned_overwrite).
            if e.pin and not allow_pinned_overwrite:
                raise PinnedEntry(slug)
            old_hook = e.hook
            e.title, e.hook = title, (hook or e.hook)
            if _has_prose(body):
                # A blank or frame-only body is no body: taken as one it replaced the stored prose
                # with the bare frame. No explicit --type on an UPDATE means "leave the kind alone": re-deriving it from
                # the slug discards what the stored body already records, and for a prefix-less slug
                # that always lands on "project".
                kept_skill = skill or _body_skill(body) or _body_skill(e.body)
                framed = _framed_body(slug, e.hook, type_ or _body_type(e.body), body)
                # The stored topics line wins over whatever the new body's frame says or lacks:
                # topics change only through set-topics (`e.body` is still the stored body here).
                e.body = _with_stored_topics(_with_skill(_synced_frame(slug, e.hook, type_, framed),
                                                         kept_skill), e.body)
            else:
                if e.hook != old_hook:
                    e.body = _reframe_description(e.body, e.hook)   # keep body description in sync
                if type_ and _body_type(e.body) != type_:
                    # An explicit kind with no new body is a re-type: without this the call printed
                    # the slug and exited 0 while the stored body kept its old kind.
                    e.body = _retype_body(slug, e.hook, type_, e.body)
                if skill and _body_skill(e.body) != skill:
                    # Tagging an existing fact with its skill must not need its body re-supplied.
                    e.body = _with_skill(_framed_body(slug, e.hook, _body_type(e.body), e.body), skill)
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
                      body=_with_skill(_synced_frame(slug, hook, type_,
                                                     _framed_body(slug, hook, type_, body)),
                                       skill), pin=pin)
            entries.append(e)
        # Every level this write rewrites is held to the block cap before any is written: this
        # level, and each other level of a fact placed by topic (refreshed below).
        _refuse_add_growth(proj, slug, e, copies, allow_pinned_overwrite)
        # The body carries the pointer's title as data (`title:`); every write through here,
        # amend-pinned and factedit's apply included, keeps the two equal.
        e.body = _with_title(e.body, e.title)
        bodies[slug] = e.body
        _commit_store(proj, scope or scope_default, entries, bodies)
    if placed:
        # The other lines of a fact placed by topic say what this one now says. After the commit
        # and outside its lock (add_pointer takes each level's own): a failure here leaves the
        # body and this level written and the rest as render drift, which --check-tree names.
        for level, ptr in copies:
            if not _same_level(level, proj) and (ptr.title, ptr.hook) != (e.title, e.hook):
                us.add_pointer(str(level), slug, e.title, e.hook)
    if not store_existed and store_dir.exists():      # this add created a brand-new store dir:
        sig.bump_stores_generation()                  # bust the cross-tree dir-cache so recall sees it
    _warn_dangling_wikilinks(anchor, "%s\n%s" % (e.hook or "", e.body or ""), slug)
    return slug, created


def _refuse_add_growth(proj, slug, e, copies, amend):
    """Raise LineGrowsPastCap when the line `e` writes at `proj`, or the refreshed line at any
    other level of `copies` (a fact placed by topic), would leave that level's block past the cap
    and larger than it is now (`_grows_past_cap`). Called under `proj`'s level lock, before
    anything is written; the other levels are read without theirs (a bound fact's writers hold
    the placement lock, which this write holds too)."""
    verb = "amend-pinned" if amend else "add"
    line = us.Pointer(slug=slug, title=e.title, hook=e.hook, pin=e.pin)
    changes = [(proj, slug, line)] + [
        (level, slug, us.Pointer(slug=slug, title=e.title, hook=e.hook, pin=ptr.pin))
        for level, ptr in copies if not _same_level(level, proj)]

    def retry(shrink, old, new):
        hook_bytes = len(e.hook.encode("utf-8"))
        if old:
            return ("Run %s again with a hook (or title) that makes the line at least %d bytes "
                    "shorter: %s %s --proj %s --slug %s --title <title> --hook-file <file> (a "
                    "line no longer than the %d bytes it takes now always goes through)"
                    % (verb, shrink, _ENGINE_ROUTE, verb, proj, slug, old))
        shorter = ("" if shrink >= hook_bytes else
                   ", or here with a hook at least %d bytes shorter" % shrink)
        return ("Add it at another level of the altitude chain that has room (%s add --proj "
                "<level> --slug %s ...)%s" % (_ENGINE_ROUTE, slug, shorter))

    text = _line_growth_refusal(verb, changes, retry)
    if text:
        raise LineGrowsPastCap(text)


def add_with_advice(proj, title, hook, body="", type_=None, pin=False, scope_default="",
                    slug=None, skill=None):
    """`add_or_update_entry` plus the advisories the CLI prints after it, returned as data.

    The CLI `add` and the mod bridge both write a fact through here, so a capture made either way
    gets the same validation and the same warnings. Returns (slug, created, advice): `created` is
    False when the fact already had a body (an update); `advice` holds the '~ warning: ...' and
    '~ note: ...' lines in the order the CLI prints them. Raises what `add_or_update_entry` raises."""
    sig.refuse_if_memory_writes_off()
    hook = (hook or "").strip()
    _require_known_type(type_)                # same refusal order as add_or_update_entry
    _require_valid_skill(skill)
    target = slug or slugify(title, type_)
    _require_valid_slug(target)
    slug, created = upsert_entry(proj, title=title, hook=hook, body=body, type_=type_, pin=pin,
                                 scope_default=scope_default, slug=slug, skill=skill)
    return slug, created, _add_advice(hook, body)


def _add_advice(hook, body):
    """The advisory lines for a just-written fact, in print order. `hook` is the RESOLVED text (a
    `--hook-file` call has no inline flag), so a caller must pass it, never the raw argument."""
    advice = []
    if us.hook_over_budget(hook):
        advice.append("~ warning: hook is %d chars (soft cap %d, advisory - fine up to the %d-char "
                      "hard cap; keep it self-sufficient, do not trim load-bearing detail to "
                      "silence this)" % (len(hook), us.HOOK_SOFT_MAX, us.HOOK_HARD_MAX))
    if us.hook_missing_trigger(hook):
        advice.append("~ warning: hook has no trigger phrase - lead with WHEN it applies "
                      "('When <situation>, <directive>'), or it will not fire during reasoning")
    for _advice in capture_constraints.advise(hook, body):
        advice.append(f"~ warning: {_advice}")
    # The recurrence count is the one durable "this was already written and did not hold" signal,
    # and this is the moment it is in hand. Naming BOTH ladders is deliberate: the body cannot say
    # whether a repeat is a rule being skipped or work being re-done, and the counter living only
    # in the rule ladder is what kept sending readers to a guard while the jig was never proposed.
    seen = us.recurrence_count(body)
    if seen is not None and seen >= us.RECURRENCE_ESCALATE_AT and _user_decided_escalation(body):
        # The user already ruled on the ladder: "propose it in THIS turn" would contradict the
        # very fact being written and re-ask a settled question.
        advice.append("~ note: this body records recurrence %d and the user's escalation decision - "
                      "not re-proposing a guard or jig" % seen)
    elif seen is not None and seen >= us.RECURRENCE_ESCALATE_AT:
        advice.append("~ warning: this body records recurrence %d - prose has already failed %d "
                      "times, so do NOT just reword it. Escalate and PROPOSE it to the user in "
                      "THIS turn: a deterministic GUARD if a rule keeps being skipped, a JIG "
                      "(toolbox tool) if the same multi-step work keeps being re-done by hand - "
                      "and BOTH when it is both." % (seen, seen))
    return advice


def amend_pinned_entry(proj, slug, hook=None, body=None, title=None, type_=None):
    """The escape hatch for a pinned fact: the same upsert as `add`, with the pinned refusal skipped.
    Keeps the existing pin state (this never unpins - `bx:pin` is untouched, only content changes);
    an empty/absent `title`, `hook` or `body` keeps the stored one, matching `add_or_update_entry`'s
    update semantics. Raises `UnknownSlug` when `slug` names no existing entry at this level -
    amending presumes a prior `add --pin`.

    `title` is here because a pinned fact's title is the most-read text in the store and this is the
    only route to it: `retitle_entry` refuses a pinned fact by design, so that the pin gate keeps
    exactly one deliberate way through. It is normalised the same way a retitle normalises it.

    `type_` is here for the same reason and it is the ONLY route to a pinned fact's kind, since
    `add` refuses a pinned entry outright. Omitting it keeps the stored kind. A pinned fact is the
    one whose classification matters most - these are the always-loaded rules - so leaving it
    unreachable would freeze a fact captured under the wrong kind for good. Re-typing never
    unpins.

    There is no `source` parameter: provenance was removed in 5.300.0 and is not stored.

    `type_` alone (no body) re-types the stored body in place; an unknown kind raises ValueError and a
    slug that is not a plain filename raises `InvalidSlug`, both before anything is read or written."""
    proj = os.path.abspath(str(proj))
    _require_valid_slug(slug)
    _require_known_type(type_)
    _scope, entries, _bodies = read_store(proj)
    by_slug = {e.slug: e for e in entries}
    if slug not in by_slug:
        raise UnknownSlug(slug)
    wanted = _normalised_title(title)
    return add_or_update_entry(proj, title=wanted or by_slug[slug].title,
                               hook=hook or "", body=body or "", type_=type_,
                               slug=slug, allow_pinned_overwrite=True)


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
        except OSError:
            continue
        # A level that cannot be read raises TreeWalkError: whether it owns the slug is unknown,
        # and "not owned" is the answer that lets add adopt a body another level still points at.
        _s, ptrs = us.parse_pointer_index(read_store_text(sig.claude_local_md_path(lvl)))
        if any(p.slug == slug for p in ptrs):
            return True
    return False


def _body_description(text):
    """The `description:` value (the hook) from a framed body's frontmatter, or '' if absent.

    Scoped to the LEADING frontmatter block (see `_frontmatter`), like `_body_type`: a
    `description:` line in the prose, or in a body that merely opens with a horizontal rule, is
    the author's text, and adopting a dangling body made it the always-loaded hook."""
    _head, m = _frontmatter(text)
    if m is None:
        return ""
    d = re.search(r"(?m)^description:[ \t]*([^\r\n]*)", m.group(1))
    return d.group(1).strip() if d else ""


def _body_type(text):
    """The `metadata: type:` value from a framed body's frontmatter, or '' if absent.

    A slug records the type only when it was minted with one (`feedback-...`); for a prefix-less
    slug the body IS the only record, so an update that reframes the body has to read it here or
    it silently re-classifies the fact - and nothing downstream reports that (`store_manifest
    verify` reads level/slug/title/pin, `lint --tree` looks for UNLABELLED bodies, and the write
    prints its usual success line). Scoped to the LEADING frontmatter block (see `_frontmatter`) so
    a `  type:` line in the prose below cannot answer for it."""
    _head, m = _frontmatter(text)
    if m is None:
        return ""
    t = re.search(r"(?m)^[ \t]+type:[ \t]*(\S+)[ \t]*\r?$", m.group(1))
    return t.group(1) if t else ""


def _body_skill(text):
    """The `metadata: skill:` value from a framed body's frontmatter, or '' if absent - the skill a
    fact is tied to (meta-self-improve step 2). Scoped to the leading frontmatter block like
    `_body_type`, so a `  skill:` line in the prose cannot answer for it."""
    _head, m = _frontmatter(text)
    if m is None:
        return ""
    s = re.search(r"(?m)^[ \t]+skill:[ \t]*(\S+)[ \t]*\r?$", m.group(1))
    return s.group(1) if s else ""


def _with_skill(text, skill):
    """Return framed `text` with its frontmatter `metadata: skill:` set to `skill`, prose untouched.

    Rewrites the line `_body_skill` reads; frontmatter without one gains it under `metadata:` (after
    the `type:` line when there is one, so the two metadata keys sit together). `text` must already
    be framed - every caller frames first - and an unframed one is returned unchanged rather than
    framed with a guessed kind."""
    head, m = _frontmatter(text)
    if m is None or not skill:
        return text
    inner = m.group(1)
    nl = "\r\n" if inner.endswith("\r\n") else "\n"
    new_inner, n = re.subn(r"(?m)^([ \t]+skill:)[ \t]*[^\s]*[ \t]*(?=\r?$)",
                           lambda s: "%s %s" % (s.group(1), skill), inner, count=1)
    if n == 0:
        new_inner, n = re.subn(r"(?m)^([ \t]+type:[^\r\n]*)(?=\r?$)",
                               lambda s: "%s%s  skill: %s" % (s.group(1), nl, skill), inner, count=1)
    if n == 0:
        new_inner, n = re.subn(r"(?m)^(metadata:)[ \t]*(?=\r?$)",
                               lambda s: "%s%s  skill: %s" % (s.group(1), nl, skill), inner, count=1)
    if n == 0:
        new_inner = inner + "metadata:%s  skill: %s%s" % (nl, skill, nl)
    return _with_frame(head, m, new_inner)


def _with_frame(head, m, inner):
    """`head` with the text between its frontmatter delimiters replaced by `inner`."""
    return head[:m.start(1)] + inner + head[m.end(1):]


def _reframe_description(text, hook):
    """Return `text` with its frontmatter `description:` reset to `hook` (whitespace collapsed), so a
    hook-only pointer update keeps the body's description in sync (spec: the body description IS the
    hook). A body with no frontmatter (see `_frontmatter`) is returned unchanged, and only a line
    INSIDE the frame is rewritten: a `description:` line in the prose is the author's text. The
    replacement is a lambda: a hook can carry backslashes (Windows paths) that re.sub would
    otherwise treat as template escapes."""
    head, m = _frontmatter(text)
    if m is None:
        return text
    desc = " ".join((hook or "").split())
    inner, n = re.subn(r"(?m)^(description:)[ \t]*[^\r\n]*",
                       lambda d: "%s %s" % (d.group(1), desc), m.group(1), count=1)
    return _with_frame(head, m, inner) if n else text


def _body_title(text):
    """The `title:` value from a framed body's frontmatter, or '' if absent. Scoped to the leading
    frontmatter block (see `_frontmatter`), like `_body_description`."""
    _head, m = _frontmatter(text)
    if m is None:
        return ""
    t = re.search(r"(?m)^title:[ \t]*([^\r\n]*)", m.group(1))
    return t.group(1).strip() if t else ""


def _with_title(text, title):
    """Return framed `text` with its frontmatter `title:` set to `title` (one line), prose untouched.

    The pointer line is the title's only other home, so the title is kept in the body as data and a
    pointer line can be rebuilt from the body alone. A frame without the key gains it after
    `description:` (or after `name:` when there is no description). An unframed `text`, or an empty
    title, is returned unchanged: every write path frames first, and a title is never invented.
    The replacement is a lambda, as in `_reframe_description`: a title can carry backslashes."""
    head, m = _frontmatter(text)
    title = _normalised_title(title)
    if m is None or not title:
        return text
    inner = m.group(1)
    nl = "\r\n" if inner.endswith("\r\n") else "\n"
    new_inner, n = re.subn(r"(?m)^(title:)[ \t]*[^\r\n]*", lambda t: "%s %s" % (t.group(1), title),
                           inner, count=1)
    for key in ("description", "name"):
        if n:
            break
        new_inner, n = re.subn(r"(?m)^(%s:[^\r\n]*)(?=\r?$)" % key,
                               lambda t: "%s%stitle: %s" % (t.group(1), nl, title), inner, count=1)
    return _with_frame(head, m, new_inner) if n else text


def _body_topics(text):
    """The topics a framed body's frontmatter carries on its `topics:` line: None when the line is
    absent (the fact was never tagged), an empty tuple for `topics: []` (tagged, and bound to no
    topic), else the sorted tags. Scoped to the leading frontmatter block (see `_frontmatter`),
    like `_body_title`. A line that does not parse as a topic list reads as None: the fact is
    then placed by nothing, and stays where its pointer is."""
    _head, m = _frontmatter(text)
    if m is None:
        return None
    t = re.search(r"(?m)^topics:[ \t]*([^\r\n]*)", m.group(1))
    if t is None:
        return None
    try:
        return tp.parse_topics(t.group(1))
    except tp.InvalidTopic:
        return None


def _body_topics_line(text):
    """The raw `topics:` line of a framed body's frontmatter, exactly as stored (no line break), or
    None when there is none. Unlike `_body_topics` it does not parse: a line that is no valid topic
    list is still returned, so a writer can carry it over instead of erasing it."""
    _head, m = _frontmatter(text)
    if m is None:
        return None
    t = re.search(r"(?m)^topics:[^\r\n]*", m.group(1))
    return t.group(0) if t else None


def _with_topics(text, topics):
    """Return framed `text` with its frontmatter `topics:` line set to `topics`, prose untouched;
    `topics=None` removes the line. A frame without the key gains it after `title:` (else after
    `description:`, else after `name:`). An unframed `text` is returned unchanged: every write
    path frames first."""
    line = None if topics is None else "topics: %s" % tp.format_topics(topics)
    return _with_topics_line(text, line)


def _with_stored_topics(text, stored):
    """Return framed `text` carrying the `topics:` line of the `stored` body: the parsed tags in
    their stored form, the raw line verbatim when it does not parse, and no line when `stored` has
    none. Whatever `text`'s own frame says is replaced - topics change only through set-topics.
    A line that does not parse is kept rather than dropped or refused: it is the author's data, and
    refusing would wedge every ordinary write to the fact over one bad line."""
    topics = _body_topics(stored)
    if topics is not None:
        return _with_topics(text, topics)
    return _with_topics_line(text, _body_topics_line(stored))


def _with_topics_line(text, line):
    """`_with_topics` for a whole `topics:` line given as it should be written (None removes it)."""
    head, m = _frontmatter(text)
    if m is None:
        return text
    inner = m.group(1)
    nl = "\r\n" if inner.endswith("\r\n") else "\n"
    if line is None:
        new_inner = re.sub(r"(?m)^topics:[^\r\n]*\r?\n", "", inner, count=1)
        return _with_frame(head, m, new_inner)
    new_inner, n = re.subn(r"(?m)^topics:[^\r\n]*", lambda _t: line, inner, count=1)
    for key in ("title", "description", "name"):
        if n:
            break
        new_inner, n = re.subn(r"(?m)^(%s:[^\r\n]*)(?=\r?$)" % key,
                               lambda t: "%s%s%s" % (t.group(1), nl, line), inner, count=1)
    return _with_frame(head, m, new_inner) if n else text


def _retype_body(slug, hook, type_, text):
    """Return `text` with its frontmatter `metadata: type:` set to `type_`, prose untouched.

    Rewrites the same line `_body_type` reads (the first indented `type:` in the leading frontmatter),
    so the kind read back is the kind written. Frontmatter with no `type:` line gains one; a body with
    no frontmatter (see `_frontmatter`), a leading horizontal rule included, is framed with the new
    kind. The replacement is a lambda for the same reason as `_reframe_description`."""
    head, m = _frontmatter(text)
    if m is None:
        return _framed_body(slug, hook, type_, text)
    inner = m.group(1)
    nl = "\r\n" if inner.endswith("\r\n") else "\n"
    new_inner, n = re.subn(r"(?m)^([ \t]+type:)[ \t]*[^\s]*[ \t]*(?=\r?$)",
                           lambda t: "%s %s" % (t.group(1), type_), inner, count=1)
    if n == 0:
        new_inner, n = re.subn(r"(?m)^(metadata:)[ \t]*(?=\r?$)",
                               lambda t: "%s%s  type: %s" % (t.group(1), nl, type_), inner, count=1)
    if n == 0:
        new_inner = inner + "metadata:%s  type: %s%s" % (nl, type_, nl)
    return _with_frame(head, m, new_inner)


def _entry_from_body(anchor, slug):
    """Reconstruct an Entry from a dangling central body so `add` can re-adopt it. The hook comes from
    the body's `description:` frontmatter; title/level are not stored in a body, so the caller's update
    supplies them. Raises TreeWalkError if the body cannot be read or is not UTF-8: returning
    nothing sent add on to call the slug a collision with a fact it had simply failed to read."""
    text = read_store_text(us.body_path(anchor, slug)).rstrip("\n")
    return Entry(slug=slug, title=slug, hook=_body_description(text), body=text)


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
            old.rename(us.free_archive_path(dest, old.name))
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


def _blank(chars, start, end):
    """Overwrite chars[start:end] with spaces, leaving newlines so line structure survives."""
    for i in range(start, end):
        if chars[i] != "\n":
            chars[i] = " "


def _mask_fenced_blocks(chars, text):
    """Blank every fenced code block in place, fence lines included, by the shared fence rule
    (`tell_chars.code_line_flags`). A missed opener is the costly direction here: a block read as
    prose reports every quoted [[ref]] in it as dangling."""
    lines = tell_chars.split_lines(text, keepends=True)
    pos = 0
    for line, is_code in zip(lines, tell_chars.code_line_flags(lines)):
        if is_code:
            _blank(chars, pos, pos + len(line))
        pos += len(line)


def _mask_inline_spans(chars):
    """Blank every inline code span in place: a run of N backticks closed by a run of exactly N.

    Matching is bounded to ONE line even though CommonMark lets a span wrap. Masking too much is
    the silent failure (a real dangling ref stops being reported), so a stray unpaired backtick
    must not be able to swallow the rest of a body - only the rest of its own line, where it is
    also literal text and therefore blanks nothing at all.
    """
    n, i = len(chars), 0
    while i < n:
        if chars[i] != "`":
            i += 1
            continue
        start = i
        while i < n and chars[i] == "`":
            i += 1
        run = i - start
        j = i
        while j < n and chars[j] != "\n":
            if chars[j] != "`":
                j += 1
                continue
            close = j
            while j < n and chars[j] == "`":
                j += 1
            if j - close == run:
                _blank(chars, i, close)
                i = j
                break


def mask_code_regions(text):
    """`text` with every fenced block and inline code span blanked to spaces, length-preserved.

    A `[[ref]]` is a link only in PROSE. Several config formats spell a construct with double square
    brackets - TOML's array-of-tables `[[tool.importlinter.contracts]]` is the one that reaches this
    store - so a fact that TEACHES such a format has to quote it, and a reader that cannot tell
    quoted syntax from a link turns that fact into a permanent orphan ref whose only escape is to
    stop teaching the syntax.

    Length is preserved so a caller can index the RAW text at the same offsets, which is how a
    rewrite decides whether a match it found is quoted.
    """
    if not text:
        return text or ""
    chars = list(text)
    _mask_fenced_blocks(chars, text)
    _mask_inline_spans(chars)
    return "".join(chars)


def dangling_wikilinks(text, existing):
    """[(target, closest-existing-or-None)] for each `[[ref]]` in `text` whose canonical slug is NOT
    in `existing`. PURE - the write-time catch for an invented-phrase link before it becomes a
    store-wide dangling ref a later `--check-tree` has to find. Deduped, order-preserving."""
    import difflib
    ex = {_canon_slug(s) for s in existing}
    out, seen = [], set()
    for m in _WIKILINK_RX.finditer(mask_code_regions(text)):
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
        _scope, pointers = us.parse_pointer_index(read_store_text(sig.claude_local_md_path(lvl)))
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
            masked = mask_code_regions(text)
            if any(_ref_slug(m.group(1)) == qcanon for m in _WIKILINK_RX.finditer(masked)):
                out.append((str(level), e.slug))
    return out


def has_inbound_refs(levels, slug):
    """True when any other entry across `levels` references `[[slug]]`."""
    return bool(inbound_ref_sources(levels, slug))


def _drop_pointer(level, slug):
    """Remove one pointer line (by slug) from a level's block, under lock, mtime-neutral."""
    local = sig.claude_local_md_path(level)
    with sig.memory_lock(local):
        text = read_store_text(local)
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
    regardless of move DIRECTION, OR the pin. Direction-independent by construction, so it can
    never discard the richer hook the way a plain overwrite did. Returns ((title, hook, pin),
    warning)."""
    keep = entry if len(entry.hook or "") >= len(dst_entry.hook or "") else dst_entry
    fields = (keep.title, keep.hook, entry.pin or dst_entry.pin)
    warning = ("duplicate at target: kept the longer hook (%d vs %d chars), "
               "dropped the shorter line" % (len(keep.hook or ""),
                                                    min(len(entry.hook or ""), len(dst_entry.hook or ""))))
    return fields, warning


def _nearest_common_level(src, dst, anchor):
    """The deepest dir above both `src` and `dst` that is a memory level (carries the level file),
    else the anchor. A sideways re-home goes up to it and down again; the bare common PATH is not
    the answer, because a dir with no level file has no pointer block to land in."""
    cur = Path(os.path.commonpath([str(src), str(dst)]))
    while anchor in cur.parents or cur == anchor:
        if cur == anchor or sig.claude_local_md_path(str(cur)).is_file():
            return cur
        cur = cur.parent
    return anchor


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

    It also refuses, before any write, a set holding a fact placed by topic (its place follows its
    topics; un-bind it first), and a set whose lines would leave the target's block past
    MAX_RENDER_BLOCK_BYTES, the cap render-topics holds every level to, unless the move does not
    grow that block (see `_move_cap_refusal`), and a target level whose path below the anchor
    crosses a directory the level walk prunes (see `NonLevelDir`).

    Returns {"slug","slugs","from","to","direction","moved","moved_slugs","refused","warnings"};
    `slug` is the comma-joined set, identical to the input for a single slug."""
    sig.refuse_if_memory_writes_off()
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
    pruned = _pruned_refusal(a_to, dst, "%s move --from-level %s --to-level {level} --slug %s"
                             % (_ENGINE_ROUTE, src, " ".join(slugs)))
    if pruned:
        rep["refused"] = pruned
        return rep
    if src == dst:
        rep["refused"] = "same level - nothing to move"
        return rep
    if dst in src.parents:
        rep["direction"] = "up"
    elif src in dst.parents:
        rep["direction"] = "down"
    else:
        hub = _nearest_common_level(src, dst, Path(a_from).resolve())
        rep["refused"] = (
            "sibling levels - a move follows the altitude chain (ancestor <-> descendant only); "
            "re-home it in two moves through the nearest level above both: `move --from-level %s "
            "--to-level %s`, then `move --from-level %s --to-level %s` (the second, down, leg "
            "refuses on its own if inbound [[refs]] would dangle)" % (src, hub, hub, dst))
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
    placed = _placed_slugs(a_from, slugs)
    if placed:
        s = next(s for s in slugs if s in placed)       # the first in the caller's order
        rep["refused"] = _PLACED_BY_TOPIC % (s, a_from, s)
        return rep

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
            fields = (entry.title, entry.hook, entry.pin)
        plan.append((entry.slug, fields))

    # The target's block is held to the cap render-topics holds every level to; the refusals of
    # render-topics and set-topics that name a move promise it.
    full = _move_cap_refusal(src, dst, plan)
    if full:
        rep["refused"] = full
        return rep

    for s, (title, hook, pin) in plan:
        try:
            us.add_pointer(str(dst), slug=s, title=title, hook=hook, pin=pin)
            _drop_pointer(str(src), s)
        except (OSError, TreeWalkError) as exc:        # the re-read inside the drop can fail too
            rep["refused"] = (
                "write failed on %r after %d of %d pointer(s) moved: %s - each move is an idempotent "
                "add-then-remove, so re-run the SAME command to complete the set"
                % (s, len(rep["moved_slugs"]), len(plan), exc))
            return rep
        rep["moved_slugs"].append(s)
    rep["warnings"].extend(dedup_warnings)
    rep["moved"] = True
    return rep


def _move_cap_refusal(src, dst, plan, verb="move"):
    """The refusal text when the lines `plan` ([(slug, (title, hook, pin))]) moves to `dst` would
    leave its block past MAX_RENDER_BLOCK_BYTES and larger than it is now, else None. A line the
    target already holds for a moving slug is replaced by the planned one (`plan` already carries
    the merged pin and the kept hook of a forced dedup, and an identical line is its own
    replacement); every other line stays. A move that does not grow the block (completing an
    interrupted one) is never refused: it makes no level fuller than it was. `verb` is the one
    the refusal names for taking the lines from `src` elsewhere (`relocate` across trees); room
    at `dst` is freed with `move`, which stays in its tree. Holds the target's block and one size
    per moving line."""
    pointers = us.parse_pointer_index(read_store_text(sig.claude_local_md_path(str(dst))))[1]
    moving = {s for s, _fields in plan}
    before = sum(_line_size(p) for p in pointers)
    kept = sum(_line_size(p) for p in pointers if p.slug not in moving)
    sizes = [_line_size(us.Pointer(slug=s, title=title, hook=hook, pin=pin))
             for s, (title, hook, pin) in plan]
    after = kept + sum(sizes)
    if after <= MAX_RENDER_BLOCK_BYTES or after <= before:
        return None
    room = MAX_RENDER_BLOCK_BYTES - kept
    fit, total = 0, 0
    for size in sorted(sizes):
        total += size
        if total > room:
            break
        fit += 1
    route = _ENGINE_ROUTE + " move --from-level %s --to-level <level> --slug <slug> [<slug> ...]"
    take = route.replace(" move ", " %s " % verb, 1)
    text = ("moving these lines to %s would leave its block at %d bytes, %d bytes over the %d "
            "bytes one level's block may hold (render-topics holds every level to it; a line "
            "counts its line break): the lines it keeps come to %d bytes and the %d line(s) "
            "moved there to %d bytes, and %d bytes are left there"
            % (dst, after, after - MAX_RENDER_BLOCK_BYTES, MAX_RENDER_BLOCK_BYTES, kept,
               len(sizes), sum(sizes), max(room, 0)))
    if fit:
        return text + (". %d of the %d line(s) fit there, smallest first: move those there and "
                       "the rest to another level of the altitude chain that has room, with "
                       + take + "; every level is held to the same %d bytes") % (
                           fit, len(sizes), src, MAX_RENDER_BLOCK_BYTES)
    return text + (". None of the lines fits there: move them to another level of the altitude "
                   "chain that has room, with " + take + ", or first free room at %s by moving "
                   "lines out of it with " + route + "; every level is held to the same %d "
                   "bytes") % (src, dst, dst, MAX_RENDER_BLOCK_BYTES)



def ensure_level(proj, scope_default="", _locked=False):
    """Ensure this level can carry curated memory: (1) its `CLAUDE.local.md` holds a managed pointer
    block with a scope descriptor (created if absent; an existing scope is kept, else a legacy scope
    harvested from `CLAUDE.md`, else `scope_default`), and (2) any LEGACY `<!-- bitranox:self-learning
    -->` scope block still sitting in `CLAUDE.md` is MOVED out into the pointer block (byte-safe outside
    the markers). Best-effort gitignore of `CLAUDE.local.md` + the anchor's `.claude-memory/` when not
    `track_private`; when git cannot confirm a pattern is ignored, a warning on stderr names it
    (the level is still set up). Idempotent + mtime-neutral. No `@import`, no `index.md`.

    REFUSES an excluded altitude (home, the system temp dir, the filesystem root): those dirs are
    never a memory level, and scaffolding them turns e.g. all of /tmp into a fake knowledge tree
    that pollutes recall (bitten twice on 2026-07-05).

    Refuses first under BITRANOX_MEMORY_WRITES=off, before the lock: it writes both level files
    with no entry, so `upsert_entry`'s guard does not cover a direct caller.

    A descriptor it writes new (harvested or `scope_default`) passes `scope_keeping_topics` against
    the level's current one first: TopicRefusal or InvalidTopic, before either file is written, for
    a `scope_default` carrying a `TOPICS:` line and for a legacy block whose line does not parse."""
    sig.refuse_if_memory_writes_off()
    proj = os.path.abspath(str(proj))
    if _is_excluded_level(proj):
        raise ExcludedLevel(proj)
    def _do():
        md_path = sig.claude_md_path(proj)
        # Both reads raise TreeWalkError rather than read as empty: this function REWRITES both
        # files, and text it could not decode is text it would write back wrong.
        md = read_store_text(md_path)
        legacy_scope = sig.read_scope_block(md)             # a scope block left in CLAUDE.md (migration)
        local = sig.claude_local_md_path(proj)
        text = read_store_text(local)
        scope, pointers = us.parse_pointer_index(text)
        want_scope = scope or (legacy_scope or scope_default or "").strip()
        if not scope and want_scope:
            # A new descriptor passes the one TOPICS gate before either file is written: checked
            # against what the level holds now - its legacy block, else nothing - so a scope_default
            # cannot bring a TOPICS line, nor a harvest move one that does not parse.
            want_scope = scope_keeping_topics(
                (legacy_scope or "").strip(), want_scope,
                stored_in=md_path if legacy_scope is not None else None)
        if legacy_scope is not None:
            _write_if_changed(md_path, _strip_scope_block(md))
        if us.INDEX_BEGIN not in text or want_scope != scope:
            us.write_if_changed(local, us.upsert_pointer_block(text, want_scope, pointers))
        if not sig.load_config().get("track_private"):     # keep local wiring + central store unpushed
            for where, pattern in ((proj, "CLAUDE.local.md"),
                                   (str(_anchor(proj)), us.STORE_DIRNAME + "/")):
                if not sig.ensure_gitignored(where, pattern):
                    sys.stderr.write("~ warning: could not make sure git ignores %s in %s (git did not "
                                     "answer, or its exclude file could not be read or written) - "
                                     "check `git status` there before staging anything\n"
                                     % (pattern, where))

    if _locked:
        _do()
    else:
        with sig.memory_lock(sig.claude_local_md_path(proj)):
            _do()


def _is_excluded_level(proj):
    """True when `proj` is the filesystem root, HOME or the temp dir. Compared on RESOLVED paths, so
    `.` means the cwd (unresolved, `Path('.')` equals its own empty anchor and read as the root) and
    a symlink to HOME is refused like HOME itself instead of scaffolding a store into it."""
    try:
        real = Path(proj).resolve()
    except (OSError, RuntimeError):
        return True
    if real == Path(real.anchor):
        return True
    excluded = set()
    for d in sig._excluded_anchor_dirs():
        excluded.add(Path(d))
        try:
            excluded.add(Path(d).resolve())
        except (OSError, RuntimeError):
            pass
    return real in excluded or Path(proj) in excluded


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
    text = read_store_text(sig.claude_local_md_path(proj))   # absent -> "" -> a block is due
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
        text = read_store_text(local)
        scope, pointers = us.parse_pointer_index(text)
        canonical = us.upsert_pointer_block(text, scope, pointers)     # round-trip -> canonical grammar
        if canonical != text and _write_if_changed(local, canonical):
            report["healed"].append(str(local))


_REFUSED_LEVEL_LINE = "    ! refused level, left untouched: %s [%s]"
"""How heal, ensure-memory-structure and ensure-all-trees print a level they left because its
legacy CLAUDE.md scope block has a TOPICS line that does not parse: the refusal text, then the
level. The text itself names the file and the fix, so the line adds no remedy of its own."""


def heal(proj):
    """Self-heal the WHOLE altitude chain for `proj`: (re)create any missing `CLAUDE.md`,
    `CLAUDE.local.md`, or managed pointer block, NORMALIZE a malformed SCOPE/pointer block to canonical.
    A pointer whose central body is missing is REPORTED (never fabricated). Idempotent, mtime-neutral,
    A pointer whose slug is not a plain filename is dropped by that normalisation and REPORTED.
    A level whose files cannot be read or are not UTF-8 is left untouched and REPORTED under
    'unreadable' - skipping it without a word read exactly like a healthy level. A level whose
    legacy CLAUDE.md scope block has a TOPICS line that does not parse is left untouched and
    REPORTED under 'refused' with the refusal, which names the file to fix by hand.
    FAIL-OPEN (never raises). Returns {'healed': [paths], 'orphans': [(level, slug)],
    'invalid_pointers': [(level, line)], 'unreadable': [(level, reason)],
    'refused': [(level, reason)], 'levels': n}.
    Under BITRANOX_MEMORY_WRITES=off it touches nothing and returns every key empty plus
    'skipped': the refusal line (SessionStart calls it on every start, so it must not raise)."""
    if sig.memory_writes_off():
        return {"healed": [], "orphans": [], "invalid_pointers": [], "unreadable": [], "refused": [],
                "levels": 0, "skipped": sig.MEMORY_WRITES_OFF_LINE}
    report = {"healed": [], "orphans": [], "invalid_pointers": [], "unreadable": [], "refused": [],
              "levels": 0}
    try:
        levels = sig.altitude_chain(proj)            # level dirs, narrowest -> the tree's anchor
    except Exception:                                # noqa: BLE001 - self-heal must never raise
        return report
    for level in levels:
        report["levels"] += 1
        level = str(level)
        try:
            _heal_one_level(level, report)
        except TreeWalkError as exc:
            report["unreadable"].append((level, str(exc)))
        except (TopicRefusal, tp.InvalidTopic) as exc:
            report["refused"].append((level, str(exc)))
        except Exception:                            # noqa: BLE001 - one bad level never blocks the rest
            continue
    return report


def backfill_titles(proj):
    """Copy each pointer's title into its body's frontmatter where the body has none, across the
    WHOLE tree of `proj`'s anchor. A body that already has a `title:` is never rewritten, an
    unframed body is left alone and counted, and a missing body is counted, never fabricated.

    Separate from `heal`, which SessionStart runs on every start and which never opens a body: a
    back-fill reads every body of the tree and writes most of them once, a one-off for stores
    written before titles were kept as data. Returns {'filled': [slugs], 'kept': n, 'unframed':
    [slugs], 'untitled': [slugs], 'missing': [slugs]}; `untitled` is a framed body whose pointer
    has an empty link text, so there is no title to copy (kept apart from `unframed`, which would
    report a frame that is there as absent). A slug pointed at from two levels is filled from the
    first level the walk meets, and each body is read and written under the lock of that first
    level only: an engine write to the same slug through another level holds that level's lock.
    Raises TreeWalkError (exit 2 on the CLI) when a level or a body cannot be read: a back-fill
    that skipped part of the tree would read as done. Missing is decided by the read itself, never
    by a `Path.is_file()` pre-check, which answers False for a body it cannot stat (EACCES) and
    would report an unreadable store as a store of missing bodies."""
    sig.refuse_if_memory_writes_off()
    anchor = _anchor(proj)
    rep = {"filled": [], "kept": 0, "unframed": [], "untitled": [], "missing": []}
    seen = set()
    for level in curated_levels_under(anchor):
        with sig.memory_lock(sig.claude_local_md_path(level)):
            text = read_store_text(sig.claude_local_md_path(level))
            for ptr in us.parse_pointer_index(text)[1]:
                if ptr.legacy or ptr.slug in seen:
                    continue
                seen.add(ptr.slug)
                raw = read_store_text(us.body_path(anchor, ptr.slug))   # "" only when absent
                if raw == "":
                    rep["missing"].append(ptr.slug)
                    continue
                body = raw.rstrip("\n")
                if _body_title(body):
                    rep["kept"] += 1
                    continue
                if _frontmatter(body)[1] is None:
                    rep["unframed"].append(ptr.slug)
                    continue
                filled = _with_title(body, ptr.title)
                if filled == body:
                    rep["untitled"].append(ptr.slug)
                    continue
                us.put_body(str(anchor), ptr.slug, filled)
                rep["filled"].append(ptr.slug)
    return rep


def _heal_one_level(level, report):
    """heal's per-level pass: record invalid pointers, repair the level if it needs it, then list
    pointers whose body is missing. Raises TreeWalkError before any write when the level's files
    cannot be read."""
    before = read_store_text(sig.claude_local_md_path(level))
    report["invalid_pointers"].extend((level, raw) for raw in us.invalid_pointer_lines(before))
    if _level_needs_heal(level):                     # skip-fast: healthy level = no lock, no write
        _heal_level(level, report)
    anchor = _anchor(level)
    # orphan check by pointer-parse + stat only - bodies are never opened here
    text = read_store_text(sig.claude_local_md_path(level))
    for ptr in us.parse_pointer_index(text)[1]:
        path = us.legacy_body_path(anchor, ptr.uuid) if ptr.legacy else us.body_path(anchor, ptr.slug)
        if not path.is_file():
            report["orphans"].append((level, ptr.slug))


def scaffold(proj, refused=None):
    """Create every MISSING CLAUDE.md (marker) + CLAUDE.local.md (pointer block) from `proj` up to the
    anchor, and the anchor's `.claude-memory/` body-store. Idempotent; returns the created paths.
    A level whose legacy CLAUDE.md scope block has a TOPICS line that does not parse is left as it
    is and the rest of the chain is still scaffolded; when `refused` is a list, each such level is
    appended to it as (level, refusal text), the refusal naming the file to fix by hand.
    Refuses first under BITRANOX_MEMORY_WRITES=off: it writes the CLAUDE.md marker
    (`_ensure_claude_md`) before `ensure_level`'s own guard is reached."""
    sig.refuse_if_memory_writes_off()
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
        except (TopicRefusal, tp.InvalidTopic) as exc:
            # a legacy block ensure_level refuses to harvest stays where it is; the next level
            # is still scaffolded, and the caller learns which level was left and why
            if refused is not None:
                refused.append((level, str(exc)))
        except OSError:
            continue                                   # an unwritable level; the next is still scaffolded
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

def _without_topics_line(data):
    """(bytes, dropped): a body's bytes with its frontmatter `topics:` line removed, and whether
    there was one. Only the leading frontmatter is read, so a `topics:` line in the prose stays.
    Decoded with surrogateescape, so bytes that are not UTF-8 and CRLF line ends come back as
    they were."""
    text = data.decode("utf-8", "surrogateescape")
    if _body_topics_line(text) is None:
        return data, False
    return _with_topics_line(text, None).encode("utf-8", "surrogateescape"), True


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

    REFUSES, before writing anything, when the target tree already holds a body under this slug that
    differs from the one being moved (whichever level owns it, or none): slugs are tree-unique, so
    that body is a different fact. An identical body is an interrupted relocate and is completed.
    It also refuses when any level of the target tree OTHER than the target level already points at
    the slug: that level owns it, whatever its body. The archived source body never replaces an
    earlier archived body of the same slug.
    A cross-tree copy drops the body's frontmatter `topics:` line (topics are tagged against one
    tree's closed list) and says so in `notes`; a same-tree move leaves the body untouched. A fact
    placed by topic is refused across trees: its other lines would stay behind in the source tree.
    A target level whose path below its anchor crosses a directory the level walk prunes is
    refused (see `NonLevelDir`), and a cross-tree line that would leave the target's block past
    MAX_RENDER_BLOCK_BYTES is refused as `move` refuses it (see `_move_cap_refusal`); both before
    any write.
    Returns {"slug","from","to","cross_tree","relocated","refused","warnings","notes"}.
    """
    sig.refuse_if_memory_writes_off()
    rep = {"slug": slug, "from": str(from_level), "to": str(to_level),
           "cross_tree": False, "relocated": False, "refused": None, "warnings": [], "notes": []}
    src, dst = Path(from_level).resolve(), Path(to_level).resolve()
    a_from, a_to = us.resolve_anchor(str(src)), us.resolve_anchor(str(dst))
    if a_from is None or a_to is None:
        rep["refused"] = "no anchor for the source or the target level"
        return rep
    pruned = _pruned_refusal(a_to, dst, "%s relocate --from-level %s --to-level {level} --slug %s"
                             % (_ENGINE_ROUTE, src, slug))
    if pruned:
        rep["refused"] = pruned
        return rep
    if Path(a_from).resolve() == Path(a_to).resolve():
        m = move_entry(from_level, to_level, slug, force=force)
        rep.update(relocated=m["moved"], refused=m["refused"], warnings=m["warnings"])
        return rep
    rep["cross_tree"] = True
    if not us.is_valid_slug(slug):
        rep["refused"] = str(InvalidSlug(slug))
        return rep

    _scope, entries, _bodies = read_store(str(src))
    entry = next((e for e in entries if e.slug == slug), None)
    if entry is None:
        rep["refused"] = "slug %r not found at the from-level" % slug
        return rep
    if entry.legacy:
        rep["refused"] = "entry is an unmigrated legacy pointer - run migrate_to_slug_store.py first"
        return rep
    if _placed_slugs(a_from, [slug]):
        # its other lines would stay behind in the source tree, pointing at an archived body
        rep["refused"] = _PLACED_BY_TOPIC % (slug, a_from, slug)
        return rep

    # Slugs are TREE-unique, so a divergent slug already in the target tree is a different fact.
    # Landing on it would destroy it silently; never pick a winner here (dedup is a decision).
    _s2, dst_entries, _b2 = read_store(str(dst))
    dst_entry = next((e for e in dst_entries if e.slug == slug), None)
    if dst_entry is not None and (dst_entry.title, dst_entry.hook) != (entry.title, entry.hook):
        rep["refused"] = ("target tree already has slug %r with a DIFFERENT hook - relocating would "
                          "overwrite that fact; dedup deliberately or rename one first" % slug)
        return rep
    # A pointer at ANY OTHER level of the target tree means the slug is already owned there - with
    # an identical body the move would leave it pointed at from two levels, and with a missing body
    # it would silently re-bind that level's pointer to a body it never had. An interrupted relocate
    # leaves its pointer only at the target level itself, which the check above already admits.
    owner = _other_level_pointing_in(a_to, dst, slug)
    if owner is not None:
        rep["refused"] = ("target tree already points at slug %r from %s - relocating would leave it "
                          "owned twice or re-bind that pointer; dedup deliberately or rename one "
                          "first" % (slug, owner))
        return rep

    # The body FILE is the tree-wide slug registry, so it is the check that sees an owner at ANY level
    # of the target tree - and a dangling body with no pointer at all - where the pointer check above
    # sees only the target level. A different body there is a different fact; an identical one is
    # the residue of an interrupted relocate, which re-running completes.
    src_body, dst_body = us.body_path(a_from, slug), us.body_path(a_to, slug)
    try:
        src_data = src_body.read_bytes() if src_body.is_file() else b""
    except OSError as exc:
        rep["refused"] = "could not read the body %s: %s" % (src_body, exc)
        return rep
    # Topics are tagged against ONE tree's closed list, so the copy leaves them behind.
    data, dropped_topics = _without_topics_line(src_data)
    if dst_body.is_file():
        # BYTES, not text: whether two files are one fact needs no decoding, and a text compare
        # crashed on a target body that was not UTF-8 instead of refusing to land on it. Either
        # copy is the residue of an interrupted relocate: with its topics line dropped, or one
        # made before relocate dropped it.
        try:
            same = dst_body.read_bytes() in (data, src_data)
        except OSError as exc:
            rep["refused"] = "could not compare with the target tree's body %s: %s" % (dst_body, exc)
            return rep
        if not same:
            rep["refused"] = ("target tree already holds a DIFFERENT body for slug %r (%s) - "
                              "relocating would overwrite that fact; dedup deliberately or rename "
                              "one first" % (slug, dst_body))
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

    # The target's block is held to the cap `move` holds it to (render-topics holds every level
    # to it); checked before the body is copied, so a refusal writes nothing.
    full = _move_cap_refusal(src, dst, [(slug, (entry.title, entry.hook, entry.pin))],
                             verb="relocate")
    if full:
        rep["refused"] = full
        return rep

    # COPY-THEN-DROP (same crash-safety direction as move_entry): a crash between the two leaves a
    # visible duplicate, never a lost fact. The body file is copied VERBATIM but for its topics
    # line - it is already framed, and re-writing it through add_or_update_entry would double-wrap
    # the frontmatter. As BYTES: a text round-trip rewrote a CRLF body's line endings on the way.
    try:
        dst_body.parent.mkdir(parents=True, exist_ok=True)
        dst_body.write_bytes(data)
    except OSError as exc:
        rep["refused"] = "could not write the body into the target tree: %s" % exc
        return rep
    us.add_pointer(str(dst), slug=slug, title=entry.title, hook=entry.hook,
                   pin=entry.pin)
    _drop_pointer(str(src), slug)
    if dropped_topics:
        rep["notes"].append("dropped the topics: line of %s - topics are tagged against one tree's "
                            "list; tag it in the target tree with set-topics" % slug)

    # Archive the source body only once nothing in the source tree points at the slug any more.
    if not _other_levels_pointing_in(a_from, slug):
        try:
            archive = us.central_facts_dir(a_from).parent / ".archive"
            archive.mkdir(parents=True, exist_ok=True)
            if src_body.is_file():
                src_body.rename(us.free_archive_path(archive, slug + ".md"))
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
    masked = mask_code_regions(text or "")

    def repl(match):
        inner = match.group(1)
        if _ref_slug(inner) != canon_old:
            return match.group(0)
        if masked[match.start():match.end()] != match.group(0):
            return match.group(0)                    # quoted syntax, not a ref - not ours to edit
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
                               pin=e.pin)
                touched.append((str(level), e.slug, "hook"))
            body = us.body_path(anchor, e.slug)
            text = read_store_text(body)            # rename_entry's collision scan read it already
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
    sig.refuse_if_memory_writes_off()
    # In a tree that places by topic, a rename holds the placement lock: the fact's lines at
    # every level change together, with no render or set-topics between them.
    anchor = us.resolve_anchor(str(Path(level).resolve()))
    with placement_lock_if_listed(anchor, "rename"):
        return _rename_entry(level, slug, to_slug)


def _rename_entry(level, slug, to_slug):
    """`rename_entry` itself; its caller holds the placement lock when the fact is bound."""
    sig.refuse_if_memory_writes_off()
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
    if not us.is_valid_slug(to_slug):
        rep["refused"] = str(InvalidSlug(to_slug))
        return rep
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

    # A fact placed by topic has a line at each level its topics place it at: renamed there too,
    # and no duplicate to report. Decided before any write, while the old body answers.
    placed = bool(_placed_slugs(anchor, [slug]))

    # Slugs are TREE-unique, so an existing one names a DIFFERENT fact. Landing on it would destroy
    # that fact silently; never pick a winner here, deduping is a decision.
    for other in curated_levels_under(anchor):
        _s, oentries, _b = read_store(str(other))
        if any(e.slug == to_slug for e in oentries):
            rep["refused"] = ("slug %r already exists at %s - slugs are tree-unique; dedup "
                              "deliberately instead of renaming onto it" % (to_slug, other))
            return rep

    # Every level holding a line of it is held to the block cap before any is written.
    rep["refused"] = _line_growth_refusal(
        "rename", [(level_dir, slug, us.Pointer(slug=to_slug, title=ptr.title, hook=ptr.hook,
                                                pin=ptr.pin))
                   for level_dir, ptr in _copies_of(anchor, slug)],
        lambda shrink, _old, _new: (
            "Rename it to a slug at least %d characters shorter: %s rename --level %s --slug %s "
            "--to-slug <slug> (a slug no longer than %s always goes through)"
            % (shrink, _ENGINE_ROUTE, level, slug, slug)))
    if rep["refused"]:
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
            dst_body.write_text(_retarget_body_name(read_store_text(src_body), to_slug),
                                encoding="utf-8")
        else:
            rep["warnings"].append("no body file at the old slug; renaming the pointer only")
    except OSError as exc:
        rep["refused"] = "could not write the body under the new slug: %s" % exc
        return rep

    us.add_pointer(str(lvl), slug=to_slug, title=entry.title, hook=entry.hook,
                   pin=entry.pin)
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
                       pin=dup.pin)
        _drop_pointer(str(other), slug)
        if placed:
            continue                                 # placed by topic: one line per level, by design
        rep["warnings"].append("slug was ALSO pointed at from %s - a pre-existing duplicate; "
                               "renamed there too, dedup it deliberately" % other)

    # After the pointer swaps, so the renamed fact's OWN body already sits at the new path and a
    # self-reference is repointed along with everyone else's.
    rep["refs_rewritten"] = _rewrite_inbound_refs(anchor, slug, to_slug)

    try:
        if src_body.is_file():
            archive = us.central_facts_dir(anchor).parent / ".archive"
            archive.mkdir(parents=True, exist_ok=True)
            src_body.rename(us.free_archive_path(archive, slug + ".md"))
    except OSError as exc:
        rep["warnings"].append("old body left in place (archive failed: %s)" % exc)
    rep["renamed"] = True
    return rep


def _normalised_title(raw):
    """One line, single-spaced. A newline in a title would SPLIT the pointer line, so the parser
    would see a fact whose link text ends mid-sentence and a stray prose line after it - the fact
    orphaned on the next round trip. `_ptr_safe_title` already neutralises `[`/`]` at render time;
    whitespace is the part it does not cover."""
    return " ".join((raw or "").split())


def retitle_entry(level, slug, to_title):
    """Change one fact's TITLE in place, touching nothing else.

    The title is the link text of an always-loaded pointer line, so it is the first thing a session
    reads and the cheapest thing to skim - a stale one steers behaviour even while the hook below it
    is correct. It was also the one field with no correction path: `add` demands a hook on every
    call, so a title fix meant re-supplying the stored 500-char text and risking a drift in what
    actually fires, and `rename` changes the slug and never the title.

    Same slug, same hook, same prose: only the label changes - in the pointer line and in the
    body's frontmatter `title:`, which carries it as data. A body with no frame is left as it is.

    A PINNED fact is refused here and goes through `amend_pinned_entry` instead, which is the single
    deliberate route through the pin gate. Returns
    {"slug","to_title","level","retitled","levels","refused","warnings"}.
    """
    sig.refuse_if_memory_writes_off()
    # In a tree that places by topic, a retitle holds the placement lock: the fact's lines at
    # every level change together, with no render or set-topics between them.
    anchor = us.resolve_anchor(str(Path(level).resolve()))
    with placement_lock_if_listed(anchor, "retitle"):
        return _retitle_entry(level, slug, to_title)


def _retitle_entry(level, slug, to_title):
    """`retitle_entry` itself; its caller holds the placement lock when the fact is bound."""
    sig.refuse_if_memory_writes_off()
    rep = {"slug": slug, "to_title": to_title, "level": str(level), "retitled": False,
           "levels": [], "refused": None, "warnings": []}
    lvl = Path(level).resolve()
    anchor = us.resolve_anchor(str(lvl))
    if anchor is None:
        rep["refused"] = "no anchor for this level"
        return rep

    title = _normalised_title(to_title)
    if not title:
        rep["refused"] = "the new title is empty"
        return rep
    rep["to_title"] = title

    _scope, entries, _bodies = read_store(str(lvl))
    entry = next((e for e in entries if e.slug == slug), None)
    if entry is None:
        rep["refused"] = "slug %r not found at this level" % slug
        return rep
    if entry.legacy:
        # A legacy `uuid:` line with no `bx:slug=` token has its slug DERIVED from the title
        # (`_slug_from_title`), so retitling one silently changes the fact's identity. `rename`
        # refuses legacy entries for the same reason.
        rep["refused"] = "entry is an unmigrated legacy pointer - run migrate_to_slug_store.py first"
        return rep
    if entry.pin:
        rep["refused"] = ("fact is pinned - use `amend-pinned --proj %s --slug %s --title ...`, "
                          "the one deliberate path through the pin gate" % (level, slug))
        return rep
    if entry.title == title:
        rep["refused"] = "the new title is the same as the old one"
        return rep
    # Decided before any write: a fact placed by topic has a line at each level its topics place
    # it at, retitled there too, and none of them is a duplicate.
    placed = bool(_placed_slugs(anchor, [slug]))
    # Every level it retitles is held to the block cap before any is written.
    old_bytes = len(entry.title.encode("utf-8"))
    rep["refused"] = _line_growth_refusal(
        "retitle", [(level_dir, slug, us.Pointer(slug=slug, title=title, hook=ptr.hook,
                                                 pin=ptr.pin))
                    for level_dir, ptr in _copies_of(anchor, slug) if not ptr.legacy],
        lambda shrink, _old, _new: (
            "Retitle it with a title at least %d bytes shorter: %s retitle --level %s --slug %s "
            "--to-title <title> (a title no longer than the %d bytes of the current one always "
            "goes through)" % (shrink, _ENGINE_ROUTE, level, slug, old_bytes)))
    if rep["refused"]:
        return rep

    us.add_pointer(str(lvl), slug=slug, title=title, hook=entry.hook,
                   pin=entry.pin)
    rep["levels"].append(str(lvl))
    # The body is re-read under the level lock rather than taken from `entry`: that copy was read
    # unlocked, and an `add` on the same slug in another session (which rewrites the body under
    # this lock) can land between that read and this write - writing the stale copy back loses its
    # prose. The lock is non-reentrant, so it is taken only after `add_pointer` released its own.
    with sig.memory_lock(sig.claude_local_md_path(str(lvl))):
        current = read_store_text(us.body_path(anchor, slug)).rstrip("\n")
        retitled_body = _with_title(current, title)
        if current and retitled_body != current:     # "" is an absent body: writing it back
            us.put_body(str(anchor), slug, retitled_body)   # would create one for a dangler

    # A slug carried by more than one level is a pre-existing violation, but leaving the OTHER
    # pointers on the old title is not neutral: `move_entry` and `relocate_entry` both refuse when
    # duplicate pointers disagree on (title, hook), so a level-local retitle arms a DIFFERENT TITLE
    # refusal for whoever moves the fact next. Retitle them too and surface the duplicate.
    for other in curated_levels_under(anchor):
        if Path(other).resolve() == lvl:
            continue
        _s, oentries, _b = read_store(str(other))
        dup = next((e for e in oentries if e.slug == slug), None)
        if dup is None:
            continue
        if dup.legacy:
            # add_pointer would flip it to the current format, which strands it unless a
            # slug-named body already exists. Leave it for the migration and say so.
            rep["warnings"].append("slug was ALSO pointed at from %s as an unmigrated legacy "
                                   "pointer - left alone; migrate it, then retitle there" % other)
            continue
        us.add_pointer(str(other), slug=slug, title=title, hook=dup.hook,
                       pin=dup.pin)
        rep["levels"].append(str(other))
        if placed:
            continue                                 # placed by topic: one line per level, by design
        rep["warnings"].append("slug was ALSO pointed at from %s - a pre-existing duplicate; "
                               "retitled there too, dedup it deliberately" % other)

    rep["retitled"] = True
    return rep


def _other_level_pointing_in(anchor, level, slug):
    """The first curated level under `anchor`, other than `level`, carrying a pointer for `slug`; None
    when there is none."""
    here = Path(level).resolve()
    for lvl in curated_levels_under(anchor):
        if Path(lvl).resolve() == here:
            continue
        _s, entries, _b = read_store(lvl)
        if any(e.slug == slug for e in entries):
            return lvl
    return None


def _other_levels_pointing_in(anchor, slug):
    """True when any curated level under `anchor` still carries a pointer for `slug`."""
    for lvl in curated_levels_under(anchor):
        _s, entries, _b = read_store(lvl)
        if any(e.slug == slug for e in entries):
            return True
    return False


def _raise_walk_error(err):
    """os.walk's onerror: a directory it cannot list stops the walk with a named TreeWalkError."""
    raise TreeWalkError(getattr(err, "filename", None) or "?",
                        "cannot list this directory, so the levels under it are unknown: %s"
                        % err) from err


def _walk_error_sink(unreadable):
    """os.walk's onerror for `curated_levels_under`: raise when no `unreadable` list was given, so
    a caller cannot get a partial answer by forgetting to ask for one; append the directory's path
    to the list when one was."""
    if unreadable is None:
        return _raise_walk_error
    return lambda err: unreadable.append(str(getattr(err, "filename", None) or err))


def _carries_pointer_block(path):
    """True when the `CLAUDE.local.md` at `path` holds a managed pointer block.

    False when it has vanished or is a dangling link - absent is a fact about the tree. Any other
    read failure, and bytes that are not UTF-8, raise TreeWalkError: whether such a file holds a
    block cannot be known, so it is neither counted nor dropped."""
    text = read_store_text(path)
    return us.INDEX_BEGIN in text or us.LEGACY_INDEX_BEGIN in text


def curated_levels_under(anchor, unreadable=None):
    """Every curated level dir under `anchor` (a `CLAUDE.local.md` carrying a managed pointer block),
    pruning what `us.is_non_level_dirname` names (vendored/build/cache dirs, the store and a
    migration's backup beside it) and the dream's own backup root - a bounded os.walk of the
    whole subtree, SIBLINGS included.
    THE single tree-walk (reconcile's `_all_curated_levels` delegates here) so the two never drift.

    Backups go under `~/.claude/self-improve-audit/` so a snapshot is never re-read as live memory.
    That holds for a tree on another mount, but `~/.claude` is itself an anchor (it carries a
    `CLAUDE.md`, and `~` is an excluded anchor so the walk stops there), putting the backup root
    INSIDE that tree - every backed-up pointer block then reads as a live level (measured: 6028
    spurious problems from `--check-tree ~/.claude`). Prune by RESOLVED PATH, never by dirname, so a
    project that happens to own a `self-improve-audit/` dir is still walked.

    Raises TreeWalkError when a directory cannot be listed (the anchor itself included) or a
    `CLAUDE.local.md` cannot be read or is not UTF-8: a list with a subtree silently missing is
    the answer every caller would trust, so the walk refuses instead of undercounting. A caller
    that REPORTS rather than acts (check-tree) passes a list as `unreadable` instead: it receives
    the path of each directory or level file that could not be read, and the walk goes on."""
    audit_root = sig._audit_dir().resolve()
    out = []
    for root, dirs, files in os.walk(str(anchor), onerror=_walk_error_sink(unreadable)):
        dirs[:] = [d for d in dirs if not us.is_non_level_dirname(d)
                   and Path(root, d).resolve() != audit_root]
        if "CLAUDE.local.md" not in files:
            continue
        try:
            if _carries_pointer_block(sig.claude_local_md_path(root)):
                out.append(root)
        except TreeWalkError as exc:
            if unreadable is None:
                raise
            unreadable.append(exc.path)
    return out


def _body_unlabelled(body):
    """True when a fact body lacks the `**Why:**` or the `**How to apply:**` label of the authoring
    template. A STYLE advisory: the ~5x application lift measured in 5.37.0 was for the frontmatter
    frame the engine always writes, never for these labels, and a body can carry its reasoning in
    prose without them. Not called "unframed": that word means no frontmatter everywhere else here,
    and sharing it is how the frontmatter's number came to be quoted for the labels."""
    return "**Why:**" not in (body or "") or "**How to apply:**" not in (body or "")


def lint_tree(anchor):
    """READ-ONLY voice/frame sweep over every curated level under `anchor` (defect J - the store had
    no sweep verb, so the debt was rediscovered every dream). Reports: hooks over the HARD cap
    (the write path refuses one, so any that exist are hand-edited or legacy), hooks missing a
    trigger phrase (never fire during
    reasoning), and bodies missing the `**Why:**`/`**How to apply:**` labels (style only, see
    `_body_unlabelled`). Advisory, never a failure. Also lists pointer lines whose slug is not a plain filename
    (`invalid_pointers`): the parser skips them and the next write drops them. Returns a report dict."""
    anchor = _anchor(str(anchor))
    over_cap, no_trigger, unlabelled, invalid = [], [], [], []
    for lvl in curated_levels_under(anchor):
        text = read_store_text(sig.claude_local_md_path(lvl))
        invalid.extend((lvl, raw) for raw in us.invalid_pointer_lines(text))
        _scope, entries, bodies = read_store(lvl)
        for e in entries:
            if len(e.hook or "") > us.HOOK_HARD_MAX:
                over_cap.append((lvl, e.slug, len(e.hook)))
            if us.hook_missing_trigger(e.hook):
                no_trigger.append((lvl, e.slug))
            if _body_unlabelled(bodies.get(e.slug, "")):
                unlabelled.append((lvl, e.slug))
    return {"anchor": str(anchor), "over_cap": over_cap, "no_trigger": no_trigger,
            "unlabelled": unlabelled,
            "invalid_pointers": invalid}


# ---- topics: which facts and levels a rule is about ------------------------------------------

FRONTMATTER_HEAD_BYTES = 16384
"""How much of a body a topic scan reads: the frontmatter sits at the head, and a scan over every
body of a tree must not read every body whole."""
MAX_TOPIC_BATCH = 5000
"""Most rows one `set-topics --batch` takes: the batch is held as one dict while it is applied."""
MAX_TOPIC_BATCH_LINE_BYTES = 4096
"""Longest line a `set-topics --batch` file may hold, its line break counted. A row is one slug and
at most tp.MAX_TOPICS tags of 32 characters, far under this; the reader holds one line at a time."""
_REFUSALS_SHOWN = 20


# A topic write declined as a whole (`uuid_store.TopicRefusal`). Defined by the store, whose
# add_pointer refuses a TOPICS line as well: uuid_store cannot import this module (the import runs
# the other way), so the shared type lives there, as InvalidSlug's does.
TopicRefusal = us.TopicRefusal


ADD_REFUSALS = (SlugCollision, HookTooLong, EmptyBody, TopicsOnCreate, PinnedEntry, InvalidSlug,
                InvalidSkill, TopicRefusal, tp.InvalidTopic)
"""What a fact write through `add_with_advice` raises when it declines the whole write (nothing
written): the CLI `add` and the mod bridge both report these as a refusal. TopicRefusal and
InvalidTopic come from the level's descriptor (an add --scope with a TOPICS line, a legacy block
whose line does not parse)."""


# ---- render: the parts a pointer line placed by topic is built from ---------------------------

MAX_RENDER_BLOCK_BYTES = 1 << 20
"""Most bytes of pointer lines one level's block may hold once `render-topics` is done with it:
the lines it places there plus the lines that stay there (pinned, legacy, and those of facts it
does not place). In the tree scope a managed line placed elsewhere does not count: the same run
drops it. A chain render never drops a line for being placed elsewhere, so there it stays and
counts. A level's lines are the one thing a render holds, and a block past this is a mistake to
fix, not text to load. Every writer of a block follows one rule against it (`_grows_past_cap`): a
write is refused only when the block would end past this AND larger than it is now."""
_RENDER_SHOWN = 20
_SWEEP_ROUTE = "hooks/memory_engine.py render-topics --proj %s --scope tree"


class RenderBlockTooLarge(TopicRefusal):
    """Raised, before that level is written, when the block one level would hold passes
    MAX_RENDER_BLOCK_BYTES: `kept` bytes of pinned, legacy or unplaced lines that stay there,
    `stale` bytes of managed lines placed at another level that stay there (only a chain render
    leaves them: it never drops a line for being placed elsewhere), and `added` bytes of every
    line the render places there (the whole count, not the count when the cap was first passed).
    `size` is their sum and `over` how far it passes the cap: the fewest bytes that must leave the
    block. `need` is how far `kept` plus `added` alone pass it (`over` when nothing is stale).

    The message names one route, the first that applies:
    - `stale` lines are there and the block fits without them (`need` <= 0): the tree-scope render
      of `anchor`, the one render that drops them (a move would take a line a later render puts
      back, and a rebind un-binds facts that are bound correctly).
    - neither pool reaches `need` alone (`kept` and `added` each pass the cap): both, a move of
      every kept line and a rebind of the rest, with the amounts and the bounds of any other
      split. A route is named only when its own pool can free the bytes it asks for.
    - the kept lines are at least as large as the added ones and reach `need`: the move that
      takes at least `need` bytes of kept lines to another level of the altitude chain, whose own
      block is held to the same cap. Only kept lines are offered: a line placed by topic is the
      render's to place, not a move's.
    - else (the added lines reach `need`): the set-topics batch that rebinds the facts which need
      not be read at that level (`bound_to` says which topics put them there), at least `need`
      bytes of their lines.
    The last three name `need`, not `over`: a tree-scope render would refuse at that level too (it
    adds at least the lines the chain does), so the stale lines cannot go first; once the rest
    fits, the next refusal is the first kind and names the render that drops them."""

    def __init__(self, level, kept, added, bound_to, stale=0, anchor=None, now=None):
        self.level, self.kept, self.added, self.stale = level, kept, added, stale
        self.size = kept + stale + added
        # The cap rule (`_grows_past_cap`): only a render that ends past the cap AND grows the
        # block is refused, so the reader learns that no smaller step is needed than this one.
        grows = ("" if now is None else
                 " It would also leave the block larger than the %d bytes it holds now; a render "
                 "that leaves a block no larger than it is now is never refused." % now)
        self.over = self.size - MAX_RENDER_BLOCK_BYTES
        self.need = kept + added - MAX_RENDER_BLOCK_BYTES
        if stale and self.need <= 0:
            super().__init__([(
                "%d bytes of lines placed by topic at another level stay at %s beside %d bytes "
                "of pinned, legacy or unplaced lines, and %d bytes of lines placed there are to "
                "be added: %d bytes over the %d bytes one level's block may hold. A chain render "
                "never drops a line for being placed elsewhere, and without those lines the block "
                "fits: run " + _SWEEP_ROUTE + ", which drops them (it holds every level to the "
                "same %d bytes and names its own route if one would pass them), then run this "
                "render again"
            ) % (stale, level, kept, added, self.over, MAX_RENDER_BLOCK_BYTES, anchor,
                 MAX_RENDER_BLOCK_BYTES) + ("." + grows if grows else "")])
            return
        also = ("" if not stale else
                " (they count here until a tree-scope render drops them, which it cannot do "
                "before the rest fits; without them the block is %d bytes over, the figure "
                "below, and once that is gone this refusal names that render)" % self.need)
        beside = ("" if not stale else
                  ", beside %d bytes of lines placed by topic at another level%s,"
                  % (stale, also))
        if kept < self.need and added < self.need:
            text = ("%d bytes of pinned, legacy or unplaced lines stay at %s%s and %d bytes of "
                    "lines placed there are to be added, %d bytes over the %d bytes one level's "
                    "block may hold. Each part alone is more than the block may hold, so neither "
                    "moving kept lines nor rebinding facts frees the %d bytes by itself; do both. "
                    "Move kept lines totalling at least %d bytes (a line counts its line break; a "
                    "line placed by topic is not one to move) to levels above or below it with "
                    "hooks/memory_engine.py move --from-level %s --to-level <level> --slug <slug> "
                    "[<slug> ...] (a legacy line needs migrate_to_slug_store.py first; each level "
                    "they go to is held to the same %d bytes, counting the lines it keeps and "
                    "those placed there). And rebind facts that need not be read there (they are "
                    "bound to %s), at least %d bytes of their lines, with hooks/memory_engine.py "
                    "set-topics --proj %s --batch <file>, one {\"slug\": ..., \"topics\": [...]} "
                    "per line giving its real topics ([] binds it to no topic and leaves its line "
                    "where it is, so a line already at that level stays and still counts). Any "
                    "split works that totals at least %d bytes, at most %d moved and %d rebound. "
                    "Then run render-topics again"
                    % (kept, level, beside, added, self.over, MAX_RENDER_BLOCK_BYTES, self.need,
                       kept, level, MAX_RENDER_BLOCK_BYTES, bound_to, self.need - kept, level,
                       self.need, kept, added))
        elif kept >= added and kept >= self.need:
            text = ("%d bytes of pinned, legacy or unplaced lines stay at %s%s and %d bytes of "
                    "lines placed there are to be added, %d bytes over the %d bytes one level's "
                    "block may hold: the pinned, legacy or unplaced lines are the larger part. "
                    "Move kept lines totalling at least %d bytes (a line counts its line break; a "
                    "line placed by topic is not one to move) to a level above or below it with "
                    "hooks/memory_engine.py "
                    "move --from-level %s --to-level <level> --slug <slug> [<slug> ...] (a legacy "
                    "line needs migrate_to_slug_store.py first); the level they go to is held to "
                    "the same %d bytes, counting the lines it keeps and those placed there. Then "
                    "run render-topics again"
                    % (kept, level, beside, added, self.over, MAX_RENDER_BLOCK_BYTES,
                       self.need, level, MAX_RENDER_BLOCK_BYTES))
        else:
            stays = ("%d bytes of lines that stay there" % kept if not stale else
                     "%d bytes of pinned, legacy or unplaced lines and %d bytes of lines placed by "
                     "topic at another level%s that stay there" % (kept, stale, also))
            text = ("%d bytes of lines placed at %s beside %s come "
                    "to %d bytes over %d, the most one level's block may hold: too many facts are "
                    "bound to %s. Rebind facts that need not be read there, at least %d bytes of "
                    "their lines, with "
                    "hooks/memory_engine.py set-topics --proj %s --batch <file>, one {\"slug\": "
                    "..., \"topics\": [...]} per line giving its real topics ([] binds it to no "
                    "topic and leaves its line where it is, so a line already at that level stays "
                    "and still counts), then run render-topics again"
                    % (added, level, stays, self.over, MAX_RENDER_BLOCK_BYTES, bound_to,
                       self.need, level))
        super().__init__([text + "." + grows if grows else text])


class CollapseTooLarge(TopicRefusal):
    """Raised by set-topics, before any write, when the line an un-bound fact keeps at the tree
    top (see `set_fact_topics`) would take the top's block past MAX_RENDER_BLOCK_BYTES. The block
    holds `kept` bytes of pinned, legacy or unplaced lines, `fixed` of them lines of facts this
    call un-binds (the collapse keeps them at the top, so they never leave it in this call),
    `placed` bytes of managed lines placed at the top and `stale` bytes of managed lines placed
    below it, which a tree-scope render drops; `added` bytes would be added. `held` is the block's
    whole count, `room` what it can still take, `over` the fewest bytes that must leave it and
    `need` how far it passes the cap without the stale lines. `fit` is how many of the added lines
    fit in `room`, smallest first; `rebind` whether a level below the top has a topic.

    A route is named only when it can free the bytes it asks for on its own figures: `kept -
    fixed` bytes can be moved, `placed` bytes rebound (after set-level-topics when no level below
    has a topic), `stale` bytes swept. The first that applies:
    - `stale` lines are there and the block fits without them (`need` <= 0): the tree-scope render.
    - the lines this call keeps at the top alone pass the cap (`fixed + added`): nothing that
      leaves the top makes room, so it says the top cannot hold a line of each of these facts at
      once and names a smaller batch, at most `room` bytes of added lines per call - only when
      that batch can un-bind a fact (`room` positive, and `fit` or `fixed` non-zero); else the
      pools that free room first.
    - the movable kept lines reach `need`: a move of them.
    - the placed lines reach `need`: the set-topics batch that rebinds facts placed at the top,
      then the tree-scope render.
    - else both, each with its amount: every movable kept line moved and the rest rebound (the
      two together always reach `need` once `fixed + added` fits)."""

    def __init__(self, top, kept, added, stale=0, placed=0, fixed=0, fit=0, rebind=True):
        self.top, self.kept, self.added, self.stale, self.placed = top, kept, added, stale, placed
        self.fixed, self.fit, self.rebind = fixed, fit, rebind
        self.movable = kept - fixed
        self.held = kept + stale + placed
        self.room = MAX_RENDER_BLOCK_BYTES - self.held
        self.over = self.held + added - MAX_RENDER_BLOCK_BYTES
        self.need = kept + placed + added - MAX_RENDER_BLOCK_BYTES
        head = ("un-binding these facts leaves one line of each at the tree top %s: %d bytes of "
                "lines are there and %d bytes would be added, %d bytes over the %d bytes one "
                "level's block may hold"
                % (top, self.held, added, self.over, MAX_RENDER_BLOCK_BYTES))
        parts = ("; of the lines there, %d bytes are pinned, legacy or unplaced%s, %d bytes are "
                 "placed by topic at the top and %d bytes are placed by topic at a level below it"
                 % (self.movable, "" if not fixed else
                    ", %d bytes are lines of facts this call un-binds (it keeps them at the top)"
                    % fixed, placed, stale)) if stale or placed or fixed else ""
        if stale and self.need <= 0:
            tail = (". Without the lines placed below the top the block fits, and a tree-scope "
                    "render drops them: run " + _SWEEP_ROUTE + " (it holds every level to the "
                    "same %d bytes and names its own route if one would pass them), then run "
                    "set-topics again") % (top, MAX_RENDER_BLOCK_BYTES)
        elif fixed + added > MAX_RENDER_BLOCK_BYTES:
            tail = self._split_text()
        elif self.movable >= self.need and (self.movable >= placed or placed < self.need):
            tail = ". " + self._move_text(self.need, "Move") + ". Then run set-topics again"
        elif placed >= self.need:
            tail = (". The lines placed by topic at the top are the larger part: "
                    + self._rebind_text(self.need) + ", then run set-topics again")
        else:
            tail = (". Neither the movable lines (%d bytes) nor those placed by topic at the top "
                    "(%d bytes) reach the %d bytes alone; do both: %s; and %s, then run "
                    "set-topics again"
                    % (self.movable, placed, self.need, self._move_text(self.movable, "move"),
                       self._rebind_text(self.need - self.movable)))
        super().__init__([head + parts + tail])

    def _later(self):
        return ("" if not self.stale else
                " (without the lines placed below the top the block is %d bytes over; once "
                "that is gone this refusal names the tree-scope render that drops them)"
                % self.need)

    def _move_text(self, amount, verb):
        return ("%s %slines totalling at least %d bytes%s (a line counts its line break; a line "
                "placed by topic is not one to move, nor one of a fact this call un-binds) from "
                "the tree top to a level below it with hooks/memory_engine.py move --from-level "
                "%s --to-level <level> --slug <slug> [<slug> ...] (a legacy line needs "
                "migrate_to_slug_store.py first); the level they go to is held to the same %d "
                "bytes, counting the lines it keeps and those placed there"
                % (verb, "pinned, legacy or unplaced " if self.stale or self.placed or self.fixed
                   else "", amount, self._later(), self.top, MAX_RENDER_BLOCK_BYTES))

    def _rebind_text(self, amount):
        first = ("" if self.rebind else
                 "no level below the top has a topic, so first give one a topic with "
                 "hooks/memory_engine.py set-level-topics --proj <level> --topics <tags>, then ")
        return (first + "rebind facts placed there whose lines total at least %d bytes to a "
                "topic a level below the top has, with hooks/memory_engine.py set-topics --proj "
                "%s --batch <file>, one {\"slug\": ..., \"topics\": [...]} per line ([] would "
                "leave each line at the top), and run " + _SWEEP_ROUTE + " to move their lines "
                "down (it drops the lines placed below the top as well)") % (amount, self.top,
                                                                              self.top)

    def _split_text(self):
        text = (". One line of each fact this call un-binds stays at the top, and those lines "
                "alone come to %d bytes (%d there already, %d to be added), more than the block "
                "may hold: the top cannot hold a line of each of them at once, and no line that "
                "leaves the top makes room for them all. Un-bind fewer facts per call with "
                "hooks/memory_engine.py set-topics --proj %s --batch <file>: the lines one call "
                "adds at the top may total at most %d bytes now (%d of the lines this call "
                "would add fit in that, smallest first; a fact whose line is already at the top "
                "adds none). The lines a call leaves at the top are then unplaced lines, which "
                "a later refusal offers to move to a level below"
                % (self.fixed + self.added, self.fixed, self.added, self.top, self.room, self.fit))
        # A smaller batch is a route only when it can un-bind a fact: one whose added line fits
        # the room, or one whose line is already at the top. With room left but less than any
        # added line and no such fact, a batch of none would be named and nothing freed, so the
        # pools that free room are named exactly as for a full block.
        if self.room > 0 and (self.fit or self.fixed):
            return text
        pools = []
        if self.stale:
            pools.append(("run " + _SWEEP_ROUTE + " (drops %d bytes of lines placed below the "
                          "top)") % (self.top, self.stale))
        if self.movable:
            pools.append(self._move_text(self.movable, "move"))
        if self.placed:
            pools.append(self._rebind_text(self.placed))
        if not pools:
            return (text + ". The block is %s and holds nothing that can leave it in this "
                    "call: only facts whose line is already at the top can be un-bound now"
                    % self._fullness())
        return (text + ". The block is %s: first free room - " % self._fullness()
                + "; or ".join(pools))

    def _fullness(self):
        return ("full" if self.room <= 0 else
                "too full for any line this call would add (%d bytes left)" % self.room)


def _grows_past_cap(before, after):
    """The one cap rule every writer of a level's block follows (add, amend-pinned, retitle,
    rename, move, relocate, a set-topics collapse and render-topics): a write is refused only
    when the block would END past MAX_RENDER_BLOCK_BYTES and GROW, ending larger than the
    `before` bytes it holds now. A write that leaves an over-full block no larger than it is (a
    render adding nothing, a refresh to a shorter line, a drop) goes through: refusing it would
    wedge every writer of that level until a person freed room, though none of them made it
    fuller."""
    return after > MAX_RENDER_BLOCK_BYTES and after > before


def _block_bytes(level_dir):
    """Bytes of every line in one level's block, each counting its line break."""
    return sum(_line_size(p) for p in
               us.parse_pointer_index(read_store_text(sig.claude_local_md_path(str(level_dir))))[1])


class LineGrowsPastCap(TopicRefusal):
    """Raised by `add` and `amend-pinned` before any write when the line they write would leave a
    level's block past MAX_RENDER_BLOCK_BYTES and larger than it is now (`_grows_past_cap`). A
    TopicRefusal, so every caller that reports the engine's refusals reports this one."""

    def __init__(self, text):
        super().__init__([text])


def _line_growth_refusal(verb, changes, retry):
    """The refusal text when a write replacing one line per level (`changes`, an iterable of
    (level dir, the slug whose line goes, the line that takes its place)) would leave any of
    those blocks past the cap and larger than now (`_grows_past_cap`), else None. Every level is
    judged before the caller writes any. The message names the first such level in the order
    given, with its own numbers, and `retry(shrink, old, new)` the route that keeps the write
    from growing every such level: `shrink` is how many bytes shorter the line must be, `old` the
    bytes of the line it replaces at the named level (0 for none) and `new` the bytes of the new
    line. Freeing room by moving other lines out is named as the second route. Reads one level's
    block at a time; holds one row."""
    named, shrink = None, 0
    for level, slug, line in changes:
        pointers = us.parse_pointer_index(read_store_text(sig.claude_local_md_path(str(level))))[1]
        before = sum(_line_size(p) for p in pointers)
        old = sum(_line_size(p) for p in pointers if p.slug == slug)
        after = before - old + _line_size(line)
        if not _grows_past_cap(before, after):
            continue
        shrink = max(shrink, after - max(MAX_RENDER_BLOCK_BYTES, before))
        if named is None:
            named = (level, before, after, old, _line_size(line))
    if named is None:
        return None
    level, before, after, old, new = named
    return ("%s would leave the block at %s at %d bytes, %d bytes over the %d bytes one level's "
            "block may hold and %d bytes larger than it is now (a line counts its line break; a "
            "write that leaves a block no larger than it is now is never refused). %s; or first "
            "free at least %d bytes at %s by moving lines out of it with %s move --from-level %s "
            "--to-level <level> --slug <slug> [<slug> ...] (a line placed by topic is not one to "
            "move; the level they go to is held to the same %d bytes)"
            % (verb, level, after, after - MAX_RENDER_BLOCK_BYTES, MAX_RENDER_BLOCK_BYTES,
               after - before, retry(shrink, old, new), after - MAX_RENDER_BLOCK_BYTES, level,
               _ENGINE_ROUTE, level, MAX_RENDER_BLOCK_BYTES))


def _read_body_head(path):
    """The first FRONTMATTER_HEAD_BYTES of the body at `path` as text, None when the file is
    missing. Raises TreeWalkError when it exists and cannot be read."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(FRONTMATTER_HEAD_BYTES)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as exc:
        raise TreeWalkError(path, "unreadable: %s" % exc) from exc
    return head.decode("utf-8", errors="replace")


def _iter_body_heads(anchor):
    """Yield (slug, head text) for every body of the tree, one at a time: nothing is held but the
    head being read."""
    facts = us.central_facts_dir(anchor)
    try:
        scan = os.scandir(facts)
    except (FileNotFoundError, NotADirectoryError):
        return
    except OSError as exc:
        raise TreeWalkError(facts, "cannot list this directory: %s" % exc) from exc
    with scan:
        for item in scan:
            if not item.name.endswith(".md") or not us.is_valid_slug(item.name[:-3]):
                continue
            head = _read_body_head(item.path)
            if head is not None:
                yield item.name[:-3], head


def _level_parts(anchor, level):
    """`level` as the path parts below `anchor` that `topic_placement` works on; () for the anchor.
    Lexical, like `topic_store.level_key` it is built on."""
    key = topic_store.level_key(anchor, level)
    return tuple(key.split("/")) if key else tp.TOP


def _line_from_head(slug, head):
    """The pointer line a managed fact gets, built from its body alone: title from `title:`, hook
    from `description:`, never pinned. None when the body lacks either: such a fact is never
    rendered, it stays where its pointer is."""
    title, hook = _body_title(head), _body_description(head)
    if not title or not hook:
        return None
    return us.Pointer(slug=slug, title=title, hook=hook)


def topic_level_map(anchor, levels=None):
    """(LevelMap, {parts: level dir}) of the tree: every curated level whose descriptor is not
    empty, with the topics its `TOPICS:` line declares (none without the line). The anchor is
    always in the dir map, and in the LevelMap only when its own descriptor is not empty, like any
    other level. A level with no descriptor is left out, so a scaffold-only level cannot block a
    roll-up.
    Raises TopicRefusal, naming the levels, when a `TOPICS:` line does not parse: placing by a
    guessed line would move rules. Holds one small record per level."""
    declared, dirs, bad, total = {}, {tp.TOP: os.path.abspath(str(anchor))}, [], 0
    for level in curated_levels_under(anchor) if levels is None else levels:
        scope = us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[0]
        if not scope.strip():
            continue
        try:
            topics = tp.descriptor_topics(scope) or ()
        except tp.InvalidTopic as exc:
            total += 1
            if len(bad) < _RENDER_SHOWN:
                bad.append("%s: its TOPICS line does not parse (%s); set-level-topics replaces it"
                           % (level, exc))
            continue
        parts = _level_parts(anchor, level)
        declared[parts], dirs[parts] = topics, os.path.abspath(str(level))
    if total:
        raise TopicRefusal(bad, total)
    return tp.LevelMap(declared), dirs


def _unplaceable_slugs(levels):
    """The slugs with a pinned or legacy line at any of `levels` (`_keeps_in_place`): the facts
    the renderer never places, whatever their bodies' `topics:` say. One record per such pointer."""
    fixed = set()
    for level in levels:
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            if _keeps_in_place(ptr):
                fixed.add(ptr.slug)
    return fixed


def _comparable_line(ptr):
    """`ptr`'s line with title and hook single-spaced (`_normalised_title`), never pinned: the form
    a body stores them in. A line that differs from its body only in whitespace says the same
    thing, and the renderer rewrites it to the body's form, so it is no reason to refuse a bind."""
    return us.Pointer(slug=ptr.slug, title=_normalised_title(ptr.title),
                      hook=_normalised_title(ptr.hook), uuid=ptr.uuid,
                      legacy=ptr.legacy).index_line()


def _line_problem(slug, anchor, lines):
    """Why `slug` cannot be bound to a topic yet, or None. `lines` is {comparable line: (level,
    pointer)} for every distinct line of the fact (see `_pointer_owners`). A rendered line is built
    from the body alone, so a legacy pointer, a body without `description:` or `title:`, or any
    line that says something else than the body would render has to be repaired first; each
    refusal names the route that repairs that cause."""
    for level, ptr in lines.values():
        if ptr.legacy:
            return ("%s: its line at %s is a legacy uuid: pointer, so the fact is not migrated to "
                    "the slug store; run hooks/migrate_to_slug_store.py --root %s --apply (without "
                    "--apply it only reports), then tag it" % (slug, level, anchor))
    head = _read_body_head(us.body_path(anchor, slug)) or ""
    # The body is shared, so a level holding any line of the fact is a level its repair may
    # target. Every route names one: factedit otherwise walks up from its cwd and cannot run
    # outside the tree, and add without --proj and --slug derives a new slug from the title,
    # writing a second fact while this one stays as it is.
    level = next(iter(lines.values()))[0]
    if not _body_description(head):
        return ("%s: its body has no description:, so no line can be rendered from it; write its "
                "prose (without the --- frontmatter) to a file and run "
                "skills/meta-dream-tree/factedit.py apply --slug %s --level %s "
                "--body-file <that file>, which rebuilds the frame from its line (or "
                "hooks/memory_engine.py add --proj %s --slug %s --title <the line's title> "
                "--hook-file <file> --body-file <that file> with the line's hook in <file>), "
                "then tag it" % (slug, slug, level, level, slug))
    if not _body_title(head):
        return ("%s: its body has no title:, so no line can be rendered from it; run "
                "hooks/memory_engine.py heal --proj %s --backfill-titles (or "
                "skills/meta-dream-tree/factedit.py apply --slug %s --level %s "
                "--title <title>), then tag it" % (slug, anchor, slug, level))
    wanted = _comparable_line(_line_from_head(slug, head))
    for line, (level, _ptr) in lines.items():
        if line != wanted:
            # Both routes name the level: factedit otherwise resolves the owning level by
            # walking up from its cwd, and rewrites a line that already matched while this one
            # stays as it is.
            return ("%s: its line at %s differs from what its body renders; run "
                    "skills/meta-dream-tree/factedit.py apply --slug %s --level %s --hook-file "
                    "<file> (or hooks/memory_engine.py add --proj %s --slug %s --title <the "
                    "body's title:> --hook-file <file>) with the body's description: as the "
                    "hook, or with the hook you want if it is not the line's current one, then "
                    "tag it" % (slug, level, slug, level, level, slug))
    return None


def read_body_topics(path):
    """`_body_topics` of the body at `path`, reading only its first FRONTMATTER_HEAD_BYTES.
    None too when the file is missing. Raises TreeWalkError when it exists and cannot be read."""
    head = _read_body_head(path)
    return None if head is None else _body_topics(head)


def iter_fact_topics(anchor):
    """Yield (slug, topics) for every body of the tree that carries a `topics:` line, one body at a
    time: nothing is held but the body's head being read."""
    for slug, head in _iter_body_heads(anchor):
        topics = _body_topics(head)
        if topics is not None:
            yield slug, topics


def _topic_list(anchor):
    """The tree's topic list as {name: meaning}. Raises TopicRefusal when the tree has none."""
    data = topic_store.load(anchor)
    if data is None:
        raise TopicRefusal(["this tree has no topic list yet (topics-set-list writes one)"])
    return data["topics"]


def _outside_list(topics, allowed):
    return [t for t in topics if t not in allowed]


def set_topic_list(proj, topics, tagger):
    """Replace the tree's closed topic list. Raises TopicRefusal, before writing, for an empty
    list (every set-topics would then be refused) and when a topic the new list drops is still
    carried by a fact or declared by a level, naming the first users. A level whose `TOPICS:` line
    or a fact whose `topics:` line does not parse declares nothing it could lose, and does not
    block the list."""
    sig.refuse_if_memory_writes_off()
    if not topics:
        raise TopicRefusal(["an empty topic list: a tree's list names at least one topic"])
    anchor = _anchor(proj)
    old = topic_store.load(anchor)
    # By the name the list will store (trimmed), one name at a time: the list is capped by
    # topic_store.MAX_LIST, not by the per-fact tp.MAX_TOPICS a whole-list normalise applies.
    names = {tp.normalise_topics([name])[0] for name in topics}
    dropped = set(old["topics"]) - names if old else set()
    users, total = [], 0
    if dropped:
        for slug, carried in iter_fact_topics(anchor):
            if dropped & set(carried):
                total += 1
                if len(users) < _REFUSALS_SHOWN:
                    users.append("fact %s carries %s" % (slug, ", ".join(sorted(dropped & set(carried)))))
        for level in curated_levels_under(anchor):
            scope = us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[0]
            try:
                declared = set(tp.descriptor_topics(scope) or ())
            except tp.InvalidTopic:
                continue
            if dropped & declared:
                total += 1
                if len(users) < _REFUSALS_SHOWN:
                    users.append("level %s declares %s" % (level, ", ".join(sorted(dropped & declared))))
    if total:
        raise TopicRefusal(users, total)
    return topic_store.save_list(anchor, topics, tagger)


def _pointer_owners(anchor, wanted):
    """{slug: (first level pointing at it, pinned anywhere, {comparable line: (first level holding
    it, its pointer)})} for the slugs in `wanted`, from one walk over the tree's levels. Holds one
    entry per wanted slug, and per slug one record per DISTINCT line (`_comparable_line`): lines
    that say the same thing at several levels are one record, so a placed fact costs one."""
    owners = {}
    for level in curated_levels_under(anchor):
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            if ptr.slug in wanted:
                first, pinned, lines = owners.get(ptr.slug) or (level, False, {})
                lines.setdefault(_comparable_line(ptr), (level, ptr))
                owners[ptr.slug] = (first, pinned or ptr.pin, lines)
    return owners


def _topic_row_problem(slug, topics, anchor, allowed, owners):
    """Why this row cannot be applied, or None."""
    if not us.is_valid_slug(slug):
        return "%r is not a valid slug" % (slug,)
    if slug not in owners:
        return "%s: no level points at it" % slug
    if owners[slug][1] and topics is not None:
        # Clearing (None) only removes an inert line, so a pinned fact may lose it; tagging one
        # would change where an always-loaded rule is read.
        return "%s is pinned; a pinned fact stays where it is (only --clear may change it)" % slug
    if topics and _outside_list(topics, allowed):
        return "%s: %s not in the topic list" % (slug, ", ".join(_outside_list(topics, allowed)))
    if topics and any(ptr.legacy for _level, ptr in owners[slug][2].values()):
        # Ahead of the frontmatter check: a legacy body sits at its uuid path, so the slug path
        # reads as empty and that check would name the wrong cause.
        return _line_problem(slug, anchor, owners[slug][2])
    body = read_store_text(us.body_path(anchor, slug))
    if _frontmatter(body)[1] is None:
        return "%s: its body has no frontmatter to carry topics" % slug
    if topics:
        # Binding a fact hands its lines to the renderer, which builds them from the body alone.
        return _line_problem(slug, anchor, owners[slug][2])
    return None


def _line_size(ptr):
    """Bytes `ptr`'s line takes in a block, its line break counted."""
    return len(ptr.index_line().encode("utf-8")) + 1


def _copy_levels(anchor, wanted):
    """{slug: ([every level dir holding a line of it, top first], the line at the first)} for the
    slugs in `wanted`, from one walk over the tree's levels. Holds per slug its levels and one
    pointer."""
    found = {}
    order = sorted(((_level_parts(anchor, level), os.path.abspath(str(level)))
                    for level in curated_levels_under(anchor)),
                   key=lambda row: (len(row[0]), row[0]))
    for _parts, level in order:
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            if ptr.slug in wanted:
                found.setdefault(ptr.slug, ([], ptr))[0].append(level)
    return found


def _collapse_plan(anchor, rows, owners):
    """{slug: (holders, line)} for each fact `rows` un-binds (`[]` or None) that is bound now,
    pinned nowhere, and has a line at more than one level: those lines collapse to one at the tree
    top. A fact that was never bound keeps its lines: a duplicate pointer, which --check-tree
    reports. Raises CollapseTooLarge, before anything is written, when the lines the collapse adds
    at the top would take its block past MAX_RENDER_BLOCK_BYTES. Holds the holders of each such
    row (batch rows times copies)."""
    # A fact with a pinned or legacy line was never placed by topic (`_keeps_in_place`), so its
    # lines are where they were put, not copies a collapse may fold.
    unbound = {slug for slug in rows if not rows[slug] and not owners[slug][1]
               and not any(ptr.legacy for _level, ptr in owners[slug][2].values())}
    if not unbound:
        return {}
    plan = {slug: copy for slug, copy in _copy_levels(anchor, unbound).items()
            if len(copy[0]) > 1 and read_body_topics(us.body_path(anchor, slug))}
    added = sum(_line_size(line) for holders, line in plan.values()
                if _level_parts(anchor, holders[0]) != tp.TOP)
    if added:
        top = os.path.abspath(str(anchor))
        held = sum(_line_size(ptr) for ptr in
                   us.parse_pointer_index(read_store_text(sig.claude_local_md_path(top)))[1])
        if held + added > MAX_RENDER_BLOCK_BYTES:
            split = _top_split(anchor, top, unbound)
            raise CollapseTooLarge(top, split["kept"] + split["fixed"], added, split["stale"],
                                   split["placed"], fixed=split["fixed"],
                                   fit=_lines_that_fit(plan, anchor, MAX_RENDER_BLOCK_BYTES - held),
                                   rebind=split["rebind"])
    return plan


def _lines_that_fit(plan, anchor, room):
    """How many of the lines a collapse `plan` adds at the tree top fit in `room` bytes, smallest
    first: what one smaller call can un-bind now. Holds one size per row of the plan."""
    fit, total = 0, 0
    for size in sorted(_line_size(line) for holders, line in plan.values()
                       if _level_parts(anchor, holders[0]) != tp.TOP):
        total += size
        if total > room:
            break
        fit += 1
    return fit


def _top_split(anchor, top, unbound):
    """{'kept', 'fixed', 'placed', 'stale': bytes, 'rebind': bool} of the tree top's block, for a
    CollapseTooLarge message. A line of a fact in `unbound` whose body is still bound is 'fixed':
    this call keeps it at the top whatever a move does (the collapse would add it back), so it is
    never one to move. A fact in `unbound` that is un-bound already is not: the call leaves its
    line alone, a move of it stays moved, and counting it as fixed would name a smaller batch of
    facts that un-binds nothing. Of the rest a pinned, legacy or unplaced line is kept; a managed
    line is placed when its fact is placed at the top, else stale (a tree-scope render drops it).
    `rebind` says whether a level below the top has a topic a fact placed at the top could be
    rebound to. Read only when the call refuses: one record per level and one body head per line
    of the top's block (two for a line of a fact in `unbound` that is un-bound already)."""
    levels = curated_levels_under(anchor)
    level_map = topic_level_map(anchor, levels)[0]
    place = _Placer(level_map)
    split = _block_split(anchor, _unplaceable_slugs(levels), top,
                         lambda slug, topics: "placed" if tp.TOP in place(topics) else "stale",
                         claim=lambda slug: "fixed" if slug in unbound and read_body_topics(
                             us.body_path(anchor, slug)) else None)
    split["rebind"] = any(level_map.topics(parts) for parts in level_map.levels()
                          if parts != tp.TOP)
    return split


def _collapse_copies(anchor, slug, holders, line, write):
    """Leave ONE line of an un-bound fact: at the tree top, written before the others are dropped,
    so no moment has the fact without a line. `holders` are the levels holding one, top first, and
    `line` the one at the first of them."""
    scratch = {"levels": {}}
    if _level_parts(anchor, holders[0]) != tp.TOP:
        _add_lines(os.path.abspath(str(anchor)),
                   {slug: us.Pointer(slug=slug, title=line.title, hook=line.hook)},
                   scratch, False, write)
    for level in holders:
        if _level_parts(anchor, level) != tp.TOP:
            _drop_lines(level, {slug}, scratch, False, write)


def set_fact_topics(proj, rows, dry_run=False, write=None, *,
                    lock_timeout=PLACEMENT_LOCK_TIMEOUT_S):
    """Set the `topics:` line of each fact in `rows`, a {slug: topics} mapping where topics is a
    tuple of tags, an empty tuple (bound to no topic) or None (remove the line).

    Every row is checked before any is written: an invalid slug, a slug no level points at, a
    pinned fact being tagged (clearing one, None, is allowed), a tag outside the tree's list, a
    body without frontmatter, or a fact being bound to a topic that has a legacy `uuid:` pointer,
    whose body lacks `title:` or `description:`, or any of whose pointer lines differs from the
    line its body renders other than in whitespace (see `_line_problem`) refuses the WHOLE call
    with TopicRefusal (the first refusals and their total). Each body is then read and written
    under the lock of the first level that points at it, the lock an ordinary write to that fact
    holds; a dry run reads without it and creates no file (`_write_lock`). Pointer
    lines are placed by `render-topics`, with one exception: a fact this call un-binds that is
    bound now, pinned nowhere and has a line at several levels keeps ONE line, at the tree top
    (`_collapse_plan`; CollapseTooLarge refuses the whole call first when the top's block would
    pass its cap). That line is written first, then the others are dropped, then the body is
    un-bound: an interrupted call leaves a fact still bound, which a render places again and
    the same call, run again, collapses. `write(path, text)` is the port those level files are
    written through (default `uuid_store.write_if_changed`).
    A real call holds the tree's placement lock (`placement_lock`) from the row checks to the
    last body write, so no render runs between a collapse's line writes and its un-bind,
    and none between its own passes while a body changes; it waits up to `lock_timeout`
    seconds for it, then raises PlacementLockBusy. A dry run takes no lock.
    Returns {'set': [slugs], 'unchanged': n, 'collapsed': [slugs]}.
    Holds `rows`, one owner entry per row and, for a collapse, the levels holding each un-bound
    row's line; a batch over MAX_TOPIC_BATCH rows is refused."""
    if not dry_run:
        sig.refuse_if_memory_writes_off()
    if len(rows) > MAX_TOPIC_BATCH:
        raise TopicRefusal(["%d rows, over the limit of %d per call" % (len(rows), MAX_TOPIC_BATCH)])
    anchor = _anchor(proj)
    allowed = _topic_list(anchor)
    if dry_run:
        return _set_fact_topics_held(anchor, rows, allowed, True, write)
    with placement_lock(anchor, "set-topics", lock_timeout):
        return _set_fact_topics_held(anchor, rows, allowed, False, write)


def _set_fact_topics_held(anchor, rows, allowed, dry_run, write):
    """`set_fact_topics` from the row checks on; a real call's caller holds the placement lock."""
    owners = _pointer_owners(anchor, set(rows))
    problems, total = [], 0
    for slug in sorted(rows):
        why = _topic_row_problem(slug, rows[slug], anchor, allowed, owners)
        if why:
            total += 1
            if len(problems) < _REFUSALS_SHOWN:
                problems.append(why)
    if total:
        raise TopicRefusal(problems, total)
    plan = _collapse_plan(anchor, rows, owners)
    write = write or us.write_if_changed
    rep = {"set": [], "unchanged": 0, "collapsed": []}
    for slug in sorted(rows):
        _placement_heartbeat()
        if slug in plan:
            # Placed by topic at several levels and bound to none from now on: one line, at the
            # tree top. Before the body changes, so a call cut short leaves a bound fact, and
            # outside its lock: the pointer writers take their own.
            if not dry_run:
                _collapse_copies(anchor, slug, *plan[slug], write)
            rep["collapsed"].append(slug)
        with _write_lock(sig.claude_local_md_path(owners[slug][0]), dry_run):
            body = read_store_text(us.body_path(anchor, slug)).rstrip("\n")
            tagged = _with_topics(body, rows[slug])
            if tagged == body:
                rep["unchanged"] += 1
                continue
            if not dry_run:
                us.put_body(str(anchor), slug, tagged)
            rep["set"].append(slug)
    return rep


def set_level_topics(level, topics, top=False):
    """Set the `TOPICS:` line of `level`'s descriptor and record the descriptor it was chosen from.

    `top` says which verb is asking. The tree top's topics decide what every session of the tree
    loads, so they change only through `set-top-topics`, a verb of its own that a nap or dream is
    told never to run; `set-level-topics` refuses the top, and `set-top-topics` refuses any other
    level. Raises TopicRefusal before writing for that, for a tag outside the list, and for a
    level with no descriptor to tag. Returns True if the descriptor changed.

    The level is named LEXICALLY, as `resolve_anchor` names its anchor: a level reached through a
    symlink is the level its path names, keyed and judged top-or-not by that path. The topic file
    is checked (list present, level keyable) before the descriptor is written, and recorded right
    after it under both locks, so a refusal there writes neither; TopicStoreError is raised for it."""
    sig.refuse_if_memory_writes_off()
    level = os.path.abspath(str(level))
    anchor = _anchor(level)
    is_top = os.path.normcase(level) == os.path.normcase(os.path.abspath(str(anchor)))
    topic_store.level_key(anchor, level)              # a level it cannot key refuses before any write
    if is_top and not top:
        raise TopicRefusal(["%s is the tree top: its topics are the user's decision "
                            "(set-top-topics, on the user's word)" % level])
    if top and not is_top:
        raise TopicRefusal(["%s is not the tree top (%s); use set-level-topics" % (level, anchor)])
    topics = tp.normalise_topics(topics)
    bad = _outside_list(topics, _topic_list(anchor))
    if bad:
        raise TopicRefusal(["%s not in the topic list" % ", ".join(bad)])
    local = sig.claude_local_md_path(level)
    with sig.memory_lock(local):
        text = read_store_text(local)
        scope, pointers = us.parse_pointer_index(text)
        if not scope.strip():
            raise TopicRefusal(["%s has no descriptor yet (set-scope writes one)" % level])
        tagged = tp.with_descriptor_topics(scope, topics)
        written = []
        topic_store.record_level(
            anchor, level, tp.descriptor_digest(tagged),
            before=lambda: written.append(
                us.write_if_changed(local, us.upsert_pointer_block(text, tagged, pointers))))
    return written[0]


def level_topics_stale(level):
    """(stale, why) for one level: stale when its descriptor has no `TOPICS:` line, or says
    something other than the text its topics were chosen from. (False, "") when fresh, and when
    the tree has no topic list (nothing is tagged there at all)."""
    level = os.path.abspath(str(level))
    anchor = _anchor(level)
    data = topic_store.load(anchor)
    if data is None:
        return False, ""
    scope = us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[0]
    if not scope.strip():
        return True, "no descriptor"
    try:
        declared = tp.descriptor_topics(scope)
    except tp.InvalidTopic:
        return True, "its TOPICS line does not parse (set-level-topics replaces it)"
    if declared is None:
        return True, "never tagged"
    if data["levels"].get(topic_store.level_key(anchor, level)) != tp.descriptor_digest(scope):
        return True, "descriptor changed since its topics were chosen"
    return False, ""


def scope_keeping_topics(old_scope, new_scope, stored_in=None):
    """`new_scope` for a descriptor write, with the stored `TOPICS:` line carried over when the
    new text has none. The one gate every descriptor writer passes: set-scope, add's --scope (an
    ensure_level `scope_default`) and ensure_level's harvest of a legacy CLAUDE.md block.

    Raises TopicRefusal when the new text carries a DIFFERENT `TOPICS:` line:
    topics change only through set-level-topics / set-top-topics, so a rewritten descriptor can
    neither drop nor change them by accident; a never-tagged level gains no line this way either,
    not even an empty one. Raises TopicRefusal too when the stored line does not parse (carried
    over or dropped, the result would be a guess; set-level-topics replaces it), and InvalidTopic
    when the new text's line does not parse. `stored_in` names the CLAUDE.md whose legacy block
    holds `old_scope`: no verb rewrites that block, so the refusal names the file to fix by hand."""
    try:
        old = tp.descriptor_topics(old_scope)
    except tp.InvalidTopic as exc:
        if stored_in is not None:
            raise TopicRefusal(["the legacy scope block in %s has a TOPICS line that does not parse "
                                "(%s); fix or remove that line there by hand, then run this again"
                                % (stored_in, exc)]) from exc
        raise TopicRefusal(["the stored TOPICS line does not parse (%s); replace it with "
                            "set-level-topics (set-top-topics at the tree top) first" % exc]) from exc
    new = tp.descriptor_topics(new_scope)
    if new is not None and new != old:
        raise TopicRefusal(["a descriptor's TOPICS line changes only through set-level-topics "
                            "(set-top-topics at the tree top); leave the line out of the new text"])
    if old is None or new is not None:
        return new_scope
    return tp.with_descriptor_topics(new_scope, old)


def _current_scope(proj):
    """(descriptor, stored_in): `proj`'s descriptor as a descriptor writer must judge it - its
    pointer block's, else the legacy CLAUDE.md block ensure_level would harvest (read here, never
    moved) together with that CLAUDE.md's path, else ("", None) for a level that has none."""
    scope = us.parse_pointer_index(read_store_text(sig.claude_local_md_path(proj)))[0]
    if scope:
        return scope, None
    md = sig.claude_md_path(proj)
    legacy = sig.read_scope_block(read_store_text(md))
    return ("", None) if legacy is None else (legacy.strip(), md)


# ---- render: place the lines ---------------------------------------------------------------

_PLACEMENT_CACHE = 512


class _Placer:
    """`LevelMap.placements` remembered per topic set. Facts share few distinct sets, so the cache
    stays small; it is emptied when it reaches _PLACEMENT_CACHE entries rather than grown."""

    def __init__(self, level_map):
        self._map, self._seen = level_map, {}

    def __call__(self, topics):
        hit = self._seen.get(topics)
        if hit is None:
            if len(self._seen) >= _PLACEMENT_CACHE:
                self._seen.clear()
            hit = self._seen[topics] = frozenset(self._map.placements(topics))
        return hit

    def remembered(self):
        """How many topic sets are remembered: never more than _PLACEMENT_CACHE. A method, not
        __len__, so an empty placer never reads as false."""
        return len(self._seen)

    def bound_to(self, parts):
        """Which facts the lines at the level `parts` come from, for a RenderBlockTooLarge message:
        the topics that level has, and at the top also the topics no level has (they fall back
        there)."""
        topics = ", ".join(sorted(self._map.topics(parts)))
        if parts != tp.TOP:
            return "a topic this level has (%s)" % topics
        return "a topic no level below the top has" + (" or one the top has (%s)" % topics
                                                        if topics else "")


def _managed_topics(slug, head, pinned):
    """The topics a body head binds its fact to when the renderer manages it, else None: managed
    means a non-empty `topics:` line, a slug not in `pinned` (the slugs with a pinned or legacy
    line anywhere, `_unplaceable_slugs`, or () when the caller judges that apart), and a body a
    line can be built from."""
    topics = _body_topics(head)
    if not topics or slug in pinned or _line_from_head(slug, head) is None:
        return None
    return topics


def _add_levels(level_map):
    """The levels the ADD phase writes, in its order: the top, then every level that has a topic."""
    return [parts for parts in level_map.levels() if parts == tp.TOP or level_map.topics(parts)]


def _block_split(anchor, pinned, level_dir, part, claim=None):
    """{part name: bytes} of one level's block, each line counting its line break: a line whose
    slug `claim(slug)` names goes under that name whatever it is; else a pinned, legacy or
    unmanaged line is 'kept', a managed line goes under `part(slug, topics)`, and is not counted
    when that is None. One body head is read per unpinned line."""
    split = {"kept": 0, "stale": 0, "placed": 0, "fixed": 0}
    for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level_dir)))[1]:
        name = "kept" if claim is None else claim(ptr.slug) or "kept"
        if name == "kept" and not (ptr.pin or ptr.legacy):
            head = _read_body_head(us.body_path(anchor, ptr.slug))
            topics = None if head is None else _managed_topics(ptr.slug, head, pinned)
            if topics is not None:
                name = part(ptr.slug, topics)
        if name is not None:
            split[name] += _line_size(ptr)
    return split


def _held_bytes(anchor, pinned, level_dir, goes=None):
    """(kept, stale): bytes of the lines a level's block still holds once this render is done with
    it, beside the lines it places there. `kept` are pinned, legacy, and those of facts it does
    not place; `stale` are managed lines placed elsewhere that this render leaves there. In the
    tree scope (`goes` None) every managed line is left out, so `stale` is 0: one placed here is
    replaced by the body's own line, which is counted from the body; one placed elsewhere is
    dropped by this same run's REMOVE phase. The chain scope drops fewer, so it passes
    `goes(slug, topics)`, true for a managed line that leaves or is replaced: the others stay,
    count, and are `stale`, since only a tree-scope render drops them. The ADD phase writes a
    level before that drop, so its file holds those lines a while longer: no read or write of a
    level file is bounded, and the cap judges the block the render leaves."""
    split = _block_split(anchor, pinned, level_dir,
                         lambda slug, topics: None if goes is None or goes(slug, topics)
                         else "stale")
    return split["kept"], split["stale"]


def _census_lines(anchor, pinned, tally):
    """Yield (slug, topics, line) for every managed fact, one body head at a time, counting into
    `tally` how many are managed and the tagged unpinned ones no line can be built from (the first
    _RENDER_SHOWN and their total)."""
    for slug, head in _iter_body_heads(anchor):
        topics = _body_topics(head)
        if not topics or slug in pinned:
            continue
        line = _line_from_head(slug, head)
        if line is None:
            tally["incomplete_total"] += 1
            if len(tally["incomplete"]) < _RENDER_SHOWN:
                tally["incomplete"].append(slug)
            continue
        tally["managed"] += 1
        yield slug, topics, line


def _census_tally():
    """An empty census report, filled by `_census_lines`."""
    return {"managed": 0, "incomplete": [], "incomplete_total": 0}


def _render_census(anchor, pinned, place, dirs, adds):
    """One pass over the bodies, before anything is written: the `_census_lines` counts, and the
    bytes each level of `adds` will hold, starting from the lines it keeps (`_held_bytes`). Raises
    RenderBlockTooLarge when a level would pass MAX_RENDER_BLOCK_BYTES, so that refusal comes
    before ANY level is written, not after the levels ahead of it in the ADD order were. It raises
    after the pass, with that level's whole count: a count stopped at the first line past the cap
    would name too few bytes to move. Of several such levels it names the first in level order
    (the sorted parts: the top first, a parent before its children, siblings by name), never the
    one a line first pushed over, which depends on the order the store lists its bodies, so the
    same tree would name a different level on another filesystem. Holds one byte count per level."""
    tally = _census_tally()
    kept = {parts: _held_bytes(anchor, pinned, dirs[parts])[0] for parts in adds}
    now = {parts: _block_bytes(dirs[parts]) for parts in adds}
    sizes = dict(kept)
    for _slug, topics, line in _census_lines(anchor, pinned, tally):
        for parts in place(topics):     # a placement is always the top or a level with a topic
            sizes[parts] += len(line.index_line().encode("utf-8")) + 1
    full = min((parts for parts in sizes if _grows_past_cap(now[parts], sizes[parts])),
               default=None)
    if full is not None:
        raise RenderBlockTooLarge(dirs[full], kept[full], sizes[full] - kept[full],
                                  place.bound_to(full), now=now[full])
    tally["incomplete"].sort()
    return tally


def _wanted_lines(anchor, place, pinned, parts, level_dir, held=(0, 0), skip=frozenset(),
                  now=0):
    """{slug: Pointer} for every managed fact placed at the level `parts` and not in `skip` (the
    chain scope's slugs a level above holds), from one streaming pass over the bodies. This dict
    is what a render holds; once its lines and the `held` (kept, stale) bytes the level keeps
    beside them pass both MAX_RENDER_BLOCK_BYTES and the `now` bytes the level's block holds
    before this pass (`_grows_past_cap`) it raises RenderBlockTooLarge. The census refused that
    case already; this check holds the bound when a body or the level's block grew between the
    census and this pass (another writer). Past that bound it stops holding lines and only
    counts, so the refusal names the whole overflow."""
    wanted, size = {}, sum(held)
    for slug, head in _iter_body_heads(anchor):
        topics = _managed_topics(slug, head, pinned)
        if topics is None or slug in skip or parts not in place(topics):
            continue
        line = _line_from_head(slug, head)
        size += len(line.index_line().encode("utf-8")) + 1
        if _grows_past_cap(now, size):
            wanted = None
        elif wanted is not None:
            wanted[slug] = line
    if wanted is None:
        raise RenderBlockTooLarge(level_dir, held[0], size - sum(held), place.bound_to(parts),
                                  stale=held[1], anchor=anchor, now=now)
    return wanted


def _note(rep, level_dir, kind, slugs):
    """Count `slugs` under `kind` for `level_dir` in the report, keeping the first few as examples."""
    if not slugs:
        return
    row = rep["levels"].setdefault(level_dir, {"added": 0, "refreshed": 0, "removed": 0, "examples": {}})
    row[kind] = row.get(kind, 0) + len(slugs)        # `kept` is counted only where it happened
    shown = row["examples"].setdefault(kind, [])
    shown.extend(sorted(slugs)[:_RENDER_SHOWN - len(shown)])


def _write_lock(local, dry_run):
    """The lock a read-modify-write of the level file `local` takes, or none for a dry run.

    A dry run writes nothing, so it must not create a file either: a lock is a `.lock` file made
    and removed beside the level file, which fails on a read-only tree, waits out (and then fails
    on) a peer's lock, may reclaim a stale one, and changes the directory's mtime - a check run
    over the store would do all of that. Unlocked, a read sees one whole text: the store's writer
    (`write_if_changed`) renames a finished temp file over the level file, so the old text or the
    new one is read, never a part. What a dry run cannot get is a tree-wide snapshot: a writer may
    change one level between the reads of two, which the locks never prevented either (each is
    held for its own level only)."""
    return contextlib.nullcontext() if dry_run else sig.memory_lock(local)


def _add_lines(level_dir, wanted, rep, dry_run, write):
    """Add the missing lines of `wanted` to one level and refresh an unpinned line that says
    something else than its body, under the level's lock (none for a dry run, `_write_lock`).
    Returns the slugs the level now holds."""
    local = sig.claude_local_md_path(level_dir)
    with _write_lock(local, dry_run):
        text = read_store_text(local)
        scope, pointers = us.parse_pointer_index(text)
        held = {p.slug: p for p in pointers}
        added, refreshed = [], []
        for slug in sorted(wanted):
            line, have = wanted[slug], held.get(slug)
            if have is None:
                pointers.append(line)
                added.append(slug)
            elif not have.pin and not have.legacy and have.index_line() != line.index_line():
                have.title, have.hook = line.title, line.hook
                refreshed.append(slug)
        if (added or refreshed) and not dry_run:
            write(local, us.upsert_pointer_block(text, scope, pointers))
    _note(rep, level_dir, "added", added)
    _note(rep, level_dir, "refreshed", refreshed)
    return set(held) | set(added)


def _drop_lines(level_dir, doomed, rep, dry_run, write):
    """Drop the unpinned lines of `doomed` from one level, under its lock (none for a dry run)."""
    if not doomed:
        return
    local = sig.claude_local_md_path(level_dir)
    with _write_lock(local, dry_run):
        text = read_store_text(local)
        scope, pointers = us.parse_pointer_index(text)
        kept = [p for p in pointers if p.slug not in doomed or p.pin or p.legacy]
        removed = [p.slug for p in pointers if p.slug in doomed and not (p.pin or p.legacy)]
        if removed and not dry_run:
            write(local, us.upsert_pointer_block(text, scope, kept))
    _note(rep, level_dir, "removed", removed)


def _misplaced_lines(anchor, place, pinned, parts, level_dir):
    """{slug: the levels (parts) its fact is placed at} for the managed lines at one level that are
    placed elsewhere: one body head is read per line of the level's block."""
    doomed = {}
    for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level_dir)))[1]:
        if ptr.pin or ptr.legacy:
            continue
        head = _read_body_head(us.body_path(anchor, ptr.slug))
        topics = None if head is None else _managed_topics(ptr.slug, head, pinned)
        if topics is not None and parts not in place(topics):
            doomed[ptr.slug] = place(topics)
    return doomed


_HOME_BLOCKS = 8
"""Most level blocks `_keep_last_lines` keeps read at once; emptied, not grown, when it fills."""


def _keep_last_lines(dirs, doomed, dry_run):
    """(drop, kept) from `doomed` ({slug: the levels it is placed at}): a line is dropped only
    when a level its fact is placed at holds a line of it NOW, read from disk; else it is kept,
    since dropping it could leave the fact with no line anywhere. The ADD pass put a line at every
    such level, so under the placement lock nothing is kept; a body rebound by a writer that
    ignores the lock (a hand edit) between the passes is what this catches. A dry run wrote no
    line to read back and drops what it would drop. Holds the slugs of at most _HOME_BLOCKS
    levels' blocks."""
    if dry_run:
        return set(doomed), set()
    blocks, kept = {}, set()

    def held(level):
        if level not in blocks:
            if len(blocks) >= _HOME_BLOCKS:
                blocks.clear()
            blocks[level] = _block_slugs(level)
        return blocks[level]

    for slug, placed_at in doomed.items():
        if not any(slug in held(dirs[parts]) for parts in placed_at if parts in dirs):
            kept.add(slug)
    return set(doomed) - kept, kept


def _render_tree(anchor, levels, adds, place, dirs, pinned, rep, dry_run, write):
    """Tree scope. ADD over `adds` (every level that has a topic, plus the anchor); then, only when
    every add went through, REMOVE over every curated level. An error in the ADD phase is raised
    before a single line is dropped, so an interrupted run leaves a surplus copy, never a fact with
    no line; nor does REMOVE drop a line whose fact has none where it is placed
    (`_keep_last_lines`)."""
    for parts in adds:
        _placement_heartbeat()
        held = _held_bytes(anchor, pinned, dirs[parts])
        _add_lines(dirs[parts], _wanted_lines(anchor, place, pinned, parts, dirs[parts], held,
                                              now=_block_bytes(dirs[parts])), rep,
                   dry_run, write)
    for level in levels:
        _placement_heartbeat()
        parts = _level_parts(anchor, level)
        level = os.path.abspath(str(level))
        drop, kept = _keep_last_lines(dirs, _misplaced_lines(anchor, place, pinned, parts, level),
                                      dry_run)
        _note(rep, level, "kept", kept)
        _drop_lines(level, drop, rep, dry_run, write)


def _chain_levels(anchor, proj, levels):
    """The curated levels from the tree top down to `proj`, as (parts, level dir), top first.
    Found lexically, as levels are keyed: a level reached through a symlink is the level its path
    names. `proj` need not be a level itself."""
    here = _level_parts(anchor, proj)
    by_parts = {_level_parts(anchor, level): os.path.abspath(str(level)) for level in levels}
    return [(here[:cut], by_parts[here[:cut]]) for cut in range(len(here) + 1)
            if here[:cut] in by_parts]


def _block_slugs(level_dir):
    """The slugs of every pointer line in one level's block."""
    return {p.slug for p in
            us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level_dir)))[1]}


def _chain_target(slug, placed, chain, adds, held_at):
    """The index of the chain level a chain render gives `slug`'s line, or None: the first level,
    top down, of `adds` the fact is `placed` at, unless a level above it holds a line of the fact
    already (`held_at`, the slugs of each chain level's block), which this chain reads."""
    for i, (parts, _level) in enumerate(chain):
        if parts in adds and parts in placed:
            return i
        if slug in held_at[i]:
            return None
    return None


def _chain_goes(place, parts, above):
    """The `_held_bytes` test at the chain level `parts`: a managed line leaves the block when a
    level above holds its slug (the DROP pass removes it) and is replaced when its fact is placed
    there (the body's own line is counted). Any other managed line stays: a chain render never
    drops a line for being placed elsewhere."""
    return lambda slug, topics: slug in above or parts in place(topics)


def _chain_census(anchor, pinned, place, chain, adds):
    """The chain scope's census, one pass over the bodies before anything is written: the
    `_census_lines` counts and, for each chain level of `adds`, the block it will hold, the lines
    it keeps (`_held_bytes` with `_chain_goes`) plus the lines added or refreshed there. Raises
    RenderBlockTooLarge for the first such level, top down, past MAX_RENDER_BLOCK_BYTES, with its
    whole count, so the refusal comes before any level is written. Holds the slugs of the chain's
    blocks and, per chain level, the slugs added there while its count is within the cap (past it
    the census refuses, so no level below needs them)."""
    tally = _census_tally()
    held_at = [_block_slugs(level) for _parts, level in chain]
    now = [_block_bytes(level) for _parts, level in chain]
    sizes, added = [0] * len(chain), [set() for _level in chain]
    for slug, topics, line in _census_lines(anchor, pinned, tally):
        i = _chain_target(slug, place(topics), chain, adds, held_at)
        if i is not None:
            sizes[i] += len(line.index_line().encode("utf-8")) + 1
            if sizes[i] <= max(MAX_RENDER_BLOCK_BYTES, now[i]):
                added[i].add(slug)
    above = set()
    for i, (parts, level) in enumerate(chain):
        if parts in adds:
            kept, stale = _held_bytes(anchor, pinned, level, _chain_goes(place, parts, above))
            if _grows_past_cap(now[i], kept + stale + sizes[i]):
                raise RenderBlockTooLarge(level, kept, sizes[i], place.bound_to(parts),
                                          stale=stale, anchor=anchor, now=now[i])
        above |= held_at[i] | added[i]
    tally["incomplete"].sort()
    return tally


def _held_above(anchor, pinned, level_dir, above):
    """The slugs of the managed lines at one level whose slug a level above it on the chain holds
    (`above`): one body head is read per such line. A pinned, legacy or unmanaged line is never
    among them."""
    doomed = set()
    for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level_dir)))[1]:
        if ptr.slug not in above or ptr.pin or ptr.legacy:
            continue
        head = _read_body_head(us.body_path(anchor, ptr.slug))
        if head is not None and _managed_topics(ptr.slug, head, pinned) is not None:
            doomed.add(ptr.slug)
    return doomed


def _render_chain(anchor, chain, adds, place, pinned, rep, dry_run, write):
    """Chain scope: only the levels of `chain` are read for their lines or written. ADD, top
    first: a level of `adds` gets the lines placed at it unless a level above holds the slug.
    Then, only when every add went through, DROP: a managed line a level above holds goes. A line
    is never dropped for being placed elsewhere: another subtree may still read it, and the tree
    scope sweeps. The slugs each level holds after its add are kept for the DROP pass, so a dry
    run reports the drops a real run makes. Holds the slugs of the chain's blocks."""
    above, holds = set(), []
    for parts, level in chain:
        _placement_heartbeat()
        wanted = {}
        if parts in adds:
            held = _held_bytes(anchor, pinned, level, _chain_goes(place, parts, above))
            wanted = _wanted_lines(anchor, place, pinned, parts, level, held, skip=above,
                                   now=_block_bytes(level))
        now = _add_lines(level, wanted, rep, dry_run, write)
        holds.append(now)
        above |= now
    above = set()
    for (_parts, level), now in zip(chain, holds, strict=True):
        _placement_heartbeat()
        _drop_lines(level, _held_above(anchor, pinned, level, above), rep, dry_run, write)
        above |= now


def render_topics(proj, scope="tree", dry_run=False, write=None, *,
                  lock_timeout=PLACEMENT_LOCK_TIMEOUT_S):
    """Place the pointer lines of every MANAGED fact of `proj`'s tree by topic.

    A fact is managed when its body's `topics:` is non-empty, no pointer of it is pinned or
    legacy (`uuid:`) at any level, and its body holds the `title:` and `description:` a line is
    built from. Every other line is never
    added, dropped or rewritten here. `scope` is 'tree' (every level; adds, then removes) or
    'chain' (only the levels from `proj` up to the tree top: a line a level above holds is not
    added below it and is dropped there, and a line merely placed elsewhere stays, for the tree
    scope to sweep; no file off the chain is written). `write(path, text)` is the port a
    level file is written through (default `uuid_store.write_if_changed`); a test passes a
    recording one. A dry run takes no lock and creates no file (`_write_lock`), so it runs on a
    read-only tree and beside a peer's held lock. Returns a report: {'list': False} alone when the tree has no topic list (then
    nothing is read further and nothing written), else scope, dry_run, managed, incomplete,
    incomplete_total and, per changed level dir, the counts added / refreshed / removed with a
    few example slugs.

    Checked before the first write: a level whose TOPICS line does not parse and a tree top with
    no pointer block raise TopicRefusal, and a level whose block - the lines placed there plus the
    lines that stay there, never a line this run drops - would pass MAX_RENDER_BLOCK_BYTES raises
    RenderBlockTooLarge, naming the route for whichever part is larger (a body or block
    that grew between the census and the ADD pass can still raise it there, after earlier levels
    were added and before any line is dropped).
    A real run holds the tree's placement lock (`placement_lock`) from the level walk to its last
    drop, so no set-topics or write to a placed fact lands between its passes; it waits up to
    `lock_timeout` seconds for it, then raises PlacementLockBusy. The tree scope's REMOVE never
    drops the last line of a fact: a misplaced line whose fact has no line at any level it is
    placed at is kept and counted as `kept` (`_keep_last_lines`).
    Holds: one record per level, one per pinned pointer, the lines of the ONE level being written;
    a chain render also the slugs of the chain's blocks."""
    if scope not in ("tree", "chain"):
        raise ValueError("scope must be 'tree' or 'chain', not %r" % (scope,))
    if not dry_run:
        sig.refuse_if_memory_writes_off()
    proj = os.path.abspath(str(proj))
    anchor = _anchor(proj)
    if topic_store.load(anchor) is None:
        return {"list": False}
    if dry_run:
        return _render_held(anchor, proj, scope, True, write)
    with placement_lock(anchor, "render-topics", lock_timeout):
        return _render_held(anchor, proj, scope, False, write)


def _render_held(anchor, proj, scope, dry_run, write):
    """`render_topics` from the level walk on; a real run's caller holds the placement lock."""
    levels = curated_levels_under(anchor)
    level_map, dirs = topic_level_map(anchor, levels)
    if not any(_level_parts(anchor, level) == tp.TOP for level in levels):
        raise TopicRefusal(["the tree top %s has no pointer block for the lines that fall back to "
                            "it (ensure-memory-structure writes one)" % anchor])
    pinned = _unplaceable_slugs(levels)     # pinned or legacy anywhere: never placed
    place, adds = _Placer(level_map), _add_levels(level_map)
    rep = {"list": True, "scope": scope, "dry_run": bool(dry_run), "levels": {}}
    write = write or us.write_if_changed
    if scope == "tree":
        rep.update(_render_census(anchor, pinned, place, dirs, adds))
        _render_tree(anchor, levels, adds, place, dirs, pinned, rep, dry_run, write)
    else:
        chain, add_set = _chain_levels(anchor, proj, levels), frozenset(adds)
        rep.update(_chain_census(anchor, pinned, place, chain, add_set))
        _render_chain(anchor, chain, add_set, place, pinned, rep, dry_run, write)
    return rep


def _print_render(rep, as_json):
    """Print a render report; the verb's whole output."""
    if as_json:
        print(json.dumps(rep, sort_keys=True))
        return
    if not rep["list"]:
        print("no topic list in this tree: nothing is placed by topic")
        return
    verb = "would change" if rep["dry_run"] else "changed"
    for level in sorted(rep["levels"]):
        row = rep["levels"][level]
        print("  %s: +%d added, %d refreshed, -%d removed" % (level, row["added"], row["refreshed"],
                                                               row["removed"]))
    kept = [(level, row) for level, row in sorted(rep["levels"].items()) if row.get("kept")]
    if kept:
        print("~ warning: kept %d line(s) placed elsewhere, because no level the fact is placed at "
              "holds a line of it (its body changed during the render): %s. Run render-topics "
              "--scope tree again to place them"
              % (sum(row["kept"] for _level, row in kept),
                 ", ".join(sorted({slug for _level, row in kept
                                   for slug in row["examples"]["kept"]}))))
    if rep["incomplete_total"]:
        print("~ %d tagged fact(s) have a body without title: or description: and stay where they "
              "are: %s%s" % (rep["incomplete_total"], ", ".join(rep["incomplete"]),
                             " ..." if rep["incomplete_total"] > len(rep["incomplete"]) else ""))
    print("render-topics (%s): %d managed fact(s); %s %d level(s)"
          % (rep["scope"], rep["managed"], verb, len(rep["levels"])))


def _read_topic_batch(path):
    """({slug: topics}, error_message) from a JSONL batch file: one `{"slug": ..., "topics": [...]}`
    object per line, `[]` for bound to no topic, `null` to remove the line.

    Read one line at a time and never past the first problem, so what it holds is the rows taken
    so far (at most MAX_TOPIC_BATCH) and one line of at most MAX_TOPIC_BATCH_LINE_BYTES, whatever
    the file's size. Each of these is an error naming the line: a line over that byte cap (its
    line break counted), a row past MAX_TOPIC_BATCH, a slug a row before already named, bytes
    that are not UTF-8 (a leading BOM is dropped), and a line that is no such object."""
    try:
        fh = open(path, "rb")
    except OSError as exc:
        return None, "! error: cannot read %s (%s)" % (path, exc.strerror or exc)
    rows, first_on = {}, {}
    with fh:
        n = 0
        while True:
            n += 1
            try:
                raw_line = fh.readline(MAX_TOPIC_BATCH_LINE_BYTES + 1)
            except OSError as exc:
                return None, "! error: cannot read %s (%s)" % (path, exc.strerror or exc)
            if not raw_line:
                return rows, None
            if len(raw_line) > MAX_TOPIC_BATCH_LINE_BYTES:
                return None, "! error: %s line %d is longer than %d bytes" % (
                    path, n, MAX_TOPIC_BATCH_LINE_BYTES)
            if n == 1 and raw_line.startswith(b"\xef\xbb\xbf"):
                raw_line = raw_line[3:]
            try:
                line = raw_line.decode("utf-8")
            except UnicodeDecodeError as exc:
                return None, "! error: %s line %d is not UTF-8 (byte at offset %d) - re-save it " \
                             "as UTF-8" % (path, n, exc.start)
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                slug, raw = obj["slug"], obj["topics"]
                if not isinstance(slug, str) or not (raw is None or isinstance(raw, list)):
                    raise TypeError("'slug' must be a string and 'topics' a list or null")
                topics = None if raw is None else tp.normalise_topics(raw)
            except (ValueError, KeyError, TypeError, RecursionError) as exc:
                return None, "! error: %s line %d: %s" % (path, n, exc)
            if slug in rows:
                return None, "! error: %s line %d: slug %r is named twice (first on line %d)" % (
                    path, n, slug, first_on[slug])
            if len(rows) >= MAX_TOPIC_BATCH:
                return None, "! error: %s holds more than %d rows" % (path, MAX_TOPIC_BATCH)
            rows[slug], first_on[slug] = topics, n


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
    sig.refuse_if_memory_writes_off()
    roots = [str(r) for r in (roots or sig.discovery_roots())]
    groups = sig.tree_groups(sig.find_claude_md_dirs(roots))
    tops = list(groups)
    report = {"roots": roots, "trees": []}
    for top, members in sorted(groups.items(), key=lambda kv: str(kv[0])):
        store = Path(top) / sig.MEMORY_DIRNAME
        entry = {"top": str(top), "store_exists": store.is_dir(),
                 "members": [str(m) for m in members], "status": "ok", "created": [], "refused": []}
        if not store.is_dir():
            beneath = [str(o) for o in tops if o != top and top in o.parents]
            if beneath:
                entry["status"] = "ambiguous"
                entry["why"] = ("stray top CLAUDE.md above %d store-bearing tree(s) (%s); "
                                "scaffolding would merge them" % (len(beneath), ", ".join(sorted(beneath))))
        if entry["status"] == "ok" and apply:
            for m in members:
                entry["created"] += [str(c) for c in scaffold(str(m), refused=entry["refused"])]
        report["trees"].append(entry)
    return report



def _read_input_file(path):
    """(text, error_message) for a file named on the command line (--hook-file, --body-file, ...).

    Decoded as `utf-8-sig`: a BOM is what a Windows editor leaves, and kept it would ride into the
    always-loaded pointer line as an invisible first character that `strip()` does not remove.
    Bytes that are not UTF-8 are an error naming the file, like an unreadable one - they used to
    escape as a UnicodeDecodeError traceback. The CLI prints the message on stderr and exits 2: an
    input it could not read means the call could not run, which is not the engine saying no."""
    try:
        return Path(path).read_text(encoding="utf-8-sig"), None
    except UnicodeDecodeError as exc:
        return None, "! error: %s is not UTF-8 (byte at offset %d) - re-save it as UTF-8" % (
            path, exc.start)
    except OSError as exc:
        return None, "! error: cannot read %s (%s)" % (path, exc.strerror or exc)


def _text_from_flag_or_file(inline, path, inline_flag, file_flag):
    """Resolve a text argument given inline or as a file path -> (text, error_message).

    The file variant exists because a hook (up to 500 chars) and a scope descriptor (multi-line)
    are too long to type inline comfortably, and the shell workaround - `--hook "$(cat f)"` - is a
    command substitution the shell EXECUTES, which the plugin's own guard denies. The file wins when
    both are given, matching --body/--body-file. Passing neither is a usage error (exit 2).
    """
    if path:
        return _read_input_file(path)
    if inline is None:
        return None, "! error: pass %s or %s" % (inline_flag, file_flag)
    return inline, None


def _input_error(message):
    """Print an input/usage error from `_text_from_flag_or_file` / `_read_input_file`; exit 2."""
    print(message, file=sys.stderr)
    return 2


def _refused(reason):
    """Print an engine refusal; exit 2. A refusal is the WHOLE action declined (nothing written),
    so it is "could not run" in the plugin-wide 0/1/2 scheme, never the "no" of a check. The
    `! refused:` text stays on stdout so a caller capturing the result still reads the reason."""
    print("! refused: %s" % reason)
    return 2


# A USER ruling on the escalation ladder, as bodies record it: "**Escalation decided 2026-08-23
# (USER): no guard and no jig - ...". Requires the phrase and the (USER) attribution on one line,
# so a body that merely discusses escalating, or records an agent's own call, still escalates.
_USER_ESCALATION_RX = re.compile(r"(?im)^[^\n]*\bescalation\s+decided\b[^\n]*\(user\)")


def _user_decided_escalation(body):
    """True when `body` records the USER's decision on the guard/jig ladder (see the regex)."""
    return bool(_USER_ESCALATION_RX.search(body or ""))


def _topic_read(args):
    """The two topic check verbs: `topics-show` (exit 1: no list) and `topics-stale` (exit 1: the
    level is stale). A topic file that cannot be used is raised to the caller as TopicStoreError."""
    if args.cmd == "topics-stale":
        stale, why = level_topics_stale(args.proj)
        print("stale: %s" % why if stale else "fresh")
        return 1 if stale else 0
    data = topic_store.load(_anchor(args.proj))
    if data is None:
        print("no topic list in this tree")
        return 1
    if args.as_json:
        print(json.dumps({"tagger": data["tagger"], "topics": data["topics"]}, sort_keys=True))
        return 0
    print("tagger: %s" % data["tagger"])
    for name in sorted(data["topics"]):
        print("%s - %s" % (name, data["topics"][name]))
    return 0


TOPIC_WRITE_VERBS = frozenset({"topics-set-list", "set-topics", "set-level-topics", "set-top-topics",
                               "render-topics"})


def _is_topic_dry_run(raw):
    """True when argv `raw` is a topic verb's `--dry-run`: it writes nothing, so it runs while
    memory writes are off. Only `set-topics` and `render-topics` have the flag (argparse refuses
    it on the others), and both refuse a real write under the switch whatever this says."""
    return raw[0] in TOPIC_WRITE_VERBS and "--dry-run" in raw[1:]


def _topics_arg(value):
    """(topics, error_message) for a `--topics` value: a value that is no topic list is a usage
    error (exit 2, `! error` on stderr) like any other bad argument, not the engine declining."""
    try:
        return tp.parse_topics(value), None
    except tp.InvalidTopic as exc:
        return None, "! error: --topics %r: %s" % (value, exc)


def _topic_write(args):
    """The topic write verbs; refusals are raised and mapped by the caller."""
    if args.cmd == "render-topics":
        _print_render(render_topics(args.proj, scope=args.scope, dry_run=args.dry_run), args.as_json)
        return 0
    if args.cmd == "topics-set-list":
        text, err = _read_input_file(args.from_file)
        if err:
            return _input_error(err)
        try:
            spec = json.loads(text)
            topics, tagger = spec["topics"], spec["tagger"]
            if not isinstance(topics, dict):
                raise TypeError("'topics' must be an object of tag: meaning")
        except (ValueError, KeyError, TypeError) as exc:
            return _input_error("! error: %s: %s" % (args.from_file, exc))
        changed = set_topic_list(args.proj, topics, tagger)
        print("topic list %s: %d topic(s), tagger %s"
              % ("updated" if changed else "unchanged", len(topics), tagger))
        return 0
    if args.cmd == "set-topics":
        if args.batch:
            rows, err = _read_topic_batch(args.batch)
            if err:
                return _input_error(err)
        else:
            given = [args.topics is not None, args.universal, args.clear]
            if not args.slug or sum(given) != 1:
                return _input_error("! error: pass --batch, or --slug with exactly one of "
                                    "--topics, --universal, --clear")
            topics = None
            if not args.clear:
                topics, err = _topics_arg("" if args.universal else args.topics)
                if err:
                    return _input_error(err)
            rows = {args.slug: topics}
        rep = set_fact_topics(args.proj, rows, dry_run=args.dry_run)
        print("%s topics on %d fact(s); %d unchanged"
              % ("would set" if args.dry_run else "set", len(rep["set"]), rep["unchanged"]))
        if rep["collapsed"]:
            shown = rep["collapsed"][:_REFUSALS_SHOWN]
            print("~ note: %d un-bound fact(s) had a line at several levels; each %s one line, at "
                  "the tree top: %s%s" % (len(rep["collapsed"]),
                                          "would keep" if args.dry_run else "now has",
                                          ", ".join(shown),
                                          " ..." if len(rep["collapsed"]) > len(shown) else ""))
        return 0
    topics, err = _topics_arg(args.topics)
    if err:
        return _input_error(err)
    changed = set_level_topics(args.proj, topics, top=args.cmd == "set-top-topics")
    print("topics %s: %s" % ("updated" if changed else "unchanged", args.proj))
    return 0


# ---- CLI: the capture procedure invokes this (never hand-writes memory files) ------------------

def main(argv=None):
    """The CLI. Exit codes (the plugin-wide 0/1/2 scheme):

    0  done (a write verb wrote, or found nothing to change; a report verb ran);
    1  `lint --tree` found something (over-cap hook, trigger-less hook, unlabelled body, invalid
       pointer), `topics-show` found no list, or `topics-stale` found the level stale - the
       verbs that are a check, so their findings are a "no";
    2  could not run: a usage error, an input file it could not read or decode, a store it could
       not read, a level lock held past its timeout, a failed write, `heal` leaving a level it
       could not read, or a refusal - `! refused: <why>` on stdout - where the engine declined
       the whole action (slug collision, hook over the hard cap, empty body on a new fact, pinned
       target, unknown or invalid slug, excluded altitude, a refused move/relocate/rename/retitle,
       any WRITE_VERBS verb under BITRANOX_MEMORY_WRITES=off, a refused topic write). Nothing
       is written on a refusal.

    TreeWalkError and OSError (TimeoutError from the lock is one) are mapped HERE, once, rather
    than at each verb: they can surface from any read or write of the store, and a verb that
    forgot to catch one let a traceback exit 1 - which reads as a "no" rather than as a call that
    could not run."""
    try:
        return _main(argv)
    except TreeWalkError as exc:
        print("! error: cannot read the memory store - %s" % exc, file=sys.stderr)
        return 2
    except (ExcludedLevel, TopicRefusal) as exc:
        # TopicRefusal: ensure_level's descriptor gate, reachable from any verb that scaffolds a
        # level; it raises before writing, so it is a refusal wherever it surfaces
        return _refused(exc)
    except OSError as exc:
        # TimeoutError (lock contention) is an OSError subclass whose strerror is None
        detail = exc if exc.strerror is None else "%s: %s" % (exc.strerror, exc.filename or "")
        print("! error: %s" % detail, file=sys.stderr)
        return 2


def _main(argv=None):
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
    a.add_argument("--skill", default=None,
                   help="the skill this fact is tied to (e.g. bitranox:compuse-git), recorded as "
                        "metadata: skill: in the body - for a fact written beside a fix queued "
                        "against that skill (meta-self-improve step 2); kept on an update that "
                        "omits it, and given alone it tags the stored body")
    ap_ = sub.add_parser("amend-pinned",
                         help="deliberately change a pinned fact (human use only; "
                              "no autonomous pass invokes this)")
    ap_.add_argument("--proj", required=True)
    ap_.add_argument("--slug", required=True)
    ap_.add_argument("--title", default=None,
                     help="the new title - the only route to a PINNED fact's title, since retitle "
                          "refuses one by design; omit it to keep the stored title")
    ap_.add_argument("--hook", default=None)
    ap_.add_argument("--hook-file", default=None,
                     help="read the hook from a file - same reason as on add: a 500-char hook via "
                          "--hook \"$(cat f)\" is a shell command substitution the guard denies")
    ap_.add_argument("--body-file", default=None)
    ap_.add_argument("--type", dest="type_", default=None,
                     choices=[None, "feedback", "project", "reference", "user"],
                     help="re-classify the fact (feedback/project/reference/user) - the only route "
                          "to a PINNED fact's kind, since add refuses a pinned entry; given alone "
                          "it re-types the stored body; omit it to keep the stored kind")
    h = sub.add_parser("heal", help="self-heal missing/malformed pointer blocks/markers across the chain")
    h.add_argument("--proj", required=True, help="project cwd (heals its whole altitude chain)")
    h.add_argument("--backfill-titles", action="store_true", dest="backfill_titles",
                   help="instead of healing the chain, copy each pointer's title into its body's "
                        "frontmatter where the body has none, across the WHOLE tree (a one-off for "
                        "stores written before titles were kept as data; reads every body)")
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

    rt = sub.add_parser("retitle",
                        help="change one fact's TITLE in place - the pointer's link text - leaving "
                             "its slug, hook and body untouched")
    rt.add_argument("--level", required=True,
                    help="the level whose pointer block carries the fact")
    rt.add_argument("--slug", required=True, help="the fact to retitle")
    rt.add_argument("--to-title", required=True, dest="to_title",
                    help="the new title (whitespace collapsed to one line)")
    tl = sub.add_parser("topics-show", help="print the tree's closed topic list (exit 1: none yet)")
    tl.add_argument("--proj", required=True)
    tl.add_argument("--json", action="store_true", dest="as_json")
    ts = sub.add_parser("topics-set-list", help="replace the tree's closed topic list")
    ts.add_argument("--proj", required=True)
    ts.add_argument("--from-file", required=True, dest="from_file",
                    help='a JSON file: {"tagger": "jev" or "opus", "topics": {"<tag>": "<one-line meaning>"}}')
    st = sub.add_parser("set-topics", help="set the topics a fact is bound to (its body's topics: line)")
    st.add_argument("--proj", required=True, help="any dir of the tree")
    st.add_argument("--slug", default=None)
    st.add_argument("--topics", default=None, help="comma-separated tags from the tree's list")
    st.add_argument("--universal", action="store_true", help="bound to no topic (topics: [])")
    st.add_argument("--clear", action="store_true", help="remove the topics: line (never tagged)")
    st.add_argument("--batch", default=None,
                    help='a JSONL file, one {"slug": ..., "topics": [...]} per line ([] universal, null clear)')
    st.add_argument("--dry-run", action="store_true", dest="dry_run")
    for verb, text in (("set-level-topics", "set a level's TOPICS: line (refused at the tree top)"),
                       ("set-top-topics", "set the tree top's TOPICS: line - the user's decision only")):
        lt = sub.add_parser(verb, help=text)
        lt.add_argument("--proj", required=True, help="the level dir")
        lt.add_argument("--topics", required=True, help="comma-separated tags; '' for none")
    rd = sub.add_parser("render-topics",
                        help="place the pointer lines of topic-bound facts: at each level that has "
                             "one of a fact's topics while no level above it does")
    rd.add_argument("--proj", required=True,
                    help="any dir of the tree (tree) / the dir whose chain is rendered (chain)")
    rd.add_argument("--scope", required=True, choices=["tree", "chain"],
                    help="tree: every level, adds then removes (the dream); chain: only the levels "
                         "from --proj up to the tree top (the nap)")
    rd.add_argument("--dry-run", action="store_true", dest="dry_run")
    rd.add_argument("--json", action="store_true", dest="as_json")
    sl = sub.add_parser("topics-stale", help="exit 1 when a level's topics need choosing again")
    sl.add_argument("--proj", required=True, help="the level dir")
    raw = sys.argv[1:] if argv is None else argv
    if raw and raw[0] in WRITE_VERBS and sig.memory_writes_off() and not _is_topic_dry_run(raw):
        return _refused(sig.MEMORY_WRITES_OFF_LINE)
    args = ap.parse_args(raw)
    if getattr(args, "proj", None):
        # `--proj .` names the cwd; made absolute here so every verb (not only the write path)
        # walks the real altitude chain instead of a relative path with no parents.
        args.proj = os.path.abspath(args.proj)

    if args.cmd == "tree-top":
        info = tree_top(args.proj)
        if args.as_json:
            print(json.dumps(info))
        else:
            print("top: %s" % info["top"])
            print("store: %s%s" % (info["store"], "  (bootstrap: not created yet)" if info["bootstrap"] else ""))
        return 0

    if args.cmd in ("topics-show", "topics-stale"):
        try:
            return _topic_read(args)
        except topic_store.TopicStoreError as exc:
            # a damaged topic file: the check could not run, which is not its "no"
            print("! error: %s" % exc, file=sys.stderr)
            return 2

    if args.cmd in TOPIC_WRITE_VERBS:
        try:
            return _topic_write(args)
        except (TopicRefusal, tp.InvalidTopic, topic_store.TopicStoreError) as exc:
            return _refused(exc)

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
            for level, why in tr["refused"]:
                print(_REFUSED_LEVEL_LINE % (why, level))
        return 0

    if args.cmd == "lint":
        rep = lint_tree(args.tree)
        print("voice/frame lint: %s" % rep["anchor"])
        for lvl, slug, n in rep["over_cap"]:
            print("    ! hook over HARD cap (%d chars, hand-edited past the refusal): %s [%s]"
                  % (n, slug, lvl))
        for lvl, slug in rep["no_trigger"]:
            print("    ~ hook missing trigger: %s [%s]" % (slug, lvl))
        for lvl, slug in rep["unlabelled"]:
            print("    ~ body missing the **Why:**/**How to apply:** labels: %s [%s]" % (slug, lvl))
        for lvl, raw in rep["invalid_pointers"]:
            print("    ! pointer whose slug is not a plain filename (skipped, dropped on the next "
                  "write): %s [%s]" % (raw, lvl))
        print("TOTAL over-cap hooks: %d | trigger-less hooks: %d | bodies without Why/How labels: %d"
              " (style advisory)" % (len(rep["over_cap"]), len(rep["no_trigger"]),
                                     len(rep["unlabelled"])))
        found = rep["over_cap"] or rep["no_trigger"] or rep["unlabelled"] or rep["invalid_pointers"]
        return 1 if found else 0

    if args.cmd == "move":
        # `--slug a --slug b` and `--slug a b` both land as a list of groups; flatten to the set
        slugs = [s for group in args.slug for s in group]
        rep = move_entry(args.from_level, args.to_level, slugs, force=args.force)
        if rep["refused"]:
            return _refused(rep["refused"])
        for w in rep["warnings"]:
            print("~ warning: %s" % w)
        print("moved %s: %s -> %s (%s)" % (rep["slug"], rep["from"], rep["to"], rep["direction"]))
        return 0

    if args.cmd == "relocate":
        rep = relocate_entry(args.from_level, args.to_level, args.slug, force=args.force)
        if rep["refused"]:
            return _refused(rep["refused"])
        for w in rep["warnings"]:
            print("~ warning: %s" % w)
        for note in rep.get("notes", []):
            print("~ note: %s" % note)
        print("relocated %s: %s -> %s (%s)" % (
            rep["slug"], rep["from"], rep["to"],
            "CROSS-TREE: body moved + source archived" if rep["cross_tree"]
            else "same tree: pointer move, body untouched"))
        return 0

    if args.cmd == "rename":
        rep = rename_entry(args.level, args.slug, args.to_slug)
        if rep["refused"]:
            return _refused(rep["refused"])
        for w in rep["warnings"]:
            print("~ warning: %s" % w)
        print("renamed %s -> %s at %s" % (rep["slug"], rep["to_slug"], rep["level"]))
        for lvl, citer, where in rep["refs_rewritten"]:
            print("    ref repointed: %s (%s) [%s]" % (citer, where, lvl))
        return 0

    if args.cmd == "retitle":
        rep = retitle_entry(args.level, args.slug, args.to_title)
        if rep["refused"]:
            return _refused(rep["refused"])
        for w in rep["warnings"]:
            print("~ warning: %s" % w)
        print("retitled %s -> %r at %s" % (rep["slug"], rep["to_title"], rep["level"]))
        for lvl in rep["levels"][1:]:
            print("    also retitled at: %s" % lvl)
        return 0

    if args.cmd == "ensure-memory-structure":
        refused = []
        created = scaffold(args.proj, refused=refused)
        print("ensure-memory-structure: created %d file(s) up the chain" % len(created))
        for p in created:
            print("    +", p)
        for level, why in refused:
            print(_REFUSED_LEVEL_LINE % (why, level))
        return 0

    if args.cmd == "set-scope":
        # Resolve BEFORE ensure_level: a refused call must not leave a level scaffolded behind it.
        scope, err = _text_from_flag_or_file(args.scope, args.scope_file, "--scope", "--scope-file")
        if err:
            return _input_error(err)
        local = sig.claude_local_md_path(args.proj)
        if _is_excluded_level(args.proj):             # before the lock, which creates a file there
            raise ExcludedLevel(args.proj)
        pruned = _pruned_part(_anchor(os.path.abspath(args.proj)), args.proj)
        if pruned is not None:                        # same: no walk would read the descriptor
            raise NonLevelDir(os.path.abspath(args.proj), *pruned,
                              route=_ENGINE_ROUTE + " set-scope --proj {level} --scope ...")
        # One read-modify-write under the level's lock. The topics check runs on the level's
        # CURRENT descriptor - its pointer block's, else the legacy CLAUDE.md block ensure_level
        # would harvest, else none - before ensure_level writes anything, so a refused call leaves
        # no level behind and no legacy block moved.
        with sig.memory_lock(local):
            current, stored_in = _current_scope(args.proj)
            try:
                scope_keeping_topics(current, scope.strip(), stored_in=stored_in)
            except (TopicRefusal, tp.InvalidTopic) as exc:
                return _refused(exc)
            ensure_level(args.proj, _locked=True)     # make sure the pointer block exists first
            text = read_store_text(local)
            old_scope, pointers = us.parse_pointer_index(text)
            try:
                scope = scope_keeping_topics(old_scope, scope.strip())
            except (TopicRefusal, tp.InvalidTopic) as exc:
                return _refused(exc)
            changed = us.write_if_changed(local, us.upsert_pointer_block(text, scope, pointers))
        print("scope %s: %s" % ("updated" if changed else "unchanged", local))
        return 0

    if args.cmd == "heal" and args.backfill_titles:
        rep = backfill_titles(args.proj)
        print("back-filled %d title(s); %d body(ies) already had one"
              % (len(rep["filled"]), rep["kept"]))
        for slug in rep["unframed"]:
            print("    ~ body has no frontmatter, left as it is: %s" % slug)
        for slug in rep["untitled"]:
            print("    ~ pointer has no title to copy, body left as it is: %s" % slug)
        for slug in rep["missing"]:
            print("    ! missing central body (not fabricated): %s" % slug)
        return 0

    if args.cmd == "heal":
        rep = heal(args.proj)
        print("healed %d file(s) across %d level(s)" % (len(rep["healed"]), rep["levels"]))
        for p in rep["healed"]:
            print("    ~ repaired: %s" % p)
        for level, slug in rep["orphans"]:
            print("    ! missing central body (not fabricated): %s [%s]" % (slug, level))
        for level, raw in rep["invalid_pointers"]:
            print("    ! dropped a pointer whose slug is not a plain filename: %s [%s]" % (raw, level))
        for level, why in rep["unreadable"]:
            print("    ! unreadable level, left untouched (fix its permissions, or re-save it as "
                  "UTF-8): %s [%s]" % (why, level))
        for level, why in rep["refused"]:
            print(_REFUSED_LEVEL_LINE % (why, level))
        # heal could not do its job at an unreadable level, so "done" would be a lie there
        return 2 if rep["unreadable"] else 0

    if args.cmd == "add":
        hook, err = _text_from_flag_or_file(args.hook, args.hook_file, "--hook", "--hook-file")
        if err:
            return _input_error(err)
        hook = hook.strip()
        body = args.body
        if args.body_file:
            body, err = _read_input_file(args.body_file)
            if err:
                return _input_error(err)
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
                return _input_error(err)
        try:
            slug, _created, advice = add_with_advice(
                args.proj, title=args.title, hook=hook, body=body, type_=args.type_,
                pin=args.pin, scope_default=scope_default, slug=args.slug, skill=args.skill)
        except ADD_REFUSALS as c:
            return _refused(c)
        print(slug)
        for line in advice:
            print(line)
        return 0

    if args.cmd == "amend-pinned":
        # The hook is OPTIONAL here (a body-only or source-only amend keeps the stored hook), so
        # neither form being present is not an error - resolve only when one of them was passed,
        # and use the resolved local downstream, never args.hook.
        hook = None
        if args.hook is not None or args.hook_file:
            hook, err = _text_from_flag_or_file(args.hook, args.hook_file, "--hook", "--hook-file")
            if err:
                return _input_error(err)
            hook = hook.strip()
        body = None
        if args.body_file:
            body, err = _read_input_file(args.body_file)
            if err:
                return _input_error(err)
        try:
            slug = amend_pinned_entry(args.proj, slug=args.slug, hook=hook, body=body,
                                      title=args.title, type_=args.type_)
        except (SlugCollision, HookTooLong, EmptyBody, UnknownSlug, InvalidSlug) as c:
            return _refused(c)
        print(slug)
        return 0
    ap.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
