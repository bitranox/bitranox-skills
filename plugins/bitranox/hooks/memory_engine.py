#!/usr/bin/env python3
"""The single write path for the curated `.claude-bx-selflearning/` memory store.

Every memory mutation (per-turn capture, migration, reconcile backfill) goes through here - NEVER
hand-write `index.md`/`facts/` via the Write/Edit tools, or the PostToolUse hooks (tell-sweep,
reformat-md-tables) fire and churn the mtime every turn. This module writes files directly with
`Path.write_text`, so those hooks do not run; it is mtime-neutral (a no-op write writes nothing).

`index.md` grammar - kept markdown-link compatible with `reconcile_memory_index.py`:

    <!-- bitranox:self-learning -->
    <scope descriptor: what this level is for; the dream's placement compass>
    <!-- /bitranox:self-learning -->

    # Memory index

    - [Title](facts/<slug>.md) - hook <!-- bx:src=a,b -->        heavy: body in facts/<slug>.md
    - [Title](#<slug>) - hook <!-- bx:src=c bx:pin -->           tiny: body inlined, indented below
      inline body line
      inline body line

Design points:
  * A body is INLINED only when it is small AND has no line starting with `@` (an inlined `@path`
    would become an accidental `@import`); otherwise it goes to `facts/<slug>.md`, which is NOT
    imported, so leading-`@` there is harmless. This removes the leading-`@` hazard by construction.
  * Provenance is a `<!-- bx:src=<comma-list> [bx:pin] -->` comment on the entry line (the reconciler
    and de-double read it uniformly without opening `facts/` files); `source` is a SET (merged on
    update) so migration idempotency + cross-tier de-double + two-slugs->same-dir merge all key off it.
  * All output is ASCII (` - ` separators, never an em dash) so the tell-sweep convention holds.

Pure standard library; cross-platform (pathlib, UTF-8, the O_EXCL lock in self_improve_signals).
"""

import argparse
import re
import sys
from pathlib import Path

import self_improve_signals as sig

SCOPE_BEGIN = sig.SCOPE_MARK_BEGIN          # <!-- bitranox:self-learning -->
SCOPE_END = sig.SCOPE_MARK_END              # <!-- /bitranox:self-learning -->
INDEX_HEADING = "# Memory index"
IMPORT_BEGIN = "<!-- BITRANOX-MEMORY:BEGIN managed by bitranox self-improve; do not hand-edit."
IMPORT_NOTE = "     Target is gitignored/local (this block lives in CLAUDE.local.md unless track_private); a fresh clone has none and the import resolves to nothing. -->"
IMPORT_LINE = "@%s/%s" % (sig.CURATED_DIRNAME, sig.CURATED_INDEX)   # @.claude-bx-selflearning/index.md
IMPORT_END = "<!-- BITRANOX-MEMORY:END -->"

INLINE_MAX_BYTES = 280                       # bodies larger than this go to facts/ (kept lazy)
_TYPE_PREFIXES = ("project", "feedback", "reference", "user")

_ENTRY_RX = re.compile(r"^- \[(?P<title>[^\]]*)\]\((?P<target>[^)]+)\) - (?P<hook>.*?)"
                       r"(?:\s*<!--\s*(?P<meta>bx:[^>]*?)\s*-->)?\s*$")
# An `@token` that Claude Code would treat as an import trigger: `@` at line start OR after
# whitespace, followed by a path-like char. Matches `@path/file`, `See @README`, standalone `@x`;
# does NOT match an email `a@b.com` (the `@` there follows a word char, not whitespace/start). A body
# containing such a token is forced to a `facts/` file (not imported), so it can never fire an import.
_IMPORT_AT_RX = re.compile(r"(?:^|\s)@[\w./~-]")


def slugify(title, type_=None):
    """A stable, filesystem-safe slug from a title (+ optional type prefix), matching the native
    topic-file convention (e.g. 'feedback-no-em-dashes'). Lowercase, hyphen-separated, deduped."""
    base = re.sub(r"[^a-z0-9]+", "-", (title or "").strip().lower()).strip("-")
    base = base or "note"
    if type_ and type_ in _TYPE_PREFIXES and not base.startswith(type_ + "-"):
        base = "%s-%s" % (type_, base)
    return base


class Entry:
    """One curated fact. `heavy` -> body lives in `facts/<slug>.md`; else `body` is inlined in the
    index. `source` is the provenance set (origin native slugs); `pin` protects it from cap-eviction."""

    __slots__ = ("slug", "title", "hook", "body", "source", "pin", "heavy")

    def __init__(self, slug, title, hook, body="", source=None, pin=False, heavy=None):
        self.slug = slug
        self.title = title
        self.hook = hook or ""
        self.body = body or ""
        self.source = set(source or ())
        self.pin = bool(pin)
        self.heavy = self._decide_heavy() if heavy is None else bool(heavy)

    def _decide_heavy(self):
        """Inline only a small body with NO import-like `@token` (which would fire an `@import`); a
        body that is large OR contains such a token goes to a `facts/` file (not imported)."""
        if not self.body.strip():
            return False
        if len(self.body.encode("utf-8")) > INLINE_MAX_BYTES:
            return True
        return bool(_IMPORT_AT_RX.search(self.body))

    def target(self):
        return "facts/%s.md" % self.slug if self.heavy else "#%s" % self.slug

    def meta_comment(self):
        parts = []
        if self.source:
            parts.append("bx:src=%s" % ",".join(sorted(self.source)))
        if self.pin:
            parts.append("bx:pin")
        return (" <!-- %s -->" % " ".join(parts)) if parts else ""

    def index_line(self):
        return "- [%s](%s) - %s%s" % (self.title, self.target(), self.hook, self.meta_comment())


