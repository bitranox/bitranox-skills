# /// script
# requires-python = ">=3.10"
# ///
"""Back up the stores a dream is about to rewrite, and prove afterwards that nothing was lost.

Every dream and every nap owes the same two steps: copy the in-scope stores, and record a
manifest it can re-derive and diff at the end. Both were hand-rolled from scratch each run, at
two different scopes, and the diff half - the half that turns "I verified it" into something a
reader can check - was the half most often skipped.

The manifest records `(level, slug, title, pin)` per fact, sorted, so it is ORDER-INDEPENDENT: a
level re-rendered in a different order is not a change. Slug alone would be too little. A fact
that keeps its slug while its title or pin flips is precisely the loss that reads as "still
there", and pin decides whether the engine will accept an ordinary `add` at all.

Enumeration is where this goes wrong, twice over, and both are pinned by tests:

- A gitignore-aware `grep -r` SKIPS the pointer files, because `CLAUDE.local.md` is gitignored.
  So this walks the filesystem and never shells out to grep.
- A bare walk OVER-counts. The plugin vendors `CLAUDE.local.md` into site-packages, so any
  unpruned virtualenv contributes levels nobody can edit - and an exact-match prune of `.venv`
  covers neither `.venv-win` nor `.venv-3.13` nor `venv-<user>`.

A manifest of zero entries verifies clean against anything, so an empty scope is a REFUSAL
rather than an empty file.

Run:
  `uv run store_manifest.py backup --from . --scope tree --out .dream-backup`
  `uv run store_manifest.py backup --from . --scope chain --out .nap-backup`
  ... do the pass ...
  `uv run store_manifest.py verify --out .dream-backup`

Exit codes: 0 = backed up / verified identical, 1 = the tree differs from the manifest,
2 = refused (no store, empty scope, unreadable backup, bad arguments).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Entry", "Diff", "NoAnchor", "derive", "diff", "manifest_key", "main"]

LEVEL_FILE = "CLAUDE.local.md"
STORE_DIR = ".claude-memory"

# Dirs a curated memory tree never keeps levels in. The PREFIX set is not decoration: a venv is
# routinely named for its python or its project, so `.venv-win`, `.venv-3.13`, `venv-<user>` and
# `venv_<project>` all occur, and an exact-name set matches none of them.
PRUNE_NAMES = {".git", "node_modules", "__pycache__", "target", "site-packages"}
PRUNE_PREFIXES = (".venv", "venv-", "venv_")

# `- [Title](mem:slug) - hook <!-- bx:pin -->`; the hook runs to the first meta comment.
POINTER_RX = re.compile(r"^\s*-\s*\[(?P<title>[^\]]*)\]\(mem:(?P<slug>[^)\s]+)\)"
                        r"(?P<rest>.*)$")


class StoreManifestError(Exception):
    """Reported as a typed message and exit 2, never as a traceback."""


class NoAnchor(StoreManifestError):
    """No `.claude-memory/` store at or above the starting directory - there is no tree here."""


class EmptyScope(StoreManifestError):
    """The scope holds no levels, so a manifest would assert nothing while looking like proof."""


@dataclass(frozen=True, order=True)
class Entry:
    """One pointer as the manifest records it: identity, what it says, and where it sits."""

    level: str
    slug: str
    title: str
    pin: bool

    def as_dict(self) -> dict:
        return {"level": self.level, "slug": self.slug, "title": self.title, "pin": self.pin}

    @staticmethod
    def from_dict(d: dict) -> "Entry":
        return Entry(str(d["level"]), str(d["slug"]), str(d.get("title", "")),
                     bool(d.get("pin", False)))


@dataclass(frozen=True)
class Change:
    """A fact that kept its slug while what it says changed."""

    slug: str
    what: list[str]
    before: Entry
    after: Entry

    def as_dict(self) -> dict:
        return {"slug": self.slug, "what": self.what,
                "before": self.before.as_dict(), "after": self.after.as_dict()}


@dataclass(frozen=True)
class Diff:
    """What moved between two manifests. `identical` is the only thing a caller may shortcut to."""

    added: list[Entry] = field(default_factory=list)
    removed: list[Entry] = field(default_factory=list)
    changed: list[Change] = field(default_factory=list)
    moved: list[Entry] = field(default_factory=list)

    @property
    def identical(self) -> bool:
        return not (self.added or self.removed or self.changed or self.moved)

    def as_dict(self) -> dict:
        return {"identical": self.identical,
                "added": [e.as_dict() for e in self.added],
                "removed": [e.as_dict() for e in self.removed],
                "changed": [c.as_dict() for c in self.changed],
                "moved": [e.as_dict() for e in self.moved]}


def is_pruned_dir(name: str) -> bool:
    """Whether a directory name is one a curated memory tree never keeps levels in."""
    return name in PRUNE_NAMES or name.startswith(PRUNE_PREFIXES)


def anchor_dir(start: Path) -> Path:
    """The tree anchor: the first ancestor holding a `.claude-memory/` store."""
    cur = Path(start).resolve()
    while True:
        if (cur / STORE_DIR).is_dir():
            return cur
        if cur.parent == cur:
            raise NoAnchor(f"no {STORE_DIR}/ store at or above {Path(start).resolve()}")
        cur = cur.parent


def levels_under(anchor: Path, exclude: tuple[Path, ...] = ()) -> list[Path]:
    """Every level dir under `anchor`, pruned. Filesystem walk, never grep - see the docstring.

    `exclude` exists for the backup dir itself. Writing the backup under the anchor puts COPIES
    of every level file inside the scope, so the next walk finds them and `verify` reports the
    whole tree as moved - the tool breaking precisely the check it exists to perform.
    """
    skip = tuple(Path(p).resolve() for p in exclude)
    found: list[Path] = []
    stack = [Path(anchor)]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.is_dir() and not e.is_symlink() and not is_pruned_dir(e.name):
                resolved = e.resolve()
                if any(resolved == s or s in resolved.parents for s in skip):
                    continue
                stack.append(e)
            elif e.is_file() and e.name == LEVEL_FILE:
                found.append(d)
    return sorted(found)


def levels_on_chain(start: Path, anchor: Path) -> list[Path]:
    """Level dirs from `start` upward to `anchor` inclusive - a nap's scope."""
    found: list[Path] = []
    cur = Path(start).resolve()
    stop = Path(anchor).resolve()
    while True:
        if (cur / LEVEL_FILE).is_file():
            found.append(cur)
        if cur == stop or cur.parent == cur:
            break
        cur = cur.parent
    return sorted(found)


