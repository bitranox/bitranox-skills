"""Shared helpers for the meta-skill-ab-test scripts: envelope, subprocess, git, hashes, schedule.

Stdlib only: the repo gate runs this suite in a bare environment. Every script in this directory
imports from here and from nothing outside the directory, because a skill is installed on its own.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePath

_NON_ALNUM_RE = re.compile(r"[^a-zA-Z0-9]")

__all__ = [
    "EXCLUDED_TREE_DIRS",
    "EXIT_ERROR",
    "EXIT_NO",
    "EXIT_YES",
    "GROUP_POLL_S",
    "JsonObject",
    "JsonValue",
    "append_jsonl",
    "clear_group",
    "dashkey",
    "envelope",
    "git",
    "git_env",
    "int_or_zero",
    "json_items",
    "median",
    "read_jsonl",
    "rotated_schedule",
    "run",
    "sha256_file",
    "signal_group",
    "tree_hashes",
    "utc_now",
]

EXIT_YES = 0
EXIT_NO = 1
EXIT_ERROR = 2
EXCLUDED_TREE_DIRS = {"__pycache__", ".skillwriter", "tests"}
# How often clear_group asks whether a process group is empty yet during its grace.
GROUP_POLL_S = 0.05

# A value as json.loads gives it (what a file written by any harness version, or by the CLI, may
# hold), or as json.dumps takes it: the read-only container types let a list[str] or a
# dict[str, str] stand. Defined here, the lowest module, so every script can type its JSON.
type JsonValue = None | bool | int | float | str | Sequence[JsonValue] | Mapping[str, JsonValue]
type JsonObject = dict[str, JsonValue]


def int_or_zero(value: JsonValue) -> int:
    """int(value or 0) over a JSON value: a usage count as the CLI writes it.

    Kept to exactly what that expression did (a numeric string converts, a float truncates, a
    non-empty list or object raises TypeError), so a stream that once accounted still does.

    Examples:
        >>> int_or_zero(None), int_or_zero(7), int_or_zero("12"), int_or_zero(3.9), int_or_zero(True)
        (0, 7, 12, 3, 1)
        >>> int_or_zero([1])
        Traceback (most recent call last):
        ...
        TypeError: int() argument must be a string, a bytes-like object or a real number, not 'list'
    """
    if not value:
        return 0
    if isinstance(value, bool | int | float | str):
        return int(value)
    raise TypeError(f"int() argument must be a string, a bytes-like object or a real number, not {type(value).__name__!r}")


def json_items(value: JsonValue) -> list[JsonValue]:
    """What `for x in value or []` walked over a JSON value: a string's characters and an object's
    keys included, a scalar's TypeError too.

    The fields read this way are lists in every file the CLI or the harness writes; any other
    shape is iterated as the plain loop always did, so a file that read before reads the same now.

    Examples:
        >>> json_items(None), json_items(["a", 1]), json_items("ab"), json_items({"k": 1})
        ([], ['a', 1], ['a', 'b'], ['k'])
    """
    if not value:
        return []
    if isinstance(value, str):
        return list(value)
    if isinstance(value, Mapping):
        return list(value.keys())
    if isinstance(value, list | tuple):
        return list(value)
    raise TypeError(f"{type(value).__name__!r} object is not iterable")


def envelope(command: str, data: JsonValue, *, ok: bool = True, skipped: list[str] | None = None) -> str:
    """The {ok, command, data, skipped} JSON envelope every subcommand prints under --json."""
    return json.dumps({"ok": ok, "command": command, "data": data, "skipped": skipped or []}, indent=1)


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
        timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    """Run argv without a shell, capturing UTF-8 text; never raises on a non-zero exit."""
    return subprocess.run(argv, cwd=str(cwd) if cwd else None, env=env, capture_output=True,  # nosec B603
                          text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)


def git_env() -> dict[str, str]:
    """os.environ minus every GIT_* variable, so an inherited GIT_DIR cannot redirect a git call."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """git -C repo args..., with every inherited GIT_* variable stripped from the child env."""
    return run(["git", "-C", str(repo), *args], env=git_env())


def sha256_file(path: Path) -> str:
    """The hex sha256 of the file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    """{relative posix path: sha256} of the files a skill ships (tests, caches and .pyc excluded)."""
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in EXCLUDED_TREE_DIRS for part in rel.parts) or p.suffix == ".pyc":
            continue
        out[rel.as_posix()] = sha256_file(p)
    return out


def rotated_schedule(arms: list[str], rounds: int) -> list[list[str]]:
    """Round r runs the arms rotated by r, so no arm always goes first (design S1)."""
    if not arms:
        raise ValueError("no arms")
    k = len(arms)
    return [[arms[(i + r) % k] for i in range(k)] for r in range(rounds)]


def median(values: list[float]) -> float:
    """The median; the mean of the two middle values for an even count. Refuses an empty list."""
    s = sorted(values)
    if not s:
        raise ValueError("median of nothing")
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def dashkey(path: PurePath) -> str:
    """Claude Code's ~/.claude/projects directory name for a cwd: every non-alphanumeric is '-'.

    Claude Code truncates a name over 200 characters and appends a hash; that case is not
    reproduced here, so a caller must not rebuild such a path from this value.
    """
    return _NON_ALNUM_RE.sub("-", str(path))


def utc_now() -> str:
    """The current UTC time as an ISO 8601 second, e.g. 2026-01-02T03:04:05Z."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_jsonl(path: Path) -> list[JsonValue]:
    """Every non-blank line of a JSONL file, parsed (an object per line in every file this harness
    writes); a missing file reads as no rows."""
    if not path.is_file():
        return []
    rows: list[JsonValue] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: Mapping[str, JsonValue]) -> None:
    """Append one row as a sorted-key JSON line, LF-terminated on every platform."""
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def signal_group(pgid: int, sig: int) -> bool:
    """Send sig to the process group pgid (POSIX); False once no member is left that this run may signal."""
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def clear_group(pgid: int, grace: float, *, reap: Callable[[], object] | None = None) -> None:
    """SIGTERM every member of the group, give them grace to exit, then SIGKILL whatever is left (POSIX).

    Returns as soon as the group is empty. A member killed but not yet reaped still counts as
    present, so the wait can run its whole grace: a caller whose own child leads the group passes
    reap (e.g. Popen.poll) so that child is collected while the others are waited for. The
    SIGKILL after a full grace is then a no-op for anything that already exited.
    """
    if not signal_group(pgid, signal.SIGTERM):
        return
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if reap is not None:
            reap()
        if not signal_group(pgid, 0):
            return
        time.sleep(GROUP_POLL_S)
    signal_group(pgid, signal.SIGKILL)
