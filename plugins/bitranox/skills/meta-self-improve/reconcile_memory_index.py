#!/usr/bin/env python3
"""Reference-check + reconcile a curated memory altitude (UUID-native).

A curated altitude is a level dir whose `CLAUDE.local.md` holds a managed pointer block
(`- [Title](mem:<slug>) - hook <!-- bx:pin -->`); the fact bodies live centrally at
`<anchor>/.claude-memory/facts/<slug>.md`. Slug is the identity, unique per tree. This tool:
  * `--check`: verifies `[[wikilink]]` integrity across an ordered altitude chain (upward-only, no
    dangling), and emits an ADVISORY warning when a level's always-loaded pointer block grows large;
  * default (reconcile): reports orphan pointers whose central body is missing (a raw body carries no
    title/hook/slug, so a pointer can NOT be reconstructed from a body - orphans are reported, never
    fabricated). A body no level points at is a DANGLING body: `--check` / `--check-tree` report
    it and `--rehome` re-attaches it; nothing here deletes one.
  * `archive_entry` forgets a fact: drop its pointer line + move its central body to `.archive/`.
    A fact placed by topic has a line at each level its topics place it at; archiving it drops
    them all. Archiving the LAST pointer is refused while another fact links it (`[[slug]]`), names it in
    plain prose, or a level's CLAUDE.md names it (`inbound_mentions`): each would be left pointing
    at nothing, and only the `[[ref]]` kind is ever reported afterwards. `--force` archives anyway.
  * `--repair-appended-type`: a one-off repair for the body damage `--check-tree` reports as an
    appended `metadata: type:` block (see `appended_type_damage`); `--dry-run` lists only.
  * a fact the engine places by topic (`render-topics`) has one line per level its topics place
    it at: those copies are no duplicate, and a `[[ref]]` to it is judged through its body, not
    by where its lines stand. `--check-tree` instead compares every level with a dry run of the
    tree render (render drift), and `--check` reports such a line held again below a level of
    the chain that holds it; each finding names the render that repairs it.

`parse_frontmatter`/`derive_title`/`derive_hook` are kept for the NATIVE `~/.claude` tier (its topic
files still carry `name`/`description` frontmatter); `migrate_memory.py` imports them.

Exit codes: 0 clean; 1 a problem was found (orphan pointer or ref, downward ref, duplicate, render
drift, a placement by topic that could not be checked, a topic-placed line repeated below a level
that holds it, decoy, frame-only or appended-type body, misplaced fact, a dangling body `--rehome`
cannot re-attach
because it is sharded or its name is not a slug, a damaged body `--repair-appended-type` could not
repair) or `--archive` named no entry or was refused because something still names the fact;
2 could not run: a dir argument does not exist, a level
file, fact body or store directory could not be read (not UTF-8, no permission - `--check-tree`
still prints every finding and counts the path in its TOTAL line, `--rehome` names the body), a
write failed (`--archive` leaves the fact as it was, or names where its body now is). A path it
could not read is never guessed at.

Pure standard library; cross-platform; ASCII output only.
"""

import argparse
import contextlib
import ntpath
import os
import re
import shutil
import sys
from collections.abc import Callable, Container, Iterable, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple, TypedDict

# reuse the UUID-native engine (single source of truth for the on-disk format) from the hooks dir
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import memory_engine as ME  # noqa: E402
import self_improve_signals as sig  # noqa: E402
import uuid_store as us  # noqa: E402

type _StrPath = str | os.PathLike[str]
"""A path as this tool's callers pass it: a str (the CLI) or a Path (the tests, the engine)."""

type _MovePort = Callable[[str, str], object]
"""The body-move seam of `archive_entry`: shutil.move, or a test's stand-in."""

type _CommitPort = Callable[[str, str, list[ME.Entry], dict[str, str]], object]
"""The pointer-write seam of `archive_entry`: the engine's store commit, or a test's stand-in."""

type _PinsPort = Callable[[_StrPath], Container[str]]
"""Asked for a tree's pinned or legacy slugs (`_TreePins`, or a fixed set in a caller)."""

type _DriftRow = tuple[str, int, int, int, list[str]]
"""One `render_drift` row: level, lines missing, differing, placed elsewhere, example slugs."""


class ReconcileReport(TypedDict):
    """What `reconcile` reports for one level."""

    dir: str
    facts: int
    already_indexed: int
    added: list[str]
    orphans: list[str]
    dry_run: bool


class ReferenceReport(TypedDict):
    """What `check_references` found on a chain: (source, ref) pairs, and repeated lines."""

    checked: int
    orphans: list[tuple[str, str]]
    downward: list[tuple[str, str]]
    repeated: list[tuple[str, str, str]]


class Mentions(TypedDict):
    """What still names a slug (`inbound_mentions`): (level, source) pairs and CLAUDE.md paths."""

    refs: list[tuple[str, str]]
    prose: list[tuple[str, str]]
    docs: list[str]


class Misplaced(TypedDict):
    """One `find_misplaced` candidate: the fact, and the other tree its body's paths name."""

    level: str
    slug: str
    target_anchor: str
    paths: list[str]


class TreeReport(TypedDict):
    """What `check_tree` found under one anchor."""

    anchor: str
    levels: int
    duplicates: dict[str, list[str]]
    render_drift: list[_DriftRow]
    render_refused: str
    orphan_pointers: list[tuple[str, str]]
    orphan_refs: list[tuple[str, str, str]]
    sideways_refs: list[tuple[str, str, str]]
    danglers: list[str]
    decoy_anchors: list[str]
    unreadable_dirs: list[str]
    frame_only_bodies: list[str]
    appended_type_damage: list[str]


def _walk_error_reason(exc: ME.TreeWalkError) -> str:
    """The reason a TreeWalkError carries."""
    return exc.reason

_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
_SLUG_SEP_RE = re.compile(r"[_-]")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s")
_FRONTMATTER_OPEN_RE = re.compile(r"---[ \t]*\r?\n")

_HOOK_MAX = 160
_TYPE_PREFIXES = us.TYPE_PREFIXES
_WIKILINK_RX = re.compile(r"\[\[([^\]]+)\]\]")   # run it over ME.mask_code_regions(text): a
                                                 # `[[x]]` inside code is quoted syntax, not a ref
_WARN_BYTES = 50_000             # SOFT: warn (never fail) when a level's pointer block grows past this
_NON_ENTRY = {"claude.md", "claude.local.md"}


# ---- frontmatter parsing (the NATIVE tier's topic files still carry name/description) ------------

