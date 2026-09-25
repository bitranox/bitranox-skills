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
rather than an empty file. So is a scope with a level or directory that could not be read: a
manifest that silently leaves it out vouches for a tree it never saw.

The anchor is the ENGINE's (the topmost dir with a `CLAUDE.md` and a store, see tree_support),
never merely the nearest store: a leftover store lower down the chain would otherwise be backed up
in place of the one the dream is about to rewrite.

Run (from the plugin root, via the launcher that forces UTF-8):
  `bash hooks/run-python.sh skills/meta-dream-tree/store_manifest.py backup --from . --scope tree --out <dir>`
  `bash hooks/run-python.sh skills/meta-dream-tree/store_manifest.py backup --from . --scope chain --out <dir>`
  ... do the pass ...
  `bash hooks/run-python.sh skills/meta-dream-tree/store_manifest.py verify --out <dir>`

`--out` must be outside the store, and either new, empty, or an earlier backup (it holds a
`manifest.json`): a re-backup clears the old copies first, so any other existing dir is refused.

Exit codes: 0 = backed up / verified identical, 1 = the tree differs from the manifest,
2 = refused (no store, empty scope, unreadable level or backup, bad arguments).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# The engine's pointer parser and anchor resolver, from the plugin's hooks dir:
# skills/<skill> -> skills -> bitranox.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import uuid_store  # noqa: E402

# tree_support is this script's sibling; a caller loading the script by path does not put this
# dir on sys.path the way running it directly does.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tree_support import STORE_DIR, store_anchor, utf8_stdio  # noqa: E402

__all__ = ["Entry", "Diff", "NoAnchor", "Unreadable", "derive", "diff", "manifest_key", "main"]

LEVEL_FILE = "CLAUDE.local.md"

# Dirs a curated memory tree never keeps levels in. The PREFIX set is not decoration: a venv is
# routinely named for its python or its project, so `.venv-win`, `.venv-3.13`, `venv-<user>` and
# `venv_<project>` all occur, and an exact-name set matches none of them.
PRUNE_NAMES = {".git", "node_modules", "__pycache__", "target", "site-packages"}
PRUNE_PREFIXES = (".venv", "venv-", "venv_")


class StoreManifestError(Exception):
    """Reported as a typed message and exit 2, never as a traceback."""


class NoAnchor(StoreManifestError):
    """No `.claude-memory/` store at or above the starting directory - there is no tree here."""


class EmptyScope(StoreManifestError):
    """The scope holds no levels, so a manifest would assert nothing while looking like proof."""


class Unreadable(StoreManifestError):
    """A level file or a directory in scope could not be read, so the scope is not fully known.

    `paths` names each one; the CLI reports them in the envelope's `skipped`."""

    def __init__(self, paths: list[str]) -> None:
        super().__init__(f"{len(paths)} path(s) in scope could not be read, so the manifest "
                         "would omit them: " + "; ".join(paths))
        self.paths = paths


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
    """The tree anchor the ENGINE uses for `start` (see tree_support.store_anchor)."""
    anchor = store_anchor(start, uuid_store.resolve_anchor)
    if anchor is None:
        raise NoAnchor(f"no {STORE_DIR}/ store at the memory anchor of {Path(start).resolve()} "
                       "(the topmost dir holding a CLAUDE.md and a store)")
    return anchor


def levels_under(anchor: Path, exclude: tuple[Path, ...] = (),
                 unreadable: list[str] | None = None) -> list[Path]:
    """Every level dir under `anchor`, pruned. Filesystem walk, never grep - see the docstring.

    `exclude` exists for the backup dir itself. Writing the backup under the anchor puts COPIES
    of every level file inside the scope, so the next walk finds them and `verify` reports the
    whole tree as moved - the tool breaking precisely the check it exists to perform.

    A directory that cannot be listed is appended to `unreadable` rather than skipped in silence:
    it may hold a level, and a manifest that omits it looks exactly like one that had none.
    """
    skip = tuple(Path(p).resolve() for p in exclude)
    found: list[Path] = []
    stack = [Path(anchor)]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            if unreadable is not None:
                unreadable.append(str(d))
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
    """Every pointer in one level file, read the way the engine reads it. PURE.

    Only the managed block counts, and each slug once: a pointer-shaped line in the prose around
    the block is not a fact the engine will ever load, so a manifest counting it would vouch for a
    fact that does not exist."""
    return [Entry(level=level, slug=p.slug, title=p.title.strip(), pin=p.pin)
            for p in uuid_store.parse_pointer_index(text or "")[1] if not p.legacy]


