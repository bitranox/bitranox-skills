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
sizes and does nothing until `--apply`. `--apply` re-plans in its own process and removes that
plan; it cannot carry over the plan an earlier dry run printed, so a `temp_*` leftover that
crossed `--min-age` in between, or a version whose last lock went stale, can be removed although
the dry run kept it. Every removal still passes the same rules. Within one `--apply` run the
listed set can only SHRINK: a session that starts between the plan and the removal claims its
version, and that directory is then refused rather than removed. Only what was actually removed
is reported as removed.

Kept, with the reason stated per directory:

* the installed version, from the `installPath` in `installed_plugins.json` (what a fresh
  session resolves to). Paths are compared RESOLVED, so another spelling of the same directory
  (a symlinked `~/.claude`, a relative `--cache-dir` or `--keep`) still matches. When the record
  is missing, unreadable or not the expected shape, every version nothing else keeps is REFUSED,
  because the installed one can no longer be told apart;
* any version with a LIVE `.in_use` lock (a session running right now, this one included), or
  whose `.in_use` directory cannot be listed;
* any version whose path appears in a settings file, which pins it - spelled absolute, or
  relative to the home or Claude config directory however that prefix is written (`~/`,
  `"$HOME"/`, `%USERPROFILE%`, `$env:USERPROFILE/`, `${CLAUDE_CONFIG_DIR}/`, quoted or not):
  the part beneath it is searched on its own. On Windows the search ignores letter case, as the
  filesystem does;
* the SOLE version of a plugin a settings file's `enabledPlugins` names, however it is set -
  counting only real version directories, since a symlinked sibling is refused and never removed;
  disabled is not uninstalled, and its cache is still wanted. `enabledPlugins` names a plugin,
  never a version, so it cannot choose between several. The settings files are the user's pair
  PLUS the same pair inside every project `~/.claude.json` lists, because a plugin enabled only
  in a project may have no `installPath` record at all;
* a `temp_*` directory younger than `--min-age` (default 60m), because an operation may be
  in flight.

A plugin nothing references at all is prunable even as the only version: that is what an
uninstalled plugin leaves behind, and no other pass reclaims it.

Refusals, because this runs on machines whose layout is not yours: a symlinked directory, a
directory reached THROUGH a symlinked marketplace or plugin directory (removing through the alias
deletes the real one it points at), a path that resolves outside the cache, and the cache
directory itself are refused outright. So is every version directory when NOT ONE of them
carries an `.in_use` directory - an idle machine leaves that directory behind empty, so its total
absence means the mechanism was renamed or dropped and every version would silently read as
unused. `--allow-missing-locks` overrides that.

Run:
  `uv run scripts/pluginprune.py`                        # the plan, with sizes
  `uv run scripts/pluginprune.py --apply`                # re-plan, then remove that plan
  `uv run scripts/pluginprune.py --marketplace my-mkt`   # one marketplace only
  `uv run scripts/pluginprune.py --keep ~/.claude/plugins/cache/m/p/1.2.3 --apply`
  `uv run scripts/pluginprune.py --json`

`--keep` takes a version directory or any path inside one (the base directory a skill invocation
prints is inside its version), relative paths resolved against the working directory. A `--keep`
that names no scanned version directory is a usage error, never silently ignored.

Exit codes: 0 = nothing blocked (a dry-run plan that can be carried out as-is, or an `--apply`
that removed everything it listed), 1 = something was refused or could not be removed, 2 = usage
error (including a `--keep` that matches nothing and an explicit `--installed-plugins` that
cannot be read), a settings source it must consult that cannot be used, or an unexpected crash.

A settings source that cannot be used - a settings file or `~/.claude.json` that exists but
cannot be read, is not UTF-8, is not valid JSON or has the wrong shape, or a `--settings` /
`--claude-json` that names a missing file - stops the run with exit 2 before anything is planned
or removed, naming the file and the reason. Skipping it would lose the pin or `enabledPlugins`
entry it holds and plan that version for deletion. A discovered file that is simply absent, or
one holding only whitespace, is ordinary and holds nothing.

`--json` emits the machine-readable envelope `{ok, command, skipped, data}` on every exit code:
on exit 2 (including a command line argparse rejects, and a crash) it is `ok: false`,
`data: null` and an `error` naming the reason. Diagnostics always go to stderr as well, so
stdout stays parseable.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import sys
import time
import traceback
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