def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (meta, body). meta has 'name'/'description' when present (stdlib, no YAML dep)."""
    meta: dict[str, str] = {}
    # a BOM made the opening delimiter unrecognisable; "\n" only because splitlines() also breaks
    # on U+2028 and \f, which can sit inside a value
    text = text.lstrip("\ufeff")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return meta, text
    end: int | None = None
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
        m = _FRONTMATTER_KEY_RE.match(line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2)
        if val in (">", "|", ">-", "|-", ">+", "|+"):
            chunk: list[str] = []
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


def _collapse(text: str | None) -> str:
    return " ".join((text or "").split())


def derive_title(meta: Mapping[str, str], body: str, filename: _StrPath) -> str:
    """A human-ish title: first body heading, else de-slugified name, else the filename stem."""
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("# "):
            return _collapse(s[2:])
    name = meta.get("name") or Path(filename).stem
    parts = _SLUG_SEP_RE.split(name)
    if len(parts) > 1 and parts[0].lower() in _TYPE_PREFIXES:
        parts = parts[1:]
    title = " ".join(p for p in parts if p).strip()
    return title[:1].upper() + title[1:] if title else Path(filename).stem


def derive_hook(meta: Mapping[str, str], body: str) -> str:
    """One-line hook: the frontmatter description, else the first body sentence; capped."""
    hook = _collapse(meta.get("description", ""))
    if not hook:
        para = _collapse(body)
        hook = _SENTENCE_END_RE.split(para)[0] if para else ""
    if len(hook) > _HOOK_MAX:
        hook = hook[: _HOOK_MAX - 3].rstrip() + "..."
    return hook


# ---- altitude model (pointer block + central bodies) -------------------------------------------

def _canon(s: str) -> str:
    """Canonical slug for MATCHING: lowercase, treat `-` and `_` as the same separator."""
    return s.strip().lower().replace("_", "-")


def _ref_slug(token: str) -> str:
    """Normalize a wiki-link token to a bare canonical slug: '[[global:fleet_ssh]]' -> 'fleet-ssh'."""
    return _canon(token.split(":")[-1])


def is_curated(d: _StrPath) -> bool:
    """A dir is CURATED when its `CLAUDE.local.md` holds a managed pointer block. The engine's own
    test, so this and the tree walk cannot disagree: absent is False, and a file that exists but
    cannot be read or is not UTF-8 raises `TreeWalkError` rather than reading as "not a level"."""
    return ME.carries_pointer_block(Path(d) / "CLAUDE.local.md")


def altitude_targets(d: _StrPath) -> set[str]:
    """Every canonical slug a curated altitude offers as a `[[wikilink]]` target: each pointer's slug.
    A NON-curated level contributes nothing (it is a plain project dir, not a memory store - never
    rglob its subtree, which would scan docs/code and manufacture false refs)."""
    d = Path(d)
    if not is_curated(d):
        return set()
    _scope, entries, _bodies = ME.read_store(str(d))
    return {_canon(e.slug) for e in entries}


def altitude_sources(d: _StrPath) -> list[tuple[str, str]]:
    """[(source_slug, text)] to scan for `[[wikilinks]]` at a curated altitude - one source PER pointer
    (its hook + central body). A NON-curated level contributes nothing."""
    d = Path(d)
    if not is_curated(d):
        return []
    _scope, entries, bodies = ME.read_store(str(d))
    return [(_canon(e.slug), e.hook + "\n" + bodies.get(e.slug, "")) for e in entries]


def _unpassed_ancestor_levels(dirs: Sequence[_StrPath]) -> list[Path]:
    """Ancestor altitudes of `dirs` the caller did NOT pass, narrow -> broad.

    `[[refs]]` are upward-only, so a level's refs can only ever resolve against itself and its
    ancestors. Resolving against just the dirs handed in therefore reports every legitimate upward
    ref as an orphan - measured as 5 false orphans from a project dir against 0 from the anchor on
    the same data.

    Levels the caller DID pass are skipped deliberately: re-adding one at a broader position would
    also grant its slugs that position, and the downward test (`max(where) < pos`) could then never
    fire for a full chain.
    """
    def _key(p: _StrPath) -> Path | None:
        try:
            return Path(p).resolve()
        except OSError:
            return None

    passed = {k for k in (_key(d) for d in dirs) if k is not None}
    seen: set[Path] = set()
    out: list[Path] = []
    for d in dirs:
        for lvl in sig.altitude_chain(str(d)):
            key = _key(lvl)
            if key is None or key in passed or key in seen:
                continue
            seen.add(key)
            out.append(Path(lvl))
    return out


def _narrow_to_broad(dirs: Iterable[Path]) -> list[Path]:
    """Order levels narrow -> broad by ancestry DEPTH, stably.

    Altitude used to come from argv POSITION with nothing checking it, so the same store answered
    differently depending on the order the caller typed: measured, one chain reported 11 problems
    passed anchor-first and 0 passed project-first, and every false finding had the shape the
    storage spec explicitly permits (a project entry citing a tree-top rule). A report like that
    invites demoting correct links to prose, and a dream driven by it would "fix" a clean store.

    The levels on a chain are ancestors of one another, so depth decides the order without asking
    the caller. The sort is STABLE, which is what keeps SIBLING levels - equal depth, not ancestors,
    so depth cannot rank them - in the order they were given rather than inventing an altitude.
    """
    def depth(path: Path) -> int:
        try:
            return len(Path(path).resolve().parts)
        except OSError:
            return len(Path(path).parts)
    return sorted(dirs, key=lambda path: -depth(path))


def check_references(dirs: Iterable[_StrPath]) -> ReferenceReport:
    """Verify `[[ref]]` integrity across an altitude chain, in any order the caller passes. Returns
    {checked, orphans, downward}: `orphans` refs resolve nowhere in the chain; `downward` refs resolve
    only at a NARROWER altitude than the source. Both are (source_slug, ref_slug) pairs.

    Ancestor altitudes above `dirs` are pulled in as TARGET providers automatically, so checking a
    single project dir is correct rather than a wall of false orphans. Only the passed dirs supply
    ref SOURCES, so `checked` still counts what the caller asked about."""
    chain = _narrow_to_broad([Path(d) for d in dirs])
    targets: dict[str, set[int]] = {}             # slug -> set of altitude positions offering it
    for pos, d in enumerate(chain):
        for s in altitude_targets(d):
            targets.setdefault(s, set()).add(pos)

    # Ancestors sit at positions broader than every passed dir, which is what they are; an upward
    # ref out of the listed dirs is the only direction the storage spec permits.
    for offset, lvl in enumerate(_unpassed_ancestor_levels(chain)):
        for s in altitude_targets(lvl):
            targets.setdefault(s, set()).add(len(chain) + offset)

    orphans: list[tuple[str, str]] = []
    downward: list[tuple[str, str]] = []
    checked = 0
    pins = _TreePins()
    for pos, d in enumerate(chain):
        for label, text in altitude_sources(d):
            for m in _WIKILINK_RX.finditer(ME.mask_code_regions(text)):
                ref = _ref_slug(m.group(1))
                if not ref or ref == label:
                    continue
                checked += 1
                where = targets.get(ref)
                # Placed by topic, its lines stand where the levels' topics put them: it may have
                # none on this chain, or only below the citer, and neither is the citer's to fix.
                # Asked only for a ref that would be reported, so a clean ref reads no body.
                if (not where or max(where) < pos) and placed_by_topic(
                        ME.anchor_dir(str(d)), ref, pins):
                    continue
                if not where:
                    orphans.append((label, ref))
                elif max(where) < pos:
                    downward.append((label, ref))
    return {"checked": checked, "orphans": sorted(set(orphans)), "downward": sorted(set(downward)),
            "repeated": chain_repeats(chain)}


def has_inbound_refs(dirs: Iterable[_StrPath], slug: str) -> bool:
    """True if any OTHER entry across the chain references `[[slug]]` - move/demotion safety.
    Delegates to the engine's scan (memory_engine.inbound_ref_sources is the single source)."""
    return ME.has_inbound_refs([str(d) for d in dirs], slug)


# ---- advisory size probe on the always-loaded pointer block ------------------------------------

def over_cap(level_dir: _StrPath, max_bytes: int = _WARN_BYTES) -> tuple[bool, int, int]:
    """(within, lines, bytes) for a level's always-loaded pointer block (the managed span in its
    CLAUDE.local.md). NOT hard-capped: `within` is False only to raise an ADVISORY warning when the
    block grows large; the remedy is to shrink the block where it is (fold near-duplicates, trim
    long hooks), never to lift its facts to a broader level, which loads them in more sessions.
    Bodies are central (not in the block), so only the pointer lines count toward the always-loaded
    budget."""
    text = ME.read_store_text(Path(level_dir) / "CLAUDE.local.md")
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

def reconcile(level_dir: _StrPath, dry_run: bool = False) -> ReconcileReport:
    """Report pointers at `level_dir` whose central body is missing (unreconstructable - a raw body
    carries no title/hook/slug). Additive/idempotent: it writes nothing (there is no backfill in the
    UUID model; the engine writes pointer + body atomically). Returns a report dict."""
    d = Path(level_dir)
    _scope, entries, _bodies = ME.read_store(str(d))
    anchor = ME.anchor_dir(str(d))
    orphans = sorted(
        _canon(e.slug) for e in entries
        if not (us.legacy_body_path(anchor, e.uuid) if e.legacy else us.body_path(anchor, e.slug)).is_file())
    return {"dir": str(d), "facts": len(entries), "already_indexed": len(entries),
            "added": [], "orphans": orphans, "dry_run": dry_run}


def _other_levels_pointing(anchor: _StrPath, level_dir: _StrPath, slug: str) -> bool:
    """True when any OTHER curated level in the tree still has a pointer for `slug` - SIBLINGS and
    DESCENDANTS included, not just `level_dir`'s altitude chain. The archive guard depends on this:
    dropping a pointer at a HIGH level must not archive the body while a LOWER level still points at
    it (that leaves an orphan pointer). Scanning only the ancestor chain missed descendant levels."""
    qcanon = _canon(slug)
    for lvl in _all_curated_levels(anchor):
        if Path(lvl).resolve() == Path(level_dir).resolve():
            continue
        # raises TreeWalkError rather than skip: "no other level points at it" is the answer
        # that archives a body a level still needs
        _s, ptrs = us.parse_pointer_index(ME.read_store_text(Path(lvl) / "CLAUDE.local.md"))
        if any(_canon(x.slug) == qcanon for x in ptrs):
            return True
    return False


def _names_invalid_pointer(level_dir: _StrPath, slug: str) -> bool:
    """True when `level_dir`'s pointer block carries a line for `slug` that the parser skips because
    the slug (or legacy uuid) is not a plain store name."""
    text = ME.read_store_text(Path(level_dir) / "CLAUDE.local.md")
    needles = ("](mem:%s)" % slug, "](uuid:%s)" % slug, "bx:slug=%s " % slug)
    return any(n in raw + " " for raw in us.invalid_pointer_lines(text) for n in needles)


# A slug-shaped token: starts and ends alphanumeric, may hold `-`, `_` and `.` inside. The
# lookarounds keep `a-b` from matching inside `xa-b` or `a-bc`.
_TOKEN_RX = re.compile(r"(?<![A-Za-z0-9_.-])[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?(?![A-Za-z0-9_-])")
_LINK_RX = re.compile(r"\[\[([^\]]+)\]\]")


def prose_mentions(texts: Mapping[str, str | None], known: Container[str]) -> dict[str, list[str]]:
    """{target: [sources]} for every known HYPHENATED slug a source names in plain text. PURE.

    `texts` maps a canonical source slug to its text. `[[...]]` spans are cut first, so a linked
    ref is never counted twice, and a source never mentions itself. A slug with no hyphen is not
    searched for: it is indistinguishable from an ordinary word. Code is NOT masked, since a slug
    quoted in backticks is still a name that goes stale."""
    out: dict[str, set[str]] = {}
    for source, text in texts.items():
        token: str
        for token in _TOKEN_RX.findall(_LINK_RX.sub(" ", text or "")):
            target = ME.canon_slug(token)
            if "-" in target and target in known and target != source:
                out.setdefault(target, set()).add(source)
    return {k: sorted(v) for k, v in out.items()}


