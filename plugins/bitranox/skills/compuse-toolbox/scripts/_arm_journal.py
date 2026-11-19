# /// script
# requires-python = ">=3.10"
# ///
"""A restore journal for mutation_arm: the originals of every mutated source, kept ON DISK.

mutation_arm restores in a `finally`, which runs on its own --timeout, on an exception and on a
Ctrl-C, but not when the process is killed from outside: a caller's tool timeout that kills the
process tree, a SIGKILL, a closed terminal. Measured: a battery killed by its caller's 10-minute
tool cap left one arm's mutation in a source that was about to be committed, and only a manual
full-diff review caught it. A catchable signal is turned into a restore by mutation_arm itself;
this journal covers the kill nothing can catch.

Before the first source is written, the journal holds a byte copy of each original plus the
SHA-256 of the exact bytes the arm is about to write, under a directory named after the writing
process's pid. A run that finishes (restored or not) removes it only once every file matches its
original. Every later start calls :func:`recover` first, which looks at each journal whose
process is gone:

* a file that holds its original again is fine;
* a file that holds exactly the recorded mutant is restored from the copy, with a notice;
* a file that holds anything else was edited after the kill: it is left untouched and reported
  as a conflict, naming the original's copy, because restoring would destroy that edit.

A journal whose process is still running is held: a second run that would mutate one of its
files is refused instead of saving the first run's MUTANT as its own original. A pid reused by an
unrelated process makes a dead run's journal look held; that only delays its recovery until that
process ends, never restores a wrong file.

The journals live under `MUTATION_ARM_STATE_DIR` when set (tests, a sandbox), else
`$XDG_STATE_HOME/mutation_arm` (`~/.local/state/mutation_arm`), or `%LOCALAPPDATA%\\mutation_arm`
on Windows: per user, outside every work tree, so no `git add` can stage a copy.

Standard library only, and loadable on 3.10: a sibling of a script that runs under a project's
own interpreter. Imported by bare name, which works because running a script puts its own
directory first on sys.path, and the tests' conftest puts scripts/ there too.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import sys
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict, cast

__all__ = ["JOURNAL_FILE", "STATE_DIR_ENV", "Conflict", "Entry", "Journal", "Recovery",
           "journal_root", "pid_alive", "recover"]

STATE_DIR_ENV = "MUTATION_ARM_STATE_DIR"
JOURNAL_FILE = "journal.json"

# Windows process access right and the exit code GetExitCodeProcess reports for a live process.
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259
_ERROR_ACCESS_DENIED = 5


class Entry(TypedDict):
    """One journalled source: where it lives, its original's copy, the mutant's digest."""

    path: str
    original: str
    mutant_sha256: str


def journal_root() -> Path:
    """Where the journals live: the override, else the per-user state directory."""
    override = os.environ.get(STATE_DIR_ENV)
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "mutation_arm"


def pid_alive(pid: int) -> bool:
    """Whether a process with this pid exists. Never signals it.

    On Windows `os.kill(pid, 0)` is not a probe: any signal other than the two console events
    becomes TerminateProcess, so it would kill the process it asks about. The process is opened
    and its exit code read instead.

    Examples:
        >>> pid_alive(os.getpid())
        True
    """
    if pid <= 0:
        return False
    if sys.platform == "win32":
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True             # it exists, owned by another user
    except OSError:
        return False
    return True


def _pid_alive_windows(pid: int) -> bool:
    if sys.platform != "win32":     # narrows for the type checker; never taken at run time
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
    if not handle:
        # Access denied means it exists under another user; anything else means it is gone.
        return ctypes.get_last_error() == _ERROR_ACCESS_DENIED
    try:
        code = ctypes.c_uint32(0)
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return True
        return code.value == _STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


class Journal:
    """The on-disk record of one arm: written before its first source write, removed after a
    restore that matched every file."""

    def __init__(self, directory: Path, entries: list[Entry]) -> None:
        self.directory = directory
        self.entries = entries

    @classmethod
    def create(cls, mutants: dict[Path, bytes], root: Path | None = None) -> Journal:
        """Copy every original and record the mutant each file is about to receive.

        `mutants` maps each source path to the exact bytes the arm will write. The copies and the
        record are durable before this returns, so a kill at any later point is recoverable.
        Raises OSError when the journal cannot be written; nothing has been mutated then.
        """
        base = root if root is not None else journal_root()
        directory = base / f"{os.getpid()}-{uuid.uuid4().hex[:12]}"
        entries: list[Entry] = []
        try:
            directory.mkdir(parents=True)
            for index, (path, mutant) in enumerate(mutants.items()):
                # Index-prefixed: two files in different directories may share a basename.
                copy = f"{index}-{path.name}"
                shutil.copyfile(path, directory / copy)
                entries.append(Entry(path=str(Path(path).resolve()), original=copy,
                                     mutant_sha256=_sha256(mutant)))
            _write_atomic(directory / JOURNAL_FILE, json.dumps(
                {"pid": os.getpid(), "files": entries}, indent=2))
        except OSError as exc:
            shutil.rmtree(directory, ignore_errors=True)
            raise OSError(f"cannot write the restore journal under {base} ({exc}); set "
                          f"{STATE_DIR_ENV} to a writable directory") from exc
        return cls(directory, entries)

    def original(self, entry: Entry) -> Path:
        return self.directory / entry["original"]

    def discard(self) -> None:
        """Remove the journal; only once every file is back. Never raises."""
        shutil.rmtree(self.directory, ignore_errors=True)


@dataclass
class Conflict:
    """A journalled file that holds neither its original nor the recorded mutant."""

    path: str
    original: str
    journal: str
    pid: int


@dataclass
class Recovery:
    """What one :func:`recover` pass did and found."""

    restored: list[str] = field(default_factory=list[str])
    conflicts: list[Conflict] = field(default_factory=list[Conflict])
    held: dict[str, int] = field(default_factory=dict[str, int])
    unreadable: list[str] = field(default_factory=list[str])

    def blocking(self, paths: Iterable[str | Path]) -> list[str]:
        """Refusal lines for the planned `paths` this recovery leaves unsafe to mutate."""
        wanted = {str(Path(p).resolve()) for p in paths}
        lines = [f"{c.path} differs from both its original and the mutation a killed run (pid "
                 f"{c.pid}) left in it; its original is {c.original} - compare, restore it by "
                 f"hand, then delete {c.journal}" for c in self.conflicts if c.path in wanted]
        lines += [f"{p} is being mutated by another mutation_arm run (pid {pid}) right now"
                  for p, pid in self.held.items() if p in wanted]
        return lines


def _journal_pid(directory: Path) -> int | None:
    head = directory.name.split("-", 1)[0]
    return int(head) if head.isdigit() else None


def _entries(data: object) -> list[Entry] | None:
    """The record's entries, or None when any is malformed: a journal read half-right could be
    discarded with a file still unrecovered, so it is reported instead."""
    files = cast("dict[str, object]", data).get("files") if isinstance(data, dict) else None
    if not isinstance(files, list):
        return None
    entries: list[Entry] = []
    for raw in cast("list[object]", files):
        item = cast("dict[str, object]", raw) if isinstance(raw, dict) else {}
        path, original, digest = item.get("path"), item.get("original"), item.get("mutant_sha256")
        if not (isinstance(path, str) and isinstance(digest, str) and isinstance(original, str)
                and original and Path(original).name == original):
            return None                 # a copy name must stay inside the journal directory
        entries.append(Entry(path=path, original=original, mutant_sha256=digest))
    return entries


def recover(root: Path | None = None) -> Recovery:
    """Repair what killed runs left behind; report what is held or in conflict. Never raises."""
    result = Recovery()
    base = root if root is not None else journal_root()
    try:
        directories = sorted(d for d in base.iterdir() if d.is_dir())
    except OSError:
        return result
    for directory in directories:
        _recover_one(directory, result)
    return result


def _recover_one(directory: Path, result: Recovery) -> None:
    pid = _journal_pid(directory)
    if pid is None:
        return                       # not one of ours
    alive = pid != os.getpid() and pid_alive(pid)
    record = directory / JOURNAL_FILE
    if not record.exists():
        # The record is written before any source is: without one nothing was mutated.
        if not alive:
            shutil.rmtree(directory, ignore_errors=True)
        return
    try:
        entries = _entries(json.loads(record.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        entries = None
    if entries is None:
        result.unreadable.append(str(directory))
        return
    if alive:
        for entry in entries:
            result.held[entry["path"]] = pid
        return
    journal = Journal(directory, entries)
    clean = True
    for entry in entries:
        clean = _recover_entry(journal, entry, pid, result) and clean
    if clean:
        journal.discard()


def _recover_entry(journal: Journal, entry: Entry, pid: int, result: Recovery) -> bool:
    """True when this file is back to its original (it was, or it is now)."""
    path, original = Path(entry["path"]), journal.original(entry)
    try:
        current, kept = path.read_bytes(), original.read_bytes()
        if current == kept:
            return True
        if _sha256(current) == entry["mutant_sha256"]:
            shutil.copyfile(original, path)
            os.utime(path)       # a fresh mtime, so a build cache does not keep the mutant's build
            result.restored.append(str(path))
            return True
    except OSError:
        pass
    result.conflicts.append(Conflict(str(path), str(original), str(journal.directory), pid))
    return False
