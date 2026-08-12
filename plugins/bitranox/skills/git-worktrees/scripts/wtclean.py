# /// script
# requires-python = ">=3.10"
# ///
"""Remove a git worktree AND the per-topic build caches it leaves behind.

`git worktree remove` deletes the checkout and nothing else. A per-worktree build cache
(`CARGO_TARGET_DIR` and friends) is deliberately kept OUTSIDE the checkout - that is the whole
point of giving each worktree its own - so it survives every cleanup and piles up invisibly at
gigabytes each. Nothing lists them, which is why they are usually found by running out of space.

Dry run by DEFAULT. This deletes directories and there is no undo, so it prints the plan with
sizes and does nothing until `--apply`. `--apply` removes EXACTLY what the plan listed - it does
not re-scan - because a plan that does not match what gets deleted is how a delete tool surprises
someone.

CACHE LAYOUT IS A CONVENTION, NOT A DISCOVERY. There is no way to ask git where your build cache
lives, so this tool derives candidates as `<base>/<prefix><topic>-<suffix>`, defaulting to
`~/wt-<topic>-target` and `~/wt-<topic>-clippy` (the shape you get from pointing each worktree's
`CARGO_TARGET_DIR` at a sibling of your home). If your caches live somewhere else, say so with
`--cache-dir` (repeatable, exact paths), or adjust `--base` / `--prefix` / `--cache-suffix`. When
the convention matches nothing, the run says which paths it checked instead of quietly reporting
an empty plan.

Refusals, because this runs on machines whose layout is not yours:

* A topic name that is a PATH rather than a bare name is refused outright, never normalised - a
  normalised traversal still deletes. Checked against both POSIX and Windows path rules, so a
  Windows-shaped escape is refused on Linux too.
* A target that IS a symbolic link is refused. Deleting through a link can destroy data outside
  the directory you named. (A link found INSIDE the tree is safe: `shutil.rmtree` removes the
  link, not what it points at.)
* A target that resolves outside `--base`, or that is a filesystem root, your home directory, or
  the base itself, is refused.
* A worktree holding uncommitted or untracked work is refused unless you pass
  `--discard-uncommitted`, which forwards `--force` to `git worktree remove` and DISCARDS that
  work. Nothing is discarded by default.

Windows: the symlink refusal does not cover a directory JUNCTION, which Windows does not report
as a symbolic link; the "resolves outside base" refusal is what covers that case, because
resolving a path does follow a junction.

Run:
  `uv run scripts/wtclean.py mytopic`                          # the plan, with sizes
  `uv run scripts/wtclean.py mytopic --apply`                  # remove the worktree and its caches
  `uv run scripts/wtclean.py .worktrees/mytopic --cache-dir ~/.cache/targets/mytopic --apply`
  `uv run scripts/wtclean.py mytopic --json`

Exit codes: 0 = nothing blocked (a dry-run plan that can be carried out as-is, or an `--apply`
that removed everything it listed), 1 = something was refused or could not be removed, 2 = usage
error. `--json` emits the machine-readable envelope; warnings always go to stderr so stdout stays
parseable.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Sequence

__all__ = [
    "CacheTarget",
    "Plan",
    "Refusal",
    "apply_plan",
    "blocked_reasons",
    "build_plan",
    "cache_dirs",
    "directory_size",
    "git_worktree_status",
    "looks_like_a_path",
    "refusal_for",
    "topic_name",
    "unsafe_argument_reason",
    "unsafe_topic_reason",
    "worktree_refusal",
]

DEFAULT_PREFIX = "wt-"
DEFAULT_CACHE_SUFFIXES = ("target", "clippy")

# A git call that has not answered by now is not going to; a delete tool must never hang its
# caller waiting for one.
GIT_TIMEOUT_SECONDS = 30

# Worktree states. "unknown" means git could not be asked at all, which is treated exactly like
# dirty: removing a checkout whose state you could not read is the same gamble.
STATUS_ABSENT = "absent"
STATUS_CLEAN = "clean"
STATUS_DIRTY = "dirty"
STATUS_UNKNOWN = "unknown"

_OVERRIDABLE_STATUSES = (STATUS_DIRTY, STATUS_UNKNOWN)


# --------------------------------------------------------------------------------------------
# Name safety
# --------------------------------------------------------------------------------------------


def unsafe_topic_reason(value: str) -> str | None:
    """Why this topic may not be interpolated into a delete path, or None when it is a bare name.

    The topic is pasted into a path that gets removed, so anything that is a PATH rather than a
    name is refused outright rather than normalised: a normalised traversal still deletes. Both
    POSIX and Windows rules are applied on every platform, so a drive-relative or backslash form
    is refused on Linux too rather than passing as an ordinary directory name.
    """
    if not value:
        return "is empty"
    if value in (".", "..", "~"):
        return "is a directory reference, not a name"
    if ".." in value:
        return "contains a parent reference"
    if ":" in value:
        return "contains a drive or stream separator"
    for flavour in (PurePosixPath, PureWindowsPath):
        pure = flavour(value)
        if pure.drive or pure.root or len(pure.parts) > 1 or pure.name != value:
            return "is a path, not a bare name"
    return None


def unsafe_argument_reason(value: str) -> str | None:
    """Why this command-line argument may not be used at all, or None when it may.

    Checked BEFORE a topic is derived from it, and that order is the whole point: the basename of
    `../../etc` is the bare, apparently-safe name `etc`, so a guard applied only to the DERIVED
    topic silently normalises a traversal rather than refusing it - which is exactly what this
    tool promises not to do. An absolute path is fine (it names a worktree outright); a parent
    reference anywhere in the argument is not.
    """
    if not value.strip():
        return "is empty"
    if value in (".", "..", "~"):
        return "is a directory reference, not a worktree"
    for flavour in (PurePosixPath, PureWindowsPath):
        if any(part == ".." for part in flavour(value).parts):
            return "contains a parent reference"
    return None


def _separators() -> str:
    return os.sep + (os.altsep or "")


def looks_like_a_path(value: str) -> bool:
    """Whether the argument names a location rather than a topic.

    Only a separator (or a home shorthand) makes it a path. A bare `wt-foo` is a NAME and must
    resolve against `--base`, not against whatever directory the tool happens to be run from.
    """
    return value.startswith("~") or any(sep in value for sep in _separators())


def topic_name(value: str, *, prefix: str = DEFAULT_PREFIX) -> str:
    """The bare topic from a worktree path or name: <somewhere>/wt-foo -> foo.

    Path splitting is deliberately platform-native (`Path` is POSIX-flavoured on Linux and
    Windows-flavoured on Windows), because a backslash is a legal filename character on Linux and
    a separator on Windows. The safety check above is the union of both flavours, so a form this
    splitter leaves intact is still refused rather than mis-targeted.
    """
    name = Path(value.rstrip(_separators())).name
    return name[len(prefix):] if prefix and name.startswith(prefix) else name


# --------------------------------------------------------------------------------------------
# Deletion safety
# --------------------------------------------------------------------------------------------


def _home() -> Path | None:
    try:
        return Path.home().resolve()
    except (RuntimeError, OSError):
        return None


def refusal_for(path: Path, *, base: Path | None = None) -> str | None:
    """Why this directory must not be deleted, or None when it may be.

    `base` is passed for convention-derived targets and withheld for paths the caller named
    explicitly with `--cache-dir`: containment is a check on the convention's arithmetic, not a
    restriction on a path a person typed out in full. The symlink, root and home refusals apply
    to both.
    """
    if path.is_symlink():
        return "is a symlink - removing through it can destroy data outside it"
    try:
        resolved = path.resolve()
    except OSError as exc:
        return f"cannot be resolved: {exc}"
    if resolved.parent == resolved:
        return "is a filesystem root"
    home = _home()
    if home is not None and resolved == home:
        return "is the home directory"
    if base is None:
        return None
    try:
        base_resolved = Path(base).resolve()
    except OSError as exc:
        return f"base cannot be resolved: {exc}"
    if resolved == base_resolved:
        return "is the base directory itself"
    if not resolved.is_relative_to(base_resolved):
        return f"resolves outside {base_resolved}"
    return None


def directory_size(path: Path) -> int:
    """Bytes held by the tree, following no symlink - so the plan cannot inflate its own numbers."""
    total = 0
    for root, _dirs, files in os.walk(path, onerror=lambda _exc: None):
        for name in files:
            try:
                total += (Path(root) / name).lstat().st_size
            except OSError:
                continue
    return total


# --------------------------------------------------------------------------------------------
# The plan
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Refusal:
    """One thing that was not removed, and why.

    Kept as a (path, reason) pair rather than a formatted string because the renderer has to
    match refusals back to plan entries. Splitting a message back apart on its colon would
    mis-handle every Windows absolute path, and a report that says "removed" about something it
    refused is the same class of lie this tool exists to prevent.
    """

    path: str
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


@dataclass(frozen=True)
class CacheTarget:
    """One cache directory, its size, and why it may not be removed (None when it may)."""

    path: Path
    size_bytes: int
    refusal: str | None

    def as_dict(self) -> dict[str, object]:
        return {"path": str(self.path), "bytes": self.size_bytes, "refusal": self.refusal}


@dataclass(frozen=True)
class Plan:
    """Exactly what an `--apply` run will act on. Nothing is rediscovered at apply time."""

    topic: str
    base: Path
    convention: str
    worktree: Path
    worktree_status: str
    worktree_refusal: str | None
    caches: tuple[CacheTarget, ...]

    @property
    def total_bytes(self) -> int:
        return sum(target.size_bytes for target in self.caches)

    def as_dict(self) -> dict[str, object]:
        return {
            "topic": self.topic,
            "base": str(self.base),
            "convention": self.convention,
            "worktree": str(self.worktree),
            "worktree_status": self.worktree_status,
            "worktree_refusal": self.worktree_refusal,
            "caches": [target.as_dict() for target in self.caches],
            "total_bytes": self.total_bytes,
        }


def cache_dirs(
    topic: str,
    *,
    base: str | Path | None = None,
    prefix: str = DEFAULT_PREFIX,
    suffixes: Sequence[str] = DEFAULT_CACHE_SUFFIXES,
) -> list[Path]:
    """Convention-derived cache dirs, or [] when the name may not be interpolated into a path."""
    if unsafe_topic_reason(topic) is not None:
        return []
    root = Path(base) if base is not None else Path.home()
    return [root / f"{prefix}{topic}-{suffix}" for suffix in suffixes]


def git_worktree_status(
    worktree: Path,
    *,
    timeout: float = GIT_TIMEOUT_SECONDS,
) -> str:
    """Whether the worktree holds uncommitted or untracked work.

    `git status --porcelain` lists modified AND untracked entries, which is the same set
    `git worktree remove` refuses on, so a clean read here means git will not refuse either. Any
    failure to ask - git missing, not a worktree, a timeout - reads as STATUS_UNKNOWN rather than
    clean, because "I could not check" must never be the permissive answer for a delete.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(worktree), "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return STATUS_UNKNOWN
    if proc.returncode != 0:
        return STATUS_UNKNOWN
    return STATUS_DIRTY if (proc.stdout or "").strip() else STATUS_CLEAN


