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
has a dangling ref, 2 the map could not be built at all.

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

POINTER_RX = re.compile(r"^- \[(?P<title>[^\]]*)\]\(mem:(?P<slug>[^)]+)\)")
REF_RX = re.compile(r"\[\[([^\]]+)\]\]")
_SKIP_DIRS = ("node_modules", ".git")


def canon(slug: str) -> str:
    """Canonical slug for MATCHING: lowercase, `_` and `-` are the same separator.

    Mirrors the engine's own rule, so a ref written `[[a_b]]` against a fact named `a-b` is a
    match, not a dangling ref. Reporting those as broken is a false positive that has already
    cost one review cycle.
    """
    return slug.strip().lower().replace("_", "-")


def read_levels(root: Path) -> dict[str, str]:
    """{canonical slug: level dir} for every pointer under `root`."""
    levels: dict[str, str] = {}
    for path in sorted(root.rglob("CLAUDE.local.md")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            match = POINTER_RX.match(line.strip())
            if match:
                levels[canon(match.group("slug"))] = str(path.parent)
    return levels


def read_refs(root: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """(outbound, inbound) maps over the central `facts/` bodies, both keyed by canonical slug."""
    outbound: dict[str, list[str]] = {}
    inbound: dict[str, list[str]] = {}
    facts = root / ".claude-memory" / "facts"
    for body in sorted(facts.glob("*.md")):
        source = canon(body.stem)
        try:
            text = body.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        targets = {canon(t.split(":")[-1]) for t in REF_RX.findall(ME.mask_code_regions(text))}
        targets.discard(source)
        outbound[source] = sorted(targets)
        for target in targets:
            inbound.setdefault(target, []).append(source)
    return outbound, {k: sorted(v) for k, v in inbound.items()}


def build(root: Path, slugs):
    """[{slug, level, inbound, outbound, unknown}] plus a flag for whether anything is wrong."""
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

    entries, problems = build(root, args.slugs)
    if args.json:
        print(json.dumps({"ok": not problems, "command": "ref-map",
                          "data": {"entries": entries}, "skipped": []}, indent=2), file=out)
    else:
        render(entries, out)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
