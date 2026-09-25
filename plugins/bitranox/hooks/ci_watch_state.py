"""Shared state for the post-push CI watch: which pushes are still unwatched.

Two hooks share this file. `ci-watch-nudge.py` (PostToolUse) records a sha when a push lands and
clears it when the CI for it is actually watched; `ci-watch-gate.py` (Stop) refuses to end a turn
while anything is still recorded. Keeping the read/write in one importable module means the two
cannot disagree about the format, and it gives the format a single test surface.

Entries are keyed by SESSION as well as project. A pending push from an EARLIER session must not
block a later unrelated one: that failure mode is already recorded here for the nap-owed Stop gate,
where a stale flag claimed the current session's context had been cleared when it had not. The
session id is stored so the gate can tell "this session pushed and did not look" from "some session
once did".

Entries also EXPIRE. A block is only worth serving while the answer is still actionable - CI for a
push made four hours ago has long since finished, so blocking on it teaches nothing and costs a
turn. `MAX_AGE_SECONDS` is that horizon, not a guess at how long CI runs.

An entry is one (session, sha) pair: two sessions in one project may push the same commit, and
each owes its own watch. Every write is a read-modify-write under an exclusive lock, through a
uniquely named temp file, so writers that overlap (the nudge and the gate, or two sessions) cannot
drop each other's entries.

Every function here swallows its own IO errors and degrades to "nothing pending". A hook must never
wedge a turn, and a state file that cannot be read is not evidence that a push needs watching.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

__all__ = [
    "MAX_AGE_SECONDS",
    "MAX_BLOCKS",
    "bump_session_blocks",
    "session_key",
    "clear_session",
    "clear_sha",
    "pending_for",
    "record_push",
    "state_path",
]

# Beyond this, CI has finished and a block is noise rather than a save.
MAX_AGE_SECONDS = 4 * 60 * 60

# How many times one push may block a stop before the gate gives up and says so. A block that
# can never be escaped wedges a session whose CI genuinely cannot be reached; one that is
# released on the first attempt is not a gate. This bounds the pressure instead of removing it.
MAX_BLOCKS = 3

# A hook waits this long for another writer before giving up on its write. Every write here is a
# few hundred bytes, so contention past this means a stuck holder, and the lock reclaims those.
_LOCK_TIMEOUT = 2.0


def session_key(event: dict) -> str:
    """Where this session's record lives.

    Both hooks must compute this the SAME way or the gate reads a different file than the nudge
    wrote. A `git -C sub push` is keyed here, not under `sub`: the Stop hook only ever sees the
    session's own directory, so keying on the pushed repo would hide the entry from the half whose
    job is to notice it. Which repo was pushed is kept as a field on the entry instead.
    """
    if not isinstance(event, dict):
        return ""
    return str(event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or "")


def state_path(project_dir: str) -> Path:
    """Per-project state file. Keyed by a hash of the path, as the other per-project gates are."""
    key = hashlib.sha1(str(project_dir).encode("utf-8", "replace")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / ("claude-ci-watch-%s.json" % key)


def _load(path: Path) -> list[dict]:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    entries = data.get("pending") if isinstance(data, dict) else None
    return [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []


def _save(path: Path, entries: list[dict]) -> None:
    """Replace the file atomically. The temp name is unique per call: a fixed one is shared by
    every concurrent writer, so one could rename another's half-written file into place.

    The replace is retried over a Windows sharing clash: `pending_for` reads without the lock,
    and on Windows a reader (or a virus scanner) holding the file open makes the rename fail,
    which would drop this write without a trace."""
    import self_improve_signals  # noqa: PLC0415 - kept off the per-shell-call import path, as in _update

    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"pending": entries}))
        self_improve_signals.retry_while_shared(os.replace, tmp, path)
        tmp = None
    except (OSError, ValueError):
        return
    finally:
        if tmp is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp)


def _update(project_dir: str, change, default=None):
    """Run `change(entries) -> (entries, result)` as one locked read-modify-write; return result.

    A lock that cannot be had in time, or any IO failure, skips the write and returns `default`.
    """
    # Imported here, not at the top: the nudge runs after EVERY shell call and almost never
    # writes, so the lock's module is loaded only on the rare call that does.
    import self_improve_signals  # noqa: PLC0415 - kept off the per-shell-call import path

    path = state_path(project_dir)
    try:
        with self_improve_signals.memory_lock(path, timeout=_LOCK_TIMEOUT):
            entries, result = change(_load(path))
            _save(path, entries)
            return result
    except (OSError, TimeoutError, ValueError):
        return default


def _blocks(entry: dict) -> int:
    try:
        return int(entry.get("blocks") or 0)
    except (TypeError, ValueError):
        return 0


def record_push(project_dir: str, session: str, sha: str, repo: str = "", branch: str = "") -> None:
    """Remember that `sha` was pushed by `session` and its CI has not been looked at yet.

    Re-recording the same sha to the same repo keeps its block count: pushing a commit again
    starts no new CI, so it must not buy that push a fresh set of reminders. A push of it to
    another repo does start new CI, and counts from zero.
    """
    def change(entries):
        mine = [e for e in entries if e.get("session") == session and e.get("sha") == sha]
        kept = [e for e in entries if not (e.get("session") == session and e.get("sha") == sha)]
        entry = {"sha": sha, "session": session, "repo": repo, "branch": branch, "at": time.time()}
        carried = max((_blocks(e) for e in mine if e.get("repo", "") == repo), default=0)
        if carried:
            entry["blocks"] = carried
        return kept + [entry], None

    _update(project_dir, change)


def clear_sha(project_dir: str, sha: str, session: str | None = None) -> None:
    """Drop one sha - its CI was watched. With `session`, only that session's entry for it."""
    def change(entries):
        return [e for e in entries if not (e.get("sha") == sha
                                           and (session is None or e.get("session") == session))], None

    _update(project_dir, change)


def clear_session(project_dir: str, session: str) -> None:
    """Drop every pending sha for this session - CI was watched without naming a sha."""
    _update(project_dir, lambda entries: ([e for e in entries if e.get("session") != session], None))


def bump_session_blocks(project_dir: str, session: str) -> list[dict]:
    """Count one block against EVERY entry of this session; return those entries, updated.

    One stop blocked for all of them, so all of them are charged: charging only the newest let a
    session holding N unwatched pushes be blocked up to MAX_BLOCKS times N.
    """
    def change(entries):
        mine = []
        for entry in entries:
            if entry.get("session") == session:
                entry["blocks"] = _blocks(entry) + 1
                mine.append(dict(entry))
        return entries, mine

    return _update(project_dir, change, default=[])


def pending_for(project_dir: str, session: str, now: float | None = None) -> list[dict]:
    """Unwatched pushes made by THIS session that are still recent enough to act on."""
    moment = time.time() if now is None else now
    return [e for e in _load(state_path(project_dir))
            if e.get("session") == session
            and moment - float(e.get("at") or 0) < MAX_AGE_SECONDS]