def git_worktree_remove(
    worktree: Path,
    *,
    force: bool = False,
    timeout: float = GIT_TIMEOUT_SECONDS,
) -> str | None:
    """Ask git to drop the worktree; return an error string, or None on success.

    Keyed on the exit code, never on the message: git's own refusal text is localised, so the
    string that comes back depends on the machine's language.
    """
    argv = ["git", "-C", str(worktree), "worktree", "remove", str(worktree)]
    if force:
        argv.append("--force")
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"git worktree remove timed out after {timeout}s"
    except OSError as exc:
        return str(exc)
    if proc.returncode == 0:
        return None
    return (proc.stderr or "").strip() or f"git worktree remove failed (exit {proc.returncode})"


def build_plan(
    topic: str,
    *,
    base: str | Path | None = None,
    prefix: str = DEFAULT_PREFIX,
    suffixes: Sequence[str] = DEFAULT_CACHE_SUFFIXES,
    explicit_caches: Sequence[str | Path] = (),
    worktree: str | Path | None = None,
    status_probe: Callable[[Path], str] = git_worktree_status,
) -> Plan:
    """What would be removed, with sizes and per-target refusals.

    Only paths that EXIST are listed: naming absent paths reads as work still to do and buries
    the real entries. `status_probe` is injected so the worktree state can be supplied by the
    caller (and by tests) instead of always costing a git call.
    """
    root = Path(base) if base is not None else Path.home()
    checkout = Path(worktree) if worktree is not None else root / f"{prefix}{topic}"

    targets: list[CacheTarget] = []
    for candidate in cache_dirs(topic, base=root, prefix=prefix, suffixes=suffixes):
        if candidate.exists() or candidate.is_symlink():
            targets.append(
                CacheTarget(candidate, directory_size(candidate), refusal_for(candidate, base=root))
            )
    for raw in explicit_caches:
        candidate = Path(raw).expanduser()
        if candidate.exists() or candidate.is_symlink():
            targets.append(CacheTarget(candidate, directory_size(candidate), refusal_for(candidate)))

    if not checkout.exists() and not checkout.is_symlink():
        status, refusal = STATUS_ABSENT, None
    else:
        # Same guards the cache targets get - a worktree argument that is a symlink, a filesystem
        # root, or the home directory is refused before git is asked anything about it.
        refusal = refusal_for(checkout)
        status = STATUS_UNKNOWN if refusal is not None else status_probe(checkout)

    suffix_list = ",".join(suffixes)
    return Plan(
        topic=topic,
        base=root,
        convention=f"{root}{os.sep}{prefix}{topic}-{{{suffix_list}}}",
        worktree=checkout,
        worktree_status=status,
        worktree_refusal=refusal,
        caches=tuple(targets),
    )