def inbound_mentions(anchor: _StrPath, slug: str) -> Mentions:
    """What still names `slug` anywhere under `anchor`: {"refs": [(level, source)], "prose":
    [(level, source)], "docs": [CLAUDE.md path]}. Raises the engine's TreeWalkError on a level or
    body it cannot read: "nothing names it" is the answer that permits an archive."""
    qcanon = ME.canon_slug(slug)
    levels = _all_curated_levels(anchor)
    refs = ME.inbound_ref_sources(levels, slug)
    texts: dict[str, str | None] = {}
    where: dict[str, str] = {}
    for lvl in levels:
        _scope, entries, bodies = ME.read_store(str(lvl))
        for e in entries:
            key = ME.canon_slug(e.slug)
            texts[key] = "%s\n%s" % (e.hook or "", bodies.get(e.slug, ""))
            where[key] = str(lvl)
    linked = {ME.canon_slug(src) for _lvl, src in refs}
    prose = [(where[src], src) for src in prose_mentions(texts, {qcanon}).get(qcanon, [])
             if src not in linked]
    docs: list[str] = []
    for lvl in sorted({str(Path(anchor))} | {str(x) for x in levels}):
        doc = Path(lvl) / "CLAUDE.md"
        try:
            text = doc.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        tokens: list[str] = _TOKEN_RX.findall(text)
        if any(ME.canon_slug(t) == qcanon for t in tokens):
            docs.append(str(doc))
    return {"refs": sorted(refs), "prose": sorted(prose), "docs": docs}


class ArchiveBlocked(Exception):
    """Archiving the last pointer was refused because something still names the fact.

    `found` is `inbound_mentions`'s result. Not an OSError: nothing failed, the archive was
    declined, and the CLI reports it as a found problem (exit 1), never as "could not run"."""

    def __init__(self, slug: str, found: Mentions) -> None:
        super().__init__("%s is still named by %d fact link(s), %d prose mention(s) and %d "
                         "CLAUDE.md file(s)" % (slug, len(found["refs"]), len(found["prose"]),
                                                len(found["docs"])))
        self.found = found


class ArchiveRollbackFailed(OSError):
    """The pointer write failed after the body was archived, and the body could not be put back.
    The message names where the body now is, since the pointer still names the old place."""


def _put_back(moved: Sequence[tuple[Path, Path]], cause: BaseException, move: _MovePort) -> None:
    """Undo the body moves of an archive whose pointer write failed, newest first, so the failure
    leaves the fact exactly as it was. Raises ArchiveRollbackFailed naming any body it could not
    return: the caller must not then report the fact as unchanged."""
    stuck: list[tuple[Path, Path]] = []
    for src, dest in reversed(moved):
        try:
            move(str(dest), str(src))
        except OSError:
            stuck.append((src, dest))
    if stuck:
        where = "; ".join(f"now at {dst}, belongs at {src}" for src, dst in stuck)
        raise ArchiveRollbackFailed(
            f"the pointer write failed ({cause}) and the body could not be put back: {where} - "
            "the pointer still names the old path, so move it back by hand") from cause


def placed_copies(anchor: _StrPath, level_dir: _StrPath, slug: str) -> list[str]:
    """The OTHER levels holding a line of `slug` when its fact is placed by topic, in level order
    (the top first, a parent before its children, siblings by name); [] for every other fact.
    Placed means what the engine's renderer manages (`memory_engine.placed_copies`: a body bound
    to a topic with `title:` and `description:`, no line of it pinned at any level). Levels are
    compared lexically, as the engine compares them. Archiving such a fact forgets it at every
    level: one line dropped would only be render drift the next render puts back."""
    others = [str(level) for level, _ptr in ME.placed_copies(anchor, slug)
              if not ME.same_level(level, level_dir)]
    return sorted(others, key=lambda level: Path(os.path.abspath(level)).parts)


class ArchiveIncomplete(OSError):
    """Archiving a fact placed by topic failed after some of its other lines were dropped. The body
    was not moved (or was moved back), so the fact is whole at the levels in `remaining`; the
    message names the re-run that finishes the archive and the render that puts the dropped lines
    back."""

    def __init__(self, slug: str, level: str, anchor: _StrPath, dropped: Sequence[str],
                 remaining: Sequence[str], cause: BaseException) -> None:
        super().__init__(
            "could not finish archiving %s (%s): its line(s) at %s are dropped; its body and its "
            "line(s) at %s are unchanged. Re-run skills/meta-self-improve/reconcile_memory_index.py "
            "--archive %s %s once the cause is fixed, or put the dropped line(s) back with "
            "%s" % (slug, cause, ", ".join(dropped), ", ".join(remaining), slug, level,
                    _RENDER_ROUTE % (anchor, "tree")))
        self.slug, self.dropped, self.remaining = slug, list(dropped), list(remaining)


def archive_entry(level_dir: _StrPath, slug: str, archive_subdir: str = ".archive",
                  dry_run: bool = False, *, move: _MovePort | None = None,
                  commit: _CommitPort | None = None, force: bool = False) -> bool:
    """Forget a fact: drop its pointer line and move its central body to `<anchor>/.claude-memory/
    <archive_subdir>/`. With `dry_run`, report whether an entry WOULD be removed but write nothing.
    Returns True if an entry was (or, under dry_run, would be) removed.

    Raises OSError when the body cannot be archived, and then leaves the pointer in place: dropping
    it anyway turned the fact into a dangling body while the CLI printed "archived". Raises OSError
    too when the pointer write fails, after moving the body BACK: the body moves first so that a
    body that cannot move costs no pointer, and a pointer write that then fails must not leave the
    pointer naming a body already in the archive. If the body cannot be put back either, the
    error is ArchiveRollbackFailed and names where it is.

    Raises ArchiveBlocked, before any write and under `dry_run` too, when this is the LAST pointer
    of the fact and `inbound_mentions` finds anything still naming it, unless `force`. Dropping one
    of several pointers keeps the fact, so nothing is left dangling and nothing is checked - except
    for a fact placed by topic (`placed_copies`): its lines at the other levels are dropped first,
    before the body moves, so the archive is always its last pointer. A failure after some of them
    were dropped raises ArchiveIncomplete (an OSError) naming them; the body is not in the archive.

    `move` and `commit` are the body-move and pointer-write seams (shutil.move and the engine's
    store commit when omitted), resolved at call time.

    The level's own block is re-read and written under its level lock (`sig.memory_lock`, the lock
    every `add` takes): what was read before taking it is a plan. Reading and writing it unlocked
    dropped the line of another fact an `add` wrote in between, and an `add` that had read before
    the archive's write put the archived line back, naming a body already in the archive (both
    sides exit 0). The lines at the other levels are dropped first, each under its own lock, so
    no level lock is ever held while another is taken. The commit writes no body: an archive only
    drops a line, and writing the kept facts' bodies back from its read undid any `add` another
    level made to them since.

    Raises `sig.MemoryWritesOff` before anything is read under BITRANOX_MEMORY_WRITES=off, unless
    `dry_run`. It cannot leave that to the commit's own guard: the body is moved BEFORE the commit,
    and a refusal there is not the OSError `_put_back` answers, so the body would stay in the
    archive while its pointer still named it.

    A real archive in a tree with a topic list holds the tree's placement lock (the engine's
    `placement_lock_if_listed`) across every line it drops and the body move, so no render places
    the fact again between them; it waits for it as `set-topics` does and raises
    PlacementLockBusy (a TimeoutError, so an OSError) when it stays held."""
    held: contextlib.AbstractContextManager[None]
    if dry_run:
        held = contextlib.nullcontext()
    else:
        sig.refuse_if_memory_writes_off()
        held = ME.placement_lock_if_listed(ME.anchor_dir(str(level_dir)),
                                           "reconcile_memory_index.py --archive")
    with held:
        return _archive_entry(level_dir, slug, archive_subdir, dry_run, move, commit, force)