def derive(root: Path, *, scope: str = "tree", start: Path | None = None,
           exclude: tuple[Path, ...] = ()) -> list[Entry]:
    """The manifest entries for the live tree, sorted so the result is order-independent.

    Raises Unreadable when any in-scope directory or level file could not be read (a permission
    error, or bytes that are not UTF-8): a partial manifest would verify as if the missing levels
    had never existed.
    """
    anchor = anchor_dir(root)
    begin = Path(start) if start is not None else Path(root)
    unreadable: list[str] = []
    levels = (levels_under(anchor, exclude, unreadable) if scope == "tree"
              else levels_on_chain(begin, anchor))
    entries: list[Entry] = []
    for lvl in levels:
        try:
            # utf-8-sig: a BOM left by a Windows editor would otherwise glue itself to the first
            # line and hide a pointer written there.
            text = (lvl / LEVEL_FILE).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append(f"{lvl / LEVEL_FILE} ({type(exc).__name__})")
            continue
        entries.extend(parse_level(text, str(lvl)))
    if unreadable:
        raise Unreadable(sorted(unreadable))
    return sorted(entries)


def manifest_key(entries: list[Entry]) -> tuple:
    """A stable identity for a manifest: order-independent by construction."""
    return tuple(sorted((e.level, e.slug, e.title, e.pin) for e in entries))


def _by_slug(entries: list[Entry]) -> dict[str, dict[str, Entry]]:
    out: dict[str, dict[str, Entry]] = {}
    for e in entries:
        out.setdefault(e.slug, {})[e.level] = e
    return out


def _changed(slug: str, b: Entry, a: Entry) -> Change | None:
    what = [name for name in ("title", "pin") if getattr(b, name) != getattr(a, name)]
    return Change(slug, what, b, a) if what else None


def _diff_slug(slug: str, before: dict[str, Entry], after: dict[str, Entry], out: Diff) -> None:
    """Fold one slug's copies into `out`. Levels present on both sides are compared in place.

    The rest is a MOVE only when the slug has as many copies after as before; otherwise the copies
    that vanished are removed and the new ones added. Keying on the slug alone kept one copy per
    slug, so removing one of two copies of a duplicated slug verified IDENTICAL.
    """
    for level in sorted(set(before) & set(after)):
        change = _changed(slug, before[level], after[level])
        if change:
            out.changed.append(change)
    gone = [before[lv] for lv in sorted(set(before) - set(after))]
    new = [after[lv] for lv in sorted(set(after) - set(before))]
    if len(before) != len(after):
        out.removed.extend(gone)
        out.added.extend(new)
        return
    for b, a in zip(gone, new):
        out.moved.append(a)
        change = _changed(slug, b, a)
        if change:
            out.changed.append(change)


def diff(before: list[Entry], after: list[Entry]) -> Diff:
    """What changed between two manifests, keyed by (level, slug). PURE.

    A MOVE is reported as a move rather than as an unrelated add plus remove, because a dream
    moves facts on purpose and an add/remove rendering makes the report unreadable exactly when
    it is being read.
    """
    by_before, by_after = _by_slug(before), _by_slug(after)
    out = Diff()
    for slug in sorted(set(by_before) | set(by_after)):
        _diff_slug(slug, by_before.get(slug, {}), by_after.get(slug, {}), out)
    out.added.sort()
    out.removed.sort()
    return out


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


def _check_out(out: Path, store: Path) -> None:
    """Refuse an --out the backup would damage, or damage itself by writing into.

    Inside the store, copytree recurses into its own output and fills the LIVE store with nested
    copies. An existing dir that is not an earlier backup may hold someone's files, and a
    re-backup clears `store/` and `levels/` before copying - so only a new, empty, or earlier
    backup dir is accepted.
    """
    target = Path(out).resolve()
    if target == store or store in target.parents:
        raise StoreManifestError(f"--out {target} is inside the store {store}; the copy would "
                                 "recurse into itself - write the backup outside the store")
    if target.is_dir() and any(target.iterdir()) and not (target / "manifest.json").is_file():
        raise StoreManifestError(f"--out {target} exists, is not empty and holds no "
                                 "manifest.json, so it is not an earlier backup; a re-backup "
                                 "clears its store/ and levels/ first - use a new dir")


