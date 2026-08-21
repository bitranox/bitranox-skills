# /// script
# requires-python = ">=3.10"
# ///
"""Reclaim the disk a Claude Code plugin cache keeps, without breaking a running session.

`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` keeps a FULL copy per version and
never drops one, so the marketplace you publish to grows by a whole plugin on every release.
Beside it sit `temp_subdir_*.clone` and `temp_git_*` directories - temporary clones from
marketplace add/update operations that a crashed or killed operation abandons.

The load-bearing question is which versions are still in use, and the cache answers it itself:
each version directory carries an `.in_use/<pid>` lock holding `{"pid":N,"procStart":"..."}`,
written by every Claude Code process that loaded it. So "is a live session using this version"
is a file to read, not something to infer from `lsof` (hooks are launched per invocation and
hold nothing open between calls, so an open-file search finds nothing and reads as "free").

A lock is only evidence while its process lives. `procStart` is the process start time, carried
precisely so a REUSED pid does not look like the original holder; a lock whose pid is gone, or
whose start time disagrees, is stale and keeps nothing.

Dry run by DEFAULT. This deletes directories and there is no undo, so it prints the plan with
sizes and does nothing until `--apply`. `--apply` removes EXACTLY what the plan listed - it does
not re-scan for new candidates - because a plan that does not match what gets deleted is how a
delete tool surprises someone. The listed set can only SHRINK: a session that starts between the
plan and the apply claims its version, and that directory is then refused rather than removed.

Kept, with the reason stated per directory:

* the installed version, from the `installPath` in `installed_plugins.json` (what a fresh
  session resolves to);
* any version with a LIVE `.in_use` lock (a session running right now, this one included);
* any version whose path appears in a settings file, which pins it;
* the SOLE version of a plugin a settings file's `enabledPlugins` names, however it is set -
  disabled is not uninstalled, and its cache is still wanted. `enabledPlugins` names a plugin,
  never a version, so it cannot choose between several. The settings files are the user's pair
  PLUS the same pair inside every project `~/.claude.json` lists, because a plugin enabled only
  in a project may have no `installPath` record at all;
* a `temp_*` directory younger than `--min-age` (default 60m), because an operation may be
  in flight.

A plugin nothing references at all is prunable even as the only version: that is what an
uninstalled plugin leaves behind, and no other pass reclaims it.

Refusals, because this runs on machines whose layout is not yours: a symlinked directory, a path
that resolves outside the cache, and the cache directory itself are refused outright. So is every
version directory when NOT ONE of them carries an `.in_use` directory - an idle machine leaves
that directory behind empty, so its total absence means the mechanism was renamed or dropped and
every version would silently read as unused. `--allow-missing-locks` overrides that.

Run:
  `uv run scripts/pluginprune.py`                        # the plan, with sizes
  `uv run scripts/pluginprune.py --apply`                # remove exactly what the plan listed
  `uv run scripts/pluginprune.py --marketplace my-mkt`   # one marketplace only
  `uv run scripts/pluginprune.py --keep ~/.claude/plugins/cache/m/p/1.2.3 --apply`
  `uv run scripts/pluginprune.py --json`

Exit codes: 0 = nothing blocked (a dry-run plan that can be carried out as-is, or an `--apply`
that removed everything it listed), 1 = something was refused or could not be removed, 2 = usage
error. `--json` emits the machine-readable envelope; warnings always go to stderr so stdout
stays parseable.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

__all__ = [
    "Entry",
    "Plan",
    "apply_plan",
    "build_plan",
    "live_lock_holder",
    "main",
    "pid_alive",
    "process_start_ticks",
]

DEFAULT_MIN_AGE_SECONDS = 3600
TEMP_PREFIX = "temp_"
LOCK_DIR = ".in_use"
INSTALLED_PLUGINS = "installed_plugins.json"
SETTINGS_NAMES = ("settings.json", "settings.local.json")

KIND_VERSION = "version"
KIND_TEMP = "temp"


# --------------------------------------------------------------------------------------------
# Is that process still there?
# --------------------------------------------------------------------------------------------


def pid_alive(pid: int) -> bool:
    """True when the process exists. Unknowable counts as alive - keeping costs disk, not a session."""
    if pid <= 0:
        return False
    if os.name == "nt":
        return _windows_pid_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _windows_pid_alive(pid: int) -> bool:
    import ctypes  # noqa: PLC0415 - Windows-only, and ctypes.windll does not exist elsewhere

    process_query_limited_information = 0x1000
    still_active = 259
    error_access_denied = 5
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return bool(kernel32.GetLastError() == error_access_denied)
    try:
        code = ctypes.c_ulong()
        if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return bool(code.value == still_active)
        return True
    finally:
        kernel32.CloseHandle(handle)


def process_start_ticks(pid: int) -> str | None:
    """The process start time as Claude Code records it, or None when this OS cannot say.

    Field 22 of `/proc/<pid>/stat`. The command name in field 2 may itself contain spaces and
    parentheses, so the split starts after its CLOSING paren rather than at the first space.
    """
    try:
        raw = Path("/proc") / str(pid) / "stat"
        text = raw.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    close = text.rfind(")")
    if close == -1:
        return None
    fields = text[close + 1 :].split()
    if len(fields) < 20:
        return None
    return fields[19]


def live_lock_holder(version_dir: Path) -> str | None:
    """Why a live process still holds this version, or None when every lock is stale.

    An unreadable lock counts as live: the safe direction is to keep a directory that might be
    in use, never to delete one because its marker could not be parsed.
    """
    lock_dir = version_dir / LOCK_DIR
    try:
        locks = sorted(lock_dir.iterdir())
    except OSError:
        return None
    for lock in locks:
        if lock.is_dir():
            continue
        pid, recorded_start = _read_lock(lock)
        if pid is None:
            return f"in use (unreadable lock {lock.name})"
        if not pid_alive(pid):
            continue
        actual_start = process_start_ticks(pid)
        if recorded_start is not None and actual_start is not None and recorded_start != actual_start:
            continue  # the pid was reused - this is a different process
        return f"in use by pid {pid}"
    return None


def _read_lock(lock: Path) -> tuple[int | None, str | None]:
    """(pid, recorded start time). The FILENAME is the pid, so a corrupt body still identifies it."""
    pid: int | None = None
    if lock.name.isdigit():
        pid = int(lock.name)
    try:
        payload = json.loads(lock.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return pid, None
    if not isinstance(payload, dict):
        return pid, None
    raw_pid = payload.get("pid")
    if isinstance(raw_pid, int):
        pid = raw_pid
    elif isinstance(raw_pid, str) and raw_pid.isdigit():
        pid = int(raw_pid)
    start = payload.get("procStart")
    return pid, str(start) if start is not None else None


# --------------------------------------------------------------------------------------------
# The plan
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    """One cache directory: what it is, what it costs, and why it stays (None when it goes)."""

    path: Path
    kind: str
    size_bytes: int
    keep_reason: str | None = None
    refusal: str | None = None
    marketplace: str | None = None
    plugin: str | None = None
    version: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "kind": self.kind,
            "bytes": self.size_bytes,
            "keep_reason": self.keep_reason,
            "refusal": self.refusal,
            "marketplace": self.marketplace,
            "plugin": self.plugin,
            "version": self.version,
        }


@dataclass(frozen=True)
class Plan:
    """Exactly what an `--apply` run will act on. Nothing is rediscovered at apply time."""

    cache_dir: Path
    entries: tuple[Entry, ...]
    saw_live_lock: bool
    saw_lock_dir: bool = True
    settings_files: tuple[Path, ...] = ()

    @property
    def refused(self) -> tuple[Entry, ...]:
        return tuple(entry for entry in self.entries if entry.refusal is not None)

    @property
    def keep(self) -> tuple[Entry, ...]:
        return tuple(
            entry
            for entry in self.entries
            if entry.refusal is None and entry.keep_reason is not None
        )

    @property
    def prune(self) -> tuple[Entry, ...]:
        return tuple(
            entry for entry in self.entries if entry.refusal is None and entry.keep_reason is None
        )

    @property
    def reclaimable_bytes(self) -> int:
        return sum(entry.size_bytes for entry in self.prune)

    def as_dict(self) -> dict[str, object]:
        return {
            "cache_dir": str(self.cache_dir),
            "prune": [entry.as_dict() for entry in self.prune],
            "keep": [entry.as_dict() for entry in self.keep],
            "refused": [entry.as_dict() for entry in self.refused],
            "reclaimable_bytes": self.reclaimable_bytes,
            "saw_live_lock": self.saw_live_lock,
            "saw_lock_dir": self.saw_lock_dir,
            "settings_files": [str(path) for path in self.settings_files],
        }


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


def refusal_for(path: Path, *, base: Path) -> str | None:
    """Why this directory must not be deleted, or None when it may be."""
    if path.is_symlink():
        return "is a symlink - removing through it can destroy data outside it"
    try:
        resolved = path.resolve()
        base_resolved = base.resolve()
    except OSError as exc:
        return f"cannot be resolved: {exc}"
    if resolved.parent == resolved:
        return "is a filesystem root"
    if resolved == base_resolved:
        return "is the cache directory itself"
    if not resolved.is_relative_to(base_resolved):
        return f"resolves outside {base_resolved}"
    return None


def installed_paths(installed_plugins: Path) -> set[str]:
    """Every `installPath` in installed_plugins.json - what a FRESH session resolves to."""
    try:
        payload = json.loads(installed_plugins.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    plugins = payload.get("plugins") if isinstance(payload, dict) else None
    if not isinstance(plugins, dict):
        return set()
    found: set[str] = set()
    for records in plugins.values():
        for record in records if isinstance(records, list) else []:
            if isinstance(record, dict) and isinstance(record.get("installPath"), str):
                found.add(os.path.normpath(record["installPath"]))
    return found


def pinning_settings(path: Path, settings_files: Iterable[Path]) -> str | None:
    """The settings file that names this exact directory, or None when nothing pins it."""
    needles = {str(path), path.as_posix()}
    for settings in settings_files:
        try:
            text = settings.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(needle in text for needle in needles):
            return settings.name
    return None


def enabling_settings(marketplace: str, plugin: str, settings_files: Iterable[Path]) -> str | None:
    """The settings file whose `enabledPlugins` names this plugin, however it is set.

    A `false` entry means disabled, not uninstalled, so its cache is still wanted.
    """
    key = f"{plugin}@{marketplace}"
    for settings in settings_files:
        try:
            payload = json.loads(settings.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        enabled = payload.get("enabledPlugins") if isinstance(payload, dict) else None
        if isinstance(enabled, dict) and key in enabled:
            return settings.name
    return None


def default_settings_files(cache_dir: Path) -> list[Path]:
    """`~/.claude/settings*.json` derived from the cache path, not from the environment."""
    claude_dir = cache_dir.parent.parent
    return [claude_dir / name for name in SETTINGS_NAMES]


def default_claude_json(cache_dir: Path) -> Path:
    """`~/.claude.json`, the sibling of the `~/.claude` directory the cache path already names."""
    claude_dir = cache_dir.parent.parent
    return claude_dir.with_name(claude_dir.name + ".json")


def project_settings_files(claude_json: Path) -> list[Path]:
    """`<project>/.claude/settings*.json` for every project `~/.claude.json` lists.

    A plugin can be enabled per project, and such a plugin may have no `installPath` record, so
    without this a project-scope plugin reads as an uninstalled leftover. Stale project entries
    are ordinary - the directory is simply gone - so a missing path is skipped, not reported.
    """
    try:
        payload = json.loads(claude_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    projects = payload.get("projects") if isinstance(payload, dict) else None
    if not isinstance(projects, dict):
        return []
    found: list[Path] = []
    for raw in projects:
        project = Path(raw)
        if not project.is_dir():
            continue
        found.extend((project / ".claude" / name) for name in SETTINGS_NAMES)
    return found


def _readable(paths: Iterable[Path]) -> list[Path]:
    """The files that exist, each once, in the order first seen."""
    seen: dict[str, Path] = {}
    for path in paths:
        try:
            key = str(path.resolve())
        except OSError:
            continue
        if key not in seen and path.is_file():
            seen[key] = path
    return list(seen.values())


def _version_dirs(cache_dir: Path, marketplaces: Sequence[str] | None) -> list[Path]:
    """Every `<marketplace>/<plugin>/<version>` directory, hidden and temp entries excluded."""
    found: list[Path] = []
    for marketplace in _child_dirs(cache_dir):
        if marketplace.name.startswith(TEMP_PREFIX):
            continue
        if marketplaces is not None and marketplace.name not in marketplaces:
            continue
        for plugin in _child_dirs(marketplace):
            found.extend(_child_dirs(plugin))
    return found


def _child_dirs(path: Path) -> list[Path]:
    try:
        children = sorted(path.iterdir())
    except OSError:
        return []
    return [child for child in children if child.is_dir() and not child.name.startswith(".")]


def build_plan(
    cache_dir: str | Path,
    *,
    keep: Sequence[str | Path] = (),
    marketplaces: Sequence[str] | None = None,
    min_age_seconds: float = DEFAULT_MIN_AGE_SECONDS,
    installed_plugins: str | Path | None = None,
    settings_files: Sequence[str | Path] | None = None,
    claude_json: str | Path | None = None,
    project_settings: bool = True,
    allow_missing_locks: bool = False,
    now: float | None = None,
) -> Plan:
    """Classify every cache directory into prune / keep / refused, with a reason for each."""
    root = Path(cache_dir).expanduser()
    installed_file = (
        Path(installed_plugins).expanduser()
        if installed_plugins is not None
        else root.parent / INSTALLED_PLUGINS
    )
    settings = _readable(
        [Path(item).expanduser() for item in settings_files]
        if settings_files is not None
        else _discovered_settings(root, claude_json=claude_json, project_settings=project_settings)
    )
    installed = installed_paths(installed_file)
    explicit = {os.path.normpath(str(Path(item).expanduser())) for item in keep}
    moment = time.time() if now is None else now

    entries: list[Entry] = []
    saw_live_lock = False
    saw_lock_dir = False
    for version_dir in _version_dirs(root, marketplaces):
        saw_lock_dir = saw_lock_dir or (version_dir / LOCK_DIR).is_dir()
        holder = live_lock_holder(version_dir)
        saw_live_lock = saw_live_lock or holder is not None
        entries.append(
            _version_entry(
                version_dir,
                root=root,
                holder=holder,
                installed=installed,
                explicit=explicit,
                settings=settings,
            )
        )
    if entries and not saw_lock_dir and not allow_missing_locks:
        entries = [_without_the_lock_mechanism(entry) for entry in entries]
    if marketplaces is None:
        entries.extend(_temp_entries(root, min_age_seconds=min_age_seconds, now=moment))
    return Plan(
        cache_dir=root,
        entries=tuple(entries),
        saw_live_lock=saw_live_lock,
        saw_lock_dir=saw_lock_dir,
        settings_files=tuple(settings),
    )


def _discovered_settings(
    root: Path, *, claude_json: str | Path | None, project_settings: bool
) -> list[Path]:
    files = default_settings_files(root)
    if not project_settings:
        return files
    index = Path(claude_json).expanduser() if claude_json is not None else default_claude_json(root)
    return files + project_settings_files(index)


def _without_the_lock_mechanism(entry: Entry) -> Entry:
    """Refuse a version directory nothing else keeps, because nothing can now prove it is free.

    Not one version directory carries an `.in_use` directory. On a machine that has run a
    lock-aware Claude Code at all, at least one does - an idle machine leaves the directory
    behind EMPTY - so the absence means the mechanism was renamed or dropped, and every version
    would silently read as unused, the running session's included.
    """
    if entry.refusal is not None or entry.keep_reason is not None:
        return entry
    return Entry(
        **{
            **entry.__dict__,
            "refusal": "no .in_use lock directory anywhere: the lock mechanism is absent or has"
            " changed, so no version can be shown free (override with --allow-missing-locks)",
        }
    )


def _version_entry(
    version_dir: Path,
    *,
    root: Path,
    holder: str | None,
    installed: set[str],
    explicit: set[str],
    settings: Sequence[Path],
) -> Entry:
    marketplace = version_dir.parent.parent.name
    plugin = version_dir.parent.name
    refusal = refusal_for(version_dir, base=root)
    entry = Entry(
        path=version_dir,
        kind=KIND_VERSION,
        size_bytes=0 if refusal else directory_size(version_dir),
        refusal=refusal,
        marketplace=marketplace,
        plugin=plugin,
        version=version_dir.name,
    )
    if refusal is not None:
        return entry
    reason = _keep_reason(
        version_dir,
        sole=len(_child_dirs(version_dir.parent)) == 1,
        holder=holder,
        installed=installed,
        explicit=explicit,
        pinned=pinning_settings(version_dir, settings),
        enabled=enabling_settings(marketplace, plugin, settings),
    )
    return Entry(**{**entry.__dict__, "keep_reason": reason})


def _keep_reason(
    version_dir: Path,
    *,
    sole: bool,
    holder: str | None,
    installed: set[str],
    explicit: set[str],
    pinned: str | None,
    enabled: str | None,
) -> str | None:
    """The first reason that applies, most specific first, or None when nothing keeps it.

    A plugin nothing references is prunable even when it is the only version: that is what an
    uninstalled plugin looks like, and no other pass reclaims it. `enabled` is the guard that
    makes that safe, and it applies ONLY to a sole version. `enabledPlugins` names a PLUGIN, not
    a version, so it says "this plugin is still wanted" and nothing about which of its versions
    to keep - honouring it per version would preserve the entire history of every enabled
    plugin, which is the whole accumulation.
    """
    normalised = os.path.normpath(str(version_dir))
    if holder is not None:
        return holder
    if normalised in explicit:
        return "named with --keep"
    if normalised in installed:
        return "installed"
    if pinned is not None:
        return f"pinned in {pinned}"
    if sole and enabled is not None:
        return f"only version, enabled in {enabled}"
    return None


def _temp_entries(root: Path, *, min_age_seconds: float, now: float) -> list[Entry]:
    entries: list[Entry] = []
    for path in _child_dirs(root):
        if not path.name.startswith(TEMP_PREFIX):
            continue
        refusal = refusal_for(path, base=root)
        age = _age_seconds(path, now=now)
        keep_reason = None
        if refusal is None and age is not None and age < min_age_seconds:
            keep_reason = f"{int(age)}s old - an operation may be in flight"
        entries.append(
            Entry(
                path=path,
                kind=KIND_TEMP,
                size_bytes=0 if refusal else directory_size(path),
                keep_reason=keep_reason,
                refusal=refusal,
            )
        )
    return entries


def _age_seconds(path: Path, *, now: float) -> float | None:
    try:
        return max(0.0, now - path.lstat().st_mtime)
    except OSError:
        return None


def apply_plan(plan: Plan) -> list[str]:
    """Remove exactly what the plan listed. Returns what could not be removed, and why.

    The listed set never grows - nothing is rediscovered here. It can SHRINK: a session can start
    between the plan and the apply and claim a version that was free when the plan was built, so
    each version directory's lock and refusal are re-checked immediately before it is removed.
    Only the safe direction is re-read, never a fresh scan for new candidates.
    """
    failures: list[str] = []
    for entry in plan.prune:
        blocker = _blocker_now(entry, base=plan.cache_dir)
        if blocker is not None:
            failures.append(f"{entry.path}: {blocker}")
            continue
        try:
            shutil.rmtree(entry.path)
        except OSError as exc:
            failures.append(f"{entry.path}: could not be removed: {exc}")
    return failures


def _blocker_now(entry: Entry, *, base: Path) -> str | None:
    """What has changed since the plan was built that must stop this removal."""
    refusal = refusal_for(entry.path, base=base)
    if refusal is not None:
        return refusal
    if entry.kind != KIND_VERSION:
        return None
    holder = live_lock_holder(entry.path)
    return None if holder is None else f"{holder} since the plan was built"


# --------------------------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------------------------


def default_cache_dir() -> Path:
    return Path.home() / ".claude" / "plugins" / "cache"


def _human(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


_DURATION = re.compile(r"^(\d+(?:\.\d+)?)([smhd]?)$")
_DURATION_UNITS = {"": 60.0, "s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}


def parse_duration(value: str) -> float:
    """Minutes by default, so `--min-age 90` and `--min-age 2h` both read as intended."""
    match = _DURATION.match(value.strip().lower())
    if match is None:
        raise argparse.ArgumentTypeError(f"not a duration: {value!r} (try 45, 90m, 2h, 1d)")
    return float(match.group(1)) * _DURATION_UNITS[match.group(2)]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pluginprune",
        description=(
            "Reclaim disk from the Claude Code plugin cache without breaking a running "
            "session. Dry run unless --apply."
        ),
        epilog=(
            "A version directory is kept when a LIVE .in_use lock holds it, when "
            "installed_plugins.json points at it, when a settings file pins it, when --keep "
            "names it, or when it is the plugin's only version. A temp_* directory is kept "
            "while it is younger than --min-age. Symlinks and paths outside the cache are "
            "refused."
        ),
    )
    parser.add_argument(
        "--cache-dir", help="the plugin cache (default: ~/.claude/plugins/cache)"
    )
    parser.add_argument(
        "--marketplace",
        action="append",
        metavar="NAME",
        help="limit the scan to this marketplace, repeatable (temp_* leftovers are then skipped)",
    )
    parser.add_argument(
        "--keep",
        action="append",
        default=[],
        metavar="DIR",
        help="a version directory to keep whatever else says, repeatable",
    )
    parser.add_argument(
        "--min-age",
        default="60m",
        type=parse_duration,
        metavar="DURATION",
        help="keep temp_* leftovers younger than this (default: 60m; bare number = minutes)",
    )
    parser.add_argument(
        "--installed-plugins", help="installed_plugins.json (default: beside the cache directory)"
    )
    parser.add_argument(
        "--settings",
        action="append",
        metavar="FILE",
        help="a settings file to scan for pinned version paths and enabledPlugins, repeatable."
        " Giving any turns discovery off; the default is ~/.claude/settings.json,"
        " settings.local.json, and the same pair inside every project ~/.claude.json lists",
    )
    parser.add_argument(
        "--claude-json", help="the project index to discover project settings from"
        " (default: ~/.claude.json)"
    )
    parser.add_argument(
        "--no-project-settings",
        action="store_true",
        help="read only the user-level settings files, skipping every project's",
    )
    parser.add_argument(
        "--allow-missing-locks",
        action="store_true",
        help="prune even when NO version directory has an .in_use directory, which means the"
        " lock mechanism is absent or has changed and no version can be shown free",
    )
    parser.add_argument(
        "--apply", action="store_true", help="actually remove (default is a dry run)"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable envelope")
    return parser


def _render(plan: Plan, *, applied: bool) -> list[str]:
    verb = "removed" if applied else "would remove"
    lines = [f"  {verb}: {entry.path}  ({_human(entry.size_bytes)})" for entry in plan.prune]
    if not lines:
        lines.append("  nothing to prune")
    else:
        tail = "" if applied else " - re-run with --apply"
        lines.append(f"\n  {_human(plan.reclaimable_bytes)} reclaimable{tail}")
    for entry in plan.keep:
        lines.append(f"  kept:   {entry.path}  ({entry.keep_reason})")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    cache_dir = Path(args.cache_dir).expanduser() if args.cache_dir else default_cache_dir()
    if not cache_dir.is_dir():
        print(f"pluginprune: no plugin cache at {cache_dir}", file=sys.stderr)
        return 2

    plan = build_plan(
        cache_dir,
        keep=args.keep,
        marketplaces=args.marketplace,
        min_age_seconds=args.min_age,
        installed_plugins=args.installed_plugins,
        settings_files=args.settings,
        claude_json=args.claude_json,
        project_settings=not args.no_project_settings,
        allow_missing_locks=args.allow_missing_locks,
    )

    if plan.saw_lock_dir and not plan.saw_live_lock and plan.prune:
        # No live lock anywhere means the running session's own version cannot be identified
        # from the cache, so name the one thing that resolves it rather than guessing.
        print(
            "pluginprune: no live .in_use lock found, so no version is provably in use by a"
            " running session - if a session is open, pass its version with --keep (its"
            " directory is the base path a skill invocation prints)",
            file=sys.stderr,
        )

    failures = apply_plan(plan) if args.apply else []
    blocked = [f"{entry.path}: {entry.refusal}" for entry in plan.refused] + failures

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not blocked,
                    "command": "pluginprune",
                    "skipped": blocked,
                    "data": {"applied": args.apply, **plan.as_dict()},
                },
                indent=2,
            )
        )
    else:
        for line in _render(plan, applied=args.apply):
            print(line)
        for item in blocked:
            print(f"  {'FAILED' if args.apply else 'REFUSED'}: {item}", file=sys.stderr)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