def _archive_entry(level_dir: _StrPath, slug: str, archive_subdir: str, dry_run: bool,
                   move: _MovePort | None, commit: _CommitPort | None, force: bool) -> bool:
    """`archive_entry` itself; its caller holds the placement lock for a bound fact."""
    move_body: _MovePort = move or shutil.move
    write: _CommitPort = commit or ME.commit_store
    d = Path(level_dir)
    _scope, entries, _bodies = ME.read_store(str(d))          # the plan; re-read under the lock
    qcanon = _canon(slug)
    if not any(_canon(e.slug) == qcanon for e in entries):
        # A hand-damaged pointer (`mem:../../CLAUDE`) is never parsed into an entry, so it owns no
        # body; forgetting it means dropping the line, which the canonical re-render below does.
        if not _names_invalid_pointer(d, slug):
            return False
        if not dry_run:
            with _level_lock(d):
                scope, current, _bodies = ME.read_store(str(d))
                write(str(d), scope, current, {})
        return True
    anchor = ME.anchor_dir(str(d))
    # A fact placed by topic is archived at EVERY level it has a line at, so this is its last
    # pointer whatever the other levels hold, and whatever names it is left naming nothing.
    others = placed_copies(anchor, d, slug)
    if not force and (others or not _other_levels_pointing(anchor, d, slug)):
        found = inbound_mentions(anchor, slug)
        if found["refs"] or found["prose"] or found["docs"]:
            raise ArchiveBlocked(slug, found)
    if dry_run:                                  # a dry run reports the outcome and writes NOTHING
        return True
    dropped: list[str] = []
    try:
        for other in others:
            # before the body moves: a failure here leaves the body, this level's line and the
            # lines not yet reached, which a render repairs, never a line with no body
            ME.drop_pointer(other, slug)
            dropped.append(other)
        with _level_lock(d):
            scope, entries, _bodies = ME.read_store(str(d))
            kept = [e for e in entries if _canon(e.slug) != qcanon]
            _archive_here(d, anchor, slug, scope, entries, kept, archive_subdir, move_body, write)
    except ArchiveRollbackFailed as exc:
        if not dropped:
            raise
        raise ArchiveRollbackFailed("%s; its line(s) at %s were dropped before that"
                                    % (exc, ", ".join(dropped))) from exc
    except OSError as exc:
        if not dropped:
            raise
        # absolute, so the re-run it names works from any cwd; lexical, as the levels compare
        here = os.path.abspath(str(d))
        remaining = sorted([here, *others[len(dropped):]], key=lambda level: Path(level).parts)
        raise ArchiveIncomplete(slug, here, anchor, dropped, remaining, exc) from exc
    return True


def _level_lock(level_dir: Path) -> contextlib.AbstractContextManager[None]:
    """The level lock of `level_dir`: the one every `add` there takes around its read and write."""
    return sig.memory_lock(sig.claude_local_md_path(str(level_dir)))


def _archive_here(d: Path, anchor: Path, slug: str, scope: str, entries: list[ME.Entry],
                  kept: list[ME.Entry], archive_subdir: str, move: _MovePort,
                  commit: _CommitPort) -> None:
    """Move the body to the archive when no OTHER level still holds a line of `slug` (the caller
    has dropped them), then write this level's block without it; a failed write moves the body
    back (see `archive_entry`). The caller holds `d`'s level lock and read `entries` under it; the
    commit names no body, so it writes none (see `archive_entry`)."""
    qcanon = _canon(slug)
    moved: list[tuple[Path, Path]] = []
    for e in entries:
        if _canon(e.slug) == qcanon:
            src = us.legacy_body_path(anchor, e.uuid) if e.legacy else us.body_path(anchor, e.slug)
            # archive the body ONLY when no other level in the tree still points at this slug
            others = _other_levels_pointing(anchor, d, e.slug)
            if src.is_file() and not others:
                archive = us.central_facts_dir(anchor).parent / archive_subdir
                archive.mkdir(parents=True, exist_ok=True)
                # an archive is the only copy of a retired fact: never move onto an earlier one
                dest = us.free_archive_path(archive, src.name)
                move(str(src), str(dest))
                moved.append((src, dest))
    try:
        commit(str(d), scope, kept, {})
    except OSError as exc:
        _put_back(moved, exc, move)
        raise


# ---- CLI ---------------------------------------------------------------------------------------

def _print_mentions(found: Mentions) -> None:
    for lvl, src in found["refs"]:
        print("    [[ref]]  %s  @ %s" % (src, lvl))
    for lvl, src in found["prose"]:
        print("    prose    %s  @ %s" % (src, lvl))
    for doc in found["docs"]:
        print("    doc      %s" % doc)


def _all_curated_levels(anchor: _StrPath, unreadable: list[str] | None = None) -> list[str]:
    """Every curated level dir under `anchor` (a `CLAUDE.local.md` with a managed pointer block).
    Delegates to the engine's `curated_levels_under` (the single tree-walk) so this tool and the
    engine's `lint --tree` never enumerate the tree differently. It raises on anything it cannot
    read unless `unreadable` is a list, which then receives each such path instead."""
    return ME.curated_levels_under(anchor, unreadable=unreadable)


def _list_store_dir(d: Path, unreadable: list[str] | None) -> list[Path]:
    """The entries of one directory of the body store; [] when it does not exist.

    A directory that exists but cannot be listed raises `TreeWalkError`, or - for a caller that
    reports rather than acts - is appended to `unreadable`: a body behind it is unknown, and an
    empty answer would read as "no dangling bodies there"."""
    try:
        return sorted(d.iterdir())
    except FileNotFoundError:
        return []
    except OSError as exc:
        if unreadable is None:
            raise ME.TreeWalkError(d, "cannot list this directory, so the bodies in it are "
                                      "unknown: %s" % exc) from exc
        unreadable.append(str(d))
        return []


def store_bodies(facts: Path, unreadable: list[str] | None = None) -> tuple[set[str], dict[str, str]]:
    """(flat slugs, {legacy uuid: "<shard>/<uuid>"}) for every body in a central store.

    Both layouts the engine reads: `facts/<slug>.md`, and the pre-pivot sharded
    `facts/<shard(uuid)>/<uuid>.md` (`uuid_store.legacy_body_path`). A file anywhere else under
    `facts/` - including a uuid filed under the wrong shard - is not where the engine looks, so it
    is not a body at all. The same rule as compuse-toolbox's `mem_levels.py`."""
    entries = _list_store_dir(facts, unreadable)
    flat = {e.stem for e in entries if e.suffix == ".md" and e.is_file()}
    sharded: dict[str, str] = {}
    for d in entries:
        if not d.is_dir() or d.is_symlink():
            continue
        for f in _list_store_dir(d, unreadable):
            if f.suffix == ".md" and f.is_file() and us.shard(f.stem) == d.name:
                sharded[f.stem] = "%s/%s" % (d.name, f.stem)
    return flat, sharded


def find_dangling_bodies(anchor: _StrPath, unreadable: list[str] | None = None) -> list[str]:
    """Central bodies that NO curated level in the tree points at - the invisible orphans: loaded
    by nothing, yet the slug is 'taken' so a plain `add` used to refuse re-creating it.

    Returns a sorted list: a flat body as its slug, then a pre-pivot sharded body as
    `<shard>/<uuid>` - a legacy pointer names it by uuid, so it dangles when no pointer carries
    that uuid. Listing only `facts/*.md` left every sharded body out, dangling or not.

    A store directory that cannot be listed raises `TreeWalkError`, unless `unreadable` is a list,
    which then receives its path instead."""
    flat, sharded = store_bodies(us.central_facts_dir(Path(anchor)), unreadable)
    pointed: set[str] = set()
    legacy: set[str] = set()
    for lvl in _all_curated_levels(anchor):
        entries = ME.read_store(str(lvl))[1]
        pointed |= {e.slug for e in entries}
        legacy |= {e.uuid for e in entries if e.legacy}
    return sorted(flat - pointed) + sorted(rel for uuid, rel in sharded.items()
                                           if uuid not in legacy)


def _is_sharded_body_name(name: str) -> bool:
    """True for a `find_dangling_bodies` name that is a pre-pivot `<shard>/<uuid>` body."""
    return "/" in name


# An absolute path mentioned in a fact body. Deliberately conservative: a path is only evidence
# of subject when it is absolute and long enough to resolve to a tree.
#
# All three shapes, not just the POSIX one: a body captured on Windows names "C:\dir\repo\x.py"
# or a UNC share, neither of which starts with '/', so the detector matched NOTHING there and
# find_misplaced returned [] for every store - reported as "TOTAL misplaced: 0", which reads as
# a clean tree rather than as a check that cannot fire.
#
# The drive alternative is written FIRST on purpose: "C:/dir/repo/x.py" also contains the POSIX
# shape "/dir/repo/x.py", and matching that substring would resolve a DIFFERENT path than the
# one the body names. Leaving the Windows shapes enabled on POSIX too costs nothing - a path
# that does not resolve to an anchor is skipped a few lines below - and keeps this testable
# from either platform. What is skipped on POSIX is a Windows shape itself (`_names_a_path_here`):
# it is not absolute there, so resolving it read it relative to the cwd and filed it under the
# cwd's tree.
_ABS_PATH_RX = re.compile(
    r"([A-Za-z]:[\\/][\w.@+-]+(?:[\\/][\w.@+-]+){1,}"      # C:\dir\repo\x.py  /  C:/dir/repo/x.py
    r"|\\\\[\w.@+-]+(?:\\[\w.@+-]+){2,}"                    # \\server\share\repo\x.py
    r"|/[\w.@+-]+(?:/[\w.@+-]+){2,})"                       # /dir/repo/x.py
)


def find_misplaced(anchor: _StrPath) -> list[Misplaced]:
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
    out: list[Misplaced] = []
    for lvl in ME.curated_levels_under(str(anchor_r)):
        _scope, entries, bodies = ME.read_store(lvl)
        for e in entries:
            body = bodies.get(e.slug) or ""
            foreign: dict[str, list[str]] = {}
            own = 0
            for m in _ABS_PATH_RX.finditer(body):
                p = m.group(1)
                if not _names_a_path_here(p):
                    continue
                found = us.resolve_anchor(p) or _existing_ancestor_anchor(p)
                if found is None:
                    continue
                a = Path(found).resolve()
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