def _parse_meta(meta):
    """Parse a `bx:src=a,b bx:pin` metadata blob -> (source_set, pin_bool)."""
    source, pin = set(), False
    for tok in (meta or "").split():
        if tok == "bx:pin":
            pin = True
        elif tok.startswith("bx:src="):
            source |= {s for s in tok[len("bx:src="):].split(",") if s}
    return source, pin


def parse(text):
    """Parse `index.md` text -> (scope_descriptor, [Entry]). Inline bodies (indented lines under an
    `(#slug)` entry) are attached to their entry; heavy entries carry no body here."""
    scope = sig.read_scope_block(text) or ""
    entries, cur = [], None
    for raw in (text or "").splitlines():
        m = _ENTRY_RX.match(raw)
        if m:
            source, pin = _parse_meta(m.group("meta"))
            target = m.group("target")
            heavy = target.endswith(".md")
            slug = (target.rsplit("/", 1)[-1][:-3] if heavy else target.lstrip("#"))
            cur = Entry(slug=slug, title=m.group("title"), hook=m.group("hook"),
                        source=source, pin=pin, heavy=heavy)
            entries.append(cur)
            continue
        if cur is not None and not cur.heavy and (raw.startswith("  ") or not raw.strip()):
            # indented continuation (or a blank within the body) belongs to the current inline entry
            cur.body = (cur.body + "\n" + raw[2:]) if cur.body else raw[2:]
        else:
            cur = None
    for e in entries:                        # trim trailing blank lines captured into inline bodies
        e.body = e.body.rstrip("\n")
    return scope, entries


def render(scope, entries):
    """Render (scope_descriptor, [Entry]) back to canonical `index.md` text. Deterministic."""
    out = ["%s\n%s\n%s" % (SCOPE_BEGIN, (scope or "").strip(), SCOPE_END), "", INDEX_HEADING, ""]
    for e in entries:
        out.append(e.index_line())
        if not e.heavy and e.body.strip():
            out.extend("  " + ln if ln else "" for ln in e.body.split("\n"))
    return "\n".join(out).rstrip("\n") + "\n"


# ---- store IO (index.md + facts/), locked + mtime-neutral --------------------------------------

def read_store(proj):
    """Return (scope, [Entry], {slug: facts_body}) for a project's curated store. Heavy bodies are
    loaded from `facts/<slug>.md` so callers see full content; missing/empty store -> ("", [], {})."""
    mem = sig.curated_index(proj)
    facts_dir = sig.claude_memory_dir(proj) / "facts"
    try:
        text = mem.read_text(encoding="utf-8")
    except OSError:
        text = ""
    scope, entries = parse(text)
    bodies = {}
    for e in entries:
        if e.heavy:
            try:
                bodies[e.slug] = (facts_dir / (e.slug + ".md")).read_text(encoding="utf-8")
            except OSError:
                bodies[e.slug] = ""
    return scope, entries, bodies


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


def _commit_store(proj, scope, entries, bodies):
    """Write index.md (index + inline) and each heavy entry's facts/<slug>.md; mtime-neutral."""
    changed = False
    changed |= _write_if_changed(sig.curated_index(proj), render(scope, entries))
    facts_dir = sig.claude_memory_dir(proj) / "facts"
    for e in entries:
        if e.heavy:
            changed |= _write_if_changed(facts_dir / (e.slug + ".md"), bodies.get(e.slug, "").rstrip("\n") + "\n")
    return changed


def add_or_update_entry(proj, title, hook, body="", type_=None, source=None, pin=False,
                        scope_default="", slug=None):
    """Upsert a curated fact into `<proj>/.claude-bx-selflearning/` (the single write path). Merges the
    provenance `source` set on update, decides inline-vs-`facts/` by size + leading-`@`, ensures the
    level's `@import` block (CLAUDE.local.md by default, CLAUDE.md if track_private) + scope, and writes
    under a lock, mtime-neutral. Returns the slug."""
    slug = slug or slugify(title, type_)
    src = set(source or ())
    lock_target = sig.curated_index(proj)
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
            e.heavy = e._decide_heavy()
        else:
            e = Entry(slug=slug, title=title, hook=hook, body=body, source=src, pin=pin)
            entries.append(e)
        bodies[slug] = e.body
        _commit_store(proj, scope or scope_default, entries, bodies)
    return slug