def worktree_refusal(
    plan: Plan,
    *,
    discard_uncommitted: bool = False,
    remove_worktree: bool = True,
) -> str | None:
    """Why the worktree will not be removed, or None when it will be (or is not being attempted).

    Returned as a reason rather than recovered by parsing a rendered message, so a path holding a
    colon (every Windows absolute path) cannot be mis-split back apart.
    """
    if not remove_worktree or plan.worktree_status == STATUS_ABSENT:
        return None
    if plan.worktree_refusal is not None:
        return plan.worktree_refusal
    if plan.worktree_status in _OVERRIDABLE_STATUSES and not discard_uncommitted:
        detail = (
            "holds uncommitted or untracked work"
            if plan.worktree_status == STATUS_DIRTY
            else "state could not be read (git unavailable, or not a worktree)"
        )
        return f"{detail} - pass --discard-uncommitted to remove it anyway"
    return None


def blocked_reasons(
    plan: Plan,
    *,
    discard_uncommitted: bool = False,
    remove_worktree: bool = True,
) -> list[Refusal]:
    """Everything the plan cannot carry out, in the order it would be attempted.

    One function answers this for BOTH the dry run and `--apply`, so the dry run cannot promise
    something the apply then refuses.
    """
    reason = worktree_refusal(
        plan, discard_uncommitted=discard_uncommitted, remove_worktree=remove_worktree
    )
    blocked = [Refusal(str(plan.worktree), reason)] if reason is not None else []
    blocked += [Refusal(str(t.path), t.refusal) for t in plan.caches if t.refusal is not None]
    return blocked