__all__ = [
    "ApplyResult",
    "Entry",
    "InstallRecord",
    "Plan",
    "SettingsError",
    "SettingsFile",
    "SettingsSources",
    "apply_plan",
    "build_plan",
    "live_lock_holder",
    "load_settings",
    "main",
    "pid_alive",
    "process_start_ticks",
    "read_install_record",
    "read_settings",
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
    except (OSError, OverflowError):
        # PermissionError: the process exists under another user. OverflowError: a corrupt lock
        # names a pid no C int holds - unknowable, so it counts as alive.
        return True
    return True


def _windows_pid_alive(pid: int) -> bool:
    if pid > 0xFFFFFFFF:
        return True  # no DWORD holds it, so the question cannot even be asked - keep
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
    in use, never to delete one because its marker could not be parsed. That holds for the lock
    DIRECTORY too - only its absence means "no lock"; one that cannot be listed may hide a live
    one.
    """
    lock_dir = version_dir / LOCK_DIR
    try:
        locks = sorted(lock_dir.iterdir())
    except FileNotFoundError:
        return None
    except OSError as exc:
        return f"in use (lock dir unreadable: {exc.strerror or exc})"
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
    size_complete: bool = True  # False: part of the tree could not be read, size is a floor

    def as_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "kind": self.kind,
            "bytes": self.size_bytes,
            "size_complete": self.size_complete,
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
    settings_problems: tuple[str, ...] = ()
    install_record: Path | None = None
    install_problem: str | None = None
    unmatched_keep: tuple[str, ...] = ()

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
            "settings_problems": list(self.settings_problems),
            "install_record": None if self.install_record is None else str(self.install_record),
            "install_problem": self.install_problem,
        }


@dataclass(frozen=True)
class InstallRecord:
    """What installed_plugins.json says is installed, or why it could not say."""

    path: Path
    install_paths: frozenset[str]
    problem: str | None = None


@dataclass(frozen=True)
class ApplyResult:
    """What an apply actually removed, and what it could not, with the reason."""

    removed: tuple[Entry, ...]
    failures: tuple[str, ...]


def canonical(path: str | Path) -> str:
    """One comparable spelling per directory: absolute, symlinks resolved, case folded on Windows.

    Every keep rule compares paths, and an unresolved string never equals another spelling of the
    same directory - a relative `--keep`, a symlinked `~/.claude` - so the rule silently misses
    and the directory it names is deleted.
    """
    raw = os.path.expanduser(str(path))
    try:
        resolved = str(Path(raw).resolve())
    except (OSError, RuntimeError, ValueError):
        resolved = os.path.abspath(raw)
    return os.path.normcase(os.path.normpath(resolved))


def directory_size(path: Path) -> tuple[int, bool]:
    """(bytes held by the tree, whether every part of it could be read).

    Follows no symlink, so the plan cannot inflate its own numbers. An unreadable subtree makes
    the figure a floor, and that is reported rather than passed off as the whole size.
    """
    total = 0
    errors: list[OSError] = []
    for root, _dirs, files in os.walk(path, onerror=errors.append):
        for name in files:
            try:
                total += (Path(root) / name).lstat().st_size
            except OSError as exc:
                errors.append(exc)
    return total, not errors


def refusal_for(path: Path, *, base: Path) -> str | None:
    """Why this directory must not be deleted, or None when it may be."""
    if path.is_symlink():
        return "is a symlink - removing through it can destroy data outside it"
    try:
        resolved = path.resolve()
        base_resolved = base.resolve()
    except (OSError, RuntimeError) as exc:
        return f"cannot be resolved: {exc}"
    if resolved.parent == resolved:
        return "is a filesystem root"
    if resolved == base_resolved:
        return "is the cache directory itself"
    if not resolved.is_relative_to(base_resolved):
        return f"resolves outside {base_resolved}"
    if _through_a_symlink(path, base=base, base_resolved=base_resolved, resolved=resolved):
        return (
            "is reached through a symlinked directory - removing through the alias deletes the"
            f" real directory {resolved}"
        )
    return None


def _through_a_symlink(path: Path, *, base: Path, base_resolved: Path, resolved: Path) -> bool:
    """True when a directory between the cache root and this path is a symlink.

    The path is spelled lexically under the cache root, so without a symlinked component its
    resolved form is the resolved root plus the same relative part. Any difference means an
    alias - a symlinked marketplace or plugin directory - and removing through it deletes the
    directory it points at, which may be the installed or a live version under its real name.
    """
    try:
        relative = Path(os.path.abspath(path)).relative_to(os.path.abspath(base))
    except ValueError:
        return False
    return os.path.normcase(str(base_resolved / relative)) != os.path.normcase(str(resolved))


def read_install_record(installed_plugins: Path) -> InstallRecord:
    """Every `installPath` in installed_plugins.json - what a FRESH session resolves to.

    A record that cannot be read or has the wrong shape is reported as a PROBLEM, never as "no
    plugin is installed": the latter reading would plan the installed version for deletion.
    """
    def broken(problem: str) -> InstallRecord:
        return InstallRecord(installed_plugins, frozenset(), f"{installed_plugins} {problem}")

    try:
        payload = json.loads(installed_plugins.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        return broken(f"cannot be read: {exc.strerror or exc}")
    except ValueError as exc:
        return broken(f"is not valid JSON: {exc}")
    plugins = payload.get("plugins") if isinstance(payload, dict) else None
    if not isinstance(plugins, dict):
        return broken("has no 'plugins' map")
    found: set[str] = set()
    for records in plugins.values():
        for record in records if isinstance(records, list) else []:
            if isinstance(record, dict) and isinstance(record.get("installPath"), str):
                found.add(canonical(record["installPath"]))
    return InstallRecord(installed_plugins, frozenset(found))


def pin_needles(
    path: Path, *, spellings: Iterable[Path] = (), anchors: Iterable[Path] = ()
) -> set[str]:
    r"""Every text a settings file may use to name this directory.

    The search is over the file's RAW TEXT (deliberately - a path can sit anywhere in it,
    including in a file that is not valid JSON), and a settings file is JSON, which ESCAPES a
    backslash: on Windows the stored text reads "C:\\Users\\..." while str(path) is
    "C:\Users\...". So each spelling is searched native, posix, JSON-escaped, and with every "/"
    written as the "\/" JSON also allows.

    A hook command usually names the path relative to a directory it spells as a variable, and
    that prefix is shell, PowerShell or cmd text: `~`, `$HOME`, `"$HOME"`, `'${HOME}'`,
    `%USERPROFILE%`, `$env:USERPROFILE`, `${CLAUDE_CONFIG_DIR}`, each quoted or not. Enumerating
    prefixes always misses one, so the part BENEATH each anchor (the home directory, the Claude
    config directory) is searched on its own, whatever precedes it. That part still names the
    marketplace, plugin and version, so it cannot match a neighbour. This function's false
    negative is a DELETION, so every extra needle errs the safe way.
    """
    needles: set[str] = set()
    anchor_list = list(anchors)
    for spelling in (path, *spellings):
        needles.update(_renderings(str(spelling), spelling.as_posix()))
        for anchor in anchor_list:
            try:
                relative = spelling.relative_to(anchor)
            except ValueError:
                continue
            if relative.parts:
                needles.update(_renderings(str(relative), relative.as_posix()))
    return needles


def _renderings(native: str, posix: str) -> set[str]:
    """The native, posix and backslash forms, each also as JSON stores it inside a string.

    The backslash form is rendered on every platform: a settings file may be shared or synced
    from Windows, and an extra needle only keeps more.
    """
    windows = posix.replace("/", "\\")
    return {
        native,
        posix,
        windows,
        json.dumps(native)[1:-1],
        json.dumps(windows)[1:-1],
        posix.replace("/", "\\/"),
    }


class SettingsError(ValueError):
    """A settings source that exists but cannot be read or understood.

    Never read as "names nothing": the pin or `enabledPlugins` entry such a file holds is exactly
    what keeps a version off the delete list, so losing it silently plans that version for
    deletion.
    """


@dataclass(frozen=True)
class SettingsFile:
    """One settings file, read once: its raw text (searched for pins) and the plugins it enables."""

    path: Path
    text: str
    enabled: frozenset[str]


def read_settings(path: Path) -> SettingsFile:
    """Read and check one settings file. Raises SettingsError when it cannot be relied on.

    A file holding only whitespace is read as empty, because nothing in it can be lost.
    """
    text = _read_source(path)
    if not text.strip():
        return SettingsFile(path, "", frozenset())
    payload = _parse_source(path, text)
    if not isinstance(payload, dict):
        raise SettingsError(f"{path} is not a JSON object")
    enabled = payload.get("enabledPlugins", {})
    if not isinstance(enabled, dict):
        raise SettingsError(f"{path} has an 'enabledPlugins' entry that is not an object")
    return SettingsFile(path, text, frozenset(enabled))


def _read_source(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8-sig")
    except OSError as exc:
        raise SettingsError(f"{path} cannot be read: {exc.strerror or exc}") from exc
    except UnicodeDecodeError as exc:
        raise SettingsError(f"{path} is not UTF-8 text: {exc.reason} at byte {exc.start}") from exc


def _parse_source(path: Path, text: str) -> object:
    try:
        return json.loads(text)
    except ValueError as exc:
        raise SettingsError(f"{path} is not valid JSON: {exc}") from exc


def _loaded(item: Path | SettingsFile) -> SettingsFile:
    return item if isinstance(item, SettingsFile) else read_settings(item)


def pinning_settings(
    path: Path,
    settings_files: Iterable[Path | SettingsFile],
    *,
    spellings: Iterable[Path] = (),
    anchors: Iterable[Path] = (),
    fold_case: bool | None = None,
) -> str | None:
    """The settings file that names this exact directory, or None when nothing pins it.

    See `pin_needles` for the spellings searched. A file that cannot be read raises
    SettingsError rather than being skipped, since skipping it deletes whatever it pins.

    `fold_case` compares without regard to letter case, which is how Windows resolves a path:
    a settings file spelling `.Claude\\Plugins\\...` names the same directory as `.claude\\...`
    there. It defaults to the running platform (`os.name == "nt"`); on a case-sensitive
    filesystem the other spelling is another directory and keeps nothing.
    """
    folding = os.name == "nt" if fold_case is None else fold_case
    needles = pin_needles(path, spellings=spellings, anchors=anchors)
    if folding:
        needles = {needle.casefold() for needle in needles}
    for item in settings_files:
        settings = _loaded(item)
        text = settings.text.casefold() if folding else settings.text
        if any(needle in text for needle in needles):
            return settings.path.name
    return None


def enabling_settings(
    marketplace: str, plugin: str, settings_files: Iterable[Path | SettingsFile]
) -> str | None:
    """The settings file whose `enabledPlugins` names this plugin, however it is set.

    A `false` entry means disabled, not uninstalled, so its cache is still wanted. A file that
    cannot be read or parsed raises SettingsError, as in `pinning_settings`.
    """
    key = f"{plugin}@{marketplace}"
    for item in settings_files:
        settings = _loaded(item)
        if key in settings.enabled:
            return settings.path.name
    return None


def default_settings_files(cache_dir: Path) -> list[Path]:
    """`~/.claude/settings*.json` derived from the cache path, not from the environment."""
    claude_dir = cache_dir.parent.parent
    return [claude_dir / name for name in SETTINGS_NAMES]


def default_claude_json(cache_dir: Path) -> Path:
    """`~/.claude.json`, the sibling of the `~/.claude` directory the cache path already names."""
    claude_dir = cache_dir.parent.parent
    if not claude_dir.name:
        return claude_dir / ".claude.json"  # a cache two levels below a root has no sibling
    return claude_dir.with_name(claude_dir.name + ".json")


def project_settings_files(claude_json: Path) -> list[Path]:
    """`<project>/.claude/settings*.json` for every project `~/.claude.json` lists.

    A plugin can be enabled per project, and such a plugin may have no `installPath` record, so
    without this a project-scope plugin reads as an uninstalled leftover. Stale project entries
    are ordinary - the directory is simply gone - so a missing path is skipped, not reported, and
    so is a missing index. An index that exists but cannot be read or parsed raises
    SettingsError: read as "no projects", it would hide every project's settings at once.
    """
    if not _present(claude_json):
        return []
    text = _read_source(claude_json)
    payload = _parse_source(claude_json, text) if text.strip() else {}
    if not isinstance(payload, dict):
        raise SettingsError(f"{claude_json} is not a JSON object")
    projects = payload.get("projects", {})
    if not isinstance(projects, dict):
        raise SettingsError(f"{claude_json} has a 'projects' entry that is not an object")
    found: list[Path] = []
    for raw in projects:
        project = Path(raw)
        if not _is_dir(project, listed_in=claude_json):
            continue
        found.extend((project / ".claude" / name) for name in SETTINGS_NAMES)
    return found


# errno says "this path cannot exist" (not "could not look"): ENOENT, ENOTDIR, and on Windows
# ERROR_INVALID_NAME for a string that is no valid path at all.
_WINERROR_INVALID_NAME = 123


def _absent(exc: OSError) -> bool:
    return isinstance(exc, (FileNotFoundError, NotADirectoryError)) or (
        getattr(exc, "winerror", None) == _WINERROR_INVALID_NAME
    )


def _present(path: Path) -> bool:
    """Whether anything sits at this path. A lookup that FAILS raises SettingsError, because
    "could not look" is not "nothing there". A dangling symlink is present, and its read fails."""
    try:
        os.lstat(path)
    except ValueError:
        return False  # an embedded NUL: no such path can exist
    except OSError as exc:
        if _absent(exc):
            return False
        raise SettingsError(f"{path} cannot be checked: {exc.strerror or exc}") from exc
    return True


def _is_dir(project: Path, *, listed_in: Path) -> bool:
    try:
        return stat.S_ISDIR(os.stat(project).st_mode)
    except ValueError:
        return False
    except OSError as exc:
        if _absent(exc):
            return False
        raise SettingsError(
            f"project {project} listed in {listed_in} cannot be checked: {exc.strerror or exc}"
        ) from exc


@dataclass(frozen=True)
class SettingsSources:
    """Every settings file read, each once, and every source that could not be relied on."""

    files: tuple[SettingsFile, ...]
    problems: tuple[str, ...]


def load_settings(candidates: Iterable[tuple[Path, bool]]) -> SettingsSources:
    """Read each `(path, required)` candidate once, in the order first seen.

    A missing file is skipped unless it is REQUIRED (named on the command line), when it is a
    problem: a typo there would otherwise read as "nothing pinned". Every other failure is a
    problem whatever the source.
    """
    files: list[SettingsFile] = []
    problems: list[str] = []
    seen: set[str] = set()
    for path, required in candidates:
        try:
            if not _present(path):
                if required:
                    problems.append(f"{path} does not exist")
                continue
            key = canonical(path)
            if key in seen:
                continue
            seen.add(key)
            files.append(read_settings(path))
        except SettingsError as exc:
            problems.append(str(exc))
    return SettingsSources(tuple(files), tuple(problems))


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
    """Classify every cache directory into prune / keep / refused, with a reason for each.

    The cache is SCANNED at its resolved path, so every rule that compares paths sees one spelling
    of each directory. The files that describe it (installed_plugins.json, the settings files,
    `~/.claude.json`) are found from the path AS GIVEN, made absolute, because a symlinked
    `~/.claude` has its own siblings where the target does not.
    """
    given = Path(os.path.abspath(os.path.expanduser(str(cache_dir))))
    root = given.resolve()
    record = read_install_record(
        Path(installed_plugins).expanduser()
        if installed_plugins is not None
        else given.parent / INSTALLED_PLUGINS
    )
    sources = _gather_settings(
        given,
        settings_files=settings_files,
        claude_json=claude_json,
        project_settings=project_settings,
    )
    context = _KeepContext(
        root=root,
        given=given,
        installed=record.install_paths,
        explicit=tuple(canonical(item) for item in keep),
        settings=sources.files,
        pin_anchors=_pin_anchors(given),
    )
    moment = time.time() if now is None else now

    entries: list[Entry] = []
    saw_live_lock = False
    saw_lock_dir = False
    for version_dir in _version_dirs(root, marketplaces):
        saw_lock_dir = saw_lock_dir or (version_dir / LOCK_DIR).is_dir()
        holder = live_lock_holder(version_dir)
        saw_live_lock = saw_live_lock or holder is not None
        entries.append(_version_entry(version_dir, holder=holder, context=context))
    if entries and not saw_lock_dir and not allow_missing_locks:
        entries = [_without_the_lock_mechanism(entry) for entry in entries]
    if record.problem is not None:
        entries = [_without_the_install_record(entry, record.problem) for entry in entries]
    if sources.problems:
        entries = [_without_readable_settings(entry, sources.problems) for entry in entries]
    if marketplaces is None:
        entries.extend(_temp_entries(root, min_age_seconds=min_age_seconds, now=moment))
    return Plan(
        cache_dir=root,
        entries=tuple(entries),
        saw_live_lock=saw_live_lock,
        saw_lock_dir=saw_lock_dir,
        settings_files=tuple(settings.path for settings in sources.files),
        settings_problems=sources.problems,
        install_record=record.path,
        install_problem=record.problem,
        unmatched_keep=_unmatched_keep(keep, context.explicit, entries),
    )


@dataclass(frozen=True)
class _KeepContext:
    """Everything a version directory's keep rules are judged against, gathered once."""

    root: Path
    given: Path
    installed: frozenset[str]
    explicit: tuple[str, ...]
    settings: tuple[SettingsFile, ...]
    pin_anchors: tuple[Path, ...]


