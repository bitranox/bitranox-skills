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

Exit codes are format-independent: 0 every slug mapped cleanly, 1 at least one slug is unknown or
has a dangling ref, 2 the map could not be built at all (no store under the root, or a level file
or fact body that cannot be read - a partial map would under-report inbound refs).

Refs resolve exactly as the engine resolves them (`[[slug|label]]`, `[[type:slug]]`, any case,
`_`/`-`/whitespace as one separator), and each fact's pointer hook is scanned beside its body.

    python3 ref_map.py --root <anchor> <slug> [<slug> ...] [--json]
"""
from __future__ import annotations

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

REF_RX = re.compile(r"\[\[([^\]]+)\]\]")


def canon(slug: str) -> str:
    """Canonical slug for MATCHING - the engine's own rule (`_`, `-` and whitespace are one
    separator, case folded), so ref_map and `move` cannot disagree about what a ref names."""
    return ME._canon_slug(slug)  # noqa: SLF001 - the engine owns the one canonical form


def _pointers(root: Path):
    """(level dir, [Pointer]) for every curated level under `root`, found by the ENGINE's walk.

    Its own rglob skipped only node_modules/.git, so a pointer block copied under a vendored dir
    (venv, site-packages, build) could claim a fact for the wrong level. Raises OSError when a
    level file the walk found cannot be read: skipping it made its facts read as DANGLING."""
    out = []
    for level in sorted(ME.curated_levels_under(root)):
        path = Path(level) / "CLAUDE.local.md"
        text = path.read_text(encoding="utf-8", errors="replace")
        out.append((level, [p for p in uuid_store.parse_pointer_index(text)[1] if not p.legacy]))
    return out


def read_levels(root: Path) -> dict[str, str]:
    """{canonical slug: level dir} for every pointer under `root`."""
    return {canon(p.slug): str(level) for level, pointers in _pointers(root) for p in pointers}


def read_hooks(root: Path) -> dict[str, str]:
    """{canonical slug: pointer hook text} for every pointer under `root`."""
    return {canon(p.slug): p.hook or "" for _level, pointers in _pointers(root) for p in pointers}


def read_refs(root: Path, hooks=None) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """(outbound, inbound) maps over each fact's pointer HOOK plus its central body, both keyed by
    canonical slug - the same text the engine's inbound scan reads, so a ref that survives only in
    the hook (the body's copy edited away) is still an edge. Raises OSError on an unreadable body:
    dropping it reported a real inbound edge as absent, which is the answer that permits a move."""
    hooks = read_hooks(root) if hooks is None else hooks
    texts = dict(hooks)
    facts = root / ".claude-memory" / "facts"
    for body in sorted(facts.glob("*.md")):
        source = canon(body.stem)
        texts[source] = "%s\n%s" % (texts.get(source, ""),
                                    body.read_text(encoding="utf-8", errors="replace"))
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
    Raises OSError when a level file or a fact body cannot be read."""
    levels = read_levels(root)
    outbound, inbound = read_refs(root)
    entries, problems = [], False
    for raw in slugs:
        slug = canon(raw)
        known = slug in levels or slug in outbound
        if not known:
            problems = True
            entries.append({"slug": slug, "level": None, "unknown": True,
                            "inbound": [], "outbound": []})
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
            "unknown": False,
            "inbound": [{"slug": s, "level": levels.get(s)} for s in inbound.get(slug, [])],
            "outbound": outs,
        })
    return entries, problems


def render(entries, out) -> None:
    for entry in entries:
        print("=" * 78, file=out)
        if entry["unknown"]:
            print("%s\n  UNKNOWN: no pointer and no body anywhere under the root" % entry["slug"],
                  file=out)
            continue
        print("%s\n  level    : %s" % (entry["slug"], entry["level"] or "NO POINTER"), file=out)
        print("  inbound  : %d  (a down-move is REFUSED while this is non-empty)"
              % len(entry["inbound"]), file=out)
        for ref in entry["inbound"]:
            print("      <- %s  @ %s" % (ref["slug"], ref["level"] or "?"), file=out)
        print("  outbound : %d  (move does NOT guard these - lifting strands any left below)"
              % len(entry["outbound"]), file=out)
        for ref in entry["outbound"]:
            print("      -> %s  @ %s" % (ref["slug"], ref["level"] or "DANGLING"), file=out)


def main(argv=None, out=None, err=None) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slugs", nargs="+", help="slugs to map (dashes or underscores)")
    parser.add_argument("--root", required=True, help="the tree anchor holding .claude-memory/")
    parser.add_argument("--json", action="store_true", help="machine-readable envelope")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print("ref_map: root does not exist: %s" % root, file=err)
        if args.json:
            print(json.dumps({"ok": False, "command": "ref-map",
                              "data": {"entries": []},
                              "error": "root does not exist: %s" % root}, indent=2), file=out)
        return 2
    if not (root / ".claude-memory" / "facts").is_dir():
        print("ref_map: no .claude-memory/facts under %s - is this the anchor?" % root, file=err)
        if args.json:
            print(json.dumps({"ok": False, "command": "ref-map", "data": {"entries": []},
                              "error": "no .claude-memory/facts under %s" % root}, indent=2),
                  file=out)
        return 2

    try:
        entries, problems = build(root, args.slugs)
    except OSError as exc:
        print("ref_map: cannot read %s - the map would be incomplete" % exc, file=err)
        if args.json:
            print(json.dumps({"ok": False, "command": "ref-map", "data": {"entries": []},
                              "error": "cannot read: %s" % exc}, indent=2), file=out)
        return 2
    if args.json:
        print(json.dumps({"ok": not problems, "command": "ref-map",
                          "data": {"entries": entries}, "skipped": []}, indent=2), file=out)
    else:
        render(entries, out)
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
