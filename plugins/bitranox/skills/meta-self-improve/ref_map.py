#!/usr/bin/env python3
"""Map a fact's `[[refs]]` in both directions before you move it.

Placement is the one dream step that can silently break the store, and the engine only guards half
of it: `move` REFUSES a down-move that would dangle an INBOUND ref, but never looks at the OUTBOUND
refs the fact itself makes, so lifting a fact to a common ancestor strands every ref it makes to a
fact left below. Both questions are answered by the same map, and there was no tool for it.

For each slug this prints the level it sits at, every fact that references it (with that fact's
level), and every fact it references (with that fact's level, or `DANGLING` when the target exists
nowhere in the tree).

Read it as: a non-empty INBOUND list is what a down-move will be refused for; an OUTBOUND target
sitting BELOW the level you are lifting to is what will be stranded.

PROSE lists the facts that name the slug in plain text rather than as a `[[ref]]` - often on
purpose, because the target sits below the citer and a link would dangle. Nothing guards these:
archiving or renaming the target leaves the name stale, and `--check-tree` does not report them.
A mention is a hyphenated token that is exactly a known slug (canonical form), outside any
`[[...]]`; a slug with no hyphen is not searched for, since it is indistinguishable from a word.

`--moves FILE` judges a whole planned batch at once: FILE is JSON lines `{"slug", "to"[, "from"]}`
(levels as paths). Every inbound and outbound `[[ref]]` of every moved fact is judged against the
FINAL level of BOTH ends, so a mutually-citing pair lifted together is clean while a fact lifted
away from a target left below is a `stranded-outbound`, and a fact moved below one of its citers
is a `dangling-inbound` (a ref resolves only to the citer's own level or an ancestor). A `from`
that is not where the fact sits now is a `stale-from` (the plan was made against an older tree).
A fact the engine places by topic is not moved by a plan, whether it has one line or several: it
is a `placed-by-topic` conflict (its levels follow the levels' topics, and a ref to it resolves
through its body wherever they are). Any other fact with a line at several levels is a
`duplicate-pointer` one. The map names its other levels as `also at`.

Exit codes are format-independent: 0 every slug mapped cleanly, 1 at least one slug is unknown or
has a dangling ref, 2 the map could not be built at all (no store under the root, or a level file
or fact body that cannot be read - a partial map would under-report inbound refs). `--json` prints
the envelope `{ok, command, data, skipped}` on every exit; `ok` means "ran without error", so it is
true on 0 and 1 and false only on 2.

Refs resolve exactly as the engine resolves them (`[[slug|label]]`, `[[type:slug]]`, any case,
`_`/`-`/whitespace as one separator), and each fact's pointer hook is scanned beside its body.

    python3 ref_map.py --root <anchor> <slug> [<slug> ...] [--json]
    python3 ref_map.py --root <anchor> --moves <moves.jsonl> [--json]
"""

import argparse
import json
import re
import sys
from pathlib import Path

# the engine owns ONE code-masking reader, so ref_map and --check-tree cannot disagree about
# whether a given `[[x]]` is a reference or quoted syntax
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import memory_engine as ME  # noqa: E402
import uuid_store  # noqa: E402 - the engine's pointer parser, so a level holds what the engine reads

# reconcile_memory_index is this script's sibling in meta-self-improve/ (same dir, already on
# sys.path when this runs as a script or under its own conftest): its `_store_bodies` is the one
# place that enumerates BOTH body layouts (flat `facts/<slug>.md` and pre-pivot sharded
# `facts/<shard>/<uuid>.md`), already shared internally by find_dangling_bodies and
# find_frame_only_bodies, so this does not re-derive the sharded-directory rule a third time.
import reconcile_memory_index as _rmi  # noqa: E402

REF_RX = re.compile(r"\[\[([^\]]+)\]\]")