def _pin_anchors(given: Path) -> tuple[Path, ...]:
    """The directories a pin may be spelled relative to: the home directory and the config dir.

    The cache path names both (`<home>/<config dir>/plugins/cache`), which holds even when the
    environment's HOME points elsewhere or the config dir is not `.claude` (CLAUDE_CONFIG_DIR);
    the user's own home is searched too, since an extra needle only keeps more.
    """
    found: list[Path] = [given.parent.parent.parent, given.parent.parent]
    try:
        found.append(Path.home())
    except (RuntimeError, KeyError, OSError):
        pass
    resolved = []
    for home in found:
        try:
            resolved.append(home.resolve())
        except (OSError, RuntimeError):
            continue
    return tuple(dict.fromkeys([*found, *resolved]))


def _keep_matches(explicit: str, version: str) -> bool:
    """A --keep names a version when it IS the directory or any path inside it."""
    return explicit == version or explicit.startswith(version.rstrip(os.sep) + os.sep)


def _unmatched_keep(
    keep: Sequence[str | Path], explicit: Sequence[str], entries: Sequence[Entry]
) -> tuple[str, ...]:
    versions = [canonical(entry.path) for entry in entries if entry.kind == KIND_VERSION]
    return tuple(
        str(raw)
        for raw, resolved in zip(keep, explicit, strict=True)
        if not any(_keep_matches(resolved, version) for version in versions)
    )