def _names_a_path_here(path: str, os_name: str = os.name) -> bool:
    r"""True when `path` can name a file on this OS: everything on Windows, and on POSIX all but a
    drive or UNC shape (`C:\dir\x.py`, `\\server\share\x.py`). On POSIX those are not absolute,
    so resolving one read it relative to the cwd: a body citing a Windows path was attributed to
    whatever tree the audit ran from, a false misplacement from another tree's cwd and a hidden
    one (its own-tree mention outvoting the real foreign path) from this tree's."""
    return os_name == "nt" or not ntpath.splitdrive(path)[0]


def _existing_ancestor_anchor(path: str) -> Path | None:
    """Anchor for the nearest EXISTING ancestor of `path` (a body cites files, not just dirs)."""
    p = Path(path)
    for cand in [p] + list(p.parents):
        if cand.exists():
            return us.resolve_anchor(str(cand))
    return None


def find_decoy_anchors(anchor: _StrPath, unreadable: list[str] | None = None) -> list[str]:
    """Every `.claude-memory` store dir STRICTLY BELOW the tree top - a DECOY anchor. resolve_anchor
    always returns the TOPMOST ancestor carrying CLAUDE.md + a store, so any store dir deeper in the
    tree is dead to the engine, yet the `CLAUDE.local.md` walk-up retrieval text resolves a
    below-level slug to that NEARER store FIRST and reads a stale or empty-stub body. A migration
    that centralizes bodies to the top must delete the drained sub-stores; this flags one it left
    behind. Backup dirs (`<store>-*`, e.g. `-migration-backup-...`) and any store nested inside them
    are NOT decoys - they are in no level's ancestor chain - so descent prunes them. Neither is a
    store inside the dream's own backup root: that lives at `~/.claude/self-improve-audit/`, which
    is INSIDE the `~/.claude` tree, so every snapshotted store there reads as a decoy (measured: 26
    of them). Prune it by RESOLVED PATH, never by dirname, so a project owning a `self-improve-audit/`
    dir of its own is still walked. Returns sorted absolute paths; empty is the healthy answer
    (exactly one store per tree, at the top).

    `unreadable`, when a list, receives the path of every directory the walk could not list: a
    plain os.walk skips one in silence, so a decoy (or a whole level) behind it reads as absent."""
    top = Path(anchor).resolve()
    audit_root = sig.audit_dir().resolve()
    found: list[str] = []

    def _note(exc: OSError) -> None:
        if unreadable is not None:
            unreadable.append(str(getattr(exc, "filename", None) or exc))

    for root, dirs, _files in os.walk(str(top), onerror=_note):
        rootp = Path(root)
        for d in dirs:
            if d == us.STORE_DIRNAME and rootp.resolve() != top:
                found.append(str(rootp / d))
        # never descend into a store, a backup/variant dir (`<store>-*`), a vendored dir, or the
        # dream's own backup root
        dirs[:] = [d for d in dirs
                   if not us.is_non_level_dirname(d) and (rootp / d).resolve() != audit_root]
    return sorted(found)


# ---- facts placed by topic (render-topics) ------------------------------------------------------

# The repair the placement findings name, as the engine's own refusals name their routes: the
# engine script path below the plugin dir, then the verb. Run as given it goes through.
_RENDER_ROUTE = "hooks/memory_engine.py render-topics --proj %s --scope %s"


def render_drift(anchor: _StrPath) -> tuple[list[_DriftRow], str]:
    """([(level, missing, differing, extra, example slugs)], refused) for `anchor`'s tree: what a
    `render-topics --scope tree` would change, read from its dry run, so the check and the
    renderer cannot disagree. Per level with a few examples, never one row per fact. `refused` is
    the reason the render could not be computed at all (a TOPICS line that does not parse, a tree
    top with no pointer block, a damaged topic file, a level over the block limit, a file the dry
    run could not read past `check_tree`'s own reads), else ''. The dry run takes no lock, so a
    read-only tree or a peer's held lock checks like any other. A tree with no topic list has no
    drift. Raises TreeWalkError when a level file or body cannot be read (the CLI exits 2 on
    it); `check_tree` reads every one of them first and does not call this when one failed."""
    try:
        rep = ME.render_topics(str(anchor), scope="tree", dry_run=True)
    except (ME.TopicRefusal, ME.topic_store.TopicStoreError, ME.tp.InvalidTopic) as exc:
        return [], str(exc) or type(exc).__name__
    except OSError as exc:                         # a file gone or unreadable between the reads
        return [], "the dry run could not read a store file (%s)" % (
            str(exc) or type(exc).__name__)
    rows: list[_DriftRow] = []
    for level in sorted(rep.levels):
        row = rep.levels[level]
        examples = sorted({slug for slugs in row.examples.values() for slug in slugs})[:5]
        rows.append((level, row.added, row.refreshed, row.removed, examples))
    return rows, ""


class _TreePins:
    """The slugs with a pinned or legacy line at any level of a tree (the engine's
    `unplaceable_slugs`), read on first use per anchor: one tree walk, one record per such
    pointer. Such a fact is never placed by topic."""

    def __init__(self) -> None:
        self._by_anchor: dict[str, set[str]] = {}

    def __call__(self, anchor: _StrPath) -> set[str]:
        key = str(anchor)
        if key not in self._by_anchor:
            self._by_anchor[key] = ME.unplaceable_slugs(ME.curated_levels_under(key))
        return self._by_anchor[key]


def placed_by_topic(anchor: _StrPath, slug: str, pins: _PinsPort) -> bool:
    """True when the renderer manages `slug` (the engine's own test): its body carries a non-empty
    `topics:` line and the title and description a line is built from, and no level pins it or
    holds a legacy line of it (`pins(anchor)`, asked only for such a body). Its lines then stand wherever the levels' topics
    place them, at levels a citing fact's chain need not include. Reads one body head."""
    if not us.is_valid_slug(slug):
        return False
    head = ME.read_body_head(us.body_path(anchor, slug))
    if head is None or ME.managed_topics(slug, head, ()) is None:
        return False
    return slug not in pins(anchor)


def _level_pointers(level: _StrPath) -> list[us.Pointer]:
    return us.parse_pointer_index(ME.read_store_text(sig.claude_local_md_path(level)))[1]


def _levels_above(level: Path, anchor: Path) -> list[Path]:
    """The curated levels above `level` up to the tree top, narrow to broad: found lexically, as
    the engine's chain render finds its chain. [] when `level` is the top or not below it."""
    if anchor not in level.parents:
        return []
    out: list[Path] = []
    for up in level.parents:
        if is_curated(up):
            out.append(up)
        if up == anchor:
            break
    return out


def chain_repeats(dirs: Iterable[_StrPath]) -> list[tuple[str, str, str]]:
    """[(slug, level, level above)] for every topic-placed line at one of `dirs` that a level
    above it also holds: both are read in the same session, so the lower copy is surplus
    (`render-topics --scope chain` from that level drops it). A fact pinned at any level, or one
    the renderer does not manage, is not placed by topic and is left to --check-tree. Holds the
    slugs of one level above at a time."""
    pins = _TreePins()
    out: set[tuple[str, str, str]] = set()
    for d in _narrow_to_broad([Path(d) for d in dirs]):
        if not is_curated(d):
            continue
        here = Path(os.path.abspath(str(d)))
        anchor = Path(os.path.abspath(str(ME.anchor_dir(str(here)))))
        mine = [p.slug for p in _level_pointers(here) if not p.legacy]
        for upper in _levels_above(here, anchor) if mine else []:
            held = {p.slug for p in _level_pointers(upper)}
            for slug in mine:
                if slug in held and placed_by_topic(anchor, slug, pins):
                    out.add((slug, str(here), str(upper)))
    return sorted(out)


