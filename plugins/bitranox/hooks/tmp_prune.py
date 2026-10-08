"""Prune dead directories from the system temp dir: Claude Code session scratch and old one-offs.

Claude Code gives every session a scratch dir, `<temp>/claude-<uid>/<project>/<session-id>/`, and
never removes it. On a tmpfs with a fixed inode cap those dirs fill the table until every file
create fails with "No space left on device" while `df -h` still shows free bytes. This module
decides which of them, and which other old dirs the user owns in the temp dir, nothing can still
use, and deletes those. It is started detached by `tmp-prune-hook.py` (SessionStart and Stop, at
most once an hour machine-wide); run it by hand for a dry run:

    python3 tmp_prune.py --json            # what it would delete
    python3 tmp_prune.py --apply --json    # delete it

What is dead:

* a SCRATCH dir when no live session in `~/.claude/sessions` carries its id, nothing inside it
  changed for a day, its transcript (`~/.claude/projects/<project>/<id>.jsonl`) has not changed
  for a day either, and no process holds a file in it;
* a ONE-OFF dir (a direct child of the temp dir the user owns, other than the scratch root and
  `pytest-of-*`, which pytest prunes itself) when nothing inside changed for seven days and no
  process holds a file in it.

Either kind is kept when it holds a socket or a FIFO (something may still connect to it), when
another filesystem is mounted inside it, and whenever an answer is unknowable: an unreadable
session registry keeps every scratch dir, and a platform with no way to see which files processes
hold keeps every one-off.

Where the scratch lives follows Claude Code itself: `CLAUDE_CODE_TMPDIR` when set, else `/tmp` on
macOS and the system temp dir on Linux and Windows. With an override set, the system temp dir is
scanned too, because Claude Code falls back to it for a child process when the override path is
long. On Windows, where there is no uid, both `claude-0` (what the CLI's own code builds) and
`claude` (what its documentation says) are accepted.

Which files a process holds is read from `/proc` on Linux (fd, cwd, root and memory maps - an
mmapped file holds no fd) and from `lsof` on macOS. Windows has neither, so there a dir is renamed
before it is deleted: Windows refuses to rename a directory while a process has a file inside it
open, so a failed rename means "in use" and the dir is left alone.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from process_liveness import LiveSessions, live_session_ids  # noqa: E402 - needs the sys.path line above

__all__ = [
    "INTERVAL_SECONDS",
    "LOCK_NAME",
    "LOG_NAME",
    "ApplyResult",
    "Decision",
    "HolderIndex",
    "PruneConfig",
    "apply",
    "claim_slot",
    "main",
    "plan",
    "release_slot",
    "scratch_bases",
    "scratch_dir_names",
]

DAY = 86400.0
INTERVAL_SECONDS = 3600.0
# A prune that runs longer than this is taken to have crashed, so its lock stops blocking others.
STALE_LOCK_SECONDS = 2 * 3600.0
LOCK_NAME = "tmp-prune.lock"
LAST_NAME = "tmp-prune.last"
LOG_NAME = "tmp-prune.log.jsonl"
LOG_KEEP_LINES = 500

SCRATCH = "scratch"
ONEOFF = "oneoff"

_SESSION_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
# Never one-offs: pytest prunes its own basetemp, and the rest are Claude Code's own runtime dirs.
_ONEOFF_EXCLUDED_PREFIXES = ("pytest-of-", "claude-", "cc-socks", "cc-daemon-")


# ---- configuration --------------------------------------------------------------------------


def scratch_dir_names(uid: int | None) -> tuple[str, ...]:
    """The scratch root's name under a temp base: `claude-<uid>`, or both Windows spellings."""
    if uid is None:
        return ("claude-0", "claude")
    return (f"claude-{uid}",)


def scratch_bases(env: Mapping[str, str], platform: str, system_tmp: str) -> tuple[Path, ...]:
    """Every temp base Claude Code may have put session scratch under, most specific first."""
    default = Path("/tmp") if platform == "darwin" else Path(system_tmp)
    override = env.get("CLAUDE_CODE_TMPDIR")
    if override and Path(override) != default:
        return (Path(override), default)
    return (default,)