def _without_the_install_record(entry: Entry, problem: str) -> Entry:
    """Refuse a version directory nothing else keeps, because the installed one is now unknown.

    Reading an unreadable record as "nothing is installed" would plan the installed version for
    deletion - the one every fresh session resolves to - so the doubt refuses instead.
    """
    if entry.kind != KIND_VERSION or entry.refusal is not None or entry.keep_reason is not None:
        return entry
    return Entry(
        **{
            **entry.__dict__,
            "refusal": f"the installed version cannot be identified: {problem}"
            " (restore the file, or name a readable one with --installed-plugins)",
        }
    )


def _without_readable_settings(entry: Entry, problems: Sequence[str]) -> Entry:
    """Refuse a version directory nothing else keeps, because a settings source is unreadable.

    The pin or `enabledPlugins` entry that source holds could be the one keeping this version,
    and reading the file as "names nothing" would plan it for deletion.
    """
    if entry.kind != KIND_VERSION or entry.refusal is not None or entry.keep_reason is not None:
        return entry
    return Entry(
        **{
            **entry.__dict__,
            "refusal": "a settings source that may pin or enable it cannot be used: "
            + "; ".join(problems)
            + " (repair it, or choose the files with --settings or --no-project-settings)",
        }
    )


def _gather_settings(
    given: Path,
    *,
    settings_files: Sequence[str | Path] | None,
    claude_json: str | Path | None,
    project_settings: bool,
) -> SettingsSources:
    """The settings files to consult: the ones named, or the discovered user and project pairs.

    A NAMED source (`--settings`, `--claude-json`) must exist; a discovered one may be absent.
    """
    if settings_files is not None:
        return load_settings((Path(item).expanduser(), True) for item in settings_files)
    candidates = [(path, False) for path in default_settings_files(given)]
    problems: list[str] = []
    if project_settings:
        try:
            candidates += [(path, False) for path in _project_candidates(given, claude_json)]
        except SettingsError as exc:
            problems.append(str(exc))
    loaded = load_settings(candidates)
    return SettingsSources(loaded.files, (*problems, *loaded.problems))


