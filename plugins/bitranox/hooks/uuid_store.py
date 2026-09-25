#!/usr/bin/env python3
"""The slug-keyed central fact store + per-altitude pointer indexes (mount-independent memory).

(Historical filename: this module began as the uuid store; the 2026-07-05 retrieval experiment -
.plan/probe-retrieval-and-platform-20260705.md - showed slug-named flat bodies get APPLIED 6/6 during
reasoning while uuid-sharded bodies were read but ignored 0/6, so the store is slug-keyed.)

Layout:
  * ONE central body-store per tree anchor: `<anchor>/.claude-memory/facts/<slug>.md` - flat,
    human-readable, greppable. The SLUG is the fact's identity, unique per TREE.
  * A POINTER index per altitude, INLINE in that level's `CLAUDE.local.md` (plain cascade text, never
    `@import`): `- [Title](mem:<slug>) - hook <!-- bx:pin -->` inside a managed fenced
    block whose header carries the RETRIEVAL RECIPE (how to walk up and Read a body mid-reasoning -
    the recipe is the experimentally proven retrieval channel, and it reaches Task subagents, which
    never see the SessionStart inject).
  * The resolver derives everything from cwd (nothing absolute is baked): walk up to the anchor,
    read `facts/<slug>.md` there. Proven byte-identical across different mount prefixes.

TRANSITION: pointer lines written before the pivot use `(uuid:<uuid>)` links + a `bx:slug=` token and
their bodies live at the old sharded path `facts/<2-hex>/<uuid>.md`. The parser accepts them (flagged
`legacy`), the renderer re-emits them UNCHANGED (so heal never flips a line whose body has not moved),
and `resolve` reads their bodies from the old path - until `migrate_to_slug_store.py` moves body +
line together.

Pure standard library; cross-platform (pathlib, UTF-8). Writers are mtime-neutral (a no-op write
writes nothing) so the PostToolUse hooks do not churn the files.
"""
import os
import re
import uuid as _uuid
from pathlib import Path

import self_improve_signals as sig

# Fixed namespace for bitranox uuid5 identities (a random-but-frozen v4 UUID; never regenerate it, or
# every fact's identity would shift and every stored pointer would dangle).
NAMESPACE = _uuid.UUID("6f1b2c9e-8a4d-5f3b-9c7e-2d1a0b3c4d5e")

STORE_DIRNAME = sig.MEMORY_DIRNAME               # the central body-store dir, co-located at the anchor
                                                 # (single source: self_improve_signals.MEMORY_DIRNAME)

# The type prefixes a slug may carry (single source; memory_engine aliases this).
TYPE_PREFIXES = ("project", "feedback", "reference", "user")


def slugify(title, type_=None):
    """A stable, filesystem-safe slug from a title (+ optional type prefix), matching the native
    topic-file convention (e.g. 'feedback-no-em-dashes'). Lowercase, hyphen-separated, deduped.
    THE one slug algorithm (memory_engine aliases it; the pointer parser derives back-compat slugs
    from titles with it)."""
    base = re.sub(r"[^a-z0-9]+", "-", (title or "").strip().lower()).strip("-")
    base = base or "note"
    if type_ and type_ in TYPE_PREFIXES and not base.startswith(type_ + "-"):
        base = "%s-%s" % (type_, base)
    if _WINDOWS_DEVICE_RX.fullmatch(base.split(".", 1)[0]):
        base += "-note"                          # `con.md` cannot exist on Windows; see is_valid_slug
    return base