def apply_plan(
    plan: Plan,
    *,
    discard_uncommitted: bool = False,
    remove_worktree: bool = True,
    git_remove: Callable[..., str | None] = git_worktree_remove,
) -> list[Refusal]:
    """Remove EXACTLY what the plan listed; return what could not be removed.

    Nothing is rediscovered here. A cache directory created between planning and applying is not
    deleted, and one deleted in between is reported rather than silently skipped, because the
    numbers a person approved must be the numbers that get acted on.
    """
    failures = blocked_reasons(
        plan, discard_uncommitted=discard_uncommitted, remove_worktree=remove_worktree
    )
    attempt_worktree = (
        remove_worktree
        and plan.worktree_status != STATUS_ABSENT
        and worktree_refusal(
            plan, discard_uncommitted=discard_uncommitted, remove_worktree=remove_worktree
        )
        is None
    )
    if attempt_worktree:
        error = git_remove(plan.worktree, force=discard_uncommitted)
        if error:
            failures.append(Refusal(str(plan.worktree), error))

    for target in plan.caches:
        if target.refusal is not None:
            continue
        try:
            shutil.rmtree(target.path)
        except OSError as exc:
            failures.append(Refusal(str(target.path), str(exc)))
    return failures


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------


def _human(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wtclean",
        description=(
            "Remove a git worktree and the per-topic build caches it leaves behind. "
            "Dry run unless --apply."
        ),
        epilog=(
            "Cache locations are a CONVENTION, not a discovery: git cannot be asked where your "
            "build cache lives. The default candidates are <base>/<prefix><topic>-<suffix>, i.e. "
            "~/wt-<topic>-target and ~/wt-<topic>-clippy. If yours live elsewhere, pass "
            "--cache-dir (exact paths, repeatable) or adjust --base/--prefix/--cache-suffix; a "
            "run that matches nothing says which paths it checked. Symlinked targets, and "
            "worktrees holding uncommitted or untracked work, are refused."
        ),
    )
    parser.add_argument("topic", help="the topic name, or the path of the worktree")
    parser.add_argument(
        "--base",
        help="directory holding the caches, and the worktree when a bare name is given"
        " (default: your home directory)",
    )
    parser.add_argument(
        "--prefix", default=DEFAULT_PREFIX, help=f"worktree name prefix (default: {DEFAULT_PREFIX})"
    )
    parser.add_argument(
        "--cache-suffix",
        action="append",
        metavar="SUFFIX",
        help="cache dir suffix, repeatable (default: "
        + " and ".join(DEFAULT_CACHE_SUFFIXES)
        + ")",
    )
    parser.add_argument(
        "--cache-dir",
        action="append",
        default=[],
        metavar="DIR",
        help="an exact cache directory, repeatable - use when your layout is not the convention",
    )
    parser.add_argument(
        "--apply", action="store_true", help="actually remove (default is a dry run)"
    )
    parser.add_argument(
        "--skip-worktree", action="store_true", help="the caches only; leave the worktree alone"
    )
    parser.add_argument(
        "--discard-uncommitted",
        action="store_true",
        help="remove the worktree even when it holds uncommitted or untracked work,"
        " DISCARDING that work (forwards --force to git worktree remove)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable envelope")
    return parser