def _project_candidates(given: Path, claude_json: str | Path | None) -> list[Path]:
    if claude_json is None:
        return project_settings_files(default_claude_json(given))
    index = Path(claude_json).expanduser()
    if not _present(index):
        raise SettingsError(f"{index} does not exist")
    return project_settings_files(index)


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


def _version_entry(version_dir: Path, *, holder: str | None, context: _KeepContext) -> Entry:
    marketplace = version_dir.parent.parent.name
    plugin = version_dir.parent.name
    refusal = refusal_for(version_dir, base=context.root)
    size, complete = (0, True) if refusal else directory_size(version_dir)
    entry = Entry(
        path=version_dir,
        kind=KIND_VERSION,
        size_bytes=size,
        size_complete=complete,
        refusal=refusal,
        marketplace=marketplace,
        plugin=plugin,
        version=version_dir.name,
    )
    if refusal is not None:
        return entry
    as_given = context.given / version_dir.relative_to(context.root)
    reason = _keep_reason(
        canonical(version_dir),
        sole=_real_version_count(version_dir.parent, base=context.root) == 1,
        holder=holder,
        installed=context.installed,
        explicit=context.explicit,
        pinned=pinning_settings(
            version_dir, context.settings, spellings=[as_given], anchors=context.pin_anchors
        ),
        enabled=enabling_settings(marketplace, plugin, context.settings),
    )
    return Entry(**{**entry.__dict__, "keep_reason": reason})


