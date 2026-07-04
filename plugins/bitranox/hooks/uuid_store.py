#!/usr/bin/env python3
"""Central UUID body-store + per-altitude pointer indexes (the mount-independent memory layout).

This is the ADDITIVE storage model that sits beside the legacy `.claude-bx-selflearning/` store (which
is untouched during the transition). Motivation and two proving probes live in `.plan/`:
`memory-architektur.md` section 11, `probe-uuid-central-store-resolve.md`,
`probe-ancestor-index-fact-retrieval.md`.

The problem it solves: an inline index in an ancestor `CLAUDE.local.md` loads reliably and DRIVES the
model to fetch bodies on demand, but only if the fact links are resolvable from a deep launch cwd. A
store-relative or ancestor-relative link resolves against the launch cwd (not the index file) and 404s;
an absolute link is mount-dependent and goes stale the moment the tree moves or is seen from another
mount point. The fix is to make IDENTITY a UUID, not a path:

  * ONE central body-store per anchor: `<anchor>/.claude-memory/facts/<2-hex-shard>/<uuid>.md`. A fact's
    body lives there exactly once (dedup by the UUID identity), referenced from any number of altitudes.
    The shard is the first two hex digits of the UUID (256 buckets; disk is cheap, shard generously).
  * A POINTER index per altitude, INLINE in that level's `CLAUDE.local.md` (plain text, not `@import` -
    an import above the workspace root does not inline, but cascade text always loads). Each line carries
    a mount-independent `uuid:<uuid>` reference, never a path.
  * The resolver derives EVERYTHING from cwd (nothing absolute is baked): walk up to the anchor, the
    central store is `<anchor>/.claude-memory/facts`, collect the `uuid:` refs from cwd up to the anchor,
    read each body by shard. The probe proved this resolves byte-identically across two mount prefixes.

Identity: `fact_uuid(altitude_dir, slug)` is a deterministic uuid5 keyed on the fact's HOME altitude dir
(not the anchor) + slug. Deterministic so a migration re-run never duplicates; keyed on the home altitude
so two altitudes under one anchor that both hold a fact with the same slug get DISTINCT uuids (their
bodies never collide in the single central store).

Pure standard library; cross-platform (pathlib, UTF-8). Writers are mtime-neutral (a no-op write writes
nothing) so the PostToolUse hooks do not churn the files.
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

INDEX_BEGIN = "<!-- BITRANOX-UUID-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->"
INDEX_END = "<!-- BITRANOX-UUID-INDEX:END -->"
INDEX_HEADING = "# Memory index"

SCOPE_BEGIN = sig.SCOPE_MARK_BEGIN               # reuse the existing scope markers (same grammar the
SCOPE_END = sig.SCOPE_MARK_END                   # model already knows from the legacy index.md)

# `- [Title](uuid:<uuid>) - hook <!-- bx:src=a,b bx:pin -->` ; meta comment optional.
_PTR_RX = re.compile(r"^- \[(?P<title>[^\]]*)\]\(uuid:(?P<uuid>[0-9a-fA-F-]+)\) - (?P<hook>.*?)"
                     r"(?:\s*<!--\s*(?P<meta>bx:[^>]*?)\s*-->)?\s*$")


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


def body_path(anchor_dir, fact_uuid_str):
    """Absolute path of a fact body in the central store: `.../facts/<shard>/<uuid>.md`."""
    return central_facts_dir(anchor_dir) / shard(fact_uuid_str) / (str(fact_uuid_str) + ".md")


# ---- anchor resolution from cwd -----------------------------------------------------------------

# THE anchor resolver lives in self_improve_signals (the base module); this is the same function.
resolve_anchor = sig.resolve_anchor


# ---- pointer-index model + render/parse ---------------------------------------------------------

class Pointer:
    """One pointer line: a mount-independent `uuid:` reference to a body in the central store, plus the
    always-loaded title + hook and the provenance `source` set / `pin` flag (same meta grammar as the
    legacy engine so de-double and reconcile read both uniformly)."""

    __slots__ = ("uuid", "title", "hook", "source", "pin", "slug")

    def __init__(self, uuid, title, hook="", source=None, pin=False, slug=""):
        self.uuid = str(uuid)
        self.title = title or ""
        self.hook = hook or ""
        self.source = set(source or ())
        self.pin = bool(pin)
        self.slug = slug or ""

    def meta_comment(self):
        parts = []
        if self.source:
            parts.append("bx:src=%s" % ",".join(sorted(self.source)))
        if self.pin:
            parts.append("bx:pin")
        if self.slug:                                # the logical identity (uuid is only the body key)
            parts.append("bx:slug=%s" % self.slug)
        return (" <!-- %s -->" % " ".join(parts)) if parts else ""

    def index_line(self):
        return "- [%s](uuid:%s) - %s%s" % (self.title, self.uuid, self.hook, self.meta_comment())


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
    """Render (scope descriptor, [Pointer]) to the canonical pointer-index text (scope block + heading +
    `uuid:` lines). Deterministic; ASCII separators only (the tell-sweep convention)."""
    out = ["%s\n%s\n%s" % (SCOPE_BEGIN, (scope or "").strip(), SCOPE_END), "", INDEX_HEADING, ""]
    for p in pointers:
        out.append(p.index_line())
    return "\n".join(out).rstrip("\n") + "\n"


def parse_pointer_index(text):
    """Parse pointer-index text (a whole `CLAUDE.local.md`, or just the block) -> (scope, [Pointer]).
    Only `- [..](uuid:..) - ..` lines become pointers; everything else is ignored."""
    scope = sig.read_scope_block(text or "") or ""
    pointers = []
    for raw in (text or "").splitlines():
        m = _PTR_RX.match(raw)
        if not m:
            continue
        source, pin, slug = _parse_meta(m.group("meta"))
        title = m.group("title")
        pointers.append(Pointer(uuid=m.group("uuid"), title=title, hook=m.group("hook"),
                                source=source, pin=pin, slug=slug or _slug_from_title(title)))
    return scope, pointers


def _index_block(scope, pointers):
    return "%s\n%s%s" % (INDEX_BEGIN, render_pointer_index(scope, pointers), INDEX_END)


def upsert_pointer_block(text, scope, pointers):
    """Splice ONE canonical managed pointer block into `text` (a `CLAUDE.local.md`), replacing any
    existing managed block and preserving all surrounding text. Byte-safe outside the fences."""
    block = _index_block(scope, pointers)
    b = text.find(INDEX_BEGIN)
    if b >= 0:
        e = text.find(INDEX_END, b)
        e = len(text) if e < 0 else e + len(INDEX_END)   # malformed (no END) -> cut to end
        head = text[:b].rstrip("\n")
        tail = text[e:].lstrip("\n")
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


def put_body(anchor_dir, fact_uuid_str, body):
    """Write a fact body to the central sharded store `<anchor>/.claude-memory/facts/<shard>/<uuid>.md`,
    mtime-neutral. Returns True if written."""
    return write_if_changed(body_path(anchor_dir, fact_uuid_str), (body or "").rstrip("\n") + "\n")


def add_pointer(altitude_dir, uuid, title, hook, source=None, pin=False, scope_default="", slug=""):
    """Upsert one pointer line into `<altitude_dir>/CLAUDE.local.md`'s managed block (merging the
    provenance set + pin on update), under a lock, mtime-neutral. Sets the scope descriptor if absent.
    `slug` is the logical identity carried on the line (the uuid is only the body-file key); it defaults
    to a title-derived slug. Does NOT write the body - the caller writes that via `put_body`. Returns the
    uuid."""
    uuid = str(uuid)
    slug = slug or _slug_from_title(title)
    local = sig.claude_local_md_path(altitude_dir)
    with sig.memory_lock(local):
        try:
            text = local.read_text(encoding="utf-8")
        except OSError:
            text = ""
        scope, pointers = parse_pointer_index(text)
        by_uuid = {p.uuid: p for p in pointers}
        if uuid in by_uuid:
            p = by_uuid[uuid]
            p.title, p.hook = title, (hook or p.hook)
            p.source |= set(source or ())
            p.pin = p.pin or pin
            p.slug = slug or p.slug
        else:
            pointers.append(Pointer(uuid=uuid, title=title, hook=hook, source=source, pin=pin, slug=slug))
        write_if_changed(local, upsert_pointer_block(text, scope or scope_default, pointers))
    return uuid


# ---- the resolver: cwd -> resolved bodies -------------------------------------------------------

class Resolved:
    """A fully resolved fact: its uuid, always-loaded title/hook, the body read from the central store,
    and the altitude (the dir whose pointer index referenced it)."""

    __slots__ = ("uuid", "title", "hook", "body", "altitude", "slug")

    def __init__(self, uuid, title, hook, body, altitude, slug=""):
        self.uuid = str(uuid)
        self.title = title
        self.hook = hook
        self.body = body
        self.altitude = altitude
        self.slug = slug or ""


def resolve(cwd):
    """From `cwd`, collect every `uuid:` pointer from cwd up to the anchor and read each body from the
    anchor's central store. Deduped by uuid (a uuid referenced at several altitudes yields one body).
    Narrowest (cwd) first. Returns [Resolved]; [] when there is no anchor. A missing body is skipped
    (never fabricated). Never raises."""
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
                if p.uuid in seen:
                    continue
                try:
                    body = body_path(anchor, p.uuid).read_text(encoding="utf-8")
                except OSError:
                    continue                         # body missing -> skip, do not fabricate
                seen.add(p.uuid)
                out.append(Resolved(uuid=p.uuid, title=p.title, hook=p.hook,
                                    body=body.rstrip("\n"), altitude=level, slug=p.slug))
        return out
    except Exception:                                # noqa: BLE001 - a read path must never wedge a turn
        return []