def canon(slug: str) -> str:
    """Canonical slug for MATCHING - the engine's own rule (`_`, `-` and whitespace are one
    separator, case folded), so ref_map and `move` cannot disagree about what a ref names."""
    return ME._canon_slug(slug)  # noqa: SLF001 - the engine owns the one canonical form


def _pointers(root: Path):
    """(level dir, [Pointer]) for every curated level under `root`, found by the ENGINE's walk.

    Its own rglob skipped only node_modules/.git, so a pointer block copied under a vendored dir
    (venv, site-packages, build) could claim a fact for the wrong level. Raises the engine's
    TreeWalkError when a level file cannot be read or is not UTF-8: skipping it made its facts read
    as DANGLING."""
    out = []
    for level in sorted(ME.curated_levels_under(root)):
        text = ME.read_store_text(Path(level) / "CLAUDE.local.md")
        out.append((level, [p for p in uuid_store.parse_pointer_index(text)[1] if not p.legacy]))
    return out


def read_levels(root: Path) -> dict[str, str]:
    """{canonical slug: level dir} for every pointer under `root`. A fact with a line at several
    levels (placed by topic, or a duplicate) is given its FIRST level in path order;
    `read_copies` has the rest."""
    levels: dict[str, str] = {}
    for level, pointers in _pointers(root):
        for p in pointers:
            levels.setdefault(canon(p.slug), str(level))
    return levels


def read_copies(root: Path) -> dict[str, list[str]]:
    """{canonical slug: [every level dir holding a line of it]} for the slugs held at more than
    one level, in path order."""
    held: dict[str, list[str]] = {}
    for level, pointers in _pointers(root):
        for p in pointers:
            held.setdefault(canon(p.slug), []).append(str(level))
    return {slug: levels for slug, levels in held.items() if len(levels) > 1}


def read_placed(root: Path, slugs) -> set[str]:
    """The members of `slugs` the engine places by topic (reconcile's test, the engine's rule): a
    topic-bound body with a title and description, pinned at no level. Its lines stand where the
    levels' topics put them, and a ref to it resolves through the central body wherever they
    are. Callers pass slugs that have a line (the engine's rule needs one); a slug with one line
    is judged like one with several. One body head per member of `slugs`."""
    if not slugs:
        return set()
    pinned = {p.slug for _level, pointers in _pointers(root) for p in pointers if p.pin}
    return {slug for slug in slugs
            if _rmi._placed_by_topic(root, slug, lambda _anchor: pinned)}  # noqa: SLF001


def read_hooks(root: Path) -> dict[str, str]:
    """{canonical slug: pointer hook text} for every pointer under `root`."""
    return {canon(p.slug): p.hook or "" for _level, pointers in _pointers(root) for p in pointers}


def _fact_texts(root: Path, hooks: dict[str, str]) -> dict[str, str]:
    """{canonical source: hook + body text} for every fact under `root`, sharded bodies included."""
    texts = dict(hooks)
    facts = root / ".claude-memory" / "facts"
    flat, sharded = _rmi._store_bodies(facts)  # noqa: SLF001 - the one body-enumeration helper
    for slug in sorted(flat):
        source = canon(slug)
        texts[source] = "%s\n%s" % (texts.get(source, ""), ME.read_store_text(facts / (slug + ".md")))
    for rel in sorted(sharded.values()):
        source = canon(rel)
        texts[source] = "%s\n%s" % (texts.get(source, ""), ME.read_store_text(facts / (rel + ".md")))
    return texts


