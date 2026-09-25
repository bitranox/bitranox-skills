# /// script
# requires-python = ">=3.10"
# ///
"""Find memory pointer lines that assert STATUS - the claims that rot without anyone noticing.

Why: a pointer line in a `CLAUDE.local.md` memory index is ALWAYS-LOADED, while the thing it
asserts is owned by something else entirely - `TODO.md`, git, a planning doc's status section.
Nothing in the memory system watches that owner, so "shipped" / "not started" / "tracked as #34"
goes on being broadcast every turn long after it stopped being true. A stale hook is worse than
an absent one: it carries the authority of a durable lesson.

Measured on one chain, 2026-08-21: 55 of 390 pointer lines carried a status claim, and three
were confirmed rotted - one had contradicted the very document it cited for three weeks.

Two things this tool is careful about, both learned the hard way:

1. **Both polarities.** The first hand-rolled version searched only TODO-ish words. The commoner
   form is positive ("deployed", "shipped", "now folded into"), which outnumbered it 33 to 4, so
   that version under-reported the population by roughly an order of magnitude.
2. **A hit is a CANDIDATE, not a defect.** "Know this is already deployed, do not rebuild it" is
   often an entry's whole value. It is rot only when the OWNER disagrees, which a human checks
   per hit. The one exception is a SELF-CONTRADICTION - a slug saying "blocked" under a hook
   saying "superseded" - which needs no lookup and is reported separately as a finding.

Exit codes: 0 = no self-contradictions, 1 = at least one, 2 = error (no levels, a missing or
unreadable level, a --chain that is not a directory, a baseline `clear` cannot read or write).
The candidate list is informational and never on its own sets exit 1.

The baseline lives in the store the ENGINE uses (the topmost dir with a `CLAUDE.md` and a store,
see tree_support), never merely the nearest one.

Run (from the plugin root, via the launcher that forces UTF-8):
  `bash hooks/run-python.sh skills/meta-dream-tree/statusrot.py scan --chain /path/to/project`
  `bash hooks/run-python.sh skills/meta-dream-tree/statusrot.py scan --level a/CLAUDE.local.md --json`
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# The engine's pointer parser and anchor resolver, from the plugin's hooks dir:
# skills/<skill> -> skills -> bitranox. One parser, so this tool and the engine agree on which
# facts a level holds - including a dotted slug, which a hand-rolled [a-z0-9-]+ silently skips
# and so mistakes its body for an orphan.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import uuid_store  # noqa: E402

# tree_support is this script's sibling; a caller loading the script by path does not put this
# dir on sys.path the way running it directly does.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tree_support import store_anchor, utf8_stdio  # noqa: E402

PATTERNS: dict[str, re.Pattern[str]] = {
    "SHIPPED": re.compile(
        r"\b(shipped|deployed|landed|merged upstream|now folded|folded into|superseded|retired|"
        r"implemented|feature.complete|is fixed|now fixed|already (?:done|built|fixed))\b",
        re.IGNORECASE),
    "UNSTARTED": re.compile(
        r"\b(TODO|not started|unstarted|not yet (?:done|built|run|started)|still open|"
        r"planned,? not|pending implementation)\b", re.IGNORECASE),
    # An identifier whose meaning is owned elsewhere and renumbers or closes with no signal here.
    # The prefix is case-blind ("Tracked as #34" opens a sentence). A bare id may end a sentence:
    # a following '.' is allowed when nothing but whitespace or the end comes after it, which
    # still refuses "#34.5" and a colour like "#34ab".
    "ID_REF": re.compile(r"\b(?i:task |tracked as |issue )#\d+|(?<![\w.])#\d{1,4}\b(?!\w|\.\S)"),
    "BRANCH": re.compile(r"\b(?:feat|fix|perf|chore)-[a-z0-9][a-z0-9-]{2,}\b"),
}

# A slug asserting a BLOCKED state under a hook that explicitly REVERSES it. The slug is where
# rot survives longest: a name outlives every body edit, so title/hook/body get corrected and it
# does not (measured: dm-linux-hotadd-blocked-by-acpi-s4, whose hook had said SUPERSEDED for
# weeks).
#
# Deliberately ONE-DIRECTIONAL, and narrow on both sides. Measured on a live 391-line chain the
# looser version flagged 5 entries and every one was wrong, because:
#   * the opposite direction (slug says done, hook says blocked) has no true positives - a
#     "works"/"deployed"/"done" token in a slug names the SUBJECT ("re-train from the DEPLOYED
#     integration", "verify open vs done"), not an asserted state. That direction is gone.
#   * "fails"/"missing" in a slug is a TRIGGER condition, not a status
#     ("seed-winre-when-reagentc-enable-fails-1614"). Those tokens are gone.
#   * a bare positive word in a hook is not a reversal; only an explicit reversal marker is.
# Precision matters more than recall here because this is the one category that sets exit 1.
_SLUG_BLOCKED = re.compile(r"(?:^|-)(blocked|broken|todo|not-started|unstarted|unsupported)(?:-|$)")
_HOOK_REVERSAL = re.compile(
    r"\b(superseded|no longer|is now fixed|now fixed|turned out|refuted|"
    r"was a misdiagnosis|actually works|has since (?:shipped|been fixed))\b",
    re.IGNORECASE)


@dataclass(frozen=True)
class Pointer:
    level: str
    slug: str
    title: str
    hook: str


@dataclass
class ScanResult:
    total_pointers: int = 0
    by_kind: dict[str, list[Pointer]] = field(default_factory=dict)
    contradictions: list[tuple[Pointer, str]] = field(default_factory=list)
    distinct_flagged: int = 0


def parse_pointers(text: str, level: str = "") -> list[Pointer]:
    """Every pointer the engine reads from `text`, each slug once, the hook without its managed
    trailer (metadata, not part of the instruction the model reads).

    Legacy `uuid:` pointers are included: the engine still loads them, so their hooks are
    broadcast every turn like any other, and skipping them left their status claims unscanned.
    """
    return [Pointer(level, p.slug, p.title.strip(), p.hook)
            for p in uuid_store.parse_pointer_index(text)[1]]


def classify(ptr: Pointer) -> set[str]:
    """Which status-claim kinds this hook carries. Empty set = a pure mechanism hook."""
    return {kind for kind, rx in PATTERNS.items() if rx.search(ptr.hook)}


def self_contradiction(ptr: Pointer) -> str | None:
    """A slug asserting BLOCKED under a hook that explicitly reverses it - rot, no lookup needed.

    One direction only, and both sides narrow, because this is the category that sets exit 1.
    See the pattern comments for the five measured false positives that shaped it.
    """
    slug_hit = _SLUG_BLOCKED.search(ptr.slug)
    hook_hit = _HOOK_REVERSAL.search(ptr.hook)
    if slug_hit and hook_hit:
        return f"slug says {slug_hit.group(1)!r}, hook says {hook_hit.group(1)!r}"
    return None


def scan(levels: list[Path]) -> ScanResult:
    """Scan the given CLAUDE.local.md files.

    Raises OSError on a missing or unreadable level and UnicodeDecodeError on one that is not
    UTF-8; a BOM is accepted (utf-8-sig), since it would otherwise hide a pointer on line one.
    """
    result = ScanResult()
    flagged: set[str] = set()
    for path in levels:
        text = Path(path).read_text(encoding="utf-8-sig")
        for ptr in parse_pointers(text, level=Path(path).parent.name or str(path)):
            result.total_pointers += 1
            for kind in classify(ptr):
                result.by_kind.setdefault(kind, []).append(ptr)
                flagged.add(ptr.slug)
            why = self_contradiction(ptr)
            if why:
                result.contradictions.append((ptr, why))
    result.distinct_flagged = len(flagged)
    return result


def hook_digest(hook: str) -> str:
    """Identity of a hook's TEXT. The baseline is keyed on this, never on the slug alone, so an
    edited hook cannot keep an old verdict: change one character and it reads as unexamined."""
    return hashlib.sha256(hook.strip().encode("utf-8")).hexdigest()


def baseline_path(start: Path) -> Path | None:
    """Where this tree's verified-baseline lives, or None when the tree has no memory store.

    The file sits in the store beside the fact bodies it describes, so a hook edit and its
    re-clearing land in the same repo and diff together. Returned even when absent - the caller
    distinguishes "no store" (None, nothing to record against) from "not cleared yet".

    The store is the one the ENGINE uses (tree_support.store_anchor): a leftover store lower down
    the chain would otherwise receive the adjudications while the real one never sees them.
    """
    anchor = store_anchor(start, uuid_store.resolve_anchor)
    return None if anchor is None else anchor / ".claude-memory" / "statusrot-baseline.json"


class BaselineUnreadable(Exception):
    """The baseline file exists but is not one this tool wrote, so rewriting it would lose data."""


def _baseline_shape_error(blob: object) -> str | None:
    """Why `blob` is not a baseline `clear` can merge into without dropping anything. PURE."""
    if not isinstance(blob, dict):
        return f"the top level is {type(blob).__name__}, not an object"
    cleared = blob.get("cleared", {})
    if not isinstance(cleared, dict):
        return "its 'cleared' is not an object"
    bad = sorted(str(s) for s, rec in cleared.items() if not isinstance(rec, dict))
    return f"these records are not objects: {', '.join(bad)}" if bad else None


def read_baseline_strict(path: Path) -> dict[str, dict[str, str]]:
    """The cleared map for `clear`, or {} when the file does not exist yet.

    Raises BaselineUnreadable when it exists but cannot be read, is not JSON (a merge conflict
    left in it), or has a shape `clear` would not round-trip: rewriting it from empty would wipe
    every earlier human verdict and report success.
    """
    if not path.exists():
        return {}
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BaselineUnreadable(f"cannot read {path}: {exc}") from exc
    why = _baseline_shape_error(blob)
    if why:
        raise BaselineUnreadable(f"{path} is not a statusrot baseline: {why}")
    return dict(blob.get("cleared", {}))


def load_baseline(path: Path | None) -> dict[str, dict[str, str]]:
    """The cleared map, or empty. An unreadable or malformed baseline yields EMPTY, and a record
    that is not an object is dropped, never half-read: reporting an entry as unexamined is the
    safe direction to fail for a SCAN (clear uses read_baseline_strict instead)."""
    if path is None or not path.is_file():
        return {}
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    cleared = blob.get("cleared") if isinstance(blob, dict) else None
    if not isinstance(cleared, dict):
        return {}
    return {s: rec for s, rec in cleared.items() if isinstance(rec, dict)}


def cleared_digests(rec: dict) -> set[str]:
    """Every hook digest a baseline record vouches for.

    A slug held at more than one chain level has one hook per copy, and each copy is cleared on
    its own text, so a record may carry `hook_sha256s` beside the single `hook_sha256`.
    """
    out = {str(d) for d in rec.get("hook_sha256s") or [] if isinstance(d, str)}
    if isinstance(rec.get("hook_sha256"), str):
        out.add(rec["hook_sha256"])
    return out


def _flagged_digests(result: "ScanResult") -> dict[str, set[str]]:
    """slug -> the digests of EVERY flagged copy of it in scope."""
    seen: dict[str, set[str]] = {}
    for ptrs in result.by_kind.values():
        for p in ptrs:
            seen.setdefault(p.slug, set()).add(hook_digest(p.hook))
    return seen


def new_or_changed(result: "ScanResult", cleared: dict[str, dict[str, str]]) -> list[str]:
    """Flagged slugs that are unexamined: never cleared, or ANY copy's hook is not one cleared.

    Every copy counts. Keeping one digest per slug let the copy iterated last stand for all of
    them, so an edit to the other copy of a slug held at two levels read as still cleared.
    """
    return sorted(s for s, digests in _flagged_digests(result).items()
                  if s not in cleared or not digests <= cleared_digests(cleared[s]))




def _sweep_dates_by_level(cleared: dict[str, dict[str, str]]) -> dict[str, str]:
    """The most recent clear date recorded per level - i.e. when that level was last swept."""
    newest: dict[str, str] = {}
    for rec in cleared.values():
        level, when = rec.get("level"), rec.get("cleared")
        if not level or not when:
            continue
        if when > newest.get(level, ""):
            newest[level] = when
    return newest


def fact_added_on(store: Path | None, slug: str) -> str | None:
    """ISO date this fact's body first entered the store's git history, or None if unanswerable.

    None covers every failure alike - no store, not a repo, no git, a body whose add-commit sits
    under a pre-rename path - and the caller must read it as "still to check". An age nobody can
    establish must never buy an entry its way off the worklist.
    """
    if store is None or not (store / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(store), "log", "--follow", "--diff-filter=A",
             "--format=%ad", "--date=short", "--", f"facts/{slug}.md"],
            capture_output=True, text=True, timeout=20, check=False,
            encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
    dates = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    return dates[-1] if dates else None


def triage_pending(result: "ScanResult", cleared: dict[str, dict[str, str]],
                   pending: list[str], store: Path | None) -> dict[str, list[str]]:
    """Split the unexamined list into the three situations that all answer "nobody checked this".

    A flat UNEXAMINED list is accurate and its SHAPE misleads: a fact WRITTEN since the last sweep
    reads identically to one that has sat unchecked for months, so a reader sizes a backlog from a
    number that is mostly freshness. Measured 2026-09-03 on the softdev tree: of 22 pending, 7 were
    re-surfaced edits and 10 were written after the baseline, leaving 4 genuinely unchecked.

    Ties are broken toward MORE work: an entry whose age git cannot answer lands in never_checked.
    Keeping a sound entry on the worklist costs one re-read; filing an unchecked claim as freshness
    hides it permanently, which is the failure this whole file exists to prevent.
    """
    level_of: dict[str, str] = {}
    for ptrs in result.by_kind.values():
        for p in ptrs:
            level_of[p.slug] = p.level
    swept = _sweep_dates_by_level(cleared)
    buckets: dict[str, list[str]] = {"resurfaced": [], "written_since": [], "never_checked": []}
    for slug in pending:
        if slug in cleared:
            buckets["resurfaced"].append(slug)
            continue
        sweep = swept.get(level_of.get(slug, ""))
        added = fact_added_on(store, slug) if sweep is not None else None
        fresh = added is not None and sweep is not None and added > sweep
        buckets["written_since" if fresh else "never_checked"].append(slug)
    return buckets

def chain_levels(start: Path) -> list[Path]:
    """Every CLAUDE.local.md from `start` upward, narrowest first (the altitude chain)."""
    found: list[Path] = []
    cur = Path(start).resolve()
    while True:
        candidate = cur / "CLAUDE.local.md"
        if candidate.is_file():
            found.append(candidate)
        if cur.parent == cur:
            return found
        cur = cur.parent


def _clear_error(msg: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"ok": False, "command": "clear", "error": msg}, indent=2))
    else:
        print(f"error: {msg}", file=sys.stderr)
    return 2


def _record_cleared(result: "ScanResult", cleared: dict[str, dict[str, str]],
                    wanted: set[str], note: str) -> int:
    """Enter every flagged slug in scope (or the `wanted` ones) into `cleared`; return how many.

    A slug held at several levels is recorded with the digest of EVERY copy, so an edit to any
    one of them comes back. The level recorded is the narrowest copy's (the chain is walked
    narrow to broad), which is the one the triage dates its sweep by.
    """
    level_of: dict[str, str] = {}
    for ptrs in result.by_kind.values():
        for p in ptrs:
            level_of.setdefault(p.slug, p.level)
    today = dt.date.today().isoformat()
    added = 0
    for slug, digests in sorted(_flagged_digests(result).items()):
        if wanted and slug not in wanted:
            continue
        prior = cleared.get(slug)
        if prior and digests <= cleared_digests(prior):
            continue
        rec = {"level": level_of[slug], "hook_sha256": sorted(digests)[0],
               "cleared": today, "note": note}
        if len(digests) > 1:
            rec["hook_sha256s"] = sorted(digests)
        cleared[slug] = rec
        added += 1
    return added


def _do_clear(result: "ScanResult", bl_path: Path | None, args: argparse.Namespace) -> int:
    """Record the currently-flagged entries as verified - all of them, or the ones `--slug` names.

    Explicit by design: nothing enters the baseline as a side effect of scanning, because a verdict
    nobody made is the one that misleads. `--slug` exists for the normal mature-chain case, where a
    human adjudicates a SUBSET: without it the only moves are a bulk clear that falsely certifies
    the candidates nobody read, or losing the work. A name that matches no flagged candidate is
    REFUSED and nothing is written - a selector that silently records nothing reports a clean sweep
    while certifying neither the typo nor the entry it was aimed at.
    """
    if bl_path is None:
        return _clear_error("no .claude-memory store above the given level; "
                            "nothing to record against", args.json)
    wanted = set(getattr(args, "slug", []) or [])
    flagged = {p.slug for ptrs in result.by_kind.values() for p in ptrs}
    if wanted:
        missing = sorted(wanted - flagged)
        if missing:
            return _clear_error(
                "not a flagged candidate in this scope: " + ", ".join(missing)
                + " (nothing was written; run scan to see the candidates)", args.json)
    try:
        cleared = read_baseline_strict(bl_path)
    except BaselineUnreadable as exc:
        return _clear_error(f"{exc} - nothing was written; fix or remove it first, since "
                            "rewriting it would drop every earlier verdict", args.json)
    added = _record_cleared(result, cleared, wanted, args.note)
    try:
        bl_path.parent.mkdir(parents=True, exist_ok=True)
        bl_path.write_text(json.dumps({"version": 1, "cleared": cleared}, indent=2,
                                      sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return _clear_error(f"cannot write {bl_path}: {exc}", args.json)
    if args.json:
        print(json.dumps({"ok": True, "command": "clear",
                          "data": {"baseline": str(bl_path), "recorded": added,
                                   "total_cleared": len(cleared)}, "skipped": []}, indent=2))
    else:
        print(f"recorded {added} entr(ies) as verified; {len(cleared)} cleared in total\n{bl_path}")
    return 0


PENDING_KINDS: tuple[tuple[str, str, str], ...] = (
    ("resurfaced", "RE-SURFACED",
     "cleared once, hook EDITED since - re-read the edit, not the whole claim"),
    ("written_since", "WRITTEN SINCE the sweep",
     "newer than the last clear at its level - freshness, not rot"),
    ("never_checked", "NEVER CHECKED",
     "predates the sweep, or its age is unanswerable - the real backlog"),
)


def _render(result: ScanResult, pending: list[str], bl_path: Path | None,
            triage: dict[str, list[str]]) -> str:
    lines = [f"scanned {result.total_pointers} pointer line(s)", ""]
    if result.contradictions:
        lines.append(f"== SELF-CONTRADICTORY ({len(result.contradictions)}) - rot, no lookup needed ==")
        for ptr, why in result.contradictions:
            lines += [f"   [{ptr.level}] {ptr.slug}", f"        {why}"]
        lines.append("")
    for kind in PATTERNS:
        group = result.by_kind.get(kind, [])
        lines.append(f"== {kind}: {len(group)} candidate(s) ==")
        lines += [f"   [{p.level}] {p.slug}" for p in group]
        lines.append("")
    lines.append(
        f"{result.distinct_flagged} of {result.total_pointers} entries carry a status claim. "
        "These are CANDIDATES: a claim is rot only when its owner (TODO.md, git, the cited doc) "
        "disagrees. Check per hit; do not bulk-edit.")
    if bl_path is None or not bl_path.is_file():
        lines.append("No verified-baseline for this tree, so every candidate above is unexamined. "
                     "After checking them, record it with: statusrot.py clear --chain <dir>")
    elif pending:
        lines += ["", f"== UNEXAMINED since the baseline: {len(pending)} =="]
        for key, head, gloss in PENDING_KINDS:
            group = triage.get(key, [])
            if not group:
                continue
            lines.append(f"  -- {head}: {len(group)} - {gloss}")
            lines += [f"     {s}" for s in group]
        lines.append("The rest were cleared against their owners and their hooks are unchanged.")
    else:
        lines.append(f"Nothing new: every candidate was cleared and no hook has changed since. "
                     f"({bl_path})")
    return "\n".join(lines)


def _usage_error(args: argparse.Namespace, msg: str) -> int:
    """Exit 2 with the JSON envelope on stdout under --json, else an error line on stderr."""
    if args.json:
        print(json.dumps({"ok": False, "command": args.cmd, "error": msg}, indent=2))
    else:
        print(f"error: {msg}", file=sys.stderr)
    return 2


def _add_level_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--level", action="append", default=[], type=Path,
                   help="a CLAUDE.local.md to scan (repeatable)")
    p.add_argument("--chain", type=Path,
                   help="walk UP from this dir, scanning every CLAUDE.local.md found")
    p.add_argument("--json", action="store_true", help="emit a JSON envelope")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan", help="scan memory levels for status claims")
    _add_level_args(sc)
    cl = sub.add_parser("clear", help="record every currently-flagged entry as verified")
    _add_level_args(cl)
    cl.add_argument("--note", default="", help="one line on what the check established")
    cl.add_argument("--slug", action="append", default=[],
                    help="record only this slug (repeatable); omit to record every flagged entry "
                         "in scope. A slug that is not a flagged candidate is refused")
    utf8_stdio()
    args = ap.parse_args(argv)

    if args.chain and not Path(args.chain).is_dir():
        # A typo'd --chain would otherwise scan its ANCESTORS and exit 0 as if it were checked.
        return _usage_error(args, f"--chain {args.chain} is not an existing directory")
    # Resolved before the dedupe, so a relative --level and a --chain naming the same file are
    # one level, not two scans of it.
    levels: list[Path] = list(dict.fromkeys(Path(p).resolve() for p in args.level))
    if args.chain:
        levels += [p for p in chain_levels(args.chain) if p not in levels]
    if not levels:
        return _usage_error(args, "no levels given (--level or --chain)")

    try:
        result = scan(levels)
    except (OSError, UnicodeDecodeError) as exc:
        return _usage_error(args, str(exc))

    anchor = args.chain or levels[0].parent
    bl_path = baseline_path(anchor)
    if args.cmd == "clear":
        return _do_clear(result, bl_path, args)

    cleared = load_baseline(bl_path)
    pending = new_or_changed(result, cleared)
    triage = triage_pending(result, cleared, pending, bl_path.parent if bl_path else None)

    if args.json:
        print(json.dumps({
            "ok": True,
            "command": "scan",
            "data": {
                "total_pointers": result.total_pointers,
                "distinct_flagged": result.distinct_flagged,
                "contradictions": [
                    {"level": p.level, "slug": p.slug, "why": why} for p, why in result.contradictions
                ],
                "candidates": {
                    kind: [{"level": p.level, "slug": p.slug} for p in ptrs]
                    for kind, ptrs in result.by_kind.items()
                },
                "baseline": str(bl_path) if bl_path and bl_path.is_file() else None,
                "new_or_changed": pending,
                "pending_triage": triage,
            },
            "skipped": [],
        }, indent=2))
    else:
        print(_render(result, pending, bl_path, triage))
    return 1 if result.contradictions else 0


if __name__ == "__main__":
    sys.exit(main())
