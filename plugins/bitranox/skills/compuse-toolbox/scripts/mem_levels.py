# /// script
# requires-python = ">=3.10"
# ///
"""Enumerate a curated memory tree's levels and the slugs at each, and look a slug's level up.

Why: answering "which levels exist and which facts sit at each?" is normally a hand-rolled walk of
every `CLAUDE.local.md` with a `mem:` regex - and that regex is the whole problem. A slug may
contain a DOT (`reference-pwshpy-tier-b-hosting-reuse-installed-ps7.6-assemblies`), so the
intuitive `[a-z0-9-]+` does not match a truncated slug, it fails to match the LINE AT ALL: the
pointer becomes invisible, and the body it points at reads as an orphan. That misreading is what
this tool exists to prevent, so the pattern here is deliberately permissive - everything up to the
closing paren - matching the engine's own `mem:[^)]+`.

The other reason to have it: `reconcile_memory_index.py --check-tree` reports PROBLEMS, and
`ref_map.py` maps one fact's refs. Neither answers the plain question "what is where", so it kept
being re-derived by hand.

Run: `uv run scripts/mem_levels.py --root <tree-anchor>`          # every level, with its slugs
     `uv run scripts/mem_levels.py --root <anchor> --slug <slug>` # which level holds it
     `uv run scripts/mem_levels.py --root <anchor> --json`

Exit: 0 = listed, or the slug was found. 1 = the slug is at no level (a real "no" answer, so this
      works in a gate). 2 = could not read the tree (missing root).

Read-only: it never writes to the store. Writes go through the engine (`memory_engine.py`).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Permissive on purpose: a slug's charset is [a-z0-9._-], so anything up to the closing paren.
# A narrower class silently skips a dotted slug's whole line - the bug this tool prevents.
POINTER_RX = re.compile(r"\]\(mem:([^)\s]+)\)")
LEVEL_FILE = "CLAUDE.local.md"
STORE_DIR = ".claude-memory"
PRUNE = {".git", "node_modules", ".venv", "__pycache__", "target"}
# A venv is routinely named for its python or its project, so exact names cannot cover them:
# `.venv-win`, `.venv-3.13`, `venv-<user>` and `venv_<project>` all occur on real trees. The
# plugin vendors CLAUDE.local.md into site-packages, so an unpruned one turns a vendored copy
# into an apparent memory level. srccount.py in this skill carries the same shapes, tested.
PRUNE_PREFIXES = (".venv", "venv-", "venv_")

__all__ = ["Report", "scan", "main"]


def is_pruned_dir(name: str) -> bool:
    """Whether a directory name is one a curated memory tree never keeps levels in."""
    return name in PRUNE or name.startswith(PRUNE_PREFIXES)


@dataclass
class Report:
    """What the tree holds: levels -> their slugs, plus the integrity odds and ends."""

    root: Path
    levels: dict[str, list[str]] = field(default_factory=dict)
    duplicates: dict[str, list[str]] = field(default_factory=dict)
    dangling: list[str] = field(default_factory=list)
    bodyless: list[str] = field(default_factory=list)

    def level_of(self, slug: str) -> list[str]:
        """Every level pointing at `slug` (normally one - slugs are tree-unique)."""
        return sorted(lvl for lvl, slugs in self.levels.items() if slug in slugs)

    def as_dict(self) -> dict:
        return {
            "root": str(self.root),
            "levels": self.levels,
            "duplicates": self.duplicates,
            "dangling": self.dangling,
            "bodyless": self.bodyless,
        }


def _iter_level_files(root: Path):
    """Walk for CLAUDE.local.md, pruning the dirs a memory tree never keeps levels in."""
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.is_dir() and not e.is_symlink() and not is_pruned_dir(e.name):
                stack.append(e)
            elif e.is_file() and e.name == LEVEL_FILE:
                yield e


def slugs_in(text: str) -> list[str]:
    """Pointer slugs in a level file, in order, de-duplicated."""
    seen, out = set(), []
    for slug in POINTER_RX.findall(text):
        if slug not in seen:
            seen.add(slug)
            out.append(slug)
    return out


def scan(root: str | Path) -> Report:
    """Read every curated level under `root`. Raises FileNotFoundError if the root is not there."""
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(str(root))
    report = Report(root=root)
    for lf in sorted(_iter_level_files(root)):
        rel = lf.parent.relative_to(root).as_posix() or "."
        try:
            report.levels[rel] = slugs_in(lf.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue

    pointed: dict[str, list[str]] = {}
    for lvl, slugs in report.levels.items():
        for s in slugs:
            pointed.setdefault(s, []).append(lvl)
    report.duplicates = {s: sorted(l) for s, l in pointed.items() if len(set(l)) > 1}

    facts = root / STORE_DIR / "facts"
    bodies = {p.stem for p in facts.glob("*.md")} if facts.is_dir() else set()
    report.dangling = sorted(bodies - set(pointed))
    report.bodyless = sorted(set(pointed) - bodies) if bodies else []
    return report


def _print_human(report: Report, out) -> None:
    total = sum(len(v) for v in report.levels.values())
    print("%d level(s), %d pointer(s) under %s" % (len(report.levels), total, report.root), file=out)
    for lvl in sorted(report.levels, key=lambda k: (-len(report.levels[k]), k)):
        print("  %4d  %s" % (len(report.levels[lvl]), lvl), file=out)
        for s in report.levels[lvl]:
            print("          %s" % s, file=out)
    for slug, lvls in sorted(report.duplicates.items()):
        print("  ! duplicate pointer: %s at %s" % (slug, ", ".join(lvls)), file=out)
    for slug in report.dangling:
        print("  ~ dangling body (no pointer at any level): %s" % slug, file=out)
    for slug in report.bodyless:
        print("  ! pointer with no body: %s" % slug, file=out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="mem_levels",
        description="List a curated memory tree's levels and the slugs at each.")
    ap.add_argument("--root", required=True, help="the tree anchor (the dir holding .claude-memory/)")
    ap.add_argument("--slug", default=None, help="report which level holds this slug (exit 1 if none)")
    ap.add_argument("--json", action="store_true", dest="as_json", help="machine-readable envelope")
    args = ap.parse_args(argv)

    try:
        report = scan(args.root)
    except FileNotFoundError as exc:
        # Warnings on stderr, never in the parsed stream; JSON mode still emits JSON on failure.
        print("no such root: %s" % exc, file=sys.stderr)
        if args.as_json:
            print(json.dumps({"ok": False, "command": "mem_levels",
                              "error": "no such root: %s" % exc}, indent=1))
        return 2

    if args.slug:
        found = report.level_of(args.slug)
        if args.as_json:
            print(json.dumps({"ok": bool(found), "command": "mem_levels",
                              "data": {"slug": args.slug, "levels": found}}, indent=1))
        elif found:
            for lvl in found:
                print(lvl)
        else:
            print("no level points at %s" % args.slug, file=sys.stderr)
        return 0 if found else 1

    if args.as_json:
        print(json.dumps({"ok": True, "command": "mem_levels", "data": report.as_dict()}, indent=1))
    else:
        _print_human(report, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