# A slug names a FILE (`facts/<slug>.md`), so it may carry no path: lowercase letters, digits,
# hyphens and dots, starting and ending with a letter or digit. Dots are allowed because real stores
# carry version numbers in slugs (`starlette-1.2-httpx2-testclient`); a leading dot would hide the
# file and a trailing one is stripped by Windows, so both ends must be alphanumeric. `slugify` output
# always matches.
_SLUG_RX = re.compile(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?")

# Windows maps these names to DEVICES whatever follows the first dot, so `con.md` or `nul.1.2.md`
# cannot be a file there: creating one fails, or the write vanishes into the device. The store is
# shared across machines, so a slug any one of them cannot hold is not a slug.
_WINDOWS_DEVICE_RX = re.compile(r"con|prn|aux|nul|com[0-9]|lpt[0-9]")


def is_valid_slug(slug):
    """True when `slug` is a plain filename the store can own on every platform. THE slug check
    every write path that takes a caller-supplied slug applies before building a body path from it:
    without it `../..` reaches outside `facts/`, and the engine becomes an arbitrary `.md` writer."""
    return (isinstance(slug, str) and _SLUG_RX.fullmatch(slug) is not None
            and _WINDOWS_DEVICE_RX.fullmatch(slug.split(".", 1)[0]) is None)


class InvalidSlug(ValueError):
    """Raised when a slug is not a plain filename (`is_valid_slug`). The slug becomes
    `facts/<slug>.md`, so an unchecked `../../CLAUDE` rewrites the tree's CLAUDE.md and `../../../x`
    writes outside the tree altogether. Raised by the path builder itself, so no write path - however
    it came by the slug - can reach a file outside the store."""

    def __init__(self, slug):
        self.slug = slug
        super().__init__("%r is not a valid slug - use lowercase letters, digits, hyphens and dots, "
                         "starting and ending with a letter or digit (no path separators)" % (slug,))


def require_valid_slug(slug):
    """Raise `InvalidSlug` unless `slug` is a plain filename the store can own."""
    if not is_valid_slug(slug):
        raise InvalidSlug(slug)


def is_valid_legacy_uuid(value):
    """True when a pre-pivot pointer's target may build a body path. That target is normally
    `str(uuid5(...))`; its first two characters name a shard DIRECTORY and the whole names the file,
    so it must be a plain name by the same rule as a slug - a `..` or a path walks out of `facts/`."""
    return is_valid_slug(value)

INDEX_BEGIN = "<!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->"
INDEX_END = "<!-- BITRANOX-MEMORY-INDEX:END -->"
# Pre-pivot fence names: still parsed (and replaced on upsert) until every live block is migrated.
LEGACY_INDEX_BEGIN = "<!-- BITRANOX-UUID-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->"
LEGACY_INDEX_END = "<!-- BITRANOX-UUID-INDEX:END -->"
INDEX_HEADING = "# Memory index"
IRON_HEADING = "## Iron rules"
MEMORY_HEADING = "## Memory index"

# The retrieval recipe rendered into every pointer-block header. EXPERIMENT-PROVEN wording
# (6/6 applied mid-reasoning compliance incl. Task subagents; 0/3 without it) - change only with a
# re-run of the retrieval probes.
RECIPE_LINE = ("(fact bodies are NOT preloaded - to read a fact's full body: walk UP from the "
               "current directory to the first ancestor that contains a `.claude-memory/` "
               "directory, then Read `<that ancestor>/.claude-memory/facts/<slug>.md`; the slug is "
               "the `mem:<slug>` link target on the fact's line)")

HOOK_SOFT_MAX = 350   # soft cap, chars, advisory only: 1-3 directive second-person sentences


def hook_over_budget(hook):
    """True when a hook exceeds the soft cap (advisory - callers warn, never fail)."""
    return len(hook or "") > HOOK_SOFT_MAX


HOOK_HARD_MAX = 500   # hard cap, chars. Every pointer line is ALWAYS loaded - at every level of the
                      # cascade, in the main session and again in every subagent that inherits it -
                      # so this is a CONTEXT BUDGET: it bounds what one fact costs a session that
                      # never uses it. It is not wrap protection: a formatter that wraps at 80
                      # columns splits a median-length line just as surely as a 1000-char one.
                      # Detail past the cap belongs in the body, which is read on demand.


def hook_over_hard_cap(hook):
    """True when a hook exceeds the hard cap. The write path REFUSES such a hook instead of
    truncating it: a silent word-boundary cut leaves an always-loaded line that still reads as a
    complete instruction while its tail is gone, which misleads a reader more than an omission
    would. The author moves the detail into the body instead."""
    return len((hook or "").strip()) > HOOK_HARD_MAX


# Trigger-first hooks fire during reasoning; trigger-less ones don't (probe-verified: hooks leading
# with the situation drove a body read in 100% of runs). Advisory, like the length cap.
_TRIGGER_STARTERS = ("when", "whenever", "before", "after", "on ", "if ", "while", "use when",
                     "during", "once ")


def hook_missing_trigger(hook):
    """True when a hook does NOT lead with a trigger phrase (When/Before/If/On/...). Advisory -
    callers warn so the author states WHEN the rule applies, never fail."""
    h = " ".join((hook or "").split()).lower()
    return not any(h.startswith(s) for s in _TRIGGER_STARTERS)


RECURRENCE_ESCALATE_AT = 2   # at this count, prose has demonstrably failed - escalate, do not reword

_ORDINAL_WORDS = {"second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
                  "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10}

# Only UNAMBIGUOUS repeat markers, each requiring a number (or a counting word) next to the noun.
# A body that merely discusses something "recurring" must not match, or every add warns and the
# signal degrades into noise the reader learns to skip.
_RECURRENCE_RX = (
    re.compile(r"\brecurrence:?\s+(\d+)", re.I),           # recurrence: 3 / recurrence 3
    re.compile(r"\b(\d+)\s*(?:st|nd|rd|th)\s+occurrence", re.I),   # 4th occurrence
    re.compile(r"\bhit\s+(\d+)\s+times?", re.I),           # hit 4 times
    re.compile(r"\b(\d+)\s+recurrences\b", re.I),          # 3 recurrences
)
_ORDINAL_RX = re.compile(r"\b(%s)\s+occurrence" % "|".join(_ORDINAL_WORDS), re.I)


def recurrence_count(body):
    """The highest repeat count a body explicitly records, or None.

    The count is the one durable signal that a lesson has already been written and did not hold,
    and it is in hand at exactly the moment a fact is (re)written - so the write path can surface
    it instead of relying on the author to notice a number inside prose they are editing for other
    reasons. Advisory, like the hook lints: callers warn, never fail.

    Returns the HIGHEST marker present, because a body often carries an older count plus a fresher
    "Nth occurrence" note and the escalation should key on the worst case, not the first match.
    """
    text = body or ""
    counts = [int(m.group(1)) for rx in _RECURRENCE_RX for m in rx.finditer(text)]
    counts += [_ORDINAL_WORDS[m.group(1).lower()] for m in _ORDINAL_RX.finditer(text)]
    return max(counts) if counts else None

SCOPE_BEGIN = sig.SCOPE_MARK_BEGIN               # reuse the existing scope markers (same grammar the
SCOPE_END = sig.SCOPE_MARK_END                   # model already knows from the legacy index.md)

# `- [Title](mem:<slug>) - hook <!-- bx:pin -->` (new) or the pre-pivot
# `- [Title](uuid:<uuid>) - hook <!-- ... bx:slug=s -->` (legacy). The hook runs to the FIRST
# `<!--` (a hook may legitimately contain bare `<placeholders>`, so a tempered scan is used, never
# a plain `[^<]` class - that truncated real hooks); anything after the first meta comment is
# trailing garbage, dropped on canonical re-render (heal repairs hand-edit damage).
_PTR_RX = re.compile(r"^- \[(?P<title>[^\]]*)\]\((?P<scheme>mem|uuid):(?P<target>[^)]+)\) - "
                     r"(?P<hook>(?:(?!<!--).)*)"
                     r"(?:<!--\s*(?P<meta>bx:[^>]*?)\s*-->)?(?P<trail>.*)$")


# ---- identity + sharded central paths -----------------------------------------------------------

def fact_uuid(altitude_dir, slug):
    """Deterministic uuid5 identity for a fact at `altitude_dir` with `slug`. Idempotent (same inputs
    -> same uuid, so migration re-runs never duplicate) and collision-free across altitudes (keyed on
    the home altitude dir, not the anchor). `altitude_dir` is normalized so `/a/b`, `/a/b/`, and
    `/a/./b` map to one identity."""
    key = "%s\x00%s" % (os.path.normpath(str(altitude_dir)), slug or "")
    return str(_uuid.uuid5(NAMESPACE, key))


def shard(fact_uuid_str):
    """The 2-hex-digit shard bucket for a uuid (its first two hex chars)."""
    return str(fact_uuid_str)[:2]


def central_facts_dir(anchor_dir):
    """The single central body-store for an anchor: `<anchor>/.claude-memory/facts`."""
    return Path(anchor_dir) / STORE_DIRNAME / "facts"


def body_path(anchor_dir, slug):
    """Absolute path of a fact body in the central store: `.../facts/<slug>.md` (flat, slug-keyed).
    Raises `InvalidSlug` for a slug that is not a plain filename: every read and write of a body goes
    through here, so this is the one place that can guarantee none of them leaves `facts/`."""
    require_valid_slug(slug)
    return central_facts_dir(anchor_dir) / (slug + ".md")


def legacy_body_path(anchor_dir, fact_uuid_str):
    """Pre-pivot body location (`.../facts/<2-hex>/<uuid>.md`) - read-only during the transition;
    `migrate_to_slug_store.py` moves these to the slug-named path. Raises ValueError for a value that
    is not a plain name (the mover would otherwise archive whatever file a `uuid:..` target names)."""
    if not is_valid_legacy_uuid(fact_uuid_str):
        raise ValueError("%r is not a plain legacy fact uuid" % (fact_uuid_str,))
    return central_facts_dir(anchor_dir) / shard(fact_uuid_str) / (fact_uuid_str + ".md")


def free_archive_path(archive_dir, name):
    """The first path in `archive_dir` that holds no file: `name`, else `<stem>~2<suffix>`,
    `<stem>~3<suffix>`, ... An archive is the only copy of a retired fact, so moving a second fact of
    the same slug onto the first would destroy it; `~` is not a slug character, so these names can
    never collide with another slug's plain archive name."""
    archive_dir = Path(archive_dir)
    candidate = archive_dir / name
    stem, suffix = os.path.splitext(name)
    n = 2
    while candidate.exists():
        candidate = archive_dir / ("%s~%d%s" % (stem, n, suffix))
        n += 1
    return candidate


# ---- anchor resolution from cwd -----------------------------------------------------------------

# THE anchor resolver lives in self_improve_signals (the base module); this is the same function.
resolve_anchor = sig.resolve_anchor


# ---- pointer-index model + render/parse ---------------------------------------------------------

class Pointer:
    """One pointer line. `slug` is the fact's identity and the body-file key. A LEGACY pointer
    (pre-pivot) carries the old `uuid` and renders/reads via the old sharded path until the
    migration moves its body - the renderer re-emits legacy lines unchanged so a heal round-trip
    can never break an unmigrated store."""

    __slots__ = ("slug", "title", "hook", "pin", "uuid", "legacy")

    def __init__(self, slug="", title="", hook="", pin=False, uuid="", legacy=False):
        self.slug = slug or ""
        self.title = title or ""
        self.hook = hook or ""
        self.pin = bool(pin)
        self.uuid = str(uuid or "")
        self.legacy = bool(legacy)

    def meta_comment(self):
        # `bx:src` provenance is NOT rendered. It was introduced when the entry line sat behind a
        # CLAUDE.md @import and cost nothing per session; the slug-store pivot then made the pointer
        # block inline always-loaded text and nobody re-priced it. Measured before removal: 8,022
        # tokens, 14.9 percent of this machine's always-loaded cascade, for data nothing reads -
        # every touch of it in the engine was a set union or a re-emit, never a decision. `source`
        # is still PARSED (see `_parse_meta`) so an older line is read without error; it simply
        # stops being written back. Dropping it is deliberate and the old values are not kept.
        parts = []
        if self.pin:
            parts.append("bx:pin")
        if self.legacy and self.slug:                # legacy lines keep their bx:slug token
            parts.append("bx:slug=%s" % self.slug)
        return (" <!-- %s -->" % " ".join(parts)) if parts else ""

    def index_line(self):
        title, hook = _ptr_safe_title(self.title), _ptr_safe_hook(self.hook)
        if self.legacy:
            return "- [%s](uuid:%s) - %s%s" % (title, self.uuid, hook, self.meta_comment())
        return "- [%s](mem:%s) - %s%s" % (title, self.slug, hook, self.meta_comment())


def _one_line(s):
    """`s` with every line boundary collapsed to one space; a string with none comes back unchanged.

    The parser reads one pointer per LINE, splitting exactly where `str.splitlines` does (`\\n`,
    `\\r`, and the rarer separators such as U+2028), so a break inside a field splits the pointer: a
    wrapped `--hook-file` hook loses its tail on the next re-render, a multi-line title drops the
    fact, and a hook whose second line looks like a pointer is read as a second fact. Only line
    boundaries are touched, so every existing single-line pointer re-renders byte for byte."""
    s = s or ""
    parts = s.splitlines()
    if "".join(parts) == s:                          # no line boundary anywhere
        return s
    return " ".join(p.strip() for p in parts if p.strip())


def _ptr_safe_title(s):
    """Neutralize characters that break a pointer line's markdown link title `[Title](mem:slug)`:
    a `]` (or `[`) in the title makes the whole line unparseable, so it is silently dropped on the
    next block round-trip - orphaning the body. The body keeps the true title's information; the
    always-loaded pointer just shows `(dev)` for `[dev]`. A line break is collapsed (`_one_line`)."""
    return _one_line(s).replace("[", "(").replace("]", ")")


def _ptr_safe_hook(s):
    """The hook runs to the FIRST `<!--` (the meta comment); a literal `<!--`/`-->` inside a hook would
    truncate or corrupt the line, so neutralize it. Brackets in a hook are fine (the hook group is a
    tempered scan, not a `[^\\]]` class). A line break is collapsed (`_one_line`)."""
    return _one_line(s).replace("<!--", "< !--").replace("-->", "-- >")


def _slug_from_title(title):
    """A back-compat slug derived from a title: used only when a pointer line carries no `bx:slug=`
    token."""
    return slugify(title)


def _parse_meta(meta):
    """(pin, slug) from a meta comment. A `bx:src=` token is CONSUMED AND DISCARDED: provenance
    was removed in 5.300.0, and an older line must still parse without error until the next
    re-render of its level drops the token."""
    pin, slug = False, ""
    for tok in (meta or "").split():
        if tok == "bx:pin":
            pin = True
        elif tok.startswith("bx:slug="):
            slug = tok[len("bx:slug="):]
    return pin, slug


def render_pointer_index(scope, pointers):
    """Render (scope descriptor, [Pointer]) to the canonical pointer-index text: scope block, the
    RETRIEVAL RECIPE line, then pinned lines under `## Iron rules` and the rest under
    `## Memory index`. Deterministic; ASCII separators only (the tell-sweep convention)."""
    out = ["%s\n%s\n%s" % (SCOPE_BEGIN, (scope or "").strip(), SCOPE_END), "",
           INDEX_HEADING, RECIPE_LINE, ""]
    pinned = [p for p in pointers if p.pin]
    rest = [p for p in pointers if not p.pin]
    if pinned:
        out.append(IRON_HEADING)
        out.extend(p.index_line() for p in pinned)
        out.append("")
    out.append(MEMORY_HEADING)
    out.extend(p.index_line() for p in rest)
    return "\n".join(out).rstrip("\n") + "\n"


def parse_pointer_index(text):
    """Parse pointer-index text (a whole `CLAUDE.local.md`, or just the block) -> (scope, [Pointer]).
    Accepts BOTH the current `mem:<slug>` lines and pre-pivot `uuid:<uuid>` lines (returned with
    `legacy=True`); trailing garbage after the first meta comment is ignored (dropped on the next
    canonical re-render). Headings and prose are ignored.

    When the text holds a managed block, pointers are read from INSIDE the block(s) only. A
    pointer-shaped line in the surrounding prose is not part of the index, and reading it would copy
    it into the block on every write while the original stays behind, so the index grows by one line
    per write. Text with no managed block (a bare rendered block, a snippet) is read whole.

    One slug yields ONE pointer, so a writer updates the copy every reader sees. A migrated `mem:`
    copy beats a legacy `uuid:` copy wherever they sit: a legacy ghost block left AHEAD of the
    migrated one would otherwise hand an update the stale (or already archived) legacy body, and it
    would be written over the migrated fact. Between two copies of the same kind the FIRST wins.

    A pointer whose slug is not a plain filename (`is_valid_slug`), or a legacy one whose target is
    not a plain name, is SKIPPED: its body path would leave `facts/`, so no reader or writer may see it.
    `invalid_pointer_lines` lists what was skipped, so the verbs that rewrite the block can say so."""
    text = text or ""
    scope = sig.read_scope_block(text) or ""
    pointers, index = [], {}
    for raw in _pointer_region(text).splitlines():
        p = _pointer_from_line(raw)
        if p is None:
            continue
        at = index.get(p.slug)
        if at is None:
            index[p.slug] = len(pointers)
            pointers.append(p)
        elif pointers[at].legacy and not p.legacy:
            p.pin = p.pin or pointers[at].pin        # a pin is never lost to the swap
            pointers[at] = p                         # the migrated copy replaces the legacy ghost
    return scope, pointers


def invalid_pointer_lines(text):
    """The pointer-shaped lines `parse_pointer_index` skips because their slug or legacy uuid would
    build a path outside `facts/`, in file order. A canonical re-render drops them, so a caller that
    rewrites the block reports these rather than letting them vanish unremarked."""
    return [raw for raw in _pointer_region(text or "").splitlines()
            if _PTR_RX.match(raw) and _pointer_from_line(raw) is None]


def _pointer_region(text):
    """The text pointers are read from: the managed block(s) when present, else the whole text."""
    spans = _managed_spans(text)
    return "\n".join(text[b:e] for b, e in spans) if spans else text


def _pointer_from_line(raw):
    """A Pointer for one pointer line, or None when the line is not a pointer or names a path that
    is not a plain store file."""
    m = _PTR_RX.match(raw)
    if not m:
        return None
    pin, slug_tok = _parse_meta(m.group("meta"))
    title = m.group("title")
    hook = m.group("hook").strip()
    if m.group("scheme") == "mem":
        p = Pointer(slug=m.group("target"), title=title, hook=hook, pin=pin)
    else:
        p = Pointer(slug=slug_tok or _slug_from_title(title), title=title,
                    hook=hook, pin=pin, uuid=m.group("target"), legacy=True)
        if not is_valid_legacy_uuid(p.uuid):
            return None
    return p if is_valid_slug(p.slug) else None


def _index_block(scope, pointers):
    return "%s\n%s%s" % (INDEX_BEGIN, render_pointer_index(scope, pointers), INDEX_END)


def _managed_spans(text):
    """Every managed-block region in `text`, both fence generations, merged if overlapping. More
    than one span happens in the wild: an old-plugin session's heal can scaffold a second (legacy)
    block next to the migrated one - the canonical writer must collapse them, not skip them."""
    spans = []
    for begin, endm in ((INDEX_BEGIN, INDEX_END), (LEGACY_INDEX_BEGIN, LEGACY_INDEX_END)):
        pos = 0
        while True:
            b = text.find(begin, pos)
            if b < 0:
                break
            e = text.find(endm, b)
            e = len(text) if e < 0 else e + len(endm)    # malformed (no END) -> cut to end
            spans.append((b, e))
            pos = e
    spans.sort()
    merged = []
    for b, e in spans:
        if merged and b < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((b, e))
    return merged


def upsert_pointer_block(text, scope, pointers):
    """Splice ONE canonical managed pointer block into `text` (a `CLAUDE.local.md`), replacing
    EVERY existing managed block (either fence generation; a stray second block is collapsed) and
    preserving all surrounding text. Byte-safe outside the fences."""
    block = _index_block(scope, pointers)
    spans = _managed_spans(text)
    if spans:
        pieces, prev = [], 0
        for b, e in spans:
            pieces.append(text[prev:b])
            prev = e
        pieces.append(text[prev:])
        head = pieces[0].rstrip("\n")
        tail = "\n\n".join(s for s in (piece.strip("\n") for piece in pieces[1:]) if s)
        parts = [p for p in (head, block, tail) if p]
        return "\n\n".join(parts).rstrip("\n") + "\n"
    sep = "" if not text.strip() else (text.rstrip("\n") + "\n\n")
    return sep + block + "\n"


# ---- mtime-neutral writers ----------------------------------------------------------------------

def write_if_changed(path, text):
    """Write only when content differs (mtime-neutral). True if written."""
    path = Path(path)
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def put_body(anchor_dir, slug, body):
    """Write a fact body to `<anchor>/.claude-memory/facts/<slug>.md`, mtime-neutral. True if written."""
    return write_if_changed(body_path(anchor_dir, slug), (body or "").rstrip("\n") + "\n")


def add_pointer(altitude_dir, slug, title, hook, pin=False, scope_default=""):
    """Upsert one pointer line (keyed by SLUG) into `<altitude_dir>/CLAUDE.local.md`'s managed block
    (merging pin on update), under a lock, mtime-neutral. Sets the scope
    descriptor if absent. Updating a LEGACY pointer flips it to the current format (the caller is
    responsible for having written the slug-named body). Does NOT write the body - the caller does,
    via `put_body`. Returns the slug. Raises `InvalidSlug` before writing for a slug that is not a
    plain filename."""
    require_valid_slug(slug)
    local = sig.claude_local_md_path(altitude_dir)
    with sig.memory_lock(local):
        try:
            text = local.read_text(encoding="utf-8")
        except OSError:
            text = ""
        scope, pointers = parse_pointer_index(text)
        by_slug = {p.slug: p for p in pointers}
        if slug in by_slug:
            p = by_slug[slug]
            p.title, p.hook = title, (hook or p.hook)
            p.pin = p.pin or pin
            p.legacy, p.uuid = False, ""             # updated fact now lives at the slug path
        else:
            pointers.append(Pointer(slug=slug, title=title, hook=hook, pin=pin))
        write_if_changed(local, upsert_pointer_block(text, scope or scope_default, pointers))
    return slug


# ---- the resolver: cwd -> resolved bodies -------------------------------------------------------

class Resolved:
    """A fully resolved fact: its slug (the identity), always-loaded title/hook, the body read from
    the central store, and the altitude (the dir whose pointer index referenced it)."""

    __slots__ = ("slug", "title", "hook", "body", "altitude")

    def __init__(self, slug, title, hook, body, altitude):
        self.slug = str(slug)
        self.title = title
        self.hook = hook
        self.body = body
        self.altitude = altitude


def resolve(cwd):
    """From `cwd`, collect every pointer from cwd up to the anchor and read each body from the
    anchor's central store (slug-named path; a LEGACY pointer's body is read from the old sharded
    path until migrated). Deduped by slug, narrowest (cwd) first. Returns [Resolved]; [] when there
    is no anchor. A missing body is skipped (never fabricated). Never raises."""
    try:
        anchor = resolve_anchor(cwd)
        if anchor is None:
            return []
        here = Path(cwd)
        ladder = [here, *here.parents]
        highest = ladder.index(anchor) if anchor in ladder else 0
        levels = ladder[:highest + 1]                # cwd up to and including the anchor
        out, seen = [], set()
        for level in levels:
            try:
                text = sig.claude_local_md_path(str(level)).read_text(encoding="utf-8")
            except OSError:
                continue
            _scope, pointers = parse_pointer_index(text)
            for p in pointers:
                if p.slug in seen:
                    continue
                path = legacy_body_path(anchor, p.uuid) if p.legacy else body_path(anchor, p.slug)
                try:
                    body = path.read_text(encoding="utf-8")
                except OSError:
                    continue                         # body missing -> skip, do not fabricate
                seen.add(p.slug)
                out.append(Resolved(slug=p.slug, title=p.title, hook=p.hook,
                                    body=body.rstrip("\n"), altitude=level))
        return out
    except Exception:                                # noqa: BLE001 - a read path must never wedge a turn
        return []