def _import_target(proj):
    """Which file carries the `@import` block. DEFAULT: the UNTRACKED `CLAUDE.local.md` (symmetric with
    the gitignored store - the wiring never touches tracked git, no clone gets a dangling line, no
    commit is needed to set up memory). When `track_private` is on (the store is committed with the
    repo) the import goes in the TRACKED `CLAUDE.md` so a teammate's clone loads it too."""
    if sig.load_config().get("track_private"):
        return sig.claude_md_path(proj)
    return sig.claude_local_md_path(proj)


def ensure_level(proj, scope_default="", _locked=False):
    """Ensure this level can load its curated memory: (1) a marked `@import` block in the level's import
    file (`CLAUDE.local.md` by default, `CLAUDE.md` when `track_private`; created if absent, nothing
    else touched), (2) `index.md` exists with its scope block, and (3) any LEGACY
    `<!-- bitranox:self-learning -->` scope block is MOVED out of `CLAUDE.md` into `index.md` (byte-safe
    outside the markers). Idempotent + mtime-neutral."""
    def _do():
        md_path = sig.claude_md_path(proj)
        local_path = sig.claude_local_md_path(proj)
        tracked = bool(sig.load_config().get("track_private"))
        try:
            md = md_path.read_text(encoding="utf-8")
        except OSError:
            md = ""
        md_changed = False
        # (3) harvest + strip a legacy scope block that lives in CLAUDE.md (regardless of import target)
        legacy_scope = sig.read_scope_block(md)
        if legacy_scope is not None:
            md = _strip_scope_block(md)
            md_changed = True
        try:
            local_txt = local_path.read_text(encoding="utf-8")
        except OSError:
            local_txt = ""
        # (1) ensure the import block once, in the RIGHT file; skip if already present in EITHER file
        block = "%s\n%s\n%s\n%s" % (IMPORT_BEGIN, IMPORT_NOTE, IMPORT_LINE, IMPORT_END)
        if IMPORT_LINE not in md and IMPORT_LINE not in local_txt:
            if tracked:
                sep = "" if not md or md.endswith("\n\n") else ("\n" if md.endswith("\n") else "\n\n")
                md = md + sep + block + "\n"
                md_changed = True
            else:
                sep = "" if not local_txt or local_txt.endswith("\n\n") else ("\n" if local_txt.endswith("\n") else "\n\n")
                local_txt = local_txt + sep + block + "\n"
                _write_if_changed(local_path, local_txt)
        if md_changed:                            # touch CLAUDE.md only when we actually changed it
            _write_if_changed(md_path, md)
        if not tracked:                           # keep the untracked wiring + store out of a public push
            sig.ensure_gitignored(proj, sig.CURATED_DIRNAME + "/", "CLAUDE.local.md")
        # (2) ensure index.md with a scope block (prefer an existing scope, else the legacy, else default)
        mem_path = sig.curated_index(proj)
        try:
            mem_text = mem_path.read_text(encoding="utf-8")
        except OSError:
            mem_text = ""
        cur_scope = sig.read_scope_block(mem_text)
        if cur_scope is None:
            scope, entries = parse(mem_text)
            new_scope = (legacy_scope or scope_default or "").strip()
            _write_if_changed(mem_path, render(new_scope, entries))

    if _locked:
        _do()
    else:
        with sig.memory_lock(sig.curated_index(proj)):
            _do()


def _strip_scope_block(text):
    """Remove a marked `<!-- bitranox:self-learning -->...<!-- /... -->` block from CLAUDE.md text,
    leaving everything else byte-identical (used to relocate a legacy scope block into index.md)."""
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


# ---- CLI: the capture procedure invokes this (never hand-writes memory files) ------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Curated memory write engine (the single write path).")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="upsert one curated fact into <proj>/.claude-bx-selflearning")
    a.add_argument("--proj", required=True, help="project cwd (the level to capture at)")
    a.add_argument("--title", required=True)
    a.add_argument("--hook", required=True, help="one-line hook (what makes the fact present)")
    a.add_argument("--type", dest="type_", default=None,
                   choices=[None, "feedback", "project", "reference", "user"])
    a.add_argument("--body", default="", help="the fact body (inline if tiny, else -> facts/)")
    a.add_argument("--body-file", default=None, help="read the body from a file (multi-line safe)")
    a.add_argument("--source", default="", help="comma-separated provenance keys")
    a.add_argument("--pin", action="store_true", help="force-keep in the always-loaded index")
    a.add_argument("--scope", default="", help="scope descriptor for this level (set if absent)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if args.cmd == "add":
        body = args.body
        if args.body_file:
            body = Path(args.body_file).read_text(encoding="utf-8")
        slug = add_or_update_entry(
            args.proj, title=args.title, hook=args.hook, body=body, type_=args.type_,
            source=[s.strip() for s in args.source.split(",") if s.strip()],
            pin=args.pin, scope_default=args.scope)
        print(slug)
        return 0
    ap.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
