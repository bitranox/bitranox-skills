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

Every function here swallows its own IO errors and degrades to "nothing pending". A hook must never
wedge a turn, and a state file that cannot be read is not evidence that a push needs watching.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

__all__ = [
    "MAX_AGE_SECONDS",
    "MAX_BLOCKS",
    "bump_blocks",
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
    try:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"pending": entries}), encoding="utf-8")
        os.replace(tmp, path)
    except (OSError, ValueError):
        return


def record_push(project_dir: str, session: str, sha: str, repo: str = "", branch: str = "") -> None:
    """Remember that `sha` was pushed and its CI has not been looked at yet."""
    path = state_path(project_dir)
    entries = [e for e in _load(path) if e.get("sha") != sha]
    entries.append({"sha": sha, "session": session, "repo": repo,
                    "branch": branch, "at": time.time()})
    _save(path, entries)


def clear_sha(project_dir: str, sha: str) -> None:
    """Drop one sha - its CI was watched."""
    path = state_path(project_dir)
    _save(path, [e for e in _load(path) if e.get("sha") != sha])


def clear_session(project_dir: str, session: str) -> None:
    """Drop every pending sha for this session - CI was watched without naming a sha."""
    path = state_path(project_dir)
    _save(path, [e for e in _load(path) if e.get("session") != session])



def bump_blocks(project_dir: str, sha: str) -> int:
    """Count one block against this sha and return the new total."""
    path = state_path(project_dir)
    entries = _load(path)
    total = 0
    for entry in entries:
        if entry.get("sha") == sha:
            total = int(entry.get("blocks") or 0) + 1
            entry["blocks"] = total
    _save(path, entries)
    return total


def pending_for(project_dir: str, session: str, now: float | None = None) -> list[dict]:
    """Unwatched pushes made by THIS session that are still recent enough to act on."""
    moment = time.time() if now is None else now
    return [e for e in _load(state_path(project_dir))
            if e.get("session") == session
            and moment - float(e.get("at") or 0) < MAX_AGE_SECONDS]