def check_tree(anchor: _StrPath) -> TreeReport:
    """Tree-wide integrity over EVERY curated level under `anchor` (SIBLINGS included) - the checks
    the chain-scoped `--check` structurally cannot make: a slug pointed at from more than one level
    (slugs are TREE-unique, so any duplicate is a violation heal never sees), a pointer whose central
    body is missing, a `[[ref]]` that resolves NOWHERE in the tree, and central bodies no level points
    at. Only levels anchored at THIS anchor count (a nested independent tree is separate). Returns a
    report dict; `duplicates`/`orphan_pointers`/`orphan_refs` are the HARD problems."""
    top = ME.anchor_dir(str(anchor))
    anchor_res = Path(top).resolve()
    unreadable: list[str] = []                  # a report names what it could not check
    levels = [lvl for lvl in _all_curated_levels(top, unreadable=unreadable)
              if Path(ME.anchor_dir(lvl)).resolve() == anchor_res]
    slug_levels: dict[str, list[str]] = {}      # canonical slug -> [level dirs pointing at it]
    orphan_pointers: list[tuple[str, str]] = []  # (level, slug) whose central body is missing
    all_targets: set[str] = set()               # every slug offered anywhere in the tree
    tagged: set[str] = set()                    # canonical slugs: renderable topic-bound
    pinned: set[str] = set()                    # canonical slugs: pinned or legacy somewhere
    ref_sources: list[tuple[str, str, str]] = []  # (level, source_slug, ref_slug)
    for lvl in levels:
        try:
            _scope, entries, bodies = ME.read_store(lvl)
        except ME.TreeWalkError as exc:             # a level file or one of its bodies
            unreadable.append(exc.path)
            continue
        for e in entries:
            cslug = _canon(e.slug)
            slug_levels.setdefault(cslug, []).append(lvl)
            all_targets.add(cslug)
            if e.pin or e.legacy:           # the engine's rule: such a fact is never placed
                pinned.add(cslug)
            if not e.legacy and ME.managed_topics(e.slug, bodies.get(e.slug, ""), ()) is not None:
                tagged.add(cslug)
            body_p = us.legacy_body_path(top, e.uuid) if e.legacy else us.body_path(top, e.slug)
            if not body_p.is_file():
                orphan_pointers.append((lvl, e.slug))
            cited = ME.mask_code_regions(e.hook + "\n" + bodies.get(e.slug, ""))
            for m in _WIKILINK_RX.finditer(cited):
                ref = _ref_slug(m.group(1))
                if ref and ref != cslug:
                    ref_sources.append((lvl, e.slug, ref))
    # A MANAGED fact (topic-bound, no line pinned or legacy) has one line per level it is placed at: those
    # copies are the renderer's, and `render_drift` below says whether they are the right ones.
    managed = tagged - pinned
    duplicates = {s: sorted(lv) for s, lv in slug_levels.items() if len(lv) > 1 and s not in managed}
    orphan_refs = sorted(set((lvl, s, r) for (lvl, s, r) in ref_sources if r not in all_targets))

    # Downward/sideways refs: the target EXISTS in the tree but at NO level on the citing fact's
    # ancestor-or-self path, so the ref resolves "somewhere" (not an orphan) yet dangles for the
    # citing level's cascade - a fact citing a sibling subtree's slug, or a broad fact citing a
    # slug that lives below it. `[[refs]]` are upward-only; the chain-only `--check` catches these
    # per chain, but tree-wide `--check-tree` must too (it saw only the nowhere-resolving orphans).
    def _reachable(ref_canon: str, citing_level: str) -> bool:
        if ref_canon in managed:
            # placed by topic: where its lines stand follows the levels' topics, not the citer,
            # and the ref resolves through the central body wherever they are
            return True
        cl = Path(citing_level).resolve()
        for t in slug_levels.get(ref_canon, ()):
            tr = Path(t).resolve()
            if tr == cl or tr in cl.parents:            # target at-or-above the citer -> upward, OK
                return True
        return False
    sideways_refs = sorted(set((lvl, s, r) for (lvl, s, r) in ref_sources
                               if r in all_targets and not _reachable(r, lvl)))
    decoys = find_decoy_anchors(top, unreadable=unreadable)
    frame_only = find_frame_only_bodies(top, unreadable=unreadable)
    appended = find_appended_type_damage(top, unreadable=unreadable)
    # With a level unreadable the render cannot be computed either; that finding already fails.
    drift: list[_DriftRow] = []
    refused = ""
    if not unreadable:
        drift, refused = render_drift(top)
    # A body pointed at only from a level that could not be read would list as dangling, and
    # --rehome would then re-attach a fact that still has a pointer - so with anything unreadable
    # the danglers are not assessed; the unreadable finding already fails the run.
    danglers: list[str] = [] if unreadable else find_dangling_bodies(top, unreadable=unreadable)
    if unreadable:
        danglers = []                           # a store dir the listing itself could not read
    return {"anchor": str(top), "levels": len(levels), "duplicates": duplicates,
            "render_drift": drift, "render_refused": refused,
            "orphan_pointers": sorted(orphan_pointers), "orphan_refs": orphan_refs,
            "sideways_refs": sideways_refs, "danglers": danglers,
            "decoy_anchors": decoys, "unreadable_dirs": sorted(set(unreadable)),
            "frame_only_bodies": frame_only, "appended_type_damage": appended}


def find_frame_only_bodies(anchor: _StrPath, unreadable: list[str] | None = None) -> list[str]:
    """Slugs whose central body is its frontmatter frame and nothing else.

    Every other tree check passes such a fact: the pointer resolves, the body FILE exists, the slug
    is unique and the frame is well formed. Only the content is absent - so the always-loaded hook
    promises a rule and the walk-up retrieval it advertises delivers an empty file. The engine now
    refuses to create one, but stores written before that still carry them.

    Checks both layouts via `store_bodies` (the same helper `find_dangling_bodies` uses): a flat
    body is reported by its slug, a pre-pivot sharded body as `<shard>/<uuid>` - listing only
    `facts/*.md` left every sharded body out, frame-only or not.

    A body that cannot be read or is not UTF-8 raises `TreeWalkError`, unless `unreadable` is a
    list, which then receives its path: skipping it in silence reported it as not frame-only."""
    out: list[str] = []
    facts = us.central_facts_dir(Path(anchor))
    if not facts.is_dir():
        return out
    flat, sharded = store_bodies(facts, unreadable)
    items = sorted((facts / (slug + ".md"), slug) for slug in flat)
    items += sorted((facts / (rel + ".md"), rel) for rel in sharded.values())
    for p, name in items:
        try:
            raw = ME.read_store_text(p)
        except ME.TreeWalkError as exc:
            if unreadable is None:
                raise
            unreadable.append(exc.path)
            continue
        if not _content_after_frontmatter(raw).strip():
            out.append(name)
    return out


# A leading frontmatter block: an opening `---` line, any lines, then a CLOSING `---` line. Without
# the closing delimiter the text is not frontmatter at all - a body that merely opens with a
# horizontal rule used to be read as an unterminated frame and reported frame-only.
_FRONTMATTER_RX = re.compile(r"---[ \t]*\n(?:.*?\n)?---[ \t]*(?:\n|\Z)", re.S)


def _content_after_frontmatter(raw: str) -> str:
    """`raw` with its leading frontmatter block removed; the whole text when there is none.
    Matched to the FIRST closing delimiter, so a payload holding its own `---` rule survives."""
    m = _FRONTMATTER_RX.match(raw)
    return raw[m.end():] if m else raw


# The damage a re-type did before the frontmatter test required a CLOSED block with a `name:` key:
# it asked only `lstrip().startswith("---")`, so a body that merely opened with a markdown rule was
# taken for a frame and `\nmetadata:\n  type: <kind>` was appended to its prose, right before the
# prose's next `---` line or at its very end. Anchored to the end of that span, so a `metadata:`
# line anywhere else is the author's text.
_APPENDED_TYPE_RX = re.compile(r"\r?\nmetadata:\r?\n  type: (\S+)[ \t]*\Z")


def appended_type_damage(raw: str) -> tuple[str, str] | None:
    """(prose, kind) when `raw` carries the appended-type damage, else None. PURE.

    The damaged span is the text before the first `---` line after the opening rule (or the whole
    text when there is none); it must end in the appended block, and `kind` must be one of the four
    kinds, or it is not this damage. Also found under a real frame, which a later re-type puts on
    top of a damaged body. `prose` is the text with only the appended block removed."""
    head, m = ME.split_frontmatter(raw)
    content = (head[m.end():] if m else head).lstrip()
    if not _FRONTMATTER_OPEN_RE.match(content) or ME.split_frontmatter(content)[1] is not None:
        return None
    end = content.find("\n---", 3)
    front, rest = (content[:end], content[end:]) if end > 0 else (content.rstrip(), "")
    t = _APPENDED_TYPE_RX.search(front)
    if t is None or t.group(1) not in _TYPE_PREFIXES:
        return None
    return front[:t.start()] + rest, t.group(1)


def find_appended_type_damage(anchor: _StrPath, unreadable: list[str] | None = None) -> list[str]:
    """Names of the bodies in `anchor`'s store carrying `appended_type_damage`: a flat body by its
    slug, a sharded one as `<shard>/<uuid>`. A body that cannot be read raises `TreeWalkError`,
    unless `unreadable` is a list, which then receives its path."""
    facts = us.central_facts_dir(Path(anchor))
    if not facts.is_dir():
        return []
    flat, sharded = store_bodies(facts, unreadable)
    items = sorted((facts / (slug + ".md"), slug) for slug in flat)
    items += sorted((facts / (rel + ".md"), rel) for rel in sharded.values())
    out: list[str] = []
    for path, name in items:
        try:
            raw = ME.read_store_text(path)
        except ME.TreeWalkError as exc:
            if unreadable is None:
                raise
            unreadable.append(exc.path)
            continue
        if appended_type_damage(raw) is not None:
            out.append(name)
    return out


REPAIR_ATTEMPTS = 3
"""How often --repair-appended-type reads a damaged body and tries its write before it reports the
fact as skipped: each refusal means another writer changed the body in between (`BodyChanged`),
so a fact still changing after three reads is left for the next run rather than raced."""


class _Repair(NamedTuple):
    """What one damaged body's repair came to: `kind` when it was written, `why` when skipped,
    neither when the damage was gone on a read (another writer fixed or replaced the body)."""

    kind: str | None = None
    why: str | None = None