def parse_level(text: str, level: str) -> list[Entry]:
    """Every pointer in one level file. PURE."""
    out: list[Entry] = []
    for raw in (text or "").splitlines():
        m = POINTER_RX.match(raw)
        if not m:
            continue
        out.append(Entry(level=level, slug=m.group("slug"), title=m.group("title").strip(),
                         pin="bx:pin" in (m.group("rest") or "")))
    return out


def derive(root: Path, *, scope: str = "tree", start: Path | None = None,
           exclude: tuple[Path, ...] = ()) -> list[Entry]:
    """The manifest entries for the live tree, sorted so the result is order-independent."""
    anchor = anchor_dir(root)
    begin = Path(start) if start is not None else Path(root)
    levels = (levels_under(anchor, exclude) if scope == "tree"
              else levels_on_chain(begin, anchor))
    entries: list[Entry] = []
    for lvl in levels:
        try:
            text = (lvl / LEVEL_FILE).read_text(encoding="utf-8")
        except OSError:
            continue
        entries.extend(parse_level(text, str(lvl)))
    return sorted(entries)


def manifest_key(entries: list[Entry]) -> tuple:
    """A stable identity for a manifest: order-independent by construction."""
    return tuple(sorted((e.level, e.slug, e.title, e.pin) for e in entries))


def diff(before: list[Entry], after: list[Entry]) -> Diff:
    """What changed between two manifests, keyed by slug. PURE.

    A MOVE is reported as a move rather than as an unrelated add plus remove, because a dream
    moves facts on purpose and an add/remove rendering makes the report unreadable exactly when
    it is being read.
    """
    by_before = {e.slug: e for e in before}
    by_after = {e.slug: e for e in after}
    added = sorted(e for s, e in by_after.items() if s not in by_before)
    removed = sorted(e for s, e in by_before.items() if s not in by_after)
    changed: list[Change] = []
    moved: list[Entry] = []
    for slug in sorted(set(by_before) & set(by_after)):
        b, a = by_before[slug], by_after[slug]
        what = [name for name in ("title", "pin") if getattr(b, name) != getattr(a, name)]
        if what:
            changed.append(Change(slug, what, b, a))
        if b.level != a.level:
            moved.append(a)
    return Diff(added=added, removed=removed, changed=changed, moved=moved)


# ---- backup and verify ---------------------------------------------------------------------