def read_refs(root: Path, hooks=None,
              texts=None) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """(outbound, inbound) maps over each fact's pointer HOOK plus its central body, both keyed by
    canonical slug - the same text the engine's inbound scan reads, so a ref that survives only in
    the hook (the body's copy edited away) is still an edge. Raises the engine's TreeWalkError on
    a body that cannot be read or is not UTF-8, the same rule the engine's own inbound scan applies:
    dropping it reported a real inbound edge as absent, which is the answer that permits a move, and
    replacing its bad bytes could cut a ref in half.

    Also scans pre-pivot SHARDED bodies (`facts/<shard>/<uuid>.md`): the engine's own
    `inbound_ref_sources` (what `move` is refused on) reads a legacy pointer's body via
    `legacy_body_path`, so a ref sitting only in such a body's text is a real inbound edge - listing
    only `facts/*.md` made it invisible here while the engine still enforced it. A sharded body
    carries no slug of its own (legacy pointers are uuid-keyed), so it is keyed by the same
    `<shard>/<uuid>` pseudo-source `find_dangling_bodies` reports it as: it can be an OUTBOUND
    source but is never a valid `--root`-queried slug or ref TARGET."""
    if texts is None:
        texts = _fact_texts(root, read_hooks(root) if hooks is None else hooks)
    outbound: dict[str, list[str]] = {}
    inbound: dict[str, list[str]] = {}
    for source in sorted(texts):
        masked = ME.mask_code_regions(texts[source])
        targets = {ME._ref_slug(t) for t in REF_RX.findall(masked)}  # noqa: SLF001 - engine rule
        targets.discard(source)
        targets.discard("")
        outbound[source] = sorted(targets)
        for target in targets:
            inbound.setdefault(target, []).append(source)
    return outbound, {k: sorted(v) for k, v in inbound.items()}


def build(root: Path, slugs):
    """[{slug, level, inbound, outbound, unknown}] plus a flag for whether anything is wrong.
    Raises the engine's TreeWalkError when a level file or a fact body cannot be read or is not
    UTF-8, or a directory under the root cannot be listed."""
    levels = read_levels(root)
    copies = read_copies(root)
    texts = _fact_texts(root, read_hooks(root))
    outbound, inbound = read_refs(root, texts=texts)
    prose = _rmi.prose_mentions(texts, set(levels))
    entries, problems = [], False
    for raw in slugs:
        slug = canon(raw)
        known = slug in levels or slug in outbound
        if not known:
            problems = True
            entries.append({"slug": slug, "level": None, "unknown": True,
                            "inbound": [], "outbound": [], "prose": []})
            continue
        outs = []
        for target in outbound.get(slug, []):
            level = levels.get(target)
            if level is None:
                problems = True
            outs.append({"slug": target, "level": level})
        entries.append({
            "slug": slug,
            "level": levels.get(slug),
            "also_at": copies.get(slug, [])[1:],
            "unknown": False,
            "inbound": [{"slug": s, "level": levels.get(s)} for s in inbound.get(slug, [])],
            "outbound": outs,
            "prose": [{"slug": s, "level": levels.get(s)} for s in prose.get(slug, [])],
        })
    return entries, problems


class BadMoves(ValueError):
    """The --moves file cannot be read as a move plan."""


def read_moves(path: Path) -> list[dict]:
    """[{slug, to, from}] from a JSON-lines plan; blank and `#` lines skipped. Raises BadMoves."""
    rows = []
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise BadMoves("cannot read %s: %s" % (path, exc)) from exc
    for n, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise BadMoves("line %d of %s is not JSON: %s" % (n, path, exc)) from exc
        if not (isinstance(row, dict) and isinstance(row.get("slug"), str)
                and isinstance(row.get("to"), str)
                and isinstance(row.get("from", ""), str)):
            raise BadMoves('line %d of %s is not {"slug": str, "to": str[, "from": str]}' % (n, path))
        rows.append({"slug": canon(row["slug"]), "to": str(Path(row["to"]).resolve()),
                     "from": str(Path(row["from"]).resolve()) if row.get("from") else None})
    return rows


def _visible_from(target_level: str, citer_level: str) -> bool:
    """True when a fact at `target_level` is reachable from `citer_level`: the same level or an
    ancestor, which is the only direction the cascade loads."""
    t, c = Path(target_level), Path(citer_level)
    return t == c or t in c.parents