@dataclass(frozen=True)
class PruneConfig:
    """Where to look and what counts as old. Every path is injectable, so tests use real trees."""

    scratch_bases: tuple[Path, ...]
    oneoff_base: Path
    projects_dir: Path
    sessions_dir: Path
    uid: int | None
    now: float
    keep_sessions: frozenset[str] = frozenset()
    scratch_max_age: float = DAY
    oneoff_max_age: float = 7 * DAY

    @classmethod
    def for_this_machine(cls, *, keep_sessions: frozenset[str] = frozenset()) -> PruneConfig:
        system_tmp = tempfile.gettempdir()
        home = Path.home() / ".claude"
        return cls(
            scratch_bases=scratch_bases(os.environ, sys.platform, system_tmp),
            oneoff_base=Path("/tmp") if sys.platform == "darwin" else Path(system_tmp),
            projects_dir=home / "projects",
            sessions_dir=home / "sessions",
            uid=os.getuid() if hasattr(os, "getuid") else None,
            now=time.time(),
            keep_sessions=keep_sessions,
        )

    def max_age(self, kind: str) -> float:
        return self.scratch_max_age if kind == SCRATCH else self.oneoff_max_age


# ---- what a directory holds -----------------------------------------------------------------


@dataclass(frozen=True)
class TreeScan:
    """What one walk of a directory saw. `unreadable` and `foreign_mount` make its age unknowable."""

    newest: float
    inodes: int
    has_ipc: bool
    unreadable: bool
    foreign_mount: bool


def scan_tree(path: Path) -> TreeScan:
    """Walk `path` without following symlinks or crossing into another filesystem."""
    top = os.lstat(path)
    newest, inodes = top.st_mtime, 1
    has_ipc = unreadable = foreign_mount = False
    stack = [str(path)]
    while stack:
        try:
            entries = list(os.scandir(stack.pop()))
        except OSError:
            unreadable = True
            continue
        for entry in entries:
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError:
                unreadable = True
                continue
            inodes += 1
            newest = max(newest, info.st_mtime)
            has_ipc = has_ipc or stat.S_ISSOCK(info.st_mode) or stat.S_ISFIFO(info.st_mode)
            if not stat.S_ISDIR(info.st_mode):
                continue
            if info.st_dev != top.st_dev:
                foreign_mount = True
                continue
            stack.append(entry.path)
    return TreeScan(newest, inodes, has_ipc, unreadable, foreign_mount)


# ---- which files processes hold -------------------------------------------------------------


@dataclass(frozen=True)
class HolderIndex:
    """Every path some process holds open, mapped or sits in, read once per run.

    `method` names how it was read: `procfs`, `lsof`, `rename` (Windows: probe at delete time) or
    `none`. `held()` answers None whenever the method cannot answer for one path up front.
    """

    method: str
    paths: tuple[str, ...] = ()

    @classmethod
    def build(cls, cfg: PruneConfig) -> HolderIndex:
        if os.name == "nt":
            return cls("rename")
        if Path("/proc/self/fd").is_dir():
            return cls("procfs", tuple(_procfs_held_paths()))
        held = _lsof_held_paths(cfg.uid)
        if held is None:
            return cls("none")
        return cls("lsof", tuple(held))

    def held(self, path: Path) -> bool | None:
        if self.method in ("rename", "none"):
            return None
        target = os.path.realpath(path)
        prefix = target.rstrip(os.sep) + os.sep
        return any(p == target or p.startswith(prefix) for p in self.paths)


def _procfs_held_paths() -> Iterator[str]:
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        base = f"/proc/{pid}"
        yield from _readlinks([f"{base}/cwd", f"{base}/root"])
        try:
            fds = [f"{base}/fd/{fd}" for fd in os.listdir(f"{base}/fd")]
        except OSError:
            fds = []
        yield from _readlinks(fds)
        yield from _mapped_paths(f"{base}/maps")


def _readlinks(links: Sequence[str]) -> Iterator[str]:
    for link in links:
        try:
            target = os.readlink(link)
        except OSError:
            continue
        # The root of every ordinary process is "/", which would "hold" every path there is.
        if target.startswith("/") and target != "/":
            yield target.removesuffix(" (deleted)")


