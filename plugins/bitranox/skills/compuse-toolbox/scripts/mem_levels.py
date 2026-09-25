# /// script
# requires-python = ">=3.10"
# ///
"""Enumerate a curated memory tree's levels and the slugs at each, and look a slug's level up.

Why: answering "which levels exist and which facts sit at each?" is normally a hand-rolled walk of
every `CLAUDE.local.md` with a `mem:` regex - and that regex is the whole problem. A slug may
contain a DOT (`reference-pwshpy-tier-b-hosting-reuse-installed-ps7.6-assemblies`), so the
intuitive `[a-z0-9-]+` does not match a truncated slug, it fails to match the LINE AT ALL: the
pointer becomes invisible, and the body it points at reads as an orphan. That misreading is what
this tool exists to prevent, so it has no pattern of its own: it reads each level with the
engine's pointer parser (`uuid_store.parse_pointer_index`), which takes a slug up to the closing
paren, reads only the managed block, and counts each slug once.

The other reason to have it: `reconcile_memory_index.py --check-tree` reports PROBLEMS, and
`ref_map.py` maps one fact's refs. Neither answers the plain question "what is where", so it kept
being re-derived by hand.

Run: `uv run scripts/mem_levels.py --root <tree-anchor>`          # every level, with its slugs
     `uv run scripts/mem_levels.py --root <anchor> --slug <slug>` # which level holds it
     `uv run scripts/mem_levels.py --root <anchor> --json`

Exit: 0 = listed, or the slug was found. 1 = the slug is at no level (a real "no" answer, so this
      works in a gate). 2 = could not answer: a missing root, a root that is not a tree anchor (no
      `.claude-memory/` there, so the body checks would be silently off), a level file or directory
      that could not be read (listed on stderr; a "no" over a partial read is not a "no"), or an
      internal error.

Pre-pivot `uuid:` pointers count as facts at their level; their bodies are looked for at the old
sharded path `facts/<2 chars>/<uuid>.md`, exactly where the engine reads them.

Read-only: it never writes to the store. Writes go through the engine (`memory_engine.py`).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# The engine's pointer parser, from the plugin's hooks dir: scripts -> compuse-toolbox -> skills
# -> bitranox. A private regex matched `](mem:x)` anywhere, so a pointer-shaped line in the prose
# around the managed block counted as a fact at that level and hid a real dangling body.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))
import uuid_store  # noqa: E402

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
    # Level files or directories that could not be read. Any entry means every other answer may
    # be incomplete, so the CLI reports them and exits 2 rather than answering.
    unreadable: list[str] = field(default_factory=list)
    # slug -> legacy uuid, for pre-pivot pointers whose body lives at the sharded path.
    legacy: dict[str, str] = field(default_factory=dict)

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
            "unreadable": self.unreadable,
        }


def _iter_level_files(root: Path, unreadable: list[str]):
    """Walk for CLAUDE.local.md, pruning the dirs a memory tree never keeps levels in.

    A directory that cannot be listed goes to `unreadable`: skipped silently, a level inside it
    vanished and a `--slug` lookup answered a confident "no" (exit 1) for a fact sitting there.
    """
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError as exc:
            unreadable.append("%s: %s" % (d, exc.strerror or exc))
            continue
        for e in entries:
            if e.is_dir() and not e.is_symlink() and not is_pruned_dir(e.name):
                stack.append(e)
            elif e.is_file() and e.name == LEVEL_FILE:
                yield e


def _pointers_in(text: str):
    return uuid_store.parse_pointer_index(text)[1]


def slugs_in(text: str) -> list[str]:
    """Pointer slugs in a level file, in order, de-duplicated, as the engine reads them.

    Pre-pivot `uuid:` pointers are included: the engine still reads them as facts at that level,
    and dropping them made `--slug` answer "at no level" for a fact the engine resolves.
    """
    return [p.slug for p in _pointers_in(text)]


def _read_levels(root: Path, report: Report) -> None:
    for lf in sorted(_iter_level_files(root, report.unreadable)):
        rel = lf.parent.relative_to(root).as_posix() or "."
        try:
            # utf-8-sig: the pointer pattern is anchored at ^, so a BOM hid the first pointer.
            text = lf.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as exc:
            report.unreadable.append("%s: %s" % (lf, exc.strerror or exc))
            continue
        pointers = _pointers_in(text)
        report.levels[rel] = [p.slug for p in pointers]
        report.legacy.update({p.slug: p.uuid for p in pointers if p.legacy})


def _has_body(root: Path, slug: str, legacy_uuid: str | None, bodies: set[str]) -> bool:
    if legacy_uuid is None:
        return slug in bodies
    return uuid_store.legacy_body_path(root, legacy_uuid).is_file()


def scan(root: str | Path) -> Report:
    """Read every curated level under `root`. Raises FileNotFoundError if the root is not there.

    A pointer with no body is reported even when the store holds no bodies at all: an empty or
    absent `facts/` used to switch the check off, so every pointer read as healthy.
    """
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(str(root))
    report = Report(root=root)
    _read_levels(root, report)

    pointed: dict[str, list[str]] = {}
    for lvl, slugs in report.levels.items():
        for s in slugs:
            pointed.setdefault(s, []).append(lvl)
    report.duplicates = {s: sorted(l) for s, l in pointed.items() if len(set(l)) > 1}

    facts = root / STORE_DIR / "facts"
    bodies = {p.stem for p in facts.glob("*.md")} if facts.is_dir() else set()
    report.dangling = sorted(bodies - set(pointed))
    report.bodyless = sorted(s for s in pointed
                             if not _has_body(root, s, report.legacy.get(s), bodies))
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


def _fail(message: str, as_json: bool) -> int:
    """Exit 2 with the reason on stderr; JSON mode still emits JSON on failure."""
    print(message, file=sys.stderr)
    if as_json:
        print(json.dumps({"ok": False, "command": "mem_levels", "error": message}, indent=1))
    return 2


def _report_unreadable(report: Report) -> None:
    for entry in report.unreadable:
        print("unreadable: %s" % entry, file=sys.stderr)


def _answer_slug(report: Report, slug: str, as_json: bool) -> int:
    found = report.level_of(slug)
    ok = bool(found) and not report.unreadable
    if as_json:
        data = {"slug": slug, "levels": found}
        if report.unreadable:
            data["unreadable"] = report.unreadable
        print(json.dumps({"ok": ok, "command": "mem_levels", "data": data}, indent=1))
    else:
        for lvl in found:
            print(lvl)
    if not found:
        print("no level points at %s" % slug, file=sys.stderr)
    _report_unreadable(report)
    if report.unreadable:
        return 2
    return 0 if found else 1


def _run(args) -> int:
    try:
        report = scan(args.root)
    except FileNotFoundError as exc:
        return _fail("no such root: %s" % exc, args.as_json)
    if not (Path(args.root) / STORE_DIR).is_dir():
        # A sub-level passed as --root read its levels fine and reported every pointer healthy,
        # because the body checks had no store to compare against. Refuse rather than answer.
        return _fail("not a tree anchor: no %s/ under %s (pass the dir that holds it)"
                     % (STORE_DIR, args.root), args.as_json)
    if args.slug:
        return _answer_slug(report, args.slug, args.as_json)
    if args.as_json:
        print(json.dumps({"ok": not report.unreadable, "command": "mem_levels",
                          "data": report.as_dict()}, indent=1))
    else:
        _print_human(report, sys.stdout)
    _report_unreadable(report)
    return 2 if report.unreadable else 0


def main(argv: list[str] | None = None) -> int:
    """List the levels or answer `--slug`. An unexpected crash exits 2, never 1: 1 is the gate's
    "no level holds it", and Python's default exit for a traceback is exactly that code."""
    ap = argparse.ArgumentParser(
        prog="mem_levels",
        description="List a curated memory tree's levels and the slugs at each.")
    ap.add_argument("--root", required=True, help="the tree anchor (the dir holding .claude-memory/)")
    ap.add_argument("--slug", default=None, help="report which level holds this slug (exit 1 if none)")
    ap.add_argument("--json", action="store_true", dest="as_json", help="machine-readable envelope")
    args = ap.parse_args(argv)
    try:
        return _run(args)
    except Exception as exc:                             # noqa: BLE001 - a crash must not read as "no"
        print("mem_levels: internal error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


def _utf8_stdout() -> None:
    """Emit UTF-8 whatever the console code page: a cp1252 stdout (Windows, redirected) crashed on
    a level directory named outside that code page. Skipped for a stream that cannot be
    reconfigured."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (ValueError, OSError):
            pass


if __name__ == "__main__":
    _utf8_stdout()
    raise SystemExit(main())