def judge_moves(root: Path, moves: list[dict]):
    """(conflicts, problems) for a planned batch, every ref judged at the FINAL levels. Raises the
    engine's TreeWalkError like `build`."""
    # read_moves resolves every target, so the levels must be resolved too: compared as given, a
    # relative or symlinked --root put every citer outside every resolved target.
    levels = {slug: str(Path(level).resolve()) for slug, level in read_levels(root).items()}
    copies = {slug: [str(Path(level).resolve()) for level in held]
              for slug, held in read_copies(root).items()}
    # every moved slug is tested, not only one with several lines: the engine's move refuses a
    # placed fact whatever its line count, so a one-line one reported clean here was then refused
    placed = read_placed(root, set(copies) | {mv["slug"] for mv in moves if mv["slug"] in levels})
    outbound, inbound = read_refs(root)
    final = dict(levels)
    conflicts = []
    for mv in moves:
        if mv["slug"] in copies or mv["slug"] in placed:
            # the engine refuses to move a fact its topics place, and a move of a duplicate (one
            # line per level) takes one line and leaves the other
            kind = "placed-by-topic" if mv["slug"] in placed else "duplicate-pointer"
            conflicts.append({"kind": kind, "slug": mv["slug"], "other": None,
                              "slug_level": levels[mv["slug"]], "other_level": None})
            continue
        cur = levels.get(mv["slug"])
        if cur is None:
            conflicts.append({"kind": "unknown", "slug": mv["slug"], "other": None,
                              "slug_level": None, "other_level": None})
            continue
        if mv["from"] and cur != mv["from"]:
            conflicts.append({"kind": "stale-from", "slug": mv["slug"], "other": None,
                              "slug_level": cur, "other_level": mv["from"]})
        final[mv["slug"]] = mv["to"]
    for mv in moves:
        slug = mv["slug"]
        if slug not in levels or slug in copies or slug in placed:
            continue
        here = final[slug]
        for target in outbound.get(slug, []):
            there = final.get(target)
            if target in placed:
                continue                          # resolved through the central body, not a level
            if any(_visible_from(copy, here) for copy in copies.get(target, ())):
                continue                          # a duplicate: one of its lines is on this chain
            if there is not None and not _visible_from(there, here):
                conflicts.append({"kind": "stranded-outbound", "slug": slug, "other": target,
                                  "slug_level": here, "other_level": there})
        for citer in inbound.get(slug, []):
            # a citer with lines at several levels is read at each of them
            for there in copies.get(citer) or [final.get(citer)]:
                if there is not None and not _visible_from(here, there):
                    conflicts.append({"kind": "dangling-inbound", "slug": slug, "other": citer,
                                      "slug_level": here, "other_level": there})
    return conflicts, bool(conflicts)


def render_moves(moves, conflicts, out) -> None:
    print("%d planned move(s), %d conflict(s) judged at the final levels" % (len(moves),
                                                                              len(conflicts)),
          file=out)
    for c in conflicts:
        print("  %-18s %s @ %s  <->  %s @ %s" % (c["kind"], c["slug"], c["slug_level"] or "?",
                                                 c["other"] or "-", c["other_level"] or "-"),
              file=out)


def render(entries, out) -> None:
    for entry in entries:
        print("=" * 78, file=out)
        if entry["unknown"]:
            print("%s\n  UNKNOWN: no pointer and no body anywhere under the root" % entry["slug"],
                  file=out)
            continue
        print("%s\n  level    : %s" % (entry["slug"], entry["level"] or "NO POINTER"), file=out)
        if entry.get("also_at"):
            print("  also at  : %s  (a line per level: placed by topic, or a duplicate "
                  "--check-tree names)" % ", ".join(entry["also_at"]), file=out)
        print("  inbound  : %d  (a down-move is REFUSED while this is non-empty)"
              % len(entry["inbound"]), file=out)
        for ref in entry["inbound"]:
            print("      <- %s  @ %s" % (ref["slug"], ref["level"] or "?"), file=out)
        print("  outbound : %d  (move does NOT guard these - lifting strands any left below)"
              % len(entry["outbound"]), file=out)
        for ref in entry["outbound"]:
            print("      -> %s  @ %s" % (ref["slug"], ref["level"] or "DANGLING"), file=out)
        print("  prose    : %d  (bare-slug mentions, not [[refs]]: nothing guards these - "
              "archiving or renaming leaves them stale)" % len(entry.get("prose", [])), file=out)
        for ref in entry.get("prose", []):
            print("      ~ %s  @ %s" % (ref["slug"], ref["level"] or "?"), file=out)


