"""Is a process, or a Claude Code session, still alive? Stdlib only, every platform.

Shared by the temp-dir pruner (tmp_prune.py) and the plugin-cache pruner
(skills/meta-prune-plugin-cache/scripts/pluginprune.py), which both refuse to delete what a live
process may still use. Both lean the same way on every unknowable answer: keeping costs disk,
deleting under a live session costs that session.

Claude Code registers each running session as `~/.claude/sessions/<pid>.json` with `pid`,
`sessionId` and `procStart`, where `procStart` is field 22 of `/proc/<pid>/stat` (the start time in
clock ticks). Comparing that start time is what tells a live session from a recycled pid.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

__all__ = ["LiveSessions", "live_session_ids", "pid_alive", "process_start_ticks"]


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
        # PermissionError: the process exists under another user. OverflowError: a corrupt record
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


@dataclass(frozen=True)
class LiveSessions:
    """The session ids with a live process behind them.

    `uncertain` is True when some registry entry could not be read: its session id is then unknown,
    so ANY session-named directory might be its own and a caller must not delete on this answer.
    """

    ids: frozenset[str]
    uncertain: bool


def live_session_ids(sessions_dir: Path) -> LiveSessions:
    """Read Claude Code's session registry and keep the entries whose process still runs."""
    if not sessions_dir.exists():
        return LiveSessions(frozenset(), uncertain=False)  # no Claude Code session ever ran here
    try:
        records = sorted(p for p in sessions_dir.iterdir() if p.suffix == ".json")
    except OSError:
        return LiveSessions(frozenset(), uncertain=True)
    ids: set[str] = set()
    uncertain = False
    for record in records:
        parsed = _read_record(record)
        if parsed is None:
            uncertain = True
            continue
        session_id, pid, recorded_start = parsed
        if _is_live(pid, recorded_start):
            ids.add(session_id)
    return LiveSessions(frozenset(ids), uncertain=uncertain)


def _is_live(pid: int, recorded_start: str | None) -> bool:
    if not pid_alive(pid):
        return False
    actual_start = process_start_ticks(pid)
    # A recycled pid runs a different process: same number, different start time.
    return recorded_start is None or actual_start is None or recorded_start == actual_start


def _read_record(record: Path) -> tuple[str, int, str | None] | None:
    """(sessionId, pid, procStart) from one registry file, or None when it cannot be trusted."""
    try:
        payload = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    session_id = payload.get("sessionId")
    pid = payload.get("pid")
    if not isinstance(session_id, str) or not session_id or not isinstance(pid, int):
        return None
    start = payload.get("procStart")
    return session_id, pid, str(start) if start is not None else None
