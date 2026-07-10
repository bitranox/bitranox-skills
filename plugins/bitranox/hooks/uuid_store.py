#!/usr/bin/env python3
"""The slug-keyed central fact store + per-altitude pointer indexes (mount-independent memory).

(Historical filename: this module began as the uuid store; the 2026-07-05 retrieval experiment -
.plan/probe-retrieval-and-platform-20260705.md - showed slug-named flat bodies get APPLIED 6/6 during
reasoning while uuid-sharded bodies were read but ignored 0/6, so the store is slug-keyed.)

Layout:
  * ONE central body-store per tree anchor: `<anchor>/.claude-memory/facts/<slug>.md` - flat,
    human-readable, greppable. The SLUG is the fact's identity, unique per TREE.
  * A POINTER index per altitude, INLINE in that level's `CLAUDE.local.md` (plain cascade text, never
    `@import`): `- [Title](mem:<slug>) - hook <!-- bx:src=a,b bx:pin -->` inside a managed fenced
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
    return base

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


HOOK_HARD_MAX = 500   # hard cap, chars: a longer pointer line risks being wrapped by a markdown
                      # formatter and then DROPPED on the next block round-trip (orphaning its body).
                      # The body keeps the full detail, so truncating the always-loaded hook is safe.


def cap_hook(hook):
    """Hard-cap a hook to one round-trip-safe pointer line, truncating at a word boundary.
    Returns the hook unchanged when within `HOOK_HARD_MAX`."""
    h = (hook or "").strip()
    if len(h) <= HOOK_HARD_MAX:
        return h
    cut = h[:HOOK_HARD_MAX]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp >= HOOK_HARD_MAX - 80 else cut).rstrip()


# Trigger-first hooks fire during reasoning; trigger-less ones don't (probe-verified: hooks leading
# with the situation drove a body read in 100% of runs). Advisory, like the length cap.
_TRIGGER_STARTERS = ("when", "whenever", "before", "after", "on ", "if ", "while", "use when",
                     "during", "once ")


def hook_missing_trigger(hook):
    """True when a hook does NOT lead with a trigger phrase (When/Before/If/On/...). Advisory -
    callers warn so the author states WHEN the rule applies, never fail."""
    h = " ".join((hook or "").split()).lower()
    return not any(h.startswith(s) for s in _TRIGGER_STARTERS)

SCOPE_BEGIN = sig.SCOPE_MARK_BEGIN               # reuse the existing scope markers (same grammar the
SCOPE_END = sig.SCOPE_MARK_END                   # model already knows from the legacy index.md)

# `- [Title](mem:<slug>) - hook <!-- bx:src=a,b bx:pin -->` (new) or the pre-pivot
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
    """Absolute path of a fact body in the central store: `.../facts/<slug>.md` (flat, slug-keyed)."""
    return central_facts_dir(anchor_dir) / (str(slug) + ".md")


def legacy_body_path(anchor_dir, fact_uuid_str):
    """Pre-pivot body location (`.../facts/<2-hex>/<uuid>.md`) - read-only during the transition;
    `migrate_to_slug_store.py` moves these to the slug-named path."""
    return central_facts_dir(anchor_dir) / shard(fact_uuid_str) / (str(fact_uuid_str) + ".md")


# ---- anchor resolution from cwd -----------------------------------------------------------------

# THE anchor resolver lives in self_improve_signals (the base module); this is the same function.
resolve_anchor = sig.resolve_anchor


# ---- pointer-index model + render/parse ---------------------------------------------------------

class Pointer:
    """One pointer line. `slug` is the fact's identity and the body-file key. A LEGACY pointer
    (pre-pivot) carries the old `uuid` and renders/reads via the old sharded path until the
    migration moves its body - the renderer re-emits legacy lines unchanged so a heal round-trip
    can never break an unmigrated store."""

    __slots__ = ("slug", "title", "hook", "source", "pin", "uuid", "legacy")

    def __init__(self, slug="", title="", hook="", source=None, pin=False, uuid="", legacy=False):
        self.slug = slug or ""
        self.title = title or ""
        self.hook = hook or ""
        self.source = set(source or ())
        self.pin = bool(pin)
        self.uuid = str(uuid or "")
        self.legacy = bool(legacy)

    def meta_comment(self):
        parts = []
        if self.source:
            parts.append("bx:src=%s" % ",".join(sorted(self.source)))
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


def _ptr_safe_title(s):
    """Neutralize characters that break a pointer line's markdown link title `[Title](mem:slug)`:
    a `]` (or `[`) in the title makes the whole line unparseable, so it is silently dropped on the
    next block round-trip - orphaning the body. The body keeps the true title's information; the
    always-loaded pointer just shows `(dev)` for `[dev]`."""
    return (s or "").replace("[", "(").replace("]", ")")


def _ptr_safe_hook(s):
    """The hook runs to the FIRST `<!--` (the meta comment); a literal `<!--`/`-->` inside a hook would
    truncate or corrupt the line, so neutralize it. Brackets in a hook are fine (the hook group is a
    tempered scan, not a `[^\\]]` class)."""
    return (s or "").replace("<!--", "< !--").replace("-->", "-- >")


def _slug_from_title(title):
    """A back-compat slug derived from a title: used only when a pointer line carries no `bx:slug=`
    token."""
    return slugify(title)


def _parse_meta(meta):
    source, pin, slug = set(), False, ""
    for tok in (meta or "").split():
        if tok == "bx:pin":
            pin = True
        elif tok.startswith("bx:src="):
            source |= {s for s in tok[len("bx:src="):].split(",") if s}
        elif tok.startswith("bx:slug="):
            slug = tok[len("bx:slug="):]
    return source, pin, slug


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
    canonical re-render). Headings and prose are ignored."""
    scope = sig.read_scope_block(text or "") or ""
    pointers = []
    for raw in (text or "").splitlines():
        m = _PTR_RX.match(raw)
        if not m:
            continue
        source, pin, slug_tok = _parse_meta(m.group("meta"))
        title = m.group("title")
        hook = m.group("hook").strip()
        if m.group("scheme") == "mem":
            pointers.append(Pointer(slug=m.group("target"), title=title, hook=hook,
                                    source=source, pin=pin))
        else:
            pointers.append(Pointer(slug=slug_tok or _slug_from_title(title), title=title,
                                    hook=hook, source=source, pin=pin,
                                    uuid=m.group("target"), legacy=True))
    return scope, pointers


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


def add_pointer(altitude_dir, slug, title, hook, source=None, pin=False, scope_default=""):
    """Upsert one pointer line (keyed by SLUG) into `<altitude_dir>/CLAUDE.local.md`'s managed block
    (merging the provenance set + pin on update), under a lock, mtime-neutral. Sets the scope
    descriptor if absent. Updating a LEGACY pointer flips it to the current format (the caller is
    responsible for having written the slug-named body). Does NOT write the body - the caller does,
    via `put_body`. Returns the slug."""
    slug = str(slug)
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
            p.source |= set(source or ())
            p.pin = p.pin or pin
            p.legacy, p.uuid = False, ""             # updated fact now lives at the slug path
        else:
            pointers.append(Pointer(slug=slug, title=title, hook=hook, source=source, pin=pin))
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