def backup(*, root: Path, scope: str, start: Path, out: Path) -> tuple[list[Entry], Path]:
    """Copy the store and every in-scope level file, then record the manifest."""
    anchor = anchor_dir(root)
    store_src = anchor / STORE_DIR
    _check_out(out, store_src.resolve())
    entries = derive(root, scope=scope, start=start, exclude=(Path(out).expanduser(),))
    if not entries:
        raise EmptyScope(f"no pointers found in scope {scope!r} under {anchor} - a manifest of "
                         "nothing verifies clean against anything, so this is a refusal")
    out.mkdir(parents=True, exist_ok=True)
    for stale in (out / "store", out / "levels"):
        # A level deleted since the last backup into this dir would otherwise survive in it.
        if stale.exists():
            shutil.rmtree(stale)
    shutil.copytree(store_src, out / "store")
    # Every in-scope level sits under the anchor: the tree walk starts there and the chain walk
    # stops there, so relative_to cannot fail.
    for lvl in sorted({Path(e.level) for e in entries}):
        dst = out / "levels" / lvl.relative_to(anchor)
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lvl / LEVEL_FILE, dst / LEVEL_FILE)
    return entries, _write_manifest(out, anchor=anchor, scope=scope, start=start, entries=entries)


def _manifest_shape_error(data: object) -> str | None:
    """Why `data` is not a manifest this tool wrote, or None when it is one. PURE."""
    if not isinstance(data, dict):
        return f"the top level is {type(data).__name__}, not an object"
    if not isinstance(data.get("anchor"), str):
        return "it has no 'anchor' string"
    entries = data.get("entries")
    if not isinstance(entries, list):
        return "it has no 'entries' list"
    for key in ("scope", "start"):
        if key in data and not isinstance(data[key], str):
            return f"its '{key}' is not a string"
    exclude = data.get("exclude", [])
    if not (isinstance(exclude, list) and all(isinstance(p, str) for p in exclude)):
        return "its 'exclude' is not a list of strings"
    for i, e in enumerate(entries):
        if not (isinstance(e, dict) and isinstance(e.get("level"), str)
                and isinstance(e.get("slug"), str)):
            return f"entry {i} is not an object with 'level' and 'slug' strings"
    return None


def load_manifest(out: Path) -> dict:
    """The manifest in `out`, validated. A truncated or hand-edited one is a typed refusal."""
    path = Path(out) / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StoreManifestError(f"cannot read {path}: {exc}") from exc
    except ValueError as exc:                    # includes UnicodeDecodeError
        raise StoreManifestError(f"{path} is not valid JSON: {exc}") from exc
    why = _manifest_shape_error(data)
    if why:
        raise StoreManifestError(f"{path} is not a store manifest: {why}")
    return data


def verify(out: Path) -> Diff:
    """Re-derive the live tree with the manifest's own scope and diff it."""
    data = load_manifest(out)
    before = [Entry.from_dict(d) for d in data["entries"]]
    anchor = Path(data["anchor"])
    after = derive(anchor, scope=data.get("scope", "tree"),
                   start=Path(data.get("start", str(anchor))),
                   exclude=tuple(Path(p) for p in data.get("exclude", [])))
    return diff(before, after)


# ---- CLI ---------------------------------------------------------------------------------------

def _emit(as_json: bool, ok: bool, command: str, data: dict, text: str,
          skipped: list[str] | None = None) -> None:
    if as_json:
        print(json.dumps({"ok": ok, "command": command, "data": data,
                          "skipped": list(skipped or [])}, indent=2))
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
    utf8_stdio()
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "backup":
            start = Path(args.start).expanduser().resolve()
            if not start.is_dir():
                # A typo'd --from would otherwise climb to an ancestor and back up ITS chain.
                raise StoreManifestError(f"--from {start} is not an existing directory")
            entries, path = backup(root=start, scope=args.scope, start=start,
                                   out=Path(args.out).expanduser())
            _emit(args.as_json, True, "backup",
                  {"entries": len(entries), "manifest": str(path), "scope": args.scope},
                  f"backed up {len(entries)} pointer(s) ({args.scope} scope) -> {path}")
            return 0
        d = verify(Path(args.out).expanduser())
        _emit(args.as_json, d.identical, "verify", d.as_dict(), _render_diff(d))
        return 0 if d.identical else 1
    except (StoreManifestError, OSError) as exc:
        # OSError: a copy or manifest write that failed part-way (full disk, read-only target).
        skipped = exc.paths if isinstance(exc, Unreadable) else []
        _emit(getattr(args, "as_json", False), False, args.cmd, {"error": str(exc)},
              f"error: {exc}", skipped)
        if not getattr(args, "as_json", False):
            print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