def _real_version_count(plugin_dir: Path, *, base: Path) -> int:
    """How many distinct REAL version directories a plugin has, for the sole-version rule.

    An alias beside a version - a symlinked sibling, whether it points at that version, at
    another plugin's or outside the cache - is refused and never removed, so it is no version
    of its own. Counted as one, it made an enabled plugin's only real version read as one of
    two, and that version was deleted. Directories are also counted once per resolved path.
    """
    return len(
        {
            canonical(child)
            for child in _child_dirs(plugin_dir)
            if refusal_for(child, base=base) is None
        }
    )


def _keep_reason(
    normalised: str,
    *,
    sole: bool,
    holder: str | None,
    installed: frozenset[str],
    explicit: Sequence[str],
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
    if holder is not None:
        return holder
    if any(_keep_matches(item, normalised) for item in explicit):
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
        size, complete = (0, True) if refusal else directory_size(path)
        entries.append(
            Entry(
                path=path,
                kind=KIND_TEMP,
                size_bytes=size,
                size_complete=complete,
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


def apply_plan(plan: Plan) -> ApplyResult:
    """Remove exactly what this plan listed. Returns what was removed and what could not be.

    The listed set never grows - nothing is rediscovered here. It can SHRINK: a session can start
    between the plan and the apply and claim a version that was free when the plan was built, so
    each version directory's lock and refusal are re-checked immediately before it is removed.
    Only the safe direction is re-read, never a fresh scan for new candidates.
    """
    removed: list[Entry] = []
    failures: list[str] = []
    for entry in plan.prune:
        blocker = _blocker_now(entry, base=plan.cache_dir)
        if blocker is not None:
            failures.append(f"{entry.path}: {blocker}")
            continue
        try:
            _remove_tree(entry.path)
        except OSError as exc:
            failures.append(f"{entry.path}: could not be removed: {exc}")
            continue
        removed.append(entry)
    return ApplyResult(removed=tuple(removed), failures=tuple(failures))


def _remove_tree(path: Path) -> None:
    """rmtree that clears the read-only attribute Windows puts on git pack files, then retries."""
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_retry_writable)
    else:
        shutil.rmtree(path, onerror=_retry_writable)  # onexc does not exist before 3.12


def _retry_writable(func: Callable[[str], object], path: str, exc: object) -> None:
    """Make one read-only FILE writable and retry the removal; anything else re-raises.

    A fresh git clone's pack files are mode 444, which on Windows is the read-only attribute and
    makes the delete fail with "Access is denied". A symlink is never chmodded - that would change
    the permissions of whatever it points at, possibly outside the cache.
    """
    error = exc[1] if isinstance(exc, tuple) else exc
    if os.path.islink(path) or not os.path.isfile(path):
        if isinstance(error, BaseException):
            raise error
        raise OSError(f"could not remove {path}")
    os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)
    func(path)


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


class _ArgumentError(Exception):
    """A command line argparse rejected, raised instead of exiting so --json can still answer."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        raise _ArgumentError(f"error: {message}")


def _wants_json(argv: Sequence[str]) -> bool:
    """Whether --json was asked for, read BEFORE parsing so a rejected command line still gets
    its envelope. argparse accepts an unambiguous prefix (`--js`), so that counts too."""
    return any(len(token) >= 3 and "--json".startswith(token) for token in argv)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="pluginprune",
        description=(
            "Reclaim disk from the Claude Code plugin cache without breaking a running "
            "session. Dry run unless --apply."
        ),
        epilog=(
            "A version directory is kept when a LIVE .in_use lock holds it (or its .in_use "
            "directory cannot be read), when installed_plugins.json points at it, when a "
            "settings file pins it, when --keep names it or a path inside it, or when it is the "
            "only version of a plugin a settings file's enabledPlugins names. A temp_* "
            "directory is kept while it is younger than --min-age. Symlinks, paths reached "
            "through a symlink and paths outside the cache are refused, and so is every "
            "otherwise unkept version when installed_plugins.json cannot be read. A settings "
            "file or ~/.claude.json that exists but cannot be read or parsed stops the run with "
            "exit 2, naming it. --apply re-plans and removes that plan."
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


def _size_text(entry: Entry) -> str:
    if entry.size_complete:
        return _human(entry.size_bytes)
    return f"at least {_human(entry.size_bytes)}, part of it unreadable"


def _render(plan: Plan, *, applied: ApplyResult | None) -> list[str]:
    """The text report. After an apply, only what was ACTUALLY removed is listed as removed."""
    shown = plan.prune if applied is None else applied.removed
    verb = "would remove" if applied is None else "removed"
    lines = [f"  {verb}: {entry.path}  ({_size_text(entry)})" for entry in shown]
    if not lines:
        lines.append("  nothing to prune" if not plan.prune else "  nothing removed")
    else:
        total = _human(sum(entry.size_bytes for entry in shown))
        tail = " reclaimable - re-run with --apply" if applied is None else " reclaimed"
        lines.append(f"\n  {total}{tail}")
    for entry in plan.keep:
        lines.append(f"  kept:   {entry.path}  ({entry.keep_reason})")
    lines.append(f"\n  install record: {plan.install_record}")
    read = ", ".join(str(path) for path in plan.settings_files) or "none found"
    lines.append(f"  settings read: {read}")
    return lines


def _tolerant_streams() -> None:
    """Never let a path the console cannot encode crash the report - possibly AFTER deleting.

    A non-UTF-8 directory name arrives as lone surrogates, and a cp1252 Windows console cannot
    encode most of Unicode; both raised UnicodeEncodeError mid-report with exit 1.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (ValueError, OSError):
            continue


def _usage_problem(plan: Plan, args: argparse.Namespace) -> str | None:
    """A flag that asked for something the plan cannot honour: exit 2 before touching anything."""
    if args.installed_plugins and plan.install_problem is not None:
        return f"--installed-plugins: {plan.install_problem}"
    if plan.unmatched_keep:
        return (
            "--keep names no scanned version directory: "
            + ", ".join(plan.unmatched_keep)
            + " (pass a version directory, or a path inside one, under the scanned cache)"
        )
    return None


_SETTINGS_ADVICE = (
    "nothing planned or removed - a pin or enabledPlugins entry in a file it cannot use may be"
    " what keeps a version, and reading that file as empty would delete it. Repair the file, or"
    " choose the files yourself with --settings or --no-project-settings."
)


def _settings_error(problems: Sequence[str]) -> str:
    """Every settings source that could not be used, and why nothing was planned."""
    return "".join(f"settings: {problem}\n" for problem in problems) + _SETTINGS_ADVICE


def _error_exit(message: str, *, json_output: bool) -> int:
    """Exit 2: the message on stderr, and under --json an envelope on stdout as well.

    A caller that asked for --json parses stdout, so an empty stdout on exit 2 reads as a broken
    tool rather than as the refusal it is.
    """
    for line in message.splitlines():
        print(f"pluginprune: {line}", file=sys.stderr)
    if json_output:
        envelope = {
            "ok": False,
            "command": "pluginprune",
            "skipped": [],
            "data": None,
            "error": message,
        }
        print(json.dumps(envelope, indent=2))
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line. An unexpected crash exits 2, never 1 ("refused or not removed")."""
    _tolerant_streams()
    raw = list(sys.argv[1:] if argv is None else argv)
    json_output = _wants_json(raw)
    try:
        args = _build_parser().parse_args(raw)
    except _ArgumentError as exc:
        return _error_exit(str(exc), json_output=json_output)
    try:
        return _run(args)
    except Exception as exc:  # noqa: BLE001 - the boundary that keeps a crash off exit code 1
        traceback.print_exc(file=sys.stderr)
        return _error_exit(f"unexpected {type(exc).__name__}: {exc}", json_output=json_output)


def _run(args: argparse.Namespace) -> int:
    cache_dir = Path(args.cache_dir).expanduser() if args.cache_dir else default_cache_dir()
    if not cache_dir.is_dir():
        return _error_exit(f"no plugin cache at {cache_dir}", json_output=args.json)

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
    problem = _usage_problem(plan, args)
    if problem is not None:
        return _error_exit(problem, json_output=args.json)
    if plan.settings_problems:
        return _error_exit(_settings_error(plan.settings_problems), json_output=args.json)

    if plan.saw_lock_dir and not plan.saw_live_lock and plan.prune:
        # No live lock anywhere means the running session's own version cannot be identified
        # from the cache, so name the one thing that resolves it rather than guessing.
        print(
            "pluginprune: no live .in_use lock found, so no version is provably in use by a"
            " running session - if a session is open, pass its version with --keep (its"
            " directory is the base path a skill invocation prints)",
            file=sys.stderr,
        )

    applied = apply_plan(plan) if args.apply else None
    failures = list(applied.failures) if applied is not None else []
    refusals = [f"{entry.path}: {entry.refusal}" for entry in plan.refused]
    blocked = refusals + failures

    if args.json:
        data: dict[str, object] = {"applied": args.apply, **plan.as_dict()}
        if applied is not None:
            data["removed"] = [str(entry.path) for entry in applied.removed]
            data["removed_bytes"] = sum(entry.size_bytes for entry in applied.removed)
        print(
            json.dumps(
                {"ok": not blocked, "command": "pluginprune", "skipped": blocked, "data": data},
                indent=2,
            )
        )
    else:
        for line in _render(plan, applied=applied):
            print(line)
        # REFUSED was never attempted; FAILED was attempted and is still there. One word for
        # both sent a reader of an --apply run hunting a removal fault that never happened.
        for item in refusals:
            print(f"  REFUSED: {item}", file=sys.stderr)
        for item in failures:
            print(f"  FAILED: {item}", file=sys.stderr)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
