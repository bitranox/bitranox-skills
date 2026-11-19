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

An entry is parsed into an `Entry` record where the file is read (`Entry.from_disk`) and written
back by `Entry.to_disk`, in the key order and shape earlier releases wrote: `blocks` only once a
stop was blocked for it. A key this release does not know is not carried over.
"""

import contextlib
import hashlib
import json
import math
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

__all__ = [
    "MAX_AGE_SECONDS",
    "MAX_BLOCKS",
    "STALE_FILE_SECONDS",
    "bump_session_blocks",
    "session_key",
    "clear_session",
    "clear_sha",
    "Entry",
    "pending_for",
    "record_push",
    "state_path",
]

# Beyond this, CI has finished and a block is noise rather than a save.
MAX_AGE_SECONDS = 4 * 60 * 60

# When a save prunes OTHER projects' state files, one untouched for this long is removed. Every
# write replaces the file, so its mtime is at least as new as its newest entry: past
# MAX_AGE_SECONDS nothing in it can be pending any more. The horizon still sits a working day out
# rather than at those four hours, because an expired entry is not dead weight - re-pushing the
# same sha carries its block count forward (record_push), and a session paused over a lunch or an
# afternoon must not come back to a fresh set of reminders for a commit it already pushed.
STALE_FILE_SECONDS = 24 * 60 * 60

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


def _recorded_at(value: object) -> float:
    """An entry's `at` as a finite float; 0.0 (long expired) when it is unreadable.

    One entry whose `at` is text, a container, an int too large for a float or an infinity must
    not decide for the others: a raise inside the gate's try dropped the block for every valid
    push beside it, and an infinite `at` stayed pending, and newest, forever.
    """
    if not isinstance(value, (int, float, str, bytes)):
        return 0.0
    try:
        number = float(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _block_count(value: object) -> int:
    """An entry's `blocks` as an int; 0 when it is unreadable, as a never-blocked entry counts."""
    if not isinstance(value, (int, float, str, bytes)):
        return 0
    try:
        return int(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def _text(raw: dict, key: str) -> str | None:
    """The string at `key`, "" when absent or null, None when it holds anything else."""
    value = raw.get(key)
    if value is None:
        return ""
    return value if isinstance(value, str) else None


@dataclass(frozen=True, slots=True)
class Entry:
    """One unwatched push: `session` pushed `sha` to `repo` (`branch` names what was pushed, as
    the nudge displays it) at `at`, and `blocks` stops have been blocked for it since."""

    sha: str
    session: str
    repo: str = ""
    branch: str = ""
    at: float = 0.0
    blocks: int = 0

    @classmethod
    def from_disk(cls, raw: object) -> Entry | None:
        """The entry a state file's list item holds, or None for an item no release wrote.

        A `sha` or `session` holding anything but a string is such an item: a session id of
        another type could otherwise read as the empty one. The other fields are coerced, never
        refused, so one bad value does not drop the push it belongs to: a non-string `repo` or
        `branch` reads as unknown (""), an unreadable `at` as long expired, `blocks` as 0."""
        if not isinstance(raw, dict):
            return None
        sha, session = _text(raw, "sha"), _text(raw, "session")
        if sha is None or session is None:
            return None
        return cls(sha=sha, session=session, repo=_text(raw, "repo") or "",
                   branch=_text(raw, "branch") or "", at=_recorded_at(raw.get("at")),
                   blocks=_block_count(raw.get("blocks")))

    def to_disk(self) -> dict[str, object]:
        """The list item a state file holds: `blocks` only once it is non-zero, as before."""
        data: dict[str, object] = {"sha": self.sha, "session": self.session, "repo": self.repo,
                                   "branch": self.branch, "at": self.at}
        if self.blocks:
            data["blocks"] = self.blocks
        return data


#: A read-modify-write step: the entries now in the file -> (the entries to store, its result).
type Change[T] = Callable[[list[Entry]], tuple[list[Entry], T]]


def _load(path: Path) -> list[Entry]:
    """The pending entries the file holds; an item that is not an entry is left out."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    entries = data.get("pending") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    return [entry for entry in map(Entry.from_disk, entries) if entry is not None]


def _save(path: Path, entries: list[Entry]) -> bool:
    """Replace the file atomically; True only when the new content is in place. The temp name is unique per call: a fixed one is shared by
    every concurrent writer, so one could rename another's half-written file into place.

    The replace is retried over a Windows sharing clash: `pending_for` reads without the lock,
    and on Windows a reader (or a virus scanner) holding the file open makes the rename fail,
    which would drop this write without a trace.

    The result matters to `_update`: a caller that is told its change landed when it did not
    acts on a count that was never stored, and the Stop gate's reminder count then never
    advanced, so its bound never released."""
    import self_improve_signals  # noqa: PLC0415 - kept off the per-shell-call import path, as in _update

    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"pending": [entry.to_disk() for entry in entries]}))
        self_improve_signals.retry_while_shared(os.replace, tmp, path)
        tmp = None
    except (OSError, ValueError):
        return False
    finally:
        if tmp is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
    return True


def _update[T](project_dir: str, change: Change[T], default: T) -> T:
    """Run `change(entries) -> (entries, result)` as one locked read-modify-write; return result.

    A lock that cannot be had in time, or any IO failure, skips the write and returns `default`.
    So does a write that did not land: `result` describes the state AFTER the change, and handing
    it back when the file still holds the old one is how a caller comes to act on a count that
    was never stored.
    """
    return _update_path(state_path(project_dir), change, default)


def _update_path[T](path: Path, change: Change[T], default: T) -> T:
    """`_update` for a state file named by its path rather than by its project."""
    # Imported here, not at the top: the nudge runs after EVERY shell call and almost never
    # writes, so the lock's module is loaded only on the rare call that does.
    import self_improve_signals  # noqa: PLC0415 - kept off the per-shell-call import path

    try:
        with self_improve_signals.memory_lock(path, timeout=_LOCK_TIMEOUT):
            entries, result = change(_load(path))
            saved = _save(path, entries)
    except (OSError, TimeoutError, ValueError):
        return default
    if not saved:
        return default
    _prune_stale_files(path)
    return result


def _is_stale(path: Path, moment: float) -> bool:
    try:
        return moment - path.stat().st_mtime > STALE_FILE_SECONDS
    except OSError:
        return False                                   # vanished mid-scan, or not ours to judge


def _remove_if_stale(path: Path, moment: float) -> None:
    """Remove `path` only while holding its lock, and only if it is STILL stale under it: a writer
    that refreshed it between the scan and the lock must keep its entries. A lock somebody else
    holds means a live writer, so the file is skipped rather than waited for."""
    import self_improve_signals  # noqa: PLC0415 - kept off the per-shell-call import path, as in _update

    if not _is_stale(path, moment):
        return
    with contextlib.suppress(OSError, TimeoutError), \
            self_improve_signals.memory_lock(path, timeout=0):
        if _is_stale(path, moment):
            path.unlink()


def _prune_stale_files(keep: Path) -> None:
    """Remove every OTHER project's state file untouched for STALE_FILE_SECONDS.

    Each project a session ever ran in leaves one of these files in the temp dir, and nothing
    else removes them: the generic temp pruner skips every `claude-` name. So the module that
    creates them cleans them up, on the rare write rather than on every read. Races are expected
    and harmless - a file another session removes first is simply gone."""
    moment = time.time()
    try:
        candidates = list(keep.parent.glob("claude-ci-watch-*.json"))
    except OSError:
        return
    for candidate in candidates:
        if candidate != keep:
            _remove_if_stale(candidate, moment)


def record_push(project_dir: str, session: str, sha: str, repo: str = "", branch: str = "") -> None:
    """Remember that `sha` was pushed by `session` and its CI has not been looked at yet.

    Re-recording the same sha to the same repo keeps its block count: pushing a commit again
    starts no new CI, so it must not buy that push a fresh set of reminders. A push of it to
    another repo does start new CI, and counts from zero.
    """
    def change(entries: list[Entry]) -> tuple[list[Entry], None]:
        mine = [e for e in entries if e.session == session and e.sha == sha]
        kept = [e for e in entries if not (e.session == session and e.sha == sha)]
        carried = max((e.blocks for e in mine if e.repo == repo), default=0)
        entry = Entry(sha=sha, session=session, repo=repo, branch=branch, at=time.time(),
                      blocks=carried)
        return kept + [entry], None

    _update(project_dir, change, None)


def clear_sha(project_dir: str, sha: str, session: str | None = None) -> None:
    """Drop one sha - its CI was watched. With `session`, only that session's entry for it."""
    def change(entries: list[Entry]) -> tuple[list[Entry], None]:
        return [e for e in entries if not (e.sha == sha
                                           and (session is None or e.session == session))], None

    _update(project_dir, change, None)


def clear_session(project_dir: str, session: str) -> None:
    """Drop every pending sha for this session - CI was watched without naming a sha.

    The session's entries are dropped from EVERY state file, not only `project_dir`'s. A file is
    keyed by the event's cwd, which is wherever the shell sits: a push from a linked worktree and
    a watch run after a `cd` to the main checkout land in two files, and clearing only the
    watcher's file left the push pending, so the Stop gate blocked a turn whose CI was watched.
    An empty session id names no session, so it clears its own file only.
    """
    def change(entries: list[Entry]) -> tuple[list[Entry], None]:
        return [e for e in entries if e.session != session], None

    own = state_path(project_dir)
    _update_path(own, change, None)
    if not session:
        return
    try:
        others = [p for p in own.parent.glob("claude-ci-watch-*.json") if p != own]
    except OSError:
        return
    for other in others:
        if any(e.session == session for e in _load(other)):
            _update_path(other, change, None)


def bump_session_blocks(project_dir: str, session: str) -> list[Entry]:
    """Count one block against EVERY entry of this session; return those entries, updated.

    One stop blocked for all of them, so all of them are charged: charging only the newest let a
    session holding N unwatched pushes be blocked up to MAX_BLOCKS times N.
    """
    def change(entries: list[Entry]) -> tuple[list[Entry], list[Entry]]:
        updated = [replace(e, blocks=e.blocks + 1) if e.session == session else e for e in entries]
        return updated, [e for e in updated if e.session == session]

    return _update(project_dir, change, [])


def pending_for(project_dir: str, session: str, now: float | None = None) -> list[Entry]:
    """Unwatched pushes made by THIS session that are still recent enough to act on."""
    moment = time.time() if now is None else now
    return [e for e in _load(state_path(project_dir))
            if e.session == session and moment - e.at < MAX_AGE_SECONDS]