def _write_manifest(out: Path, *, anchor: Path, scope: str, start: Path,
                    entries: list[Entry]) -> Path:
    # `exclude` is recorded, not recomputed: verify runs later, possibly from another cwd, and
    # must skip exactly the dir this backup wrote - otherwise it re-reads its own copies.
    payload = {"scope": scope, "anchor": str(anchor), "start": str(start),
               "exclude": [str(Path(out).resolve())],
               "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "entries": [e.as_dict() for e in entries]}
    out.mkdir(parents=True, exist_ok=True)
    path = out / "manifest.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def backup(*, root: Path, scope: str, start: Path, out: Path) -> tuple[list[Entry], Path]:
    """Copy the store and every in-scope level file, then record the manifest."""
    anchor = anchor_dir(root)
    entries = derive(root, scope=scope, start=start, exclude=(Path(out).expanduser(),))
    if not entries:
        raise EmptyScope(f"no pointers found in scope {scope!r} under {anchor} - a manifest of "
                         "nothing verifies clean against anything, so this is a refusal")
    out.mkdir(parents=True, exist_ok=True)
    store_src = anchor / STORE_DIR
    store_dst = out / "store"
    if store_dst.exists():
        shutil.rmtree(store_dst)
    shutil.copytree(store_src, store_dst)
    for lvl in sorted({Path(e.level) for e in entries}):
        try:
            rel = lvl.relative_to(anchor)
        except ValueError:                       # a chain level above the anchor: keep it flat
            rel = Path(lvl.name)
        dst = out / "levels" / rel
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lvl / LEVEL_FILE, dst / LEVEL_FILE)
    return entries, _write_manifest(out, anchor=anchor, scope=scope, start=start, entries=entries)


def load_manifest(out: Path) -> dict:
    path = Path(out) / "manifest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StoreManifestError(f"cannot read {path}: {exc}") from exc
    except ValueError as exc:
        raise StoreManifestError(f"{path} is not valid JSON: {exc}") from exc


def verify(out: Path) -> Diff:
    """Re-derive the live tree with the manifest's own scope and diff it."""
    data = load_manifest(out)
    before = [Entry.from_dict(d) for d in data.get("entries", [])]
    anchor = Path(data["anchor"])
    after = derive(anchor, scope=data.get("scope", "tree"),
                   start=Path(data.get("start", str(anchor))),
                   exclude=tuple(Path(p) for p in data.get("exclude", [])))
    return diff(before, after)


# ---- CLI ---------------------------------------------------------------------------------------

def _emit(as_json: bool, ok: bool, command: str, data: dict, text: str) -> None:
    if as_json:
        print(json.dumps({"ok": ok, "command": command, "data": data, "skipped": []}, indent=2))
    else:
        print(text)


def _render_diff(d: Diff) -> str:
    if d.identical:
        return "IDENTICAL: the tree matches the manifest"
    lines = ["DIFFERS from the manifest:"]
    lines += [f"  removed  {e.slug}  ({e.level})" for e in d.removed]
    lines += [f"  added    {e.slug}  ({e.level})" for e in d.added]
    lines += [f"  changed  {c.slug}  ({', '.join(c.what)})" for c in d.changed]
    lines += [f"  moved    {e.slug}  -> {e.level}" for e in d.moved]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    bk = sub.add_parser("backup", help="copy the in-scope stores and record the manifest")
    bk.add_argument("--from", dest="start", default=".", help="a dir inside the tree")
    bk.add_argument("--scope", choices=["tree", "chain"], default="tree",
                    help="tree = every level under the anchor; chain = ancestors of --from only")
    bk.add_argument("--out", required=True, help="where to write the backup and manifest")
    bk.add_argument("--json", action="store_true", dest="as_json")

    vf = sub.add_parser("verify", help="re-derive the tree and diff it against the manifest")
    vf.add_argument("--out", required=True, help="the backup dir holding manifest.json")
    vf.add_argument("--json", action="store_true", dest="as_json")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "backup":
            start = Path(args.start).expanduser().resolve()
            entries, path = backup(root=start, scope=args.scope, start=start,
                                   out=Path(args.out).expanduser())
            _emit(args.as_json, True, "backup",
                  {"entries": len(entries), "manifest": str(path), "scope": args.scope},
                  f"backed up {len(entries)} pointer(s) ({args.scope} scope) -> {path}")
            return 0
        d = verify(Path(args.out).expanduser())
        _emit(args.as_json, d.identical, "verify", d.as_dict(), _render_diff(d))
        return 0 if d.identical else 1
    except StoreManifestError as exc:
        _emit(getattr(args, "as_json", False), False, args.cmd, {"error": str(exc)},
              f"error: {exc}")
        if not getattr(args, "as_json", False):
            print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