def _repair_one(level: str, top: Path, name: str, dry_run: bool,
                reread: Callable[[_StrPath], str]) -> _Repair:
    """Repair `name`'s body at `level` (see `repair_appended_type`): read it, derive the prose and
    the kind from that read, and write them only while the stored body is still that read."""
    for _attempt in range(REPAIR_ATTEMPTS):
        raw = reread(us.body_path(top, name))
        damage = appended_type_damage(raw)
        if damage is None:                       # repaired or rewritten since the scan: no damage
            return _Repair()
        prose, appended = damage
        kind = ME.body_type(raw) or appended
        if dry_run:
            return _Repair(kind=kind)
        try:
            # An empty title and hook with must_exist keep the ones stored when the level lock is
            # taken, so a retitle or hook change since the walk stands; expect_body refuses a
            # write derived from a body another writer has changed since this read.
            ME.upsert_entry(level, title="", hook="", body=prose, type_=kind, slug=name,
                            allow_pinned_overwrite=True, must_exist=True, expect_body=raw)
        except ME.UnknownSlug:
            return _Repair(why=f"its pointer left {level} after the scan - run the repair again")
        except ME.BodyChanged:
            continue
        return _Repair(kind=kind)
    return _Repair(why=f"its body kept changing while it was repaired ({REPAIR_ATTEMPTS} reads) - "
                       "run the repair again")