def _mapped_paths(maps: str) -> Iterator[str]:
    try:
        with open(maps, encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return
    for line in lines:
        parts = line.split(None, 5)
        if len(parts) == 6 and parts[5].startswith("/"):
            yield parts[5].rstrip("\n").removesuffix(" (deleted)")


def _lsof_held_paths(uid: int | None) -> list[str] | None:
    """Every name `lsof` reports for the user's processes, or None when lsof cannot answer."""
    lsof = shutil.which("lsof")
    if lsof is None or uid is None:
        return None
    try:
        proc = subprocess.run(
            [lsof, "-n", "-P", "-F", "n", "-u", str(uid)],
            capture_output=True, encoding="utf-8", errors="replace", timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    # lsof exits 1 when some requested item had nothing to report; anything else is a failure.
    if proc.returncode not in (0, 1) or not proc.stdout:
        return None
    return [line[1:] for line in proc.stdout.splitlines() if line.startswith("n/")]


# ---- the decision ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    path: Path
    kind: str
    prune: bool
    reason: str
    inodes: int
    transcript: Path | None = None


def plan(cfg: PruneConfig) -> list[Decision]:
    """Judge every candidate directory. Reads only; deletes nothing."""
    live = live_session_ids(cfg.sessions_dir)
    holders = HolderIndex.build(cfg)
    return [_decide(cfg, path, kind, transcript, live, holders) for path, kind, transcript in _candidates(cfg)]


def _candidates(cfg: PruneConfig) -> Iterator[tuple[Path, str, Path | None]]:
    for root in _scratch_roots(cfg):
        for project in _child_dirs(root):
            for session in _child_dirs(project):
                if _SESSION_ID.match(session.name):
                    yield session, SCRATCH, cfg.projects_dir / project.name / f"{session.name}.jsonl"
    for child in _child_dirs(cfg.oneoff_base):
        if _is_oneoff(cfg, child):
            yield child, ONEOFF, None


def _scratch_roots(cfg: PruneConfig) -> list[Path]:
    roots: list[Path] = []
    for base in cfg.scratch_bases:
        roots.extend(base / name for name in scratch_dir_names(cfg.uid))
    return list(dict.fromkeys(roots))


def _child_dirs(path: Path) -> list[Path]:
    try:
        entries = list(os.scandir(path))
    except OSError:
        return []
    return sorted(Path(e.path) for e in entries if e.is_dir(follow_symlinks=False))


def _is_oneoff(cfg: PruneConfig, path: Path) -> bool:
    if path.name.startswith(_ONEOFF_EXCLUDED_PREFIXES) or path.name in scratch_dir_names(cfg.uid):
        return False
    if cfg.uid is None:
        return True  # a Windows temp dir is per user, so whatever is in it is the user's
    try:
        return os.lstat(path).st_uid == cfg.uid
    except OSError:
        return False


def _decide(
    cfg: PruneConfig, path: Path, kind: str, transcript: Path | None, live: LiveSessions, holders: HolderIndex
) -> Decision:
    try:
        scan = scan_tree(path)
    except OSError as exc:
        return Decision(path, kind, False, f"vanished or unreadable ({exc.strerror or exc})", 0, transcript)
    reason = _keep_reason(cfg, path, kind, scan, transcript, live, holders)
    return Decision(path, kind, reason is None, reason or "dead", scan.inodes, transcript)


def _keep_reason(
    cfg: PruneConfig,
    path: Path,
    kind: str,
    scan: TreeScan,
    transcript: Path | None,
    live: LiveSessions,
    holders: HolderIndex,
) -> str | None:
    """Why this directory must stay, or None when nothing can still use it."""
    if kind == SCRATCH:
        session_reason = _session_keep_reason(cfg, path, transcript, live)
        if session_reason:
            return session_reason
    age_reason = _content_keep_reason(cfg, kind, scan)
    if age_reason:
        return age_reason
    held = holders.held(path)
    if held:
        return "held open by a running process"
    if held is None and kind == ONEOFF and holders.method == "none":
        return "no way to check which files processes hold on this platform"
    return None


def _session_keep_reason(cfg: PruneConfig, path: Path, transcript: Path | None, live: LiveSessions) -> str | None:
    if path.name in cfg.keep_sessions or path.name in live.ids:
        return "belongs to a live session"
    if live.uncertain:
        return "session registry has an unreadable entry, so any session could be live"
    if transcript is not None and _changed_within(transcript, cfg.now, cfg.scratch_max_age):
        return "its session transcript changed recently"
    return None


def _content_keep_reason(cfg: PruneConfig, kind: str, scan: TreeScan) -> str | None:
    if scan.foreign_mount:
        return "another filesystem is mounted inside it"
    if cfg.now - scan.newest < cfg.max_age(kind):
        return "something inside changed recently"
    if scan.has_ipc:
        return "holds a socket or fifo something may still connect to"
    if scan.unreadable and kind == ONEOFF:
        return "some entries could not be read, so its age is unknown"
    return None


def _changed_within(path: Path, now: float, window: float) -> bool:
    try:
        return now - os.stat(path).st_mtime < window
    except OSError:
        return False


# ---- applying -------------------------------------------------------------------------------


@dataclass
class ApplyResult:
    examined_dirs: int = 0
    removed_dirs: int = 0
    removed_inodes: int = 0
    kept_dirs: int = 0
    holder_check: str = ""
    failures: list[str] = field(default_factory=list)
    removed: list[dict[str, object]] = field(default_factory=list)


def apply(cfg: PruneConfig, decisions: Sequence[Decision], *, dry_run: bool = False) -> ApplyResult:
    """Delete what `decisions` prunes, re-judging each directory immediately before it goes."""
    result = ApplyResult(examined_dirs=len(decisions))
    project_mtimes = _project_mtimes(cfg)
    live = live_session_ids(cfg.sessions_dir)
    holders = HolderIndex.build(cfg)
    result.holder_check = holders.method
    fresh = replace(cfg, now=time.time()) if not dry_run else cfg
    for decision in decisions:
        if not decision.prune:
            result.kept_dirs += 1
            continue
        current = _decide(fresh, decision.path, decision.kind, decision.transcript, live, holders)
        if not current.prune:
            result.kept_dirs += 1
            continue
        if dry_run or _remove(decision.path, result):
            result.removed_dirs += 1
            result.removed_inodes += current.inodes
            result.removed.append({"path": str(decision.path), "kind": decision.kind, "inodes": current.inodes})
    if not dry_run:
        _remove_empty_projects(cfg, project_mtimes)
    return result


def _remove(path: Path, result: ApplyResult) -> bool:
    target = path
    if os.name == "nt":
        target = path.with_name(f"{path.name}.pruning-{os.getpid()}")
        try:
            os.rename(path, target)
        except OSError:
            return False  # Windows refuses the rename while a process has a file inside open
    _make_removable(target)
    errors: list[str] = []

    def retry(func: object, failed: str, _exc: object) -> None:
        _retry_writable(func, failed, errors)

    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(target, onexc=retry)
        else:  # onexc arrived in 3.12; onerror is deprecated from there on
            shutil.rmtree(target, onerror=retry)
    except OSError as exc:
        errors.append(f"{target}: {exc.strerror or exc}")
    if errors or target.exists():
        result.failures.append(f"{path}: {errors[0] if errors else 'still present'}")
        return False
    return True


def _make_removable(path: Path) -> None:
    """Give the owner rwx on every directory first: a mode-000 fixture dir stops rmtree with EACCES.

    Top-down, so each directory is opened up before the walk tries to list it.
    """
    _grant_owner_rwx(str(path))
    for root, dirs, _files in os.walk(path, topdown=True):
        for name in (os.path.join(root, d) for d in dirs):
            _grant_owner_rwx(name)


def _grant_owner_rwx(name: str) -> None:
    try:
        info = os.lstat(name)
        if stat.S_ISDIR(info.st_mode) and info.st_mode & 0o700 != 0o700:
            os.chmod(name, info.st_mode | 0o700)
    except OSError:
        return


_RETRYABLE = (os.unlink, os.remove, os.rmdir)


def _retry_writable(func: object, path: str, errors: list[str]) -> None:
    """A read-only file blocks deletion on Windows: clear the flag and retry a REMOVAL once.

    Only a removal is retried. rmtree also reports failures of calls that take more than a path
    (`os.open(path, flags, dir_fd=...)`, `os.scandir`), and re-calling those with one argument
    raises TypeError, which would escape rmtree and abort every directory after this one.
    """
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        if func in _RETRYABLE:
            func(path)  # type: ignore[operator]
            return
    except OSError as exc:
        errors.append(f"{path}: {exc.strerror or exc}")
        return
    errors.append(f"{path}: could not be removed")


def _project_mtimes(cfg: PruneConfig) -> dict[Path, float]:
    """Project dirs and their mtime BEFORE anything is deleted - deleting a child resets it."""
    mtimes: dict[Path, float] = {}
    for root in _scratch_roots(cfg):
        for project in _child_dirs(root):
            try:
                mtimes[project] = os.lstat(project).st_mtime
            except OSError:
                continue
    return mtimes


def _remove_empty_projects(cfg: PruneConfig, mtimes: Mapping[Path, float]) -> None:
    for project, mtime in mtimes.items():
        if cfg.now - mtime < cfg.scratch_max_age:
            continue  # a session may be about to create its dir there
        try:
            os.rmdir(project)  # refuses unless empty
        except OSError:
            continue


# ---- the machine-wide throttle --------------------------------------------------------------


def claim_slot(state_dir: Path, *, now: float, interval: float = INTERVAL_SECONDS) -> bool:
    """True when this caller may start a prune: none ran in the last `interval`, none is running."""
    state_dir.mkdir(parents=True, exist_ok=True)
    if _age(state_dir / LAST_NAME, now) < interval:
        return False
    lock = state_dir / LOCK_NAME
    if not _create_exclusive(lock, now):
        if _age(lock, now) < STALE_LOCK_SECONDS:
            return False
        lock.unlink(missing_ok=True)
        if not _create_exclusive(lock, now):
            return False
    last = state_dir / LAST_NAME
    last.write_text(f"{now}\n", encoding="utf-8")
    os.utime(last, (now, now))
    return True


def release_slot(state_dir: Path) -> None:
    (state_dir / LOCK_NAME).unlink(missing_ok=True)


def _create_exclusive(path: Path, now: float) -> bool:
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    os.write(fd, f"{os.getpid()}\n".encode())
    os.close(fd)
    os.utime(path, (now, now))
    return True


def _age(path: Path, now: float) -> float:
    try:
        return now - os.stat(path).st_mtime
    except OSError:
        return float("inf")


# ---- the CLI --------------------------------------------------------------------------------


def default_state_dir() -> Path:
    return Path.home() / ".claude" / "self-improve-audit"


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prune dead temp dirs (dry run unless --apply).")
    parser.add_argument("--apply", action="store_true", help="delete; without it nothing is removed")
    parser.add_argument("--json", action="store_true", help="print a JSON envelope")
    parser.add_argument("--keep-session", action="append", default=[], help="a session id never to prune")
    parser.add_argument("--release-slot", action="store_true", help="release the throttle lock when done")
    parser.add_argument("--scratch-base", action="append", type=Path, help="temp base holding claude-<uid>/")
    parser.add_argument("--oneoff-base", type=Path, help="temp dir whose old children are one-offs")
    parser.add_argument("--projects-dir", type=Path, help="Claude Code transcript dir")
    parser.add_argument("--sessions-dir", type=Path, help="Claude Code session registry")
    parser.add_argument("--state-dir", type=Path, default=None, help="where the run log and lock live")
    return parser.parse_args(argv)


def _config_from(args: argparse.Namespace) -> PruneConfig:
    cfg = PruneConfig.for_this_machine(keep_sessions=frozenset(args.keep_session))
    overrides: dict[str, object] = {}
    if args.scratch_base:
        overrides["scratch_bases"] = tuple(args.scratch_base)
    for name in ("oneoff_base", "projects_dir", "sessions_dir"):
        if getattr(args, name) is not None:
            overrides[name] = getattr(args, name)
    return replace(cfg, **overrides)  # type: ignore[arg-type]


def _summary(cfg: PruneConfig, result: ApplyResult, *, dry_run: bool) -> dict[str, object]:
    return {
        "ts": cfg.now,
        "dry_run": dry_run,
        "holder_check": result.holder_check,
        "examined_dirs": result.examined_dirs,
        "removed_dirs": result.removed_dirs,
        "removed_inodes": result.removed_inodes,
        "kept_dirs": result.kept_dirs,
        "failures": result.failures[:20],
    }


def _append_log(state_dir: Path, record: Mapping[str, object]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    log = state_dir / LOG_NAME
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    lines = [*lines[-(LOG_KEEP_LINES - 1) :], json.dumps(record, sort_keys=True)]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(sys.argv[1:] if argv is None else argv)
    state_dir = args.state_dir or default_state_dir()
    try:
        cfg = _config_from(args)
        result = apply(cfg, plan(cfg), dry_run=not args.apply)
        summary = _summary(cfg, result, dry_run=not args.apply)
        _append_log(state_dir, summary)
        listed = {**summary, "removed": result.removed}  # the log stays counts-only
    except Exception as exc:  # noqa: BLE001 - a detached worker has no one to raise to; report it
        _emit(args.json, {"ok": False, "command": "tmp_prune", "data": {"error": repr(exc)}, "skipped": []})
        return 2
    finally:
        if args.release_slot:
            release_slot(state_dir)
    _emit(args.json, {"ok": True, "command": "tmp_prune", "data": listed, "skipped": []})
    return 0


def _emit(as_json: bool, envelope: Mapping[str, object]) -> None:
    if as_json:
        print(json.dumps(envelope, sort_keys=True))
        return
    data = envelope["data"]
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