def _render(
    plan: Plan, *, applied: bool, remove_worktree: bool, blocked: list[Refusal]
) -> list[str]:
    """The removal lines, listing ONLY what is actually going (or actually went).

    Anything in `blocked` is excluded by exact path, so a run that refused the worktree never
    reports having removed it.
    """
    verb = "removed" if applied else "would remove"
    blocked_paths = {refusal.path for refusal in blocked}
    lines: list[str] = []
    if (
        remove_worktree
        and plan.worktree_status != STATUS_ABSENT
        and str(plan.worktree) not in blocked_paths
    ):
        lines.append(f"  {verb}: {plan.worktree}  (worktree, {plan.worktree_status})")
    removed = [t for t in plan.caches if t.refusal is None and str(t.path) not in blocked_paths]
    for target in removed:
        lines.append(f"  {verb}: {target.path}  ({_human(target.size_bytes)})")
    if not lines and not blocked:
        lines.append("  nothing to remove")
    elif removed:
        tail = "" if applied else " - re-run with --apply"
        lines.append(f"\n  {_human(sum(t.size_bytes for t in removed))} of build cache{tail}")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    warnings: list[str] = []

    def warn(message: str) -> None:
        # Always stderr, --json included, so stdout stays a clean parseable envelope.
        warnings.append(message)
        print(f"wtclean: {message}", file=sys.stderr)

    given = args.topic
    reason = unsafe_argument_reason(given)
    if reason is not None:
        print(f"wtclean: refusing {given!r} - it {reason}", file=sys.stderr)
        return 2
    topic = topic_name(given, prefix=args.prefix)
    reason = unsafe_topic_reason(topic)
    if reason is not None:
        print(f"wtclean: refusing topic {topic!r} - it {reason}", file=sys.stderr)
        return 2

    base = Path(args.base).expanduser() if args.base else None
    suffixes = tuple(args.cache_suffix) if args.cache_suffix else DEFAULT_CACHE_SUFFIXES

    plan = build_plan(
        topic,
        base=base,
        prefix=args.prefix,
        suffixes=suffixes,
        explicit_caches=args.cache_dir,
        worktree=Path(given).expanduser() if looks_like_a_path(given) else None,
    )
    if not plan.caches and not args.cache_dir:
        warn(
            f"no cache directory matched the convention {plan.convention} - if yours live"
            " elsewhere pass --cache-dir, or adjust --base/--prefix/--cache-suffix"
        )

    remove_worktree = not args.skip_worktree
    blocked = blocked_reasons(
        plan, discard_uncommitted=args.discard_uncommitted, remove_worktree=remove_worktree
    )

    if args.apply:
        blocked = apply_plan(
            plan,
            discard_uncommitted=args.discard_uncommitted,
            remove_worktree=remove_worktree,
            git_remove=git_worktree_remove,
        )

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not blocked,
                    "command": "wtclean",
                    "skipped": warnings + [str(item) for item in blocked],
                    "data": {"applied": args.apply, **plan.as_dict()},
                },
                indent=2,
            )
        )
    else:
        for line in _render(
            plan, applied=args.apply, remove_worktree=remove_worktree, blocked=blocked
        ):
            print(line)
        for item in blocked:
            print(f"  REFUSED: {item}" if not args.apply else f"  FAILED: {item}", file=sys.stderr)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