def repair_appended_type(anchor: _StrPath, dry_run: bool = False, *,
                         read: Callable[[_StrPath], str] | None = None
                         ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Re-frame every damaged body through the engine: the prose with the appended block removed,
    under a real frame carrying the kind (the real frame's own kind when the body has one, else the
    appended one). Title, hook and pin come from the pointer and are kept: the write is the
    engine's update-only upsert (`must_exist`), which reads the title and hook under the level
    lock it writes under. Passing the title and hook read at the start of this walk wrote them
    back over a retitle or a hook change that landed in between.

    Returns (repaired [(slug, kind)], skipped [(name, why)]). A body no pointer names, or a sharded
    one, is skipped: there is no title or hook to re-frame it with. So is a fact whose line left
    its level after the walk read it (moved or archived): the update-only write refuses it rather
    than create it anew. A body whose damage is gone when it is read again (a writer changed it
    after the scan) needs no repair: it is neither repaired nor skipped, and nothing is written
    for it. The new body and kind are derived from that read, so the write refuses a body changed
    since (`expect_body`) and the body is read again, up to `REPAIR_ATTEMPTS` reads; a body still
    changing after the last is skipped.

    `read` is the seam the body is re-read through (the engine's `read_store_text` when omitted),
    resolved at call time."""
    reread = read or ME.read_store_text
    top = Path(anchor)
    owners: dict[str, str] = {}
    for lvl in _all_curated_levels(top):
        for e in ME.read_store(str(lvl))[1]:
            owners.setdefault(e.slug, lvl)
    repaired: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    for name in find_appended_type_damage(top):
        if _is_sharded_body_name(name) or name not in owners:
            skipped.append((name, "no pointer names this body - re-home it first (--rehome)"))
            continue
        done = _repair_one(owners[name], top, name, dry_run, reread)
        if done.why is not None:
            skipped.append((name, done.why))
        elif done.kind is not None:
            repaired.append((name, done.kind))
    return repaired, skipped


def rehome_pointer(anchor: _StrPath, slug: str) -> us.Pointer:
    """The pointer line a re-home writes for the dangling body `slug`: its hook from the body's
    `description:`, its title from the body's `title:`. Only a body written before titles were
    kept as data has none, and then the title is derived from the slug - the stored one, when
    there is one, is the fact's own: deriving it anyway also overwrote it in the body, since every
    engine write keeps the two equal."""
    text = ME.read_store_text(us.body_path(anchor, slug))
    return us.Pointer(slug=slug, title=ME.body_title(text) or slug.replace("-", " "),
                      hook=ME.body_description(text))


def rehome_dangling_bodies(anchor: _StrPath, to_level: _StrPath | None = None, dry_run: bool = False) -> list[str]:
    """Re-attach a pointer for each dangling body at `to_level` (default: the anchor top) so it becomes
    visible + loadable again; a later dream re-levels it. The line is `rehome_pointer`'s. Returns the
    rehomed slugs.

    Every body `unrehomable_bodies` names is skipped - the engine would refuse its name, it is a
    sharded body with no slug to re-attach under, or it cannot be read - and the caller reports
    each one. Skipping them here, rather than raising, keeps one such body from stopping the
    re-home of every body after it."""
    top = Path(anchor)
    target = str(to_level or top)
    blocked = {name for name, _why in unrehomable_bodies(top)}
    done: list[str] = []
    for slug in find_dangling_bodies(top):
        if slug in blocked:
            continue
        line = rehome_pointer(top, slug)
        if not dry_run:
            # add with no body keeps the existing central body; Fix A re-adopts the dangling slug.
            # allow_over_cap_hook: a rehome MOVES a stored hook verbatim, so a legacy over-cap one
            # must travel with its fact rather than block the move.
            ME.add_or_update_entry(target, title=line.title, hook=line.hook, slug=slug,
                                   allow_over_cap_hook=True)
        done.append(slug)
    return done


def unrehomable_bodies(anchor: _StrPath) -> list[tuple[str, str]]:
    """[(name, why)] for each dangling body a re-home must not act on:

    * a pre-pivot sharded body (`<shard>/<uuid>`): it carries no slug, and making one up would
      mint a fact under a name nobody chose - it is reported for a person to read and re-capture;
    * a filename that is not a valid slug, so no pointer can name it until it is renamed;
    * a body that cannot be read or is not UTF-8: re-attaching it would put a pointer in the
      always-loaded index whose hook was never read."""
    top = Path(anchor)
    out: list[tuple[str, str]] = []
    for name in find_dangling_bodies(top):
        if _is_sharded_body_name(name):
            out.append((name, "a pre-pivot sharded body no pointer names; it carries no slug to "
                              "re-attach under - read it, then re-capture it with memory_engine "
                              "add, or move it to .claude-memory/.archive/"))
        elif not us.is_valid_slug(name):
            out.append((name, "its name is not a valid slug; rename the body file"))
        else:
            try:
                ME.read_store_text(us.body_path(top, name))
            except ME.TreeWalkError as exc:
                out.append((name, _walk_error_reason(exc)))
    return out


def _unreadable_line(path: str) -> str:
    """The --check-tree line for one path the check could not read: a level file, a fact body, or
    a directory. Only a FILE can be re-saved as UTF-8, so the advice follows what the path is."""
    p = Path(path)
    if p.name == "CLAUDE.local.md":
        return ("unreadable level file (not checked - fix its permissions, or re-save it as "
                "UTF-8): %s" % path)
    if p.is_file():
        return "unreadable fact body (not checked - fix its permissions, or re-save it as " \
               "UTF-8): %s" % path
    return "unreadable directory (not checked - fix its permissions): %s" % path


def _print_report(rep: ReconcileReport) -> None:
    print("curated dir: %s" % rep["dir"])
    print("  facts: %d | orphan pointers (no central body): %d" % (rep["facts"], len(rep["orphans"])))
    for slug in rep["orphans"]:
        print("    ! orphan (pointer line, no central body): %s" % slug)


def main(argv: Sequence[str] | None = None) -> int:
    """The CLI; exit codes are in the module docstring.

    TreeWalkError and OSError are mapped to 2 HERE, once, rather than in each mode: any read or
    write of the store can raise one, and a mode that forgot to catch it let a traceback exit 1 -
    the code for "problems found", so a store that could not be read passed for one with findings.
    --check-tree collects what it could not read instead, so every other finding is still
    reported, and then exits 2. A write mode under BITRANOX_MEMORY_WRITES=off (the engine refuses
    with MemoryWritesOff, a RuntimeError) is mapped here too: unmapped it was a traceback and exit 1.
    """
    try:
        return _main(argv)
    except sig.MemoryWritesOff as exc:
        print("! refused: %s" % exc, file=sys.stderr)
        return 2
    except ME.TreeWalkError as exc:
        print("! error: cannot read the memory store - %s" % exc, file=sys.stderr)
        return 2
    except OSError as exc:                  # a failed write (TimeoutError from a held lock is one)
        print("! error: %s" % exc, file=sys.stderr)
        return 2


def _main(argv: Sequence[str] | None = None) -> int:
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
                         "over-promoted to the whole tree. Exit 1 when a dangling body is sharded or "
                         "its filename is not a valid slug, which it names and cannot re-home; exit 2 "
                         "when one cannot be read")
    ap.add_argument("--rehome-to", metavar="LEVEL", default=None, dest="rehome_to",
                    help="with --rehome: re-attach the dangling bodies at LEVEL (a dir in the tree) "
                         "instead of the tree top - so a subtree's orphaned bodies land in that subtree")
    ap.add_argument("--archive", metavar="SLUG", default=None,
                    help="forget a fact: drop its pointer line at the given level (the positional dir) "
                         "and move its central body to .archive/ (only when no other level still "
                         "points at it)")
    ap.add_argument("--force", action="store_true",
                    help="with --archive: archive even while other facts or a CLAUDE.md still name "
                         "the slug (they are listed, and left pointing at nothing)")
    ap.add_argument("--check-tree", action="store_true", dest="check_tree",
                    help="TREE-WIDE integrity from any dir in the tree (resolved to its anchor): flags a "
                         "slug pointed at from >1 level (tree-unique violation), orphan pointers, refs "
                         "resolving nowhere, render drift of the facts placed by topic, and dangling "
                         "bodies - the cross-sibling problems --check "
                         "(chain-only) cannot see; exit 1 on any hard problem, 2 when a path could "
                         "not be read (every finding is still printed)")
    ap.add_argument("--check-misplaced", action="store_true", dest="check_misplaced",
                    help="TREE-WIDE wrong-tree audit: facts whose body cites ONLY another tree's "
                         "paths, i.e. captured in the wrong store (capture routes by cwd). Reports "
                         "candidates + the relocate command; never moves anything. Exit 1 if any")
    ap.add_argument("--repair-appended-type", action="store_true", dest="repair_appended_type",
                    help="one-off repair of the body damage --check-tree reports as an appended "
                         "`metadata: type:` block: re-frame each such body's prose through the "
                         "engine with that kind (title, hook and pin kept). --dry-run lists only. "
                         "Exit 1 when a damaged body could not be repaired (no pointer names it)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    # Absolutize ONCE at the boundary. A relative dir reached the level/anchor resolution in
    # several downstream paths and produced confident nonsense rather than an error: `--check .`
    # examined 0 refs and printed success, while `--check-tree .` invented 33 problems and labelled
    # every level "[.]". Both agreed with the absolute form the moment the input was resolved.
    args.dirs = [str(Path(d).resolve()) for d in args.dirs]
    # A typo'd path resolves to an empty tree, and every mode then printed its clean verdict
    # ("TOTAL tree problems: 0") with exit 0 - so a gate pointed at the wrong dir passed.
    missing = [d for d in args.dirs if not Path(d).is_dir()]
    if missing:
        for d in missing:
            print("! no such directory: %s" % d, file=sys.stderr)
        return 2

    if args.check_misplaced:
        anchor = ME.anchor_dir(args.dirs[0])
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
        level: str = args.dirs[0]
        found: Mentions | None = None
        anchor = ME.anchor_dir(level)
        # Only a LAST pointer leaves its mentions dangling; while another level still points at
        # the slug the fact survives, and listing its mentions would claim they now name nothing.
        # a slug that is no filename owns no body; archive_entry reports it as no entry
        others = (placed_copies(anchor, level, args.archive) if us.is_valid_slug(args.archive)
                  else [])
        if args.force and (others or not _other_levels_pointing(anchor, level, args.archive)):
            found = inbound_mentions(anchor, args.archive)
        try:
            removed = archive_entry(level, args.archive, dry_run=args.dry_run, force=args.force)
        except ArchiveBlocked as exc:
            print("! refused: %s - re-point or edit them first (ref_map.py lists [[refs]] and "
                  "prose mentions), or pass --force to archive anyway:" % exc)
            _print_mentions(exc.found)
            return 1
        except (ArchiveRollbackFailed, ArchiveIncomplete) as exc:
            print(f"! failed: could not archive {args.archive}: {exc}", file=sys.stderr)
            return 2
        except OSError as exc:
            # exit 2, not 1: 1 already means "no such entry", and a failed write is not that
            print("! failed: could not archive %s (%s) - its pointer and body are unchanged"
                  % (args.archive, exc), file=sys.stderr)
            return 2
        if removed:
            also = (" and at the %d other level(s) its topics place it at: %s"
                    % (len(others), ", ".join(others))) if others else ""
            if args.dry_run:
                print("would archive %s (pointer would be dropped at %s%s) - dry run, nothing written"
                      % (args.archive, level, also))
            else:
                print("archived %s (pointer dropped at %s%s)" % (args.archive, level, also))
            if found and (found["refs"] or found["prose"] or found["docs"]):
                print("--force: these still name %s and now point at nothing:" % args.archive)
                _print_mentions(found)
            return 0
        print("! no such entry: %s at %s (nothing archived)" % (args.archive, level))
        return 1

    if args.check_tree:
        rep = check_tree(ME.anchor_dir(args.dirs[0]))
        problems = 0
        print("tree integrity: %d curated level(s) under %s" % (rep["levels"], rep["anchor"]))
        for slug, lvls in sorted(rep["duplicates"].items()):
            print("    ! duplicate pointer: %s at %d levels -> %s"
                  % (slug, len(lvls), ", ".join(lvls)))
            problems += 1
        for level, missing, differing, extra, examples in rep["render_drift"]:
            print("    ! render drift: %s -> %d line(s) missing, %d differing from the body, %d "
                  "placed elsewhere (%s); %s repairs it"
                  % (level, missing, differing, extra, ", ".join(examples),
                     _RENDER_ROUTE % (rep["anchor"], "tree")))
            problems += 1
        if rep["render_refused"]:
            print("    ! the placement by topic could not be checked: %s" % rep["render_refused"])
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
        for slug in rep["frame_only_bodies"]:
            print("    ! frame-only body (frontmatter and nothing else; the pointer promises a rule "
                  "and the reader gets an empty file): %s" % slug)
            problems += 1
        for name in rep["appended_type_damage"]:
            print("    ! a `metadata: type:` block appended to a body that opens with a --- rule "
                  "and has no frame (run --repair-appended-type, --dry-run first): %s" % name)
            problems += 1
        for path in rep["unreadable_dirs"]:
            print("    ! %s" % _unreadable_line(path))
            problems += 1
        for slug in rep["danglers"]:
            print("    ~ dangling body (no pointer at any level): %s" % slug)
        print("TOTAL tree problems: %d" % problems)
        if rep["danglers"]:
            print("TOTAL dangling bodies: %d (advisory - run with --rehome to re-attach them)"
                  % len(rep["danglers"]))
        if rep["unreadable_dirs"]:
            return 2                        # part of the tree could not be checked at all
        return 1 if problems else 0

    if args.repair_appended_type:
        anchor = ME.anchor_dir(args.dirs[0])
        repaired, skipped = repair_appended_type(anchor, dry_run=args.dry_run)
        for slug, kind in repaired:
            print("%s: %s (type %s)" % ("would repair" if args.dry_run else "repaired", slug, kind))
        for name, why in skipped:
            print("cannot repair: %s - %s" % (name, why))
        print("TOTAL %s: %d" % ("would repair" if args.dry_run else "repaired", len(repaired)))
        return 1 if skipped else 0

    if args.rehome:
        anchor = ME.anchor_dir(args.dirs[0])
        done = rehome_dangling_bodies(anchor, to_level=args.rehome_to, dry_run=args.dry_run)
        for slug in done:
            print("%s: %s" % ("would re-home" if args.dry_run else "re-homed", slug))
        print("TOTAL re-homed: %d" % len(done))
        if done:
            # The cost every re-home to a level is reported with: the bytes its lines add to
            # that level's always-loaded block (a dangling body has no line there yet).
            target = args.rehome_to or str(anchor)
            added = sum(ME.line_size(rehome_pointer(anchor, s)) for s in done)
            print("cost: %s %d byte(s) to the always-loaded pointer block at %s%s"
                  % ("would add" if args.dry_run else "added", added, target,
                     " (the tree top, loaded by every session in the tree)"
                     if Path(target).resolve() == Path(anchor).resolve() else ""))
        stuck = unrehomable_bodies(anchor)
        for name, why in stuck:
            print("cannot re-home: %s.md - %s" % (name, why))
        # a sharded body or a non-slug name is a finding for a person (1); anything else on the
        # list is a body that could not be READ, which is not an answer but a failure (2)
        unread = [n for n, _why in stuck if not _is_sharded_body_name(n) and us.is_valid_slug(n)]
        if unread:
            return 2
        return 1 if stuck else 0

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
        for slug, level, upper in refs["repeated"]:
            print("    ! repeated line: %s at %s is also held by %s above it; %s drops the "
                  "lower copy" % (slug, level, upper, _RENDER_ROUTE % (level, "chain")))
            problems += 1
        warnings = 0
        for d in args.dirs:
            if is_curated(d):
                within, lines, nbytes = over_cap(d)
                if not within:
                    print("    ~ warning: %s pointer block is %d bytes / %d lines - large always-loaded "
                          "index; shrink it in place (fold near-duplicates, trim long hooks) - lifting "
                          "a fact to a broader level loads it in more sessions, not fewer"
                          % (d, nbytes, lines))
                    warnings += 1
        danglers = find_dangling_bodies(ME.anchor_dir(args.dirs[0]))
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
    # exit 1 on an orphan, like every other mode that finds a hard problem: a pointer whose body
    # is gone is the same fault --check-tree fails on, and exit 0 here let a gate read it as clean
    return 1 if total_orphans else 0


def _reconfigure_stdout() -> None:
    """A cp1252 console (bare `python3` on Windows) crashed on a level path it could not encode,
    mid-report. Escape instead; guarded, since a replaced stream may not support reconfigure."""
    for stream in (sys.stdout, sys.stderr):
        # looked up, not called through TextIO: the declared stream type has no reconfigure, and
        # a replaced stream may lack it at run time
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass


if __name__ == "__main__":
    _reconfigure_stdout()
    sys.exit(main())