def main(argv=None, out=None, err=None) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slugs", nargs="*", help="slugs to map (dashes or underscores)")
    parser.add_argument("--moves", default=None, metavar="FILE",
                        help='judge a planned batch: JSON lines {"slug", "to"[, "from"]}')
    parser.add_argument("--root", required=True, help="the tree anchor holding .claude-memory/")
    parser.add_argument("--json", action="store_true", help="machine-readable envelope")
    args = parser.parse_args(argv)
    if not args.slugs and not args.moves:
        parser.error("give one or more slugs, or --moves FILE")

    def _fail(error):
        if args.json:
            print(json.dumps({"ok": False, "command": "ref-map", "data": {"entries": []},
                              "skipped": [], "error": error}, indent=2), file=out)
        return 2

    root = Path(args.root)
    if not root.is_dir():
        print("ref_map: root does not exist: %s" % root, file=err)
        return _fail("root does not exist: %s" % root)
    if not (root / ".claude-memory" / "facts").is_dir():
        print("ref_map: no .claude-memory/facts under %s - is this the anchor?" % root, file=err)
        return _fail("no .claude-memory/facts under %s" % root)

    # The one place a read failure becomes exit 2. TreeWalkError is not an OSError, so catching
    # only OSError here let an undecodable level file escape as a traceback that exited 1 - the
    # code for "a slug is unknown or has a dangling ref".
    if args.moves:
        return _main_moves(args, root, out, err, _fail)
    try:
        entries, problems = build(root, args.slugs)
    except (OSError, ME.TreeWalkError) as exc:
        print("ref_map: cannot read %s - the map would be incomplete" % exc, file=err)
        return _fail("cannot read: %s" % exc)
    if args.json:
        # ok = "ran without error": an unknown slug or a dangling ref is the answer (exit 1)
        print(json.dumps({"ok": True, "command": "ref-map",
                          "data": {"entries": entries}, "skipped": []}, indent=2), file=out)
    else:
        render(entries, out)
    return 1 if problems else 0


def _main_moves(args, root, out, err, fail) -> int:
    """The --moves branch of main: exit 0 clean, 1 any conflict, 2 a plan or tree it cannot read."""
    try:
        moves = read_moves(Path(args.moves))
        conflicts, problems = judge_moves(root, moves)
    except BadMoves as exc:
        print("ref_map: %s" % exc, file=err)
        return fail(str(exc))
    except (OSError, ME.TreeWalkError) as exc:
        print("ref_map: cannot read %s - the judgement would be incomplete" % exc, file=err)
        return fail("cannot read: %s" % exc)
    if args.json:
        print(json.dumps({"ok": True, "command": "ref-map",
                          "data": {"moves": moves, "conflicts": conflicts}, "skipped": []},
                         indent=2), file=out)
    else:
        render_moves(moves, conflicts, out)
    return 1 if problems else 0


def _reconfigure_stdout() -> None:
    """A cp1252 console (bare `python3` on Windows) crashed on a level path it could not encode.
    Escape instead; guarded, since a replaced stream may not support reconfigure."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (ValueError, OSError):
            pass


if __name__ == "__main__":
    _reconfigure_stdout()
    raise SystemExit(main())
