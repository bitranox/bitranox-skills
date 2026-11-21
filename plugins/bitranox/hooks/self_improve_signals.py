"""Shared learning-signal patterns for the self-improve hooks.

Single source of truth, imported by:
  * self-improve-gate.py  - the per-turn Stop hook (uses the STRICT patterns: high
    precision, fires a capture nudge on the last turn).
  * self-improve-audit.py - the SessionEnd hook (uses STRICT + the BROADER recall
    patterns to find CANDIDATE MISSES across the whole session: a turn the broad set
    flags but the strict set did not, i.e. a likely gate gap to review next session).

Signals cluster in FAMILIES; cover the family, do not wait to be fed one phrase at a time:
  (1) USER correction, (2) USER explicit "remember", (3) ENDORSEMENT of a good idea from
  EITHER side, (4) ASSISTANT self-admitted miss, (5) ASSISTANT realization/discovery.

Role split: correction/"remember" count only from the USER; self-admitted misses and
realizations only from the ASSISTANT; endorsement counts from either side. English + German.
"""

import contextlib
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Generator, Iterable, Iterator, Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import BinaryIO, Final, Literal, NamedTuple, TypedDict, TypeIs, cast

import claude_paths
import process_liveness
import shell_text

# A filesystem path as callers hand it in: a str from hook stdin or argv, or a Path built here.
type _StrPath = str | os.PathLike[str]

# One decoded JSON object: a queue entry, a tombstone, a session or nap marker. The values are
# whatever the file held, so each reader narrows the field it uses.
type JsonRecord = dict[str, object]


def _is_record(value: object) -> TypeIs[JsonRecord]:
    """True for a decoded JSON object. Its keys are str for anything json.loads produced, which
    is the only source the readers here take."""
    return isinstance(value, dict)


def _is_list(value: object) -> TypeIs[list[object]]:
    """True for a decoded JSON array."""
    return isinstance(value, list)


# float() and int() refuse what they cannot convert with TypeError or ValueError, and every caller
# here catches both: a stored value is whatever a hand edit left, so the conversion IS the check.
_coerce_float = cast("Callable[[object], float]", float)
_coerce_int = cast("Callable[[object], int]", int)

# ---- Audit-file location (shared by self-improve-audit.py writer + session-start reader) --

def proj_key(proj: object) -> str:
    """Stable per-project key (matches the gate's state-file scheme).

    The path is normalized to an absolute, dot-free form BEFORE hashing, so one project spelled
    `.`, with a trailing slash, or through a `..` segment yields ONE key. Hashing the raw string
    meant a relative spelling addressed a different state file entirely - measured as
    `contrib_queue.py list .` reporting an empty queue while the absolute path reported a pending
    item, and `dream_state.py done .` recording against a key nothing else reads. Silent in both
    directions: no error, just a confident answer about a project that does not exist.

    This names ~15 per-project state files (dream marker, contribution queue and its closed logs,
    session, watermark, promote counters, filler/topical word lists, recall caches), so the choice
    of normalizer is a compatibility decision:

    * `abspath`, deliberately NOT `resolve`: following symlinks would re-key any project reached
      through one and orphan every state file it already has. The defect here is SPELLING, not
      aliasing, and the fix stays inside that scope.
    * An already-absolute, normalized path hashes exactly as before, so nothing existing moves.
      A test pins that with a literal digest.

    A non-string argument is coerced rather than raised on - a key that throws would take down
    every hook that names a state file. A bytes path is decoded the way the OS decodes a file
    name (`os.fsdecode`), so `b"/x"` and `"/x"` name one project; hashing the bytes path itself
    raised AttributeError.
    """
    try:
        # Any object reaches here; os.fspath raises the TypeError a non-path gets.
        normalized: str = (os.path.abspath(os.fsdecode(os.fspath(cast("_StrPath", proj))))
                           if proj else os.getcwd())
    except (TypeError, ValueError):
        normalized = str(proj)
    return hashlib.sha1(normalized.encode("utf-8", "replace")).hexdigest()[:16]


def audit_file(proj: _StrPath | None) -> Path:
    """Where the SessionEnd audit writes candidate misses for the next SessionStart to read."""
    return claude_paths.audit_dir() / (proj_key(proj) + ".md")


# The characters that carry STRUCTURE in the frames a snippet is quoted into: the audit envelope's
# `</SELF-IMPROVE-AUDIT>` tag, the Stop hint's ` | ` record separator, and the quotes a snippet is
# fenced in. Mapped to safe lookalikes rather than escaped as entities: a snippet is capped evidence
# meant to be READ, and spending four characters per hit would eat the budget it is quoted within.
_SNIPPET_INERT = str.maketrans({"<": "(", ">": ")", "|": "/", '"': "'"})
_SNIPPET_ESCAPED_MARK = " [escaped]"   # rendered OUTSIDE the fence, never inside the text


_SNIPPET_LEAD = "..."    # marks a snippet whose window does not start at the text's first character


def inert_snippet(text: object, limit: int | None = None, *, around: int | None = None) -> str:
    """`text` as one line of quoted evidence that cannot escape the frame it is displayed in.

    `around` is an offset into the WHITESPACE-COLLAPSED text (what `" ".join(text.split())` gives,
    which is what this function quotes). With it and a `limit`, the snippet is a window of at most
    `limit` characters placed so that offset falls inside it, a short lead of context before it,
    and a window that does not start at character 0 opens with `...` (counted within `limit`).
    Without it the snippet is the text's head, as it always was. A caller that found its reason
    to quote the text part-way through - a learning stated after a long preamble - passes the
    offset, or the head cap cuts away the very sentence the snippet exists to show.

    Untrusted text reaches a model's context through three frames - the `<SELF-IMPROVE-AUDIT>`
    envelope injected at SessionStart, the Stop hook's block reason, and the dream's report - and
    the source is genuinely outside our control: a `tool_result` is a fetched page, remote stderr or
    the contents of a file someone else wrote, and `last_assistant_message` is written by a subagent
    that may itself have been summarising any of those. Verified in the 2026-08-28 audit: a
    tool_result carrying a literal closing tag ended the envelope early, so everything after it was
    read as ordinary session context instead of as quoted candidate data.

    Applied at the PRODUCER, which is the trust boundary - the point where text nobody vouches for
    enters main-session storage. The three consumers then render data that is already inert, rather
    than each re-deriving the same escaping and one of them forgetting.

    What this does NOT do, and must not be read as doing: make the text stop SOUNDING like an
    instruction. No escaping turns "SYSTEM: ignore the audit" into something that reads as inert
    prose. What is defended here is the FRAME - the payload cannot close the envelope, forge a
    record boundary, or close its own quotes. Labelling it as untrusted is the consumers' job, and
    is mitigation rather than elimination.
    """
    collapsed = " ".join(str(text or "").split())
    # 1:1 substitution, so the cap still means exactly `limit` characters.
    inert = collapsed.translate(_SNIPPET_INERT)
    if limit is None:
        return inert
    if around is None or len(inert) <= limit:
        return inert[:limit]
    start = max(0, min(int(around) - limit // 5, len(inert) - limit))
    if start == 0:
        return inert[:limit]
    # The marker replaces the first characters of the LEAD, never the tail: the window can sit at
    # the very end of the text, and the offset is always at least `limit // 5` past `start`.
    return _SNIPPET_LEAD + inert[start + len(_SNIPPET_LEAD):start + limit]


def snippet_was_escaped(text: object) -> bool:
    """True when `inert_snippet` would substitute something in `text`.

    A CONTROL signal, kept out of the data band on purpose. Appending a marker to the snippet put
    it inside the fence, where a payload ending in that same literal rendered identically to a
    snippet we really had altered - so the signal could be forged by the very text it described.
    The producer records this beside the snippet and the render reads it from there.
    """
    collapsed = " ".join(str(text or "").split())
    return collapsed.translate(_SNIPPET_INERT) != collapsed


def quoted_snippet(record: Mapping[str, object]) -> str:
    """A STORED snippet as it must appear in any frame a model reads: re-neutralised, then fenced.

    Deliberate defense in depth, against the usual rule that internal calls trust the type
    contract. The render is the last point before the text reaches a model, and neutralising only
    at the producer covers exactly the records this version wrote: 42 buffered records existed when
    this was added, 14 carrying a structural character from the older producer. A producer added
    later that forgets `inert_snippet` would reach every consumer raw - which is how the third
    consumer came to be forgotten in the first place.

    No cap: the stored snippet was already capped by its producer, and re-capping here would eat a
    legitimately-sized snippet a second time.

    Takes the RECORD, never the text plus a flag. The two are always a pair, and passing them
    separately made the flag optional in practice: a consumer that handed over only the text
    rendered a producer-escaped record unmarked, and nothing could detect it, because the stored
    text is already inert so the render's own check finds nothing to report. Forgetting is made
    impossible here rather than merely discouraged - a bare string is refused.

    `escaped` is the producer's own record of having substituted - a producer-time fact the render
    cannot recover, because the substitution is lossy and idempotent. The render marks on that flag
    OR on its own substitution: the first covers a record written inert, the second a record stored
    raw by a producer that skipped `inert_snippet`. Either alone leaves half the records silently
    misrepresented. The marker sits OUTSIDE the quotes, so nothing within them can imitate it.
    """
    fields = _snippet_record(record)
    text = fields.get("snippet") or ""
    mark = _SNIPPET_ESCAPED_MARK if (fields.get("escaped") or snippet_was_escaped(text)) else ""
    return '"%s"%s' % (inert_snippet(text), mark)


def _snippet_record(record: object) -> Mapping[str, object]:
    """`record` as the mapping `quoted_snippet` reads; TypeError for anything else, a bare snippet
    string above all. Typed `object` because the refusal is for callers the type does not stop."""
    if not isinstance(record, Mapping):
        raise TypeError("quoted_snippet takes the record, not the snippet text: %r" % type(record).__name__)
    return cast("Mapping[str, object]", record)


_SESSION_KEY_MAX = 64


def session_key(session: object) -> str:
    """`session` reduced to ONE safe filename component - the session-side twin of `proj_key`.

    `session_id` arrives on hook stdin and a dozen state files are named after it. A path built by
    concatenation is confined by nothing: measured before this existed, `../../../tmp/pwned` walked
    out of the audit dir and `/tmp/absolute-pwned` replaced the base dir outright, because joining
    an absolute path DISCARDS what it was joined to. Severity is bounded - Claude Code mints the id,
    not the model - so this is defense in depth at a trust boundary, not a live hole; what earns it
    one shared helper is that a dozen sites each built their own path.

    An ALLOWLIST, not an escape of the characters that happen to be dangerous today: everything
    outside `[A-Za-z0-9_.-]` becomes `_`, so no separator, no drive colon and no NUL survives to be
    interpreted by the filesystem. `.` and `-` stay because a real id is a UUID and must pass
    through UNCHANGED - a sanitiser that rewrote those would silently orphan every state file
    already on disk. `..` therefore survives as a name, which is harmless: the result is always
    appended to a suffix, so it can only ever name a file inside the audit dir.

    Over-long ids keep a digest of the FULL id rather than being truncated flat. Truncation
    aliases: two sessions sharing a long prefix would land on one state file and the second would
    read the first one's, silently. Real ids are 36-char UUIDs so neither branch fires on them.
    """
    raw = str(session or "")
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", raw)
    if len(safe) <= _SESSION_KEY_MAX:
        return safe
    # Hash the RAW id, not the sanitised one: two ids differing only in a stripped character are
    # different sessions and must not converge here either.
    digest = hashlib.sha1(raw.encode("utf-8", "replace")).hexdigest()[:16]
    return safe[:_SESSION_KEY_MAX - len(digest) - 1] + "-" + digest


def session_state_path(session: object, suffix: str) -> Path:
    """The audit-dir path of `session`'s `suffix` state file, confined to a single component.

    Hooks call THIS rather than joining `audit_dir()` themselves: making the sink shared is what
    stops the next session-keyed state file from reintroducing the traversal one hook at a time.
    """
    return audit_dir() / (session_key(session) + suffix)


# ---- meta-dream-tree consolidation: cadence markers + mode (shared by session-start + dream_state) --

_DREAM_THRESHOLD_S = 24 * 3600  # do not nudge a fresh consolidation more often than this


def project_slug(proj: str) -> str:
    """Claude Code's ~/.claude/projects directory name for a project cwd.

    Transcribed from the CLI binary (2.1.240):
        h1r(e) = e.replace(/[^a-zA-Z0-9]/g, "-")
    EVERY non-alphanumeric collapses to "-", not just "/". Replacing only "/" agrees for a plain
    path and then silently points at a directory Claude never wrote as soon as a component holds
    a ".", "_" or a space. Past 200 characters Claude truncates and appends a hash, which is not
    reproduced here - see is_truncated_slug in migrate_memory for that case.
    """
    return re.sub(r"[^a-zA-Z0-9]", "-", proj)


def memory_dir(proj: str) -> Path:
    """The native Auto-memory dir for a project cwd."""
    return claude_paths.config_dir() / "projects" / project_slug(proj) / "memory"


# ---- curated store relocation: <proj>/.claude-bx-selflearning (the new per-project home) ----
# The curated tier lives IN the project tree (travels with it; gitignored on public repos) so a
# single `@import` line pulls its `index.md` into context. That line lives in the UNTRACKED
# `CLAUDE.local.md` by default (symmetric with the gitignored store), or the TRACKED `CLAUDE.md` when
# `track_private` is on. The native `memory_dir()` above stays as the raw second tier.

MEMORY_DIRNAME = ".claude-memory"             # the LIVE central body-store dir, co-located at a tree's
                                              # anchor; the store-colocation key for anchor resolution

# Dirs never worth walking for stores/CLAUDE.md (vendored / build / VCS / cache). Single source;
# gather_scan and the multi-tree walks alias this.
VENDOR_DIRNAMES = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "site-packages", ".mypy_cache",
    ".pytest_cache", ".tox", ".idea", ".ruff_cache", "dist", "build", ".eggs",
}

# LEGACY dirnames: the retired pre-UUID store layout. Kept ONLY for the one-shot migration tools
# (migrate_memory receipts, the store walks that must never descend into an old store) and
# gather_scan's transitional dual-read on downstream installs - including recall-memory.py, which
# labels a legacy `index.md` hit that dual-read returns and strips its scope block by these names.
# Nothing else may key on these.
CURATED_DIRNAME = ".claude-bx-selflearning"
CURATED_INDEX = "index.md"                    # named `index.md` (not `memory.md`) so it is never
                                              # confused with Claude Code's native `MEMORY.md` tier


def claude_memory_dir(proj: _StrPath) -> Path:
    """The project-local curated memory dir: `<proj>/.claude-bx-selflearning`.
    Holds `index.md` (the @imported index), `facts/<slug>.md` (lazy bodies), `state/`, `.archive/`."""
    return Path(proj) / CURATED_DIRNAME


def claude_md_path(proj: _StrPath) -> Path:
    """The project's TRACKED CLAUDE.md. Carries the `@import` of `index.md` only when `track_private`
    is on (memory committed with the repo); otherwise the import lives in `claude_local_md_path`."""
    return Path(proj) / "CLAUDE.md"


def claude_local_md_path(proj: _StrPath) -> Path:
    """The project's UNTRACKED `CLAUDE.local.md` - the DEFAULT home for the `@import` of `index.md`
    (track_private off). Symmetric with the gitignored store: the memory wiring never touches tracked
    git, a fresh clone has neither the wiring nor the store, and no commit is needed to set up memory."""
    return Path(proj) / "CLAUDE.local.md"


def _git_in(proj: _StrPath, *args: str) -> tuple[int, str] | None:
    """One git call from `proj`: (returncode, stdout as a path string), or None when git could not
    run. git prints paths as raw filename bytes; text mode decoded them with the locale's codec
    (ASCII under LANG=C) and raised UnicodeDecodeError, which no OSError guard catches, so the
    output goes through os.fsdecode, the exact inverse of how this interpreter opens a path."""
    import subprocess
    try:
        r = subprocess.run(["git", "-C", str(proj), *args], capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.returncode, os.fsdecode(r.stdout).strip()


_EXCLUDE_HEADER = "# bitranox curated memory (local; CLAUDE.local.md @imports it)"

# (absolute dir, pattern) pairs this process already saw git ignore. Every add re-checks its
# level's two private files, and each check spawns git twice under the level lock: about 250 ms
# per add on Windows, which is most of a bulk add loop's hold time. A pattern does not stop being
# ignored during one short-lived hook or CLI process, and a long-lived one re-checks after a
# restart; `track_private` is still read on every call.
_IGNORED_HERE: set[tuple[str, str]] = set()

# Absolute dirs this process already saw git place outside any repo: nothing to ignore there.
# Not remembered, a level outside git spawned `git rev-parse` on every add. Same lifetime as
# `_IGNORED_HERE`; a dir git could not be asked about (git missing, a timeout) is not remembered.
_OUTSIDE_GIT_HERE: set[str] = set()


def ensure_gitignored(proj: _StrPath, *patterns: str) -> bool:
    """Best-effort: on a git repo, make sure git ignores each `pattern`. Honors `track_private`
    (skip if set - the user wants memory committed). Used by per-turn capture so a fresh untracked
    `CLAUDE.local.md` + curated store are never accidentally staged into a public repo.

    git is ASKED whether each pattern is already ignored (`check-ignore --no-index`, so a tracked
    file still counts by its rules), and one that is - from the exclude file, a nested
    `.gitignore`, a global excludes file - is left alone. Reading only the root `.gitignore` for a
    literal line re-added it on every capture in a repo that kept it in `.git/info/exclude`.

    What is missing goes into the repo's own exclude file (`git rev-parse --git-path
    info/exclude`, which a linked worktree shares with its main checkout), never the TRACKED
    `.gitignore`: the files are per-clone, and a tracked ignore line is what a public repo would
    then publish - the memory wiring never touches tracked git.

    Never raises (a hook reaches it through the memory engine). Returns True when nothing is left
    to do - the patterns are ignored, `track_private` is set, or `proj` is not in a git repo - and
    False when it could not make sure: git did not answer, or the exclude file could not be read
    or written. A caller that goes on to rely on the files being ignored reads that, rather than
    assuming a write it cannot see.

    The file is decoded with surrogateescape and written back the same way, so a byte in another
    encoding survives the rewrite instead of raising (UnicodeDecodeError is not an OSError, and
    escaped every fail-open handler here); the file's own line ending is kept.

    A pattern found ignored (or written) is remembered for the rest of the process
    (`_IGNORED_HERE`), so a loop of adds asks git once per level and pattern, not on every add;
    so is a dir git answered is in no repo (`_OUTSIDE_GIT_HERE`)."""
    if load_config().get("track_private"):
        return True
    here = str(Path(proj).absolute())
    if here in _OUTSIDE_GIT_HERE:
        return True
    patterns = tuple(p for p in patterns if (here, p) not in _IGNORED_HERE)
    if not patterns:
        return True
    top = _git_in(proj, "rev-parse", "--show-toplevel")
    if top is None:
        return False
    if not top[1]:
        _OUTSIDE_GIT_HERE.add(here)
        return True
    add: list[str] = []
    for pattern in patterns:
        asked = _git_in(proj, "check-ignore", "-q", "--no-index", pattern)
        if asked is None or asked[0] not in (0, 1):
            return False
        if asked[0] == 1:
            add.append(pattern)
        else:
            _IGNORED_HERE.add((here, pattern))
    if not add:
        return True
    where = _git_in(proj, "rev-parse", "--git-path", "info/exclude")
    if where is None or where[0] != 0 or not where[1]:
        return False
    try:
        exclude = Path(where[1]) if os.path.isabs(where[1]) else Path(proj) / where[1]
        cur = exclude.read_bytes().decode("utf-8", "surrogateescape") if os.path.lexists(exclude) else ""
        nl = "\r\n" if "\r\n" in cur else "\n"
        # The header names the section once; a later call that adds the other private file would
        # otherwise stack a second identical header above its single line.
        has_header = _EXCLUDE_HEADER in (ln.strip() for ln in cur.splitlines())
        text = ((cur.rstrip("\r\n") + nl if cur.strip() else "")
                + ("" if has_header else _EXCLUDE_HEADER + nl)
                + nl.join(add) + nl)
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_bytes(text.encode("utf-8", "surrogateescape"))
    except OSError:
        return False
    _IGNORED_HERE.update((here, pattern) for pattern in add)
    return True


def curated_index(proj: _StrPath) -> Path:
    """The always-@imported curated index file (`index.md`) for a project."""
    return claude_memory_dir(proj) / CURATED_INDEX


def curated_state_dir(proj: _StrPath | None) -> Path:
    """Tree-shared state dir in the LIVE store: `<anchor>/.claude-memory/state`. Per-project files
    inside it encode the project in their filename (see migrate_memory's receipts)."""
    return global_rules_dir(proj) / "state"


# ---- cross-platform advisory lock for memory read-modify-write --------------------------------
# The write engine, dream, and migration all read-modify-write `index.md`/`facts/`; two sessions (or
# the migration fan-out) on a shared/NFS checkout can lost-update. An atomic O_EXCL lockfile is used
# (NOT fcntl/msvcrt) so this module imports cleanly on EVERY OS - a top-level `import fcntl` would
# ImportError on Windows and kill every hook. On contention past `timeout` we raise so the caller can
# skip-and-report the WHOLE target (never a partial write).

LOCK_STALE_S = 120.0

# A waiter's place in the queue (see `memory_lock`): one `<lock>.q<ns>-<pid>-<thread>` file each,
# its mtime refreshed on every poll. A place whose waiter has not polled for this long (it is
# descheduled, or it crashed) stops holding up the line; one older than LOCK_STALE_S is removed.
_QUEUE_PLACE_FRESH_S = 2.0

# How often the waiter at the head of the queue tries the lock, when its own `poll` is longer: a
# released lock sits idle until the head polls, so this bounds the gap every hand-off costs; the
# waiters behind it keep their own `poll`.
_HEAD_POLL_S = 0.005

# How often a waiter looks at the lock file's age for a crashed holder. Each look is a stat(), and
# on Windows a stat() holds a handle: one that lands as the holder deletes the lock keeps the name
# delete-pending, and the next O_EXCL create of it is refused. At the head's 5 ms poll that was a
# stat every try; a lock is stale only after LOCK_STALE_S, so once a second loses nothing.
_STALE_CHECK_S = 1.0

# Windows reports "another handle has this name open" as PermissionError, not as a distinct error.
# A lock file the previous holder just deleted stays delete-pending while any handle (a virus
# scanner, a waiter's stat()) is still open on it, and a new O_EXCL create of that name fails with
# ACCESS_DENIED instead of EEXIST; os.replace onto a file a reader holds open fails the same way.
# Both clear within milliseconds, so on Windows they are contention to wait out. On POSIX a
# PermissionError is a real permission problem and must surface at once.
_WINDOWS = os.name == "nt"


def is_transient_sharing_error(exc: BaseException, windows: bool = _WINDOWS) -> bool:
    """True when `exc` is Windows saying another open handle holds the name, which clears on its
    own; False on POSIX, where the same exception is a lasting permission problem."""
    return bool(windows) and isinstance(exc, PermissionError)


def retry_while_shared[*Ts, T](op: Callable[[*Ts], T], *args: *Ts, timeout: float = 1.0,
                               poll: float = 0.01, windows: bool = _WINDOWS) -> T:
    """Return `op(*args)`, retrying while Windows reports the file held by another handle.

    Re-raises the PermissionError once `timeout` passes, and at once on POSIX or for any other
    OSError. Use it for the single call that must not be dropped over a momentary sharing clash:
    the `os.replace` that publishes a write, the unlink that releases a lock.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            return op(*args)
        except PermissionError as exc:
            if not is_transient_sharing_error(exc, windows) or time.monotonic() >= deadline:
                raise
        time.sleep(poll)


def _reclaim_stale_lock(lock: Path, clock: Callable[[], float]) -> bool:
    """Delete a lock whose holder crashed; True when it was stale and is now gone."""
    try:
        if clock() - lock.stat().st_mtime > LOCK_STALE_S:
            lock.unlink()
            return True
    except OSError:
        pass
    return False


def _queue_places(lock: Path) -> list[tuple[str, float]]:
    """(name, mtime) of every queue place of `lock`, oldest place first (the name orders them).
    A place older than LOCK_STALE_S is a crashed waiter's, and is removed instead of listed."""
    prefix = lock.name + ".q"
    places: list[tuple[str, float]] = []
    try:
        entries = list(os.scandir(lock.parent))
    except OSError:
        return []
    for entry in entries:
        if not entry.name.startswith(prefix):
            continue
        try:
            mtime = entry.stat().st_mtime
        except OSError:
            continue
        if time.time() - mtime > LOCK_STALE_S:
            with contextlib.suppress(OSError):
                os.unlink(entry.path)
            continue
        places.append((entry.name, mtime))
    return sorted(places)


def _my_turn(lock: Path, place: Path | None) -> bool:
    """True when no waiter queued before `place` (any waiter at all, for a caller with no place)
    has polled within _QUEUE_PLACE_FRESH_S."""
    mine = place.name if place is not None else None
    return not any((mine is None or name < mine) and time.time() - mtime <= _QUEUE_PLACE_FRESH_S
                   for name, mtime in _queue_places(lock))


def _take_place(lock: Path) -> Path | None:
    """Join `lock`'s queue: a new place file named after the current time, so it sorts behind
    every place taken before it. None when the dir refuses it: the waiter then polls unqueued."""
    place = lock.with_name("%s.q%020d-%d-%d" % (lock.name, time.time_ns(), os.getpid(),
                                                threading.get_ident()))
    try:
        os.close(os.open(str(place), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    except OSError:
        return None
    return place


def _keep_place(lock: Path, place: Path | None) -> Path | None:
    """Refresh `place`'s mtime so it keeps its turn; a place removed meanwhile (taken for a
    crashed waiter's after a long stall) is taken again, at the back."""
    if place is None:
        return _take_place(lock)
    try:
        os.utime(place)
    except FileNotFoundError:
        return _take_place(lock)
    except OSError:
        pass
    return place


def _leave_queue(place: Path | None) -> None:
    if place is not None:
        with contextlib.suppress(OSError):
            retry_while_shared(place.unlink)


@contextlib.contextmanager
def memory_lock(target_path: _StrPath, timeout: float = 5.0, poll: float = 0.05,
                now: Callable[[], float] | None = None) -> Generator[None]:
    """Advisory exclusive lock around a memory read-modify-write, via an atomic `<target>.lock`
    O_EXCL create (cross-platform, no fcntl/msvcrt). Raises TimeoutError on contention past `timeout`;
    reclaims a lock older than `LOCK_STALE_S` (holder crashed). `now` injectable for tests.

    On Windows a create refused with PermissionError is contention too (see `_WINDOWS`): a waiter
    that arrives while the previous holder's lock is still being deleted must wait, not abandon
    its write - every caller skips its write on any error this raises.

    Waiters are served in arrival order. A caller refused once takes a place in the lock's queue
    (`<target>.lock.q...`, refreshed every poll, removed when it gets the lock or gives up), and
    nobody tries the lock while a place taken earlier is still live - a caller arriving with no
    place included. Every queued waiter polls every _HEAD_POLL_S, so the head notices a hand-off,
    and the next in line its turn, within milliseconds, not a whole `poll`; a waiter the dir
    refused a place keeps its own `poll`. Without it a holder that took the lock again the moment it let go left a
    50 ms poller a gap of microseconds: the waiter timed out behind a writer that was making
    progress all along (thousands of holds in a row, measured), and every caller skips its write
    on that TimeoutError.

    Decisions:
        - Chosen: a FIFO queue of place files over a short backoff. Why: a real writer holds this
          rhythm - an in-process loop of `upsert_entry` at one level (reconcile's repair, the
          migration, a re-home) on one loaded CPU kept a single-add waiter out for up to 4.5 s of
          its 5 s budget, and a holder re-taking at once kept it out for 1342 holds; a backoff
          only changes the phase it misses. A place goes quiet after _QUEUE_PLACE_FRESH_S
          without a poll, so a crashed or stalled waiter costs the line seconds, never the lock.
          Evidence: measured: the starvation test in tests/test_self_improve_signals.py (1342
          holds before, at most 3 after). Reopen if: the lock moves to an OS primitive that
          queues its waiters itself.
          Pinned by: tests/test_self_improve_signals.py::test_a_waiter_is_let_in_by_a_holder_that_retakes_the_lock_at_once
        - Kept the queue after removing git from the level lock (ensure_level no longer runs
          ensure_gitignored under it, and caches its answer per process). Why: that shortened each
          add, measured 5.4 ms to 2.6 ms per add on Linux, and argued from a Windows
          profile (2.47 s of 2.97 s for 10 adds in git) to about 250 ms to 50 ms there; a
          shorter hold does not stop a holder re-taking the lock at once, which is what starved
          the waiter. Evidence: argued from the starvation test, which re-takes with no work at
          all. Reopen if: no in-process caller loops over adds at one level any more.
        - Chosen: look for a stale lock at most once per _STALE_CHECK_S. Why: on Windows each
          look is a handle on the lock file, and one open as the holder deletes it refuses the
          next create (seen on the Windows dev box, counted as contention); 120 s staleness needs
          no 5 ms look. Evidence: argued; the count is pinned. Reopen if: LOCK_STALE_S drops to
          seconds.
          Pinned by: tests/test_self_improve_signals.py::test_a_waiter_looks_for_a_stale_lock_at_most_once_a_second"""
    clock = time.time if now is None else now
    lock = Path(str(target_path) + ".lock")
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    deadline = clock() + timeout
    next_stale_check = clock()
    fd: int | None = None
    place: Path | None = None
    try:
        while fd is None:
            turn = _my_turn(lock, place)
            if turn:
                try:
                    fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    break
                except FileExistsError:
                    if clock() >= next_stale_check:
                        next_stale_check = clock() + _STALE_CHECK_S
                        if _reclaim_stale_lock(lock, clock):
                            continue
                except PermissionError as exc:
                    if not is_transient_sharing_error(exc):
                        raise
            if clock() >= deadline:
                raise TimeoutError("memory_lock: contention on %s" % lock)
            place = _keep_place(lock, place)
            time.sleep(min(poll, _HEAD_POLL_S) if turn or place is not None else poll)
    finally:
        _leave_queue(place)
    try:
        yield
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        # A release that fails leaves the lock in place until it goes stale, and every other
        # writer times out behind it in the meantime - so a sharing clash here is waited out too.
        try:
            retry_while_shared(lock.unlink)
        except OSError:
            pass


def last_dream_file(proj: _StrPath | None) -> Path:
    """Marker holding the unix timestamp of the last completed dream for this project."""
    return claude_paths.audit_dir() / (proj_key(proj) + ".dream")


def dream_mode(proj: _StrPath | None = None) -> object:
    """Dream mode (single source of truth = the machine-local config; see load_config):
      off     -> no dream nudges; a manual dream (every skill of the family, the cross-tree ones
                 included) consolidates private memory only: no CLAUDE.md edit, no skill change
      auto    -> dream applies CLAUDE.md edits and ships skill changes WITHOUT per-change prompts
      propose -> (default) dream applies CLAUDE.md edits too (backed up, reported per file, and
                 gated by the ancestor-reachability invariant) and routes skill changes to a self-PR
    Reads `~/.claude/.bitranox-memory.json`; without it, the recommended default applies.
    """
    return load_config().get("dream_mode", "propose")


def _newest_mtime(d: Path) -> float:
    newest = 0.0
    try:
        for p in d.glob("*.md"):
            try:
                newest = max(newest, p.stat().st_mtime)
            except OSError:
                continue
    except OSError:
        return 0.0
    return newest


# ---- real-fact accounting across BOTH tiers (native raw + curated) ------------------------------
# The dream cadence + new-project seeding must react to REAL facts, not file mtimes (gap-fill creates
# an empty scope-only `index.md`, and mtimes churn) and must see BOTH the native raw tier and the
# curated `.claude-bx-selflearning/` tier. `store_signature` is a content hash over the facts in both
# tiers, scope-block EXCLUDED - it changes only when a fact is added/edited/removed, so it is stable
# under gap-fill and non-content writes (and self_improve_signals does not import the memory engine,
# to avoid a cycle - it reads the curated store with a light, grammar-free scan).

def strip_scope(text: str | None) -> str:
    text = text or ""
    b = text.find(SCOPE_MARK_BEGIN)
    if b < 0:
        return text
    e = text.find(SCOPE_MARK_END, b)
    if e < 0:
        return text
    return text[:b] + text[e + len(SCOPE_MARK_END):]


def _curated_fact_parts(proj: _StrPath) -> list[str]:
    """Signature parts for the curated tier: the fact POINTER lines (`- [Title](uuid:..) - hook ...`)
    from this level's `CLAUDE.local.md` pointer block (scope descriptor excluded). Empty when the level
    holds no real facts (a scope-only block contributes nothing). A pointer line's title + hook + slug
    change whenever a fact is added, edited, or removed, so this is a stable fact fingerprint without
    reading every central body."""
    parts: list[str] = []
    try:
        text = claude_local_md_path(proj).read_text(encoding="utf-8")
        region = "\n".join(ln for ln in text.splitlines() if ln.startswith("- ["))
        if region.strip():
            parts.append(region)
    except OSError:
        pass
    return parts


def _native_fact_parts(proj: str) -> list[str]:
    """Signature parts for the native raw tier: each topic `*.md` (excluding the MEMORY.md index)."""
    parts: list[str] = []
    try:
        for p in sorted(memory_dir(proj).glob("*.md")):
            if p.name == "MEMORY.md":
                continue
            try:
                parts.append(p.read_text(encoding="utf-8"))
            except OSError:
                continue
    except OSError:
        pass
    return parts


def store_signature(proj: str) -> str:
    """Content hash over the REAL facts in BOTH tiers (scope block excluded). '' when there are none.
    Stable under gap-fill / mtime churn; changes only when a fact is added, edited, or removed."""
    parts = sorted(_native_fact_parts(proj) + _curated_fact_parts(proj))
    if not parts:
        return ""
    return hashlib.sha1("\x00".join(parts).encode("utf-8", "replace")).hexdigest()


def _has_native_fact(proj: str) -> bool:
    """True at the first topic `*.md` (not the MEMORY.md index) that can be opened.

    Opened, never read: a fact counts as soon as it exists readably, and reading every body of a
    large native store only to test it for emptiness was the whole cost of this question. Same set
    as `_native_fact_parts`, so an unreadable entry still does not count."""
    try:
        for p in memory_dir(proj).glob("*.md"):
            if p.name == "MEMORY.md":
                continue
            try:
                with p.open("rb"):
                    return True
            except OSError:
                continue
    except OSError:
        pass
    return False


def has_any_facts(proj: str) -> bool:
    """True if the project holds at least one real fact in either tier (native or curated)."""
    return _has_native_fact(proj) or bool(_curated_fact_parts(proj))


def _read_dream_record(proj: _StrPath | None) -> tuple[float, str] | None:
    """(last_ts, last_sig) from the .dream marker, or None. New format = JSON {ts, sig}; a legacy
    bare-float timestamp yields (ts, '') so the first post-upgrade check re-dreams once."""
    try:
        raw = last_dream_file(proj).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    try:
        d = json.loads(raw)
        return float(d["ts"]), str(d.get("sig", ""))
    except (ValueError, KeyError, TypeError):
        try:
            return float(raw), ""
        except ValueError:
            return None


def dream_due(proj: str, threshold_s: float = _DREAM_THRESHOLD_S, now: float | None = None) -> bool:
    """True if a memory consolidation is due: mode not off, the fact SIGNATURE changed since the last
    dream (real facts added/edited/removed - not mtime churn, not a gap-fill scope-only write), and
    the last dream is older than the threshold. No facts or mode off -> not due."""
    if dream_mode(proj) == "off":
        return False
    sig_now = store_signature(proj)
    if not sig_now:
        return False  # no facts to consolidate
    now = time.time() if now is None else now
    rec = _read_dream_record(proj)
    if rec is None:
        return True  # never dreamed but facts exist -> due
    last_ts, last_sig = rec
    return sig_now != last_sig and (now - last_ts) > threshold_s


def mark_dream_done(proj: str, now: float | None = None) -> bool:
    """Record that a dream just completed: store the current timestamp AND fact signature, so the
    nudge stays silent until a real fact changes (not merely a file mtime). Also discharges an owed
    post-compaction nap - running the dream IS what the marker was demanding."""
    f = last_dream_file(proj)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"ts": time.time() if now is None else now,
                                 "sig": store_signature(proj)}), encoding="utf-8")
        clear_nap_owed(proj)
        return True
    except OSError:
        return False


# ---- contribution queue: make the intent-to-ship outlive the session ---------------------------
# A learning that warrants a SKILL or HOOK change reaches the marketplace only if the model happens
# to author the self-PR before the session ends - nothing recorded the INTENT, so it died with the
# context while the private fact survived. This is that missing state: a durable per-project TODO.
# Unlike the audit (a review note, consumed once at SessionStart), a pending contribution is NOT
# consumed by being surfaced - it stands until it actually ships and something drains it.

# Names its own scope on purpose: this prefix is honored ONLY by contrib_file, while ~15 other
# per-project state files derive their name from proj_key(). A generic `key:` would read like a
# facility every state function understands, and passing it to one that does not would silently
# resolve it as a literal directory and write to the wrong file. `queue_key:` cannot be misread.
QUEUE_KEY_PREFIX = "queue_key:"
_QUEUE_KEY_RE = re.compile(r"[0-9a-f]{16}")   # exactly what proj_key emits: sha1 hex, truncated

MEMORY_WRITES_ENV = "BITRANOX_MEMORY_WRITES"
MEMORY_WRITES_OFF_LINE = (
    "memory writes are off for this session (BITRANOX_MEMORY_WRITES=off): nothing was recorded. "
    "A harness sets this per run; the lesson belongs in that run's report, not the shared store.")


class MemoryWritesOff(RuntimeError):
    """A memory write path was reached while BITRANOX_MEMORY_WRITES=off.

    Raised at the TOP of every write path (engine verbs, the mod tools, the contribution queue,
    factedit apply) so nothing is staged before the refusal; callers turn it into one line and the
    plugin-wide "could not run" exit (2), or the mod tools' error envelope.
    """


def memory_writes_off(environ: Mapping[str, str] | None = None) -> bool:
    """True when the process runs with BITRANOX_MEMORY_WRITES=off (case-insensitive, trimmed).

    One spelling only: "0", "false" or a typo leave writes ON, because a switch that fails closed
    on a typo would silently disable the store for a normal session.
    """
    env = os.environ if environ is None else environ
    return (env.get(MEMORY_WRITES_ENV) or "").strip().lower() == "off"


def refuse_if_memory_writes_off() -> None:
    """Raise MemoryWritesOff when the switch is set; the first statement of every write path."""
    if memory_writes_off():
        raise MemoryWritesOff(MEMORY_WRITES_OFF_LINE)


def contrib_file(proj: _StrPath | None) -> Path:
    """Queue of pending upstream contributions (skill/hook changes a learning warrants).

    `proj` may also be the pseudo-path `queue_key:<hash>`, naming a queue by its own file key. The
    key is one-way (sha1 of the path), so a queue whose project directory was deleted or renamed is
    otherwise unreachable by every verb - it cannot be listed, shipped or dropped, and the operator
    cannot even see that it exists. `contrib_queue.py queues` prints these keys. The prefix is
    queue-scoped by NAME because only the queue and its tombstones (`rejected_file`) honor it."""
    return audit_dir() / (_queue_file_key(proj) + ".contrib.jsonl")


def _main_root_from_gitfile(repo: Path, gitfile: Path) -> Path:
    """The main checkout a linked worktree's `.git` FILE points at; `repo` itself for anything
    else that uses a gitfile (a submodule is a repository of its own)."""
    text = gitfile.read_text(encoding="utf-8", errors="replace").strip()
    if not text.startswith("gitdir:"):
        return repo
    gitdir = (repo / text[len("gitdir:"):].strip()).resolve()
    if gitdir.parent.name != "worktrees":
        return repo
    common = gitdir.parent.parent
    return common.parent if common.name == ".git" else common


def queue_home(proj: _StrPath | None) -> _StrPath | None:
    """The directory whose contribution queue `proj` belongs to: the repo's MAIN checkout.

    An entry is about the repo, not about where the session happened to stand, so one added from
    a linked worktree or a subdirectory must land in the queue the repo's dream reads. Keyed on
    the raw cwd, a worktree's entries sat under a key nothing looked at and outlived the
    worktree. Read from the `.git` entry with no git process: this runs inside hooks. A path
    outside any repository is its own home, so its key is the one it always had.
    """
    try:
        start = Path(os.path.abspath(os.fspath(proj) if proj else os.getcwd()))
    except (TypeError, ValueError):
        return proj
    for directory in (start, *start.parents):
        # Only a marker git itself accepts: an empty `.git` directory left in /tmp otherwise made
        # every project under it share the queue of /tmp.
        if not shell_text.is_work_tree_root(str(directory)):
            continue
        dotgit = directory / ".git"
        try:
            if dotgit.is_file():
                return str(_main_root_from_gitfile(directory, dotgit))
        except OSError:
            return str(start)
        return str(directory)
    return str(start)


def _queue_file_key(proj: _StrPath | None) -> str:
    """The file key of `proj`'s queue AND its tombstones: a `queue_key:` pseudo-path names it
    directly, anything else is hashed. One resolver for both files, because a tombstone written
    under a different key than its queue does not block the re-queue it exists to block."""
    if isinstance(proj, str) and proj.startswith(QUEUE_KEY_PREFIX):
        key = proj[len(QUEUE_KEY_PREFIX):]
        # REFUSED, not flattened, unlike a session id: this key is `proj_key` output and nothing
        # else, so anything that is not 16 hex is a typo or an attempt to steer the path. Silently
        # repairing it would address a DIFFERENT queue and every verb would report that queue's
        # emptiness in the same words a shipped-out queue produces.
        if not _QUEUE_KEY_RE.fullmatch(key):
            raise ValueError(
                "not a queue key: %r - expected the 16 hex chars `contrib_queue.py queues` prints" % key)
        return key
    return proj_key(queue_home(proj))


def _read_jsonl_records(path: Path) -> list[JsonRecord]:
    """The dict records of a JSONL file that carry a `what`, in order. Raises OSError (including
    FileNotFoundError) when the file cannot be read; malformed lines are skipped.

    Decoded leniently: one byte a hand edit left in another encoding used to fail the WHOLE read,
    so the queue read as empty and the next add rewrote it with only the new entry. utf-8-sig
    drops a BOM that would otherwise make the first line unparseable, and the split is on "\\n"
    only - splitlines() also breaks on U+2028 and \\f, which can sit inside a JSON string."""
    out: list[JsonRecord] = []
    for ln in path.read_text(encoding="utf-8-sig", errors="replace").split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except ValueError:
            continue
        if _is_record(rec) and rec.get("what"):
            out.append(rec)
    return out


def _load_queue(f: Path) -> list[JsonRecord]:
    """The queue at `f` for a read-modify-write: [] only when the file does not exist. Any other
    read failure raises, because answering [] there makes the writer replace the whole queue."""
    try:
        return _read_jsonl_records(f)
    except FileNotFoundError:
        return []


def read_contributions(proj: _StrPath | None) -> list[JsonRecord]:
    """The pending contributions for `proj`, oldest first. Never consumes.

    [] only when there is no queue: the file is absent, or `proj` is a malformed queue key (which
    names no file). Raises OSError when the queue file exists but cannot be read - an unreadable
    queue answered [] made `list` print "no pending upstream contributions" and `queues` count it
    as nothing open, the exact words an emptied queue produces. A hook that must never wedge
    catches the error itself."""
    try:
        f = contrib_file(proj)
    except ValueError:                # contrib_file refusing a malformed queue key
        return []
    return _load_queue(f)


def _contribution_key(rec: Mapping[str, object]) -> tuple[str, str]:
    """The identity of a contribution intent: (what, target). The queue dedups on it, a closed
    one blocks a re-queue by it, and the closed set holds one tombstone per key."""
    return str(rec.get("what")), str(rec.get("target") or "")


def add_contribution(proj: _StrPath | None, record: Mapping[str, object], max_items: int = 100,
                     strict: bool = False) -> bool:
    """Queue one pending contribution: {'what' (required), 'target', 'why', 'source'}.

    Deduped on (what, target) - re-noticing the same gap is not a second TODO. Stamped with `ts`.
    The read-modify-write runs under `memory_lock` on the queue file: unguarded, a concurrent
    close (drain) or add racing the same file loses whichever write lands second.

    Returns True when queued, False when not (a duplicate, a closed intent, no `what`). Best-effort
    by default: a store error is also False and never raises. `strict=True` raises that OSError
    instead, so an operator CLI does not report a failed write as "already queued".

    One exception to best-effort, in either mode: under BITRANOX_MEMORY_WRITES=off this raises
    MemoryWritesOff before the queue is read, because a False would read as "already queued" and
    hide that the switch refused the write."""
    refuse_if_memory_writes_off()
    if not isinstance(record, dict) or not record.get("what"):
        return False
    try:
        f = contrib_file(proj)
        with memory_lock(f):
            cur = _load_queue(f)
            key = _contribution_key(record)
            if any(_contribution_key(r) == key for r in cur):
                return False
            # A CLOSED intent stays closed, whichever outcome closed it. Without this the dedup key
            # only spans the LIVE queue, so a later dream that re-notices a disproven gap silently
            # re-queues it and every future dream re-evaluates it again - and a DELIVERED one comes
            # back as a TODO for work already shipped. Read the closed set, never just rejections,
            # and through the RAISING loader: a closed set that exists but cannot be read must
            # refuse the add, not let every closed intent back in.
            if any(_contribution_key(r) == key for r in _load_closed(proj)):
                return False
            rec = dict(record)
            rec.setdefault("ts", time.time())
            # Stamp the project PATH: the filename is a one-way hash, so without this the only way
            # to answer "which projects have pending contributions?" is to brute-force sha1 over
            # the filesystem (measured: a walk of 705,896 directories), and a queue whose cwd was
            # deleted resolves to nothing at all.
            if (not rec.get("proj")
                    and not (isinstance(proj, str) and proj.startswith(QUEUE_KEY_PREFIX))):
                try:
                    home = queue_home(proj)
                    if home is not None:        # abspath(None) raised the TypeError skipped here
                        rec["proj"] = os.path.abspath(home)
                except (TypeError, ValueError):
                    pass
            cur.append(rec)
            if len(cur) > max_items:
                cur = cur[-max_items:]
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("\n".join(json.dumps(r, sort_keys=True) for r in cur) + "\n",
                         encoding="utf-8")
        return True
    except OSError:                   # also covers memory_lock's TimeoutError
        if strict:
            raise
        return False
    except ValueError:                # contrib_file refusing a malformed queue key
        return False


def drain_contributions(proj: _StrPath | None, note: str = "", strict: bool = False,
                        max_items: int = 200) -> list[JsonRecord]:
    """Close the WHOLE queue as SHIPPED - ONLY after the contributions actually shipped. Returns
    the drained records ([] when the queue was empty or absent).

    Every entry is tombstoned exactly like `ship_contribution` does for one: a drain that only
    deleted the file let the next dream re-queue each drained intent as a new TODO, and `shipped`
    never listed them. The tombstones are written BEFORE the queue is removed, so a failure between
    the two leaves entries queued-and-closed (a retry finishes it), never gone with no record.

    Locked like `add_contribution`, so a drain can never remove a record an in-flight add has not
    written yet, nor race its read-modify-write. Best-effort by default; `strict=True` raises the
    OSError of a failed close so an operator CLI does not report a drain that did not happen."""
    try:
        f = contrib_file(proj)
        with memory_lock(f):
            cur = _load_queue(f)
            if cur:
                _append_tombstones(proj, [_tombstone(r, SHIPPED, note) for r in cur], max_items)
            f.unlink(missing_ok=True)
        return cur
    except OSError:                   # also covers the lock timeout
        if strict:
            raise
        return []
    except ValueError:                # contrib_file refusing a malformed queue key
        return []


# ---- closed: an intent leaves the queue AND stays gone, by one of two OUTCOMES -----------------
# An intent leaves the queue either because it SHIPPED or because it was disproven/superseded, and
# both must stay gone: the add-dedup spans only the live queue, so a later dream that re-notices the
# same gap re-queues it and it gets re-evaluated forever. The tombstone is what makes leaving stick.
#
# Both outcomes live in ONE file with an `outcome` field rather than two files, because the re-queue
# block reads the closed set - a second file is one more read for that check to forget, and a
# forgotten one silently resurrects a delivered contribution. Reporting filters by outcome instead,
# so a shipped contribution is never described to the reader as rejected.

SHIPPED: Final = "shipped"
REJECTED: Final = "rejected"
# How an intent left the queue: the two values a tombstone's `outcome` field takes.
type Outcome = Literal["shipped", "rejected"]


def rejected_file(proj: _StrPath | None) -> Path:
    """Tombstones for contributions that have left the queue, either outcome (never re-queued).
    Keyed exactly like `contrib_file`, `queue_key:` included.

    The name says rejected but the file holds shipped records too; `outcome` tells them apart.
    It is not renamed because every installed plugin version reads this path: an open session
    on an older version would find no closed set and let a dream re-queue every closed entry."""
    return audit_dir() / (_queue_file_key(proj) + ".contrib-rejected.jsonl")


def read_closed(proj: _StrPath | None) -> list[JsonRecord]:
    """Every contribution that has left the queue, oldest first, both outcomes. [] when none.

    This is the set the re-queue block must consult: a delivered intent and a disproven one are
    equally not-a-TODO. Records written before the outcome field existed were all drops, so a
    missing `outcome` reads as rejected.

    [] only when nothing was ever closed (absent file, or a malformed queue key, which names no
    file). Raises OSError when the file exists but cannot be read: answering [] there let a closed
    intent be re-queued and made `shipped` / `rejected` report nothing."""
    try:
        return _load_closed(proj)
    except ValueError:                # a malformed queue key names no file
        return []


def why_not_queued(proj: _StrPath | None, what: str, target: str | None) -> str:
    """Why an add was refused: "shipped earlier", "rejected earlier" or "already queued".

    The add itself already read the closed set through the raising loader, so an unreadable one
    failed it before this runs; a read failure here is a change in between, and says so rather
    than guessing "already queued"."""
    try:
        closed = {(r.get("what"), r.get("target") or ""): r.get("outcome")
                  for r in read_closed(proj)}
    except OSError as exc:
        return "already queued or closed - the closed set could not be read: %s" % exc
    # Keyed by object: the stored outcome is whatever the closed set holds.
    labels: dict[object, str] = {SHIPPED: "shipped earlier", REJECTED: "rejected earlier"}
    return labels.get(closed.get((what, target or "")), "already queued")


def _tombstone(rec: Mapping[str, object], outcome: Outcome, note: str = "") -> JsonRecord:
    """The closed-record form of queue entry `rec` under `outcome`."""
    tomb = dict(rec)
    tomb["outcome"] = outcome
    tomb["note" if outcome == SHIPPED else "reason"] = str(note or "")
    tomb["closed_ts"] = time.time()
    return tomb


def _load_closed(proj: _StrPath | None) -> list[JsonRecord]:
    """`proj`'s closed set: [] only when the file does not exist. Any other read failure raises,
    because an [] there made the next close REPLACE every earlier tombstone with its own - each
    earlier intent then became re-queueable. Raises ValueError for a malformed queue key."""
    try:
        out = _read_jsonl_records(rejected_file(proj))
    except FileNotFoundError:
        return []
    for rec in out:
        rec.setdefault("outcome", REJECTED)
    return out


def _write_closed(proj: _StrPath | None, records: Iterable[Mapping[str, object]]) -> None:
    """Replace `proj`'s closed set with `records`. Raises OSError when it cannot be written."""
    rf = rejected_file(proj)
    rf.parent.mkdir(parents=True, exist_ok=True)
    rf.write_text("\n".join(json.dumps(r, sort_keys=True) for r in records) + "\n",
                  encoding="utf-8")


def _append_tombstones(proj: _StrPath | None, tombs: Sequence[JsonRecord], max_items: int = 200) -> None:
    """Append `tombs` to `proj`'s closed set (capped). Raises OSError when it cannot be written,
    or when the existing set cannot be read (it is never replaced blind).

    One tombstone per intent, keyed on (what, target) like the queue's own dedup: a close retried
    after a partial failure (tombstones written, queue update failed) closes entries that are
    already closed. Appending again duplicated every one, and the duplicates evicted OTHER closed
    intents from the cap, which could then be re-queued. The new tombstone replaces the old one,
    so the latest outcome and note win."""
    keys = {_contribution_key(t) for t in tombs}
    prev = [r for r in _load_closed(proj) if _contribution_key(r) not in keys]
    prev.extend(tombs)
    if len(prev) > max_items:
        prev = prev[-max_items:]
    _write_closed(proj, prev)


def read_rejected(proj: _StrPath | None) -> list[JsonRecord]:
    """The contributions dropped as wrong or stale, oldest first. Excludes what SHIPPED. Raises
    OSError on an unreadable closed set, like `read_closed`."""
    return [r for r in read_closed(proj) if r.get("outcome") != SHIPPED]


def read_shipped(proj: _StrPath | None) -> list[JsonRecord]:
    """The contributions that actually shipped, oldest first. Raises OSError on an unreadable
    closed set, like `read_closed`."""
    return [r for r in read_closed(proj) if r.get("outcome") == SHIPPED]


def resolve_contribution(proj: _StrPath | None, index: int | None = None,
                         match: str | None = None) -> int:
    """The 0-based position of exactly ONE queued contribution, by `index` (1-based) or `match`.

    `match` is a case-insensitive substring of the entry's `what` or `target`, or `<what> -> <target>`
    as the listing prints it, which is the only way to tell apart two entries with one `what`. It
    exists because an INDEX SHIFTS under the previous close: closing two entries by the indices of
    one listing hits the wrong second entry, which silently destroys a contribution that was meant
    to stay queued. Raises IndexError (out of range, no match, or an ambiguous match) rather than
    guessing, and OSError when the queue cannot be read."""
    return _resolve_in(read_contributions(proj), index, match)


def _contribution_matches(record: Mapping[str, object], needle: str) -> bool:
    """Does lowercased `needle` select `record`: a substring of what or target, or `what -> target`."""
    what = str(record.get("what") or "").lower()
    target = str(record.get("target") or "").lower()
    if needle in what or needle in target:
        return True
    head, arrow, tail = needle.partition(" -> ")
    return bool(arrow) and head.strip() in what and tail.strip() in target


def _resolve_in(cur: Sequence[Mapping[str, object]], index: int | None = None,
                match: str | None = None) -> int:
    """`resolve_contribution` over an already-loaded queue `cur` (the close holds the lock and
    must select from the records it will rewrite, not from a second read)."""
    if match:
        needle = str(match).lower()
        hits = [i for i, r in enumerate(cur) if _contribution_matches(r, needle)]
        if not hits:
            raise IndexError("no queued contribution matches %r (queue holds %d)" % (match, len(cur)))
        if len(hits) > 1:
            raise IndexError("%r matches %d queued contributions - narrow it: %s"
                             % (match, len(hits), "; ".join(str(cur[i].get("what"))[:40] for i in hits)))
        return hits[0]
    if not isinstance(index, int) or index < 1 or index > len(cur):
        raise IndexError("no queued contribution at index %r (queue holds %d)" % (index, len(cur)))
    return index - 1


def _close_contribution(proj: _StrPath | None, index: int | None, outcome: Outcome, note: str = "",
                        max_items: int = 200, match: str | None = None) -> JsonRecord:
    """Remove ONE entry from the queue (by `index` or `match`) and tombstone it under `outcome`.

    Raises IndexError on a selector that does not resolve to exactly one entry, so a mistyped or
    shifted selector cannot silently close the wrong intent (or none, while reporting success).

    Raises OSError when the close cannot be RECORDED (TimeoutError, an OSError, on lock
    contention). Unlike the queue's best-effort writers this is an operator verb whose whole
    output is "it will not come back", so a swallowed error made it report a close that never
    happened. The tombstone is written BEFORE the queue is rewritten: a failure between the two
    then leaves the entry both queued and tombstoned (re-queue still blocked, a retry closes it),
    never out of the queue with nothing recording that it left."""
    try:
        f = contrib_file(proj)
    except ValueError as exc:         # a malformed queue key selects nothing: refuse like a bad index
        raise IndexError(str(exc)) from exc
    with memory_lock(f):
        # _load_queue, not read_contributions: an unreadable queue must fail the close as an
        # OSError, not read as empty and be refused as "no queued contribution matches".
        cur = _load_queue(f)
        rec = cur.pop(_resolve_in(cur, index, match))
        _append_tombstones(proj, [_tombstone(rec, outcome, note)], max_items)
        if cur:
            f.write_text("\n".join(json.dumps(r, sort_keys=True) for r in cur) + "\n", encoding="utf-8")
        else:
            f.unlink(missing_ok=True)
    return rec


def drop_contribution(proj: _StrPath | None, index: int | None = None, reason: str = "",
                      max_items: int = 200, match: str | None = None) -> JsonRecord:
    """Close ONE entry (by 1-based `index` or by `match`) as DISPROVEN or stale."""
    return _close_contribution(proj, index, REJECTED, reason, max_items, match)


def ship_contribution(proj: _StrPath | None, index: int | None = None, note: str = "",
                      max_items: int = 200, match: str | None = None) -> JsonRecord:
    """Close ONE entry (by 1-based `index` or by `match`) as DELIVERED. Returns the record.

    Distinct from `drop_contribution` only in the outcome recorded: both leave the queue and both
    block a re-queue, but a delivered contribution reported back as rejected misleads every later
    reader about whether the work was done."""
    return _close_contribution(proj, index, SHIPPED, note, max_items, match)


# ---- claims: a sweeping session marks the entry it is working ----------------------------------
# Two sessions sweeping the same queue had no way to see each other: on 2026-10-30 a peer shipped
# two entries while another session's batch had the same two in progress, and the duplicate work
# ended in a merge conflict. A claim is advisory and expires, so a session that died mid-entry
# blocks nobody for longer than its own estimate; ship and drop ignore it, since whoever lands the
# work is the one to record it.


class ClaimHeld(Exception):
    """Another holder has an unexpired claim on the entry. `.claim` is that claim."""

    def __init__(self, claim: Mapping[str, object]) -> None:
        super().__init__("claimed by %s until %s" % (claim.get("session"), claim.get("until")))
        self.claim = claim


class ClaimState(StrEnum):
    """The state of a claim on a queue entry. The values are the strings listings have always shown,
    so a comparison against a misspelt member fails at import rather than silently never matching."""

    LIVE = "live"
    EXPIRED = "expired"


def claim_state(rec: Mapping[str, object], now: float | None = None) -> ClaimState | None:
    """ClaimState.LIVE or .EXPIRED for a record carrying a claim, None for one without."""
    claim = rec.get("claim") if isinstance(rec, dict) else None
    if not _is_record(claim):
        return None
    until = claim.get("until")
    if not isinstance(until, (int, float)):
        return ClaimState.EXPIRED
    return ClaimState.LIVE if until > (time.time() if now is None else now) else ClaimState.EXPIRED


_SESSION_ID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def claim_holder(holder: object) -> str:
    """A claim's holder for display: a session id cut to the 8 characters its transcript file name
    starts with, any other name as it is."""
    holder = str(holder or "?")
    return holder[:8] if _SESSION_ID_RE.fullmatch(holder) else holder


def claim_label(rec: Mapping[str, object], now: float | None = None) -> str:
    """'[claimed by X, Nm left] ', '[expired claim by X] ' or '' - the prefix a listing gives an
    entry, so every reader of the queue sees the same claim the same way."""
    state = claim_state(rec, now)
    if state is None:                                # also every `rec` that is not a dict
        return ""
    claim = rec.get("claim")
    if not _is_record(claim):                        # never: a state is only set for a dict claim
        return ""
    until = claim.get("until")
    # A LIVE claim always has a numeric `until`; the second test only tells the checker so.
    if state is ClaimState.EXPIRED or not isinstance(until, (int, float)):
        return "[expired claim by %s] " % claim_holder(claim.get("session"))
    left = (until - (time.time() if now is None else now)) / 60
    return "[claimed by %s, %dm left] " % (claim_holder(claim.get("session")), left)


def _rewrite_queue(f: Path, cur: Iterable[Mapping[str, object]]) -> None:
    f.write_text("\n".join(json.dumps(r, sort_keys=True) for r in cur) + "\n", encoding="utf-8")


def claim_contribution(proj: _StrPath | None, match: str, holder: str, hours: float,
                       now: float | None = None) -> JsonRecord:
    """Mark the ONE entry `match` selects as worked on by `holder` for `hours`. Returns the record.

    Raises ClaimHeld when a DIFFERENT holder's claim on it has not expired; the same holder claiming
    again restarts the clock from `now`. Raises IndexError for a selector that does not resolve to
    exactly one entry and OSError when the queue cannot be read or written, like a close."""
    stamp = time.time() if now is None else now
    try:
        f = contrib_file(proj)
    except ValueError as exc:
        raise IndexError(str(exc)) from exc
    with memory_lock(f):
        cur = _load_queue(f)
        rec = cur[_resolve_in(cur, match=match)]
        held = rec.get("claim")
        # claim_state answers LIVE only for a dict claim; _is_record states that for the checker.
        if (claim_state(rec, stamp) is ClaimState.LIVE and _is_record(held)
                and held.get("session") != holder):
            raise ClaimHeld(held)
        rec["claim"] = {"session": str(holder), "cwd": os.getcwd(), "ts": stamp,
                        "until": stamp + float(hours) * 3600}
        _rewrite_queue(f, cur)
    return rec


def release_contribution(proj: _StrPath | None, match: str) -> object:
    """Remove the claim from the ONE entry `match` selects. Returns the removed claim, or None when
    it carried none. Raises like `claim_contribution`, except never ClaimHeld."""
    try:
        f = contrib_file(proj)
    except ValueError as exc:
        raise IndexError(str(exc)) from exc
    with memory_lock(f):
        cur = _load_queue(f)
        rec = cur[_resolve_in(cur, match=match)]
        held = rec.pop("claim", None)
        if held is not None:
            _rewrite_queue(f, cur)
    return held


# ---- orphaned tombstones: closes the pre-7.24.0 queue_key: path wrote under the wrong key -------
# Before `_queue_file_key`, `rejected_file("queue_key:<H>")` hashed the PSEUDO-PATH, made absolute
# under whatever cwd the close ran from. So a ship or drop addressed by queue key removed the entry
# from queue <H> and wrote its tombstone to a file keyed by nothing any reader consults: `shipped`
# never listed it and a later add of the same intent was accepted. Such a file can suppress nothing
# (its key names no real project); it only fails to protect its own queue.
#
# Attribution is by the `proj` stamp add_contribution writes. The stamp landed after proj_key's
# path normalization, so a stamped record sits under a key other than its own project's hash ONLY
# through a pseudo-path close - and one file key is one pseudo-path, so every record in the file,
# stamped or not, left the same queue. A file whose stamps disagree is reported, never moved; a file
# with no stamp at all is indistinguishable from an old correctly-keyed one and is left alone.

_TOMBSTONE_SUFFIX = ".contrib-rejected.jsonl"
_REHOMED_SUFFIX = ".rehomed"


class OrphanTombstone(TypedDict):
    """A closed-set file whose every stamp names ONE other queue: `home`, its key."""
    path: Path
    status: Literal["orphan"]
    home: str
    records: list[JsonRecord]


class AmbiguousTombstone(TypedDict):
    """A closed-set file that is not its own queue's but cannot be moved: its stamps disagree,
    or a queue lives at its key. Reported, never rehomed, so it names no `home`."""
    path: Path
    status: Literal["ambiguous"]
    home: None
    records: list[JsonRecord]


def _classify_tombstone_file(path: Path) -> OrphanTombstone | AmbiguousTombstone | None:
    """The entry for one closed-set file, or None when it is its own queue's ("home": correctly
    keyed or unattributable - leave it)."""
    key = path.name[:-len(_TOMBSTONE_SUFFIX)]
    records = _read_jsonl_records(path)
    homes = {proj_key(r["proj"]) for r in records if r.get("proj")}
    if not homes or homes == {key}:
        return None
    if key in homes or len(homes) > 1 or (audit_dir() / (key + ".contrib.jsonl")).exists():
        return {"path": path, "status": "ambiguous", "home": None, "records": records}
    return {"path": path, "status": "orphan", "home": homes.pop(), "records": records}


def find_orphan_tombstones() -> list[OrphanTombstone | AmbiguousTombstone]:
    """[{path, status, home, records}] for every closed-set file that is NOT its own queue's:
    status "orphan" (with the queue key `home` it belongs to) or "ambiguous" (stamps disagree, or a
    queue lives at its key - reported, never moved). An unreadable file raises OSError."""
    out: list[OrphanTombstone | AmbiguousTombstone] = []
    try:
        paths = sorted(audit_dir().glob("*" + _TOMBSTONE_SUFFIX))
    except OSError:
        return out
    for path in paths:
        found = _classify_tombstone_file(path)
        if found is not None:
            out.append(found)
    return out


def _closed_ts(rec: Mapping[str, object]) -> float:
    """A tombstone's close time for ordering; 0 when absent or not a number."""
    try:
        return _coerce_float(rec.get("closed_ts") or 0)
    except (TypeError, ValueError):
        return 0.0


def _free_rehomed_path(path: Path) -> Path:
    """`<path>.rehomed`, or `.rehomed-<n>` when an earlier repair already used that name."""
    cand = path.with_name(path.name + _REHOMED_SUFFIX)
    n = 1
    while os.path.lexists(cand):
        n += 1
        cand = path.with_name("%s%s-%d" % (path.name, _REHOMED_SUFFIX, n))
    return cand


def rehome_orphan_tombstone(orphan: OrphanTombstone) -> int:
    """Merge one orphan (from `find_orphan_tombstones`) into its queue's closed set, then rename
    the orphan file aside (kept as `<name>.rehomed`, never deleted). Returns the number of records
    that were new to the home set. Raises OSError when either step fails.

    The home set is written FIRST, so a failure before the rename leaves the records in both
    places; a re-run finds the file again and adds nothing twice (records are deduped on
    (what, target), the key the re-queue block reads). No cap: a repair must not push the oldest
    home tombstones out to make room."""
    home = QUEUE_KEY_PREFIX + orphan["home"]
    with memory_lock(contrib_file(home)):
        prev = _load_closed(home)
        have = {(str(r.get("what")), str(r.get("target") or "")) for r in prev}
        new: list[JsonRecord] = []
        for rec in sorted(orphan["records"], key=_closed_ts):
            ident = (str(rec.get("what")), str(rec.get("target") or ""))
            if ident not in have:
                have.add(ident)
                new.append(dict(rec, outcome=rec.get("outcome") or REJECTED))
        if new:
            _write_closed(home, prev + new)
        retry_while_shared(os.replace, str(orphan["path"]), str(_free_rehomed_path(orphan["path"])))
    return len(new)


# ---- nap-owed: make the post-compaction consolidation non-optional ----------------------------
# Compaction clears the model's CONTEXT (the transcript file survives), so the learnings of the
# pre-compaction stretch are only recoverable by a pass that reads from DISK. A hook cannot RUN that
# pass (hooks have no model), so PostCompact records an OBLIGATION here and the Stop gate refuses to
# stop while it is owed - the same proven block mechanism the capture nudge uses. Running the dream
# (mark_dream_done) discharges it.
#
# The marker is keyed by the REPOSITORY the cwd sits in (its main checkout), never the raw cwd. A
# session's cwd drifts with every `cd` - into a subdirectory, into a linked worktree - so a raw key
# put the flag where PostCompact stood, the Stop gate read another key, and `done --kind nap`
# cleared a third (measured 2026-10-31: one session ran `done --kind nap` for three directories in
# a row before the gate let it stop). A directory outside any work tree keeps its own key.

# Git variables that point a git call at some OTHER repository than the one -C names; a session
# launched from a git hook or a worktree push can inherit them.
_GIT_SCOPE_PREFIX = "GIT_"


def git_scoped(cwd: _StrPath, *args: str) -> tuple[int, str] | None:
    """(returncode, stdout) of one git call in `cwd` with inherited GIT_* scoping removed, or None."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(_GIT_SCOPE_PREFIX)}
    try:
        r = subprocess.run(["git", "-C", str(cwd), *args], check=False, capture_output=True,
                           timeout=5, env=env)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.returncode, os.fsdecode(r.stdout).strip()


def main_checkout_root(cwd: _StrPath) -> Path | None:
    """The main checkout's root for the repository `cwd` is in, or None outside a work tree."""
    top = git_scoped(cwd, "rev-parse", "--path-format=absolute", "--show-toplevel",
                     "--git-common-dir")
    if top is None or top[0] != 0:
        return None
    lines = top[1].splitlines()
    if len(lines) != 2:
        return None
    toplevel, common = Path(lines[0]), Path(lines[1])
    # A linked worktree's common dir is the main checkout's `.git`; anything else (a separate git
    # dir, a submodule's modules/ path) has no main checkout to find, so the work tree is used.
    if common.name == ".git" and common.parent.is_dir():
        return common.parent
    return toplevel


@functools.lru_cache(maxsize=64)
def _nap_owner_of(absolute: str) -> str:
    root = main_checkout_root(absolute) if os.path.isdir(absolute) else None
    return str(root) if root else absolute


def nap_owner(proj: _StrPath | None) -> _StrPath | None:
    """The directory an owed nap is keyed by: the main checkout of `proj`'s repository, else
    `proj` itself (normalized). Cached per process: the Stop gate reads the marker several times."""
    try:
        absolute: str = os.path.abspath(os.fspath(proj) if proj else os.getcwd())
    except (TypeError, ValueError):
        return proj
    return _nap_owner_of(absolute)


def _nap_owed_files(proj: _StrPath | None) -> list[Path]:
    """[canonical, legacy raw-cwd] marker paths, deduped. The legacy one was written before the
    marker was keyed by repository; it is read and cleared so an old obligation does not silently
    stop blocking, and never written again."""
    files = [audit_dir() / (proj_key(nap_owner(proj)) + ".nap-owed")]
    legacy = audit_dir() / (proj_key(proj) + ".nap-owed")
    return files if legacy == files[0] else files + [legacy]


def nap_owed_file(proj: _StrPath | None) -> Path:
    """Marker: a compaction happened and the consolidation pass has not run since. The existing
    file when there is one (canonical first), else the canonical path a new marker is written to."""
    files = _nap_owed_files(proj)
    for f in files:
        try:
            if f.is_file():
                return f
        except OSError:
            pass
    return files[0]


def mark_nap_owed(proj: _StrPath | None, session_id: str | None = None,
                  transcript_path: _StrPath | None = None) -> None:
    """Record that a post-compaction nap is owed for `proj`. Best-effort.

    The obligation is keyed per PROJECT but the material it protects is per SESSION, so the
    compacting session's id and transcript path are recorded WITH it. Without them a nap run in a
    later session reviews only its own transcript while clearing the flag, discharging the
    compacted stretch unread - and the block text asserts a compaction that session never had."""
    record: JsonRecord = {"ts": time.time(), "session_id": str(session_id or ""),
                          "transcript_path": str(transcript_path or "")}
    # Where the transcript ended at the compaction: the stretch the nap owes. Recorded so a review
    # past it discharges even the current session's obligation, whatever cwd it ran from.
    try:
        if transcript_path:
            record["offset"] = os.path.getsize(str(transcript_path))
    except OSError:
        pass
    try:
        canonical, *legacy = _nap_owed_files(proj)
        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
        for old in legacy:                          # the new marker supersedes a raw-cwd one
            with contextlib.suppress(OSError):
                old.unlink()
    except OSError:
        pass


def is_nap_owed(proj: _StrPath | None) -> bool:
    """True while a post-compaction nap is owed for `proj`."""
    try:
        return nap_owed_file(proj).is_file()
    except OSError:
        return False


def nap_owed_info(proj: _StrPath | None) -> JsonRecord:
    """{'ts','session_id','transcript_path'} for the owed nap, or {} when none is owed.

    Tolerates a LEGACY marker written before the session was recorded (it carries only `ts`), so an
    obligation from an older plugin version still blocks - it just cannot name its transcript."""
    try:
        d = _decode_json_file(nap_owed_file(proj))
        return d if _is_record(d) else {}
    except (OSError, ValueError):
        return {}


def decline_nap_owed(proj: _StrPath | None, by: str | None, now: float | None = None) -> bool:
    """Record that `by` (normally "user") declined the owed nap; False when none is owed.

    The decline is stored INSIDE the obligation it answers, so the next compaction - the only
    event that brings material this decline did not cover - rewrites the marker through
    `mark_nap_owed` and the block returns by itself. A decline is not a discharge: the marker
    stays, naming the transcript nobody consolidated, until a dream runs. Raises ValueError for an
    empty `by` (a decline nobody gave is the record this exists to prevent) and StateWriteError
    when the write does not land."""
    who = str(by or "").strip()
    if not who:
        raise ValueError("a nap decline needs a who (by)")
    info = nap_owed_info(proj) if is_nap_owed(proj) else None
    if info is None:
        return False
    info["declined"] = {"by": who, "ts": time.time() if now is None else now}
    _write_json_state(nap_owed_file(proj), info)
    return True


def nap_owed_declined(proj: _StrPath | None) -> JsonRecord:
    """{'by', 'ts'} of the decline standing on the owed nap, or {} when none (or nothing owed)."""
    rec = nap_owed_info(proj).get("declined")
    return rec if _is_record(rec) and rec.get("by") else {}


def calling_session_id() -> str:
    """The Claude Code session this process runs under, or "" outside one. The CLI exports it to
    every Bash call, so a script knows whose transcript is its own without asking the cwd."""
    return os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()


def _live_sessions() -> frozenset[str]:
    """The ids of the Claude Code sessions with a live process behind them."""
    return process_liveness.live_session_ids(claude_paths.config_dir() / "sessions").ids


def nap_owed_by_live_peer(proj: _StrPath | None, session_id: str | None) -> bool:
    """True when the owed nap names ANOTHER session that is still running.

    That session's transcript is still growing and its own Stop gate owes the nap, so a second
    session reviewing it can only duplicate the peer's capture, and each review finds a new stretch
    to read. False when `session_id` is empty: with no caller to compare, the flag stands."""
    owner = str(nap_owed_info(proj).get("session_id") or "")
    if not owner or not session_id or owner == str(session_id):
        return False
    return owner in _live_sessions()


def nap_owed_blocks(proj: _StrPath | None, session_id: str | None = "") -> bool:
    """True while an owed nap still blocks a Stop: owed, not declined, and not owed by a live peer
    of `session_id`. The Stop gate blocks on this and the context watcher yields on it, so the two
    cannot disagree about a declined nap."""
    return (is_nap_owed(proj) and not nap_owed_declined(proj)
            and not nap_owed_by_live_peer(proj, session_id))


def clear_nap_owed(proj: _StrPath | None) -> None:
    """Discharge the owed nap (best-effort), the legacy raw-cwd marker included."""
    for f in _nap_owed_files(proj):
        with contextlib.suppress(OSError):
            f.unlink()


# The watermark reviewer the dream (and the nap) consume transcripts under. dream_state.py marks
# with this same name, so the gate can tell whether an owed transcript has any unread bytes left.
DREAM_REVIEWER = "dream"

NAP_OWED_TRANSCRIPT_GONE: Final = "gone"
NAP_OWED_TRANSCRIPT_CONSUMED: Final = "consumed"
# Why an owed nap cannot be satisfied; "" while the obligation is real.
type NapOwedUnsatisfiable = Literal["", "gone", "consumed"]


def unsatisfiable_nap_owed(proj: _StrPath | None,
                           session_id: str | None = "") -> tuple[str, NapOwedUnsatisfiable]:
    """(transcript_path, why) when the owed nap names a transcript nothing can still consume.

    The flag is written at compaction and cleared only by `dream_state.py done`, so it can outlive
    its transcript by weeks. Claude Code deletes old transcripts under its retention setting
    (`cleanupPeriodDays`, 30 days by default), and a block naming a deleted file can never be
    satisfied: every later session in that cwd is stopped for a read that cannot happen. Why is
    `NAP_OWED_TRANSCRIPT_GONE` then.

    `NAP_OWED_TRANSCRIPT_CONSUMED` covers an EARLIER session's transcript whose dream watermark has
    already reached its end: the obligation was that file's unread bytes and there are none. The
    current session's own transcript is never judged consumed, because it keeps growing after the
    compaction point and its watermark cannot say where that point was.

    Returns ("", "") while the obligation is real, or when the flag names no transcript at all (a
    legacy marker: nothing to judge, so it stays)."""
    info = nap_owed_info(proj)
    path = str(info.get("transcript_path") or "")
    if not path:
        return "", ""
    if not os.path.exists(path):
        return path, NAP_OWED_TRANSCRIPT_GONE
    offset = _as_offset(info.get("offset"))
    if offset and furthest_watermark(path, DREAM_REVIEWER) >= offset:
        return path, NAP_OWED_TRANSCRIPT_CONSUMED
    owed_session = str(info.get("session_id") or "")
    if not owed_session or owed_session == str(session_id or ""):
        return "", ""
    try:
        size = os.path.getsize(path)
    except OSError:
        return "", ""
    if furthest_watermark(path, DREAM_REVIEWER) >= size:
        return path, NAP_OWED_TRANSCRIPT_CONSUMED
    return "", ""


# ---- machine-local config: one JSON for all informed-consent knobs (recommended defaults) ----
# Every habit-dependent decision is recorded here and applied automatically (asked once, never
# re-nagged). The `meta-memory-settings` skill views / sets / resets it.

def config_path() -> Path:
    """The machine-local memory settings file every knob is read from and written to."""
    return claude_paths.config_dir() / ".bitranox-memory.json"


DEFAULT_CONFIG: dict[str, object] = {
    "dream_mode": "propose",       # off | auto | propose
    "privacy": "open",             # open (secret/PII scrub only) | walled (by privacy domain)
    "promotion": "corroborated",   # corroborated (inferred needs dwell) | eager
    "skill_placement": "lowest",   # lowest scope that fits; ask before the public marketplace
    "nudges": True,                # session-start nudges on/off
    "track_private": False,        # git-track .claude-bx-selflearning on a private repo? (public: never)
    "mcp_search": "auto",          # off | auto (use a full-text+graph MCP for cross-project recall if present)
    "cross_tree_search": True,     # per-prompt recall may scan OTHER knowledge trees (False: current tree only)
    "discovery_roots": [],         # extra roots to walk for curated stores; [] -> derive at runtime (never
                                   # ship hardcoded maintainer absolute paths in this tracked default)
    # context-watcher. The window is DETECTED from the model this project has used (~/.claude.json
    # keeps the full id including the `[1m]` suffix, which the transcript drops), so 0 means auto.
    # The context limit is min(pct of window, cap): the pct leg keeps a cushion on a small window,
    # and the cap catches a big-window session past the measured rot onset while still only 40%
    # full. That limit is the value CLAUDE_CODE_AUTO_COMPACT_WINDOW should hold: the watcher asks
    # for a checkpoint before the harness compacts there, and the session goes on.
    "context_window": 0,           # 0 = detect; set a token count only to override the detection
    "context_handover_pct": 70,    # percentage leg of the context limit
    "context_handover_cap": 400000,  # absolute leg, in tokens (measured context-rot onset)
    # Opt-in text classifier (hooks/classifier.py). The backend is the master switch; each site
    # has its own knob, so one site can be compared in shadow while the others stay off. Shadow
    # never changes a hook's decision: it only logs Jev's verdict beside the regex's. Decide (the
    # skill router only) lets Jev's answer choose the nudge, the keywords only when Jev is silent.
    "classifier_backend": "off",       # off | jev
    "classifier_model": "jev-latest",  # the TypeSafe model id sent with every request
    "classifier_stop_signal": "off",   # off | shadow | decide - self-improve Stop gate signal
    "classifier_skill_router": "off",  # off | shadow | decide - UserPromptSubmit skill router
    "classifier_recall_rerank": "off",  # off | shadow | decide - UserPromptSubmit memory recall ranking
    "classifier_subagent_signal": "off",  # off | shadow | decide - SubagentStop learning-signal capture
    "classifier_skills": "off",        # off | shadow - skill-step Jev shadow (needs classifier_backend=jev too)
    # tmp-prune-hook.py: at most once an hour, delete dead Claude Code session scratch and old
    # one-off dirs from the temp dir (tmp_prune.py says what counts as dead).
    "tmp_prune": "on",                 # on | dry-run | off
}


class ConfigUnreadable(OSError):
    """The config file exists but is not a readable JSON object, so it cannot be safely rewritten."""


def read_config_file() -> tuple[dict[str, object] | None, str | None]:
    """(settings, problem) for the config file: ({}, None) when there is none, (object, None)
    when it holds a JSON object, and (None, why) when it exists but cannot be used - unreadable,
    not UTF-8, not JSON, or JSON that is not an object. THE one reader, so `load_config` and
    `save_config` agree on what "unusable" means."""
    p = config_path()
    try:
        # utf-8-sig: a file saved by a Windows editor carries a BOM, which json.loads refuses, so
        # every knob the user set there silently read as its default.
        text = p.read_text(encoding="utf-8-sig")
    except (FileNotFoundError, NotADirectoryError):   # no config can exist there
        return {}, None
    except OSError as exc:
        return None, "cannot read %s: %s" % (p, exc)
    except UnicodeDecodeError as exc:
        return None, "%s is not UTF-8 text (%s)" % (p, exc)
    try:
        raw = json.loads(text)
    except ValueError as exc:
        return None, "%s is not valid JSON (%s)" % (p, exc)
    if not _is_record(raw):
        return None, "%s holds a JSON %s, not an object" % (p, type(raw).__name__)
    return raw, None


def load_config() -> dict[str, object]:
    """Config merged over DEFAULT_CONFIG. Robust: a missing or unusable file yields the
    recommended defaults.

    Each value is whatever the file holds for a known key, which a hand edit can make any JSON
    type, so it is typed `object` and every reader checks the value it uses."""
    cfg = dict(DEFAULT_CONFIG)
    raw, _problem = read_config_file()
    known = raw or {}
    cfg.update({k: known[k] for k in known if k in DEFAULT_CONFIG})
    return cfg


def save_config(updates: Mapping[str, object], strict: bool = False) -> dict[str, object]:
    """Merge known keys from `updates` into the config file (created if missing); return the
    merged dict. Unknown keys are ignored so the file stays a clean, known schema.

    Best-effort by default (hooks must never fail a turn over it). `strict=True` raises the
    OSError of a failed write instead: an operator CLI that reports the new value after a write
    that never happened tells the user a choice is recorded when it is not.

    A config that exists but cannot be used - unreadable, not UTF-8, not a JSON object - is never
    written, for every caller: `load_config` answers the defaults for it, so a save would replace
    every knob the file still holds with its default. Strict raises `ConfigUnreadable` (an
    OSError) naming why; best-effort returns the merged dict unsaved."""
    raw, problem = read_config_file()
    cfg = dict(DEFAULT_CONFIG)
    known = raw or {}
    cfg.update({k: known[k] for k in known if k in DEFAULT_CONFIG})
    cfg.update({k: updates[k] for k in updates if k in DEFAULT_CONFIG})
    try:
        if problem:
            raise ConfigUnreadable(problem)
        p = config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        if strict:
            raise
    return cfg


# ---- altitude homes (always-present tiers, narrowest -> broadest) --------------------

def excluded_anchor_dirs() -> set[Path]:
    """Dirs that must NEVER be a memory altitude anchor even if they carry a `CLAUDE.md` + store: the
    user's HOME and the system temp dir (the filesystem root is handled separately via `d.anchor`).
    Walking UP by `.parent` from a real project cwd never reaches these in practice - a project lives
    under a mount like `/media/.../projects`, not directly at `~` or `/tmp` - so this is a safety net,
    not the primary bound: it stops a stray `CLAUDE.md` left at `~` / `/tmp`, or a test/probe running
    under the temp dir, from hijacking the anchor. Read fresh each call so a monkeypatched HOME/TMPDIR
    is honored."""
    out: set[Path] = set()
    for env in ("HOME", "USERPROFILE"):
        h = os.environ.get(env)
        if h:
            try:
                out.add(Path(h))
            except (OSError, ValueError):
                pass
    try:
        out.add(Path(tempfile.gettempdir()))
    except (OSError, ValueError):
        pass
    return out


def resolve_anchor(proj: _StrPath | None) -> Path | None:
    """THE canonical anchor resolver (single source; `uuid_store.resolve_anchor` delegates here).

    The anchor of `proj`'s knowledge TREE: the TOPMOST ancestor (including `proj`) that carries a
    `CLAUDE.md` AND the co-located central store (`.claude-memory/`). Tying the anchor to the store it
    must hold stops a STRAY `CLAUDE.md` higher up (nested workspaces routinely have `CLAUDE.md` at many
    levels) from hijacking the tree top - a real fragility a probe caught. Only at BOOTSTRAP, when no
    dir in the chain has a store yet, fall back to the topmost `CLAUDE.md` (the first write creates the
    store there and thereafter the colocation pins it). Never anchors at `/`, `~`, or the temp dir
    (see `excluded_anchor_dirs`). Returns a Path, or None when no ancestor has a `CLAUDE.md` at all.
    With MULTIPLE independent trees on one machine, each cwd resolves to its OWN tree's anchor."""
    if proj is None:                                 # os.fspath(None) raised the TypeError below
        return None
    try:
        # Absolute FIRST: a relative path has an empty anchor and Path("") == Path("."), so the
        # root guard below skipped the only rung and the walk never climbed above the cwd. abspath
        # rather than resolve(): it keeps symlinked spellings as given, so an absolute input
        # answers exactly as before and the excluded dirs (also unresolved) still compare equal.
        here = Path(os.path.abspath(os.fspath(proj)))
        ladder = [here, *here.parents]
    except (TypeError, ValueError):
        return None
    excluded = excluded_anchor_dirs()
    highest_both: Path | None = None                 # topmost dir with a CLAUDE.md AND a store (robust)
    highest_md: Path | None = None                   # topmost dir with a CLAUDE.md (bootstrap fallback)
    for d in ladder:
        try:
            if d == Path(d.anchor) or d in excluded:  # never anchor at /, ~, or the temp dir
                continue
            has_md = (d / "CLAUDE.md").is_file()
            has_store = (d / MEMORY_DIRNAME).is_dir()
        except OSError:
            continue
        if has_md:
            highest_md = d
        if has_md and has_store:
            highest_both = d
    return highest_both or highest_md


# The historical name; same resolver (kept so call sites and prose stay readable).
topmost_claude_md_dir = resolve_anchor


def global_rules_dir(proj: _StrPath | None = None) -> Path:
    """The tree-top central store: `<anchor>/.claude-memory` for `proj`'s OWN tree (share-visible, so
    it reaches every machine that mounts the tree). NEVER `~/.claude` (machine-local, invisible from a
    remote mount). If no ancestor - nor `proj` itself - has a `CLAUDE.md`, `proj` IS the top level and
    accumulates everything. `proj` defaults to the current working directory."""
    base = proj if proj is not None else os.getcwd()
    return (resolve_anchor(base) or Path(base)) / MEMORY_DIRNAME


def discovery_roots() -> list[Path]:
    """Filesystem roots to WALK for other projects' curated `.claude-memory` stores (used by
    cross-project recall + as the MCP's watched roots). When the config `discovery_roots` list (a
    machine-local override in ~/.claude/.bitranox-memory.json) is set, it is honored EXACTLY -
    `$HOME` is the DERIVED default ONLY when no roots are configured, so the tracked DEFAULT_CONFIG
    never ships hardcoded maintainer absolute paths (public-plugin safe). Force-adding `$HOME` on top
    of an explicit list would drag a huge unrelated home tree (build caches, no stores) into every
    walk; an explicit config is a precise statement of where the stores are. The walk is additionally
    backstopped by reverse-resolving native slugs (see resolve_slug), so a project outside these
    roots is still discoverable. Deduped, existing dirs only."""
    roots: set[Path] = set()
    for r in _configured_roots(load_config().get("discovery_roots")):
        try:
            roots.add(Path(r).expanduser())
        except (OSError, ValueError):
            continue
    if not roots:                       # no explicit config -> the public-safe derived default
        roots.add(Path.home())
    return sorted({p for p in roots if _is_dir(p)}, key=str)


def _configured_roots(raw: object) -> list[str]:
    """The root paths of a configured `discovery_roots` value: its string elements. Only a hand
    edit can write anything else (the settings CLI writes a list of strings), and the answer is
    the one `mcp_search` gives a hand-edited mode: what cannot be read as roots is reported on
    stderr and left out, never raised (the per-prompt recall hook asks), never iterated as it
    stands (a string read per character named one root per letter). A value that is not a list
    contributes no root, so the derived default applies, as for an unset one."""
    if raw is None or raw == []:
        return []
    if not _is_list(raw):
        print("self_improve_signals: config discovery_roots is a JSON %s, not a list of paths; "
              "using the default ($HOME)" % type(raw).__name__, file=sys.stderr)
        return []
    bad = [r for r in raw if not isinstance(r, str)]
    if bad:
        print("self_improve_signals: config discovery_roots holds %d entr%s that %s not a path "
              "string (%s); skipped" % (len(bad), "y" if len(bad) == 1 else "ies",
                                       "is" if len(bad) == 1 else "are",
                                       ", ".join(sorted({type(r).__name__ for r in bad}))),
              file=sys.stderr)
    return [r for r in raw if isinstance(r, str)]


def audit_dir() -> Path:
    """Machine-local scratch dir the recall/gather caches and the stores-generation marker share."""
    return claude_paths.audit_dir()


def _stores_gen_file() -> Path:
    return audit_dir() / "stores-generation.txt"


def stores_generation() -> int:
    """Monotonic counter bumped whenever a NEW curated store dir is created (see the engine). The
    cross-tree dir-cache stamps itself with this value, so a brand-new store busts the cache at once
    while a cached walk of unchanged roots stays valid. Absent/garbled marker -> 0 (cache still valid
    via its TTL). Never raises."""
    try:
        return int(_stores_gen_file().read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return 0


def bump_stores_generation() -> None:
    """Increment the stores-generation marker under a lock, busting the cross-tree dir-cache. Called
    by the engine only when it actually creates a new `.claude-memory` store dir (rare), so it does
    NOT run on the hot per-fact write path. Best-effort: a missed bump merely means a new store waits
    out the cache TTL; never raises."""
    f = _stores_gen_file()
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    try:
        with memory_lock(f):
            try:
                cur = int(f.read_text(encoding="utf-8").strip() or "0")
            except (OSError, ValueError):
                cur = 0
            f.write_text(str(cur + 1), encoding="utf-8")
    except (OSError, TimeoutError):
        pass


def _is_dir(p: _StrPath) -> bool:
    try:
        return Path(p).is_dir()
    except OSError:
        return False


def find_claude_md_dirs(roots: Iterable[_StrPath]) -> list[Path]:
    """Every dir under `roots` that carries a `CLAUDE.md` - the raw material for tree discovery.
    Prunes vendor/hidden/backup dirs, the store dirs themselves, Claude's config dir, and the
    excluded anchor dirs; never follows symlinks (a link into another tree must not merge them)."""
    out: set[Path] = set()
    excluded = {str(d) for d in excluded_anchor_dirs()}
    config_dir = str(claude_paths.config_dir())
    for root in roots:
        try:
            for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
                base = os.path.basename(dirpath)
                if (base in VENDOR_DIRNAMES or base in (MEMORY_DIRNAME, CURATED_DIRNAME)
                        or ".bak-" in base or base.endswith(".bak")
                        or dirpath == config_dir):
                    dirnames[:] = []
                    continue
                dirnames[:] = [d for d in dirnames
                               if d not in VENDOR_DIRNAMES
                               and d not in (MEMORY_DIRNAME, CURATED_DIRNAME)
                               and not d.startswith(".")
                               and ".bak-" not in d and not d.endswith(".bak")]
                if "CLAUDE.md" in filenames and dirpath not in excluded:
                    out.add(Path(dirpath))
        except OSError:
            continue
    return sorted(out, key=str)


def tree_groups(md_dirs: Iterable[_StrPath]) -> dict[Path, list[Path]]:
    """Group CLAUDE.md-bearing dirs into their knowledge TREES: {top_dir: [members]}, members
    deepest-first (lexicographic ties). The top is each member's `resolve_anchor` - so independent
    trees (a marketing company and a bakery share nothing) come out as separate groups, each with
    its own top and store."""
    groups: dict[Path, list[Path]] = {}
    for d in md_dirs:
        top = resolve_anchor(str(d))
        if top is None:
            top = Path(d)
        groups.setdefault(top, []).append(Path(d))
    for top, members in groups.items():
        members.sort(key=lambda m: (-len(m.parts), str(m)))
    return groups


def altitude_chain(proj: _StrPath) -> list[Path]:
    """Ordered altitude LEVEL DIRS for `proj`, narrowest -> broadest: the project dir itself, then
    each ancestor directory up to and INCLUDING the tree's anchor (gap levels between are included so
    they can be filled). The LAST (broadest) position is the tree top - NEVER `~/.claude`. If no
    ancestor - nor `proj` - has a `CLAUDE.md`, the chain is just `[proj]` (it is the top; everything
    accumulates there). Each level's pointer block lives in `<level>/CLAUDE.local.md`; the bodies all
    live centrally at the anchor's `.claude-memory/`. Reference-integrity uses this: a `[[ref]]` must
    resolve to a target at the SAME or a LATER (higher) position - upward only."""
    try:
        # Absolute FIRST: a relative path has an empty anchor, and Path("") == Path("."), so the
        # root guard below fired for every relative input and returned an empty chain in silence -
        # callers then saw a level with no ancestors and read that as a clean result.
        here = Path(proj).resolve()
        if here == Path(here.anchor) or here in excluded_anchor_dirs():
            return []                             # /, ~, tempdir: never an altitude, never a top
        ladder = [here, *here.parents]            # project dir up toward /
        top = resolve_anchor(str(here))           # the tree's anchor, or None
        if top is None:                           # project is the top; single-tier chain
            return [here]
        # `ladder` holds RESOLVED paths, so an unresolved anchor would never match and the
        # ValueError below would quietly degrade the chain to a single level.
        highest = ladder.index(Path(top).resolve())
        chain = ladder[:highest + 1]
        kept = [d for d in chain if ".claude" not in d.parts]   # a `.claude` config dir (or its
        return kept or chain                                    # worktrees/ scaffold) is never an altitude
    except (TypeError, ValueError):
        return [Path(proj)]


# ---- session meta + transcript watermark: let the DREAM read the session from DISK -------------
# The dream "skims the session" from the model's IN-CONTEXT memory, so anything compaction cleared
# (or that scrolled out) is invisible to capture-first - the transcript FILE survives compaction, the
# context does not. But a dream is a model pass and never receives `transcript_path`; a hook does, so
# a hook records it here and the dream looks it up by cwd. The watermark then keeps that read
# INCREMENTAL: each reviewer (the regex audit, the LLM review) has its own mark, so an
# already-reviewed prefix is never re-read (re-feeding it to the model is the expensive waste).

def session_meta_file(proj: _StrPath | None) -> Path:
    """Where the current session's id + transcript path are recorded for `proj` (a dream input)."""
    return audit_dir() / (proj_key(proj) + ".session.json")


def record_session_meta(proj: _StrPath | None, session: str | None,
                        transcript_path: _StrPath | None) -> None:
    """Record the live session id + transcript path for `proj`. Best-effort; called from a hook."""
    if not (proj and transcript_path):
        return
    try:
        f = session_meta_file(proj)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"session_id": str(session or ""),
                                 "transcript_path": str(transcript_path),
                                 "ts": time.time()}, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


def read_session_meta(proj: _StrPath | None) -> JsonRecord:
    """{'session_id','transcript_path','ts'} for `proj`, or {} when unknown."""
    try:
        d = _decode_json_file(session_meta_file(proj))
        return d if _is_record(d) else {}
    except (OSError, ValueError):
        return {}


class StateWriteError(OSError):
    """A state file whose write the caller reports as done could not be written; nothing changed.

    Raised, never swallowed, by the writers of the review watermark, the promotion sightings,
    the learned word lists and a nap decline.
    Those used to swallow every OSError, so a failed write returned exactly what a successful one
    did and only a caller that happened to read the value back could tell. An OSError subclass, so
    a hook's fail-open handler that already catches OSError still keeps the turn moving."""


def _decode_json_file(path: _StrPath) -> object:
    """The parsed JSON at `path`. Raises OSError (unreadable) or ValueError (does not parse).

    The ONE decoder for this module's JSON state files, readers and updaters alike. utf-8-sig
    because a hand edit on Windows prepends a BOM that plain utf-8 keeps as U+FEFF, which JSON
    refuses: a reader decoding differently from its updater then answered EMPTY (a sighting dwell
    of 0) for a store its own updater parsed and counted."""
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _load_any_json_for_update(path: _StrPath) -> object:
    """The parsed JSON at `path` for a read-modify-write, any shape: None when the file is absent
    or does not parse (it then holds nothing to lose). A file that EXISTS but cannot be READ
    raises StateWriteError: answering empty there makes the writer replace every other entry with
    its one new value."""
    try:
        return _decode_json_file(path)
    except FileNotFoundError:
        return None
    except ValueError:
        return None
    except OSError as exc:
        raise StateWriteError("cannot read %s to update it, so it was left unchanged (%s)"
                              % (path, exc)) from exc


def _load_json_for_update(path: _StrPath) -> JsonRecord:
    """The JSON object at `path` for a read-modify-write: {} when the file is absent or does not
    parse into an object. Raises StateWriteError like `_load_any_json_for_update`."""
    data = _load_any_json_for_update(path)
    return data if _is_record(data) else {}


def _write_json_state(path: _StrPath, data: object) -> None:
    """Write `data` to `path` as JSON; see `_write_text_state`. Raises StateWriteError."""
    _write_text_state(path, json.dumps(data, sort_keys=True))


def _write_text_state(path: _StrPath, text: str) -> None:
    """Write `text` to `path` through a temp file and a replace, so a failure leaves the
    previous content whole rather than a torn file that later reads as empty. Raises
    StateWriteError when the write does not land.

    A read-only target is refused rather than replaced: a rename over it would succeed on POSIX
    and fail on Windows, and on both a read-only mark means someone asked for it to stay put."""
    path = Path(path)
    if os.path.lexists(path) and path.is_file() and not os.access(path, os.W_OK):
        raise StateWriteError("could not write %s (the file is read-only)" % path)
    tmp: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        retry_while_shared(os.replace, tmp, str(path))
        tmp = None
    except OSError as exc:
        raise StateWriteError("could not write %s (%s)" % (path, exc)) from exc
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def watermark_file(proj: _StrPath | None) -> Path:
    """Per-(transcript, reviewer) high-water marks: how far each reviewer has consumed."""
    return audit_dir() / (proj_key(proj) + ".watermark.json")


def _watermarks(proj: _StrPath | None) -> JsonRecord:
    try:
        d = _decode_json_file(watermark_file(proj))
        return d if _is_record(d) else {}
    except (OSError, ValueError):
        return {}


def get_watermark(proj: _StrPath | None, transcript: _StrPath, reviewer: str) -> int:
    """Byte offset `reviewer` has already consumed of `transcript`. 0 when unmarked.

    `proj`'s own mark when it has one, since that is what it last wrote and a write is checked by
    reading it back. Otherwise the furthest mark any project recorded for this transcript: the
    marks are filed under the cwd a review ran from, and one `cd` into another repository moved
    that cwd, so a session already reviewed to its end read as unreviewed from byte 0 there."""
    own = _watermarks(proj).get(str(reviewer), {})
    if _is_record(own) and str(transcript) in own:
        return _as_offset(own.get(str(transcript)))
    return furthest_watermark(transcript, reviewer)


def furthest_watermark(transcript: _StrPath, reviewer: str) -> int:
    """The furthest offset `reviewer` has consumed of `transcript` from ANY cwd. 0 when unmarked.

    The question an owed nap asks: were these bytes read at all? `get_watermark` prefers the
    cwd's own mark for its read-back, so a stale lower mark a worktree once wrote hid a review
    that later reached the end from the launch checkout, and the Stop gate kept blocking."""
    furthest = 0
    try:
        stores = list(audit_dir().glob("*.watermark.json"))
    except OSError:
        return 0
    for store in stores:
        try:
            marks = _decode_json_file(store)
        except (OSError, ValueError):
            continue
        per = marks.get(str(reviewer)) if _is_record(marks) else None
        if _is_record(per):
            furthest = max(furthest, _as_offset(per.get(str(transcript))))
    return furthest


def _as_offset(value: object) -> int:
    """A stored mark as an int; 0 for anything that is not one."""
    try:
        return _coerce_int(value or 0)
    except (TypeError, ValueError):
        return 0


def set_watermark(proj: _StrPath | None, transcript: _StrPath, reviewer: str, offset: int) -> None:
    """Record that `reviewer` has consumed `transcript` up to `offset`.

    Raises StateWriteError when the mark is not recorded (a failed write, or an existing store
    that cannot be read and so must not be overwritten), and ValueError/TypeError for an offset
    that is not an integer. Both used to be swallowed, so a caller reported a review as recorded
    while the next review re-read the same stretch - or, worse, a later mark landed on a store
    that had silently lost every other reviewer's position."""
    offset = int(offset)
    f = watermark_file(proj)
    marks = _load_json_for_update(f)
    per_reviewer = marks.get(str(reviewer))
    if not _is_record(per_reviewer):
        per_reviewer = marks[str(reviewer)] = {}
    per_reviewer[str(transcript)] = offset
    _write_json_state(f, marks)


class TranscriptPart(NamedTuple):
    """One part of a transcript's unreviewed stretch: bytes `start`..`end` of a `size`-byte file,
    decoded as `text`. `end == size` means the part reaches the end of the file."""
    text: str
    start: int
    end: int
    size: int


def unreviewed_transcript_part(proj: _StrPath | None, reviewer: str, transcript: _StrPath | None = None,
                               max_bytes: int = 2_000_000) -> TranscriptPart:
    """The OLDEST part of the transcript `reviewer` has NOT consumed yet, as a TranscriptPart.

    `end` is always the end of the text returned, never further: marking it reviewed can only ever
    discharge what the caller was shown. The cap used to return the NEWEST `max_bytes` with the
    offset of the file END, so a caller that marked that offset discharged everything older
    unread; and a single unreviewed line longer than the cap came back as "", which reads as
    "nothing new". Now a stretch over `max_bytes` is cut after its last newline, so the next call
    resumes on a whole line; a single line longer than the cap is cut at the last whole UTF-8
    character before the byte bound (see `_whole_characters`). Call again after marking to get the
    next part.

    Nothing new is ("", mark, mark, size): that is what stops a second dream in one session from
    re-analyzing (and re-paying for) the whole transcript. A transcript SHORTER than the mark means
    a rotated/replaced file, so the mark is ignored and the file is read from the start rather than
    silently skipping a fresh session. No transcript at all (none recorded, or the file is gone) is
    ("", 0, 0, 0).

    Raises OSError when the transcript exists but cannot be read. Answering "nothing new" there let
    a caller that marks the returned end discharge every unread byte of it."""
    # The recorded path is whatever the meta file holds; a value that is no path fails below, in
    # getsize or open, as it always did.
    transcript = cast("_StrPath", transcript or (read_session_meta(proj) or {}).get("transcript_path")
                      or "")
    if not transcript:
        return TranscriptPart("", 0, 0, 0)
    try:
        size = os.path.getsize(transcript)
    except (FileNotFoundError, NotADirectoryError):   # gone, or can never exist
        return TranscriptPart("", 0, 0, 0)
    mark = get_watermark(proj, transcript, reviewer)
    if mark > size:
        mark = 0                                   # rotated/replaced: never skip a fresh transcript
    end = min(size, mark + max(1, int(max_bytes)))
    with open(transcript, "rb") as fh:             # opened even when nothing is new: an unreadable
        fh.seek(mark)                              # file must raise, not read as consumed
        data = fh.read(end - mark)
        if mark + len(data) < size:
            if b"\n" in data:
                data = data[:data.rfind(b"\n") + 1]    # resume on a whole line next time
            else:
                data = _whole_characters(data, fh)
    return TranscriptPart(data.decode("utf-8", "replace"), mark, mark + len(data), size)


def _whole_characters(data: bytes, fh: BinaryIO) -> bytes:
    """`data` cut back to the last complete UTF-8 character; extended from `fh` to complete the
    first one instead when nothing whole would be left, so every call still makes progress.

    A line longer than the cap is cut at a byte bound, which can fall inside a multi-byte
    character: decoded with "replace", the end of one part and the start of the next each carried
    U+FFFD for a character that is in the file. Bytes that are not UTF-8 at all are left as they
    are - the cut only moves for a lead byte whose continuation was cut off."""
    lead = len(data) - 1
    while lead >= 0 and len(data) - lead <= 3 and 0x80 <= data[lead] < 0xC0:
        lead -= 1                                  # step back over continuation bytes
    if lead < 0:
        return data
    first = data[lead]
    need = 2 if 0xC0 <= first < 0xE0 else 3 if 0xE0 <= first < 0xF0 else 4 if 0xF0 <= first < 0xF8 else 1
    if len(data) - lead >= need:
        return data                                # the last character is complete
    if lead > 0:
        return data[:lead]
    return data + fh.read(need - len(data))        # only a partial first character: finish it


def unreviewed_transcript_text(proj: _StrPath | None, reviewer: str, transcript: _StrPath | None = None,
                               max_bytes: int = 2_000_000) -> tuple[str, int]:
    """(new_text, new_offset) of `unreviewed_transcript_part`: the oldest unreviewed part and the
    byte offset where it ends. Raises OSError, like it, for a transcript that cannot be read."""
    part = unreviewed_transcript_part(proj, reviewer, transcript, max_bytes)
    return part.text, part.end


def live_transcripts(proj: str) -> list[str]:
    """The transcripts in `proj`'s native dir whose session is running right now."""
    native = memory_dir(proj).parent
    return [str(native / (sid + ".jsonl")) for sid in _live_sessions()
            if (native / (sid + ".jsonl")).is_file()]


def _review_shown_file(proj: _StrPath | None) -> Path:
    # Per session as well as per project: two live sessions in one cwd review different transcripts.
    return session_state_path("%s-%s" % (calling_session_id(), proj_key(proj)), ".review-shown")


def record_review_shown(proj: _StrPath | None, transcript: _StrPath) -> None:
    """Remember which transcript the calling session's last session-review showed.
    Raises StateWriteError when the write does not land."""
    _write_json_state(_review_shown_file(proj), {"path": str(transcript)})


def last_review_shown(proj: _StrPath | None) -> str:
    """The transcript the calling session's last session-review showed, or ""."""
    try:
        d = _decode_json_file(_review_shown_file(proj))
    except (OSError, ValueError):
        return ""
    return str(d.get("path") or "") if _is_record(d) else ""


def resolve_transcript(proj: str) -> str:
    """The transcript path for `proj`: the calling session's own when it has one here, else the
    hook-recorded one, else the newest *.jsonl under the project's native dir, else "".

    The session's own comes first because the hook-recorded path is per cwd: with two live sessions
    in one cwd it names whichever stopped last, and a review would read and mark the peer's file.

    A manual session-review runs with NO Stop hook having recorded meta (right after /clear, or on a
    cwd-key mismatch). Without a fallback it reviews NOTHING while reporting "nothing new" - a silent
    miss of capture-first. The glob self-locates the live transcript so the review self-heals; newest
    by MTIME, never by name (a session-id prefix is not time-ordered)."""
    sid = calling_session_id()
    if sid and Path(sid).name == sid:
        own = memory_dir(proj).parent / (sid + ".jsonl")
        with contextlib.suppress(OSError):
            if own.is_file():
                return str(own)
    # Whatever the meta file holds, returned as it stands when it names a path that exists.
    recorded = cast("str", (read_session_meta(proj) or {}).get("transcript_path") or "")
    if recorded and os.path.exists(recorded):
        return recorded
    try:
        cands = list(memory_dir(proj).parent.glob("*.jsonl"))
    except OSError:
        return ""

    def _mtime(p: Path) -> float:
        try:
            return p.stat().st_mtime
        except OSError:
            return -1.0

    return str(max(cands, key=_mtime)) if cands else ""


# ---- subagent learnings: buffered by the SubagentStop hook, drained by the main capture --------
# A subagent's learning is otherwise LOST: the capture nudge is a main-session Stop hook, nothing
# scans a subagent transcript, and only a subagent's final text can reach the main transcript (on
# older builds a named agent's not even that unless it SendMessages it). A subagent also cannot cleanly write curated memory itself
# (its cwd/subject may differ and it is scoped to one task), so the hook BUFFERS the signal here and
# the main session's capture routes + writes it. Session-keyed, out of the dreamed store.

def subagent_learnings_file(session: object) -> Path:
    """Queue of learning signals detected in this session's SUBAGENT transcripts."""
    return session_state_path(session, ".subagent-learnings")


def read_subagent_learnings(session: object) -> list[JsonRecord]:
    """The buffered subagent learning records for `session`, oldest first. [] when none."""
    if not session:
        return []
    out: list[JsonRecord] = []
    try:
        for ln in subagent_learnings_file(session).read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
            except ValueError:
                continue
            if _is_record(rec):
                out.append(rec)
    except OSError:
        return []
    return out


def buffer_subagent_learning(session: object, record: Mapping[str, object], max_items: int = 60) -> None:
    """Append one subagent learning record (newest-capped). Best-effort: never raises."""
    if not session or not isinstance(record, dict):
        return
    try:
        cur = read_subagent_learnings(session)
        cur.append(record)
        if len(cur) > max_items:
            cur = cur[-max_items:]
        f = subagent_learnings_file(session)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("\n".join(json.dumps(r, sort_keys=True) for r in cur) + "\n", encoding="utf-8")
    except OSError:
        pass


def drain_subagent_learnings(session: object) -> None:
    """Consume the queue (the main capture has surfaced it). Best-effort."""
    try:
        subagent_learnings_file(session).unlink()
    except OSError:
        pass


# ---- checkpoint-asked: when the context watcher last told this session to save its state --------
# Written by context-watcher.py each time it asks for a pre-compaction checkpoint, read by
# compact-resume.py after the compaction: a handover.md written AFTER this moment is the session's
# own checkpoint, while an older one describes an earlier moment and must not be re-fed as current.

def checkpoint_asked_file(session: object) -> Path:
    return session_state_path(session, ".checkpoint-asked")


def mark_checkpoint_asked(session: object, now: float | None = None) -> None:
    """Record the moment of a checkpoint request (epoch seconds). Best-effort: never raises."""
    try:
        flag = checkpoint_asked_file(session)
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("%.3f\n" % (time.time() if now is None else float(now)), encoding="utf-8")
    except (OSError, TypeError, ValueError):
        pass


def checkpoint_asked_at(session: object) -> float:
    """Epoch seconds of this session's latest checkpoint request, or 0.0 when it has none."""
    try:
        return float(checkpoint_asked_file(session).read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0.0


# ---- touched-paths: the per-session evidence of WHICH repos this session actually edited -------
# Written by the PostToolUse `touched-paths` hook, read by the Stop gate / capture. Session-keyed
# (the probe proved `session_id` is stable across PostToolUse/Stop/SubagentStop), OUT of the dreamed
# store so it never bumps a store mtime or affects convergence.

def touched_file(session: object) -> Path:
    """Scratch file holding the paths this session's turns wrote/edited (capture-routing evidence)."""
    return session_state_path(session, ".touched")


def read_touched_paths(session: object) -> list[str]:
    """The distinct paths recorded for `session`, least recently touched first. [] when none."""
    try:
        lines = touched_file(session).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [ln for ln in (x.strip() for x in lines) if ln]


def record_touched_path(session: object, path: _StrPath | None, max_lines: int = 400) -> None:
    """Record `path` for `session` as its newest entry (deduped, newest-capped). Never raises.

    A path carrying a line break (CR or LF) is REFUSED, not recorded: the file holds one path per
    line, so such a path came back as two bogus fragments that never deduped against each other,
    and each repeat grew the file. Escaping it instead would only hand `nearest_level` a path that
    names no file, so dropping that one path as routing evidence is the cheaper failure.
    """
    path = str(path or "").strip()
    if not path or not session or "\n" in path or "\r" in path:
        return
    try:
        cur = read_touched_paths(session)
        if cur and cur[-1] == path:
            return                                  # dedup: already the newest entry, nothing moves
        if path in cur:
            # A repeat edit is NEW for the cap below: left in its first-seen slot, a file rewritten
            # just now (compact-resume's handover.md) was the first one a long session evicted.
            cur.remove(path)
        cur.append(path)
        if len(cur) > max_lines:
            cur = cur[-max_lines:]                  # keep the NEWEST (the turn's current subject)
        f = touched_file(session)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("\n".join(cur) + "\n", encoding="utf-8")
    except OSError:
        pass


def clear_touched_paths(session: object) -> None:
    """Drop the session's touched-path evidence (best-effort)."""
    try:
        touched_file(session).unlink()
    except OSError:
        pass


def nearest_level(path: _StrPath) -> str | None:
    """The memory LEVEL a filesystem path belongs to: the NEAREST ancestor (including `path` itself
    when it is a dir) that carries a `CLAUDE.md` - i.e. the project a fact about that file would be
    filed at. `resolve_anchor` gives the TOPMOST rung; this gives the narrowest one. Returns a str
    path, or None when the path sits under no CLAUDE.md-bearing dir (or is an excluded altitude)."""
    try:
        # Absolute first, for the reason `resolve_anchor` gives: a relative path stopped at once.
        here = Path(os.path.abspath(os.fspath(path)))
        here = here if here.is_dir() else here.parent
        excluded = excluded_anchor_dirs()
        for d in [here, *here.parents]:
            if d == Path(d.anchor) or d in excluded:
                break                              # /, ~, tempdir: never a level
            if claude_md_path(str(d)).is_file():
                return str(d)
    except (OSError, TypeError, ValueError):
        pass
    return None


class SubjectLevel(TypedDict):
    """One memory level a touched path belongs to, as `subject_levels` reports it."""
    level: str
    anchor: str
    cross_tree: bool


def subject_levels(touched: Iterable[_StrPath] | None, cwd: _StrPath) -> list[SubjectLevel]:
    """The OTHER memory levels the given paths belong to - the routing evidence for capture.

    Capture is cwd-keyed, so a learning ABOUT a repo you edited from somewhere else lands in the
    wrong store (and cross-tree it can never be re-homed). Given the file paths the session
    wrote/edited and the session cwd, return the DISTINCT levels those paths belong to that are NOT cwd's own
    level - each as {"level", "anchor", "cross_tree"}. `cross_tree` marks a level in a DIFFERENT
    knowledge tree than cwd (the unrecoverable case); False means a sibling project in the SAME tree
    (the common case, which the tree dream can still re-level). Ancestors/descendants of cwd's own
    level are NOT flagged - they are the same project. Sorted by level for stable output.

    This is EVIDENCE, not a verdict: the capture step still judges whether the learning is about one
    of these repos or about the cwd workflow itself."""
    own = nearest_level(cwd)
    own_anchor = resolve_anchor(cwd) if own else None
    out: dict[str, SubjectLevel] = {}
    for p in touched or ():
        lvl = nearest_level(p)
        if not lvl or lvl == own:
            continue
        anchor = resolve_anchor(lvl)
        out[lvl] = {"level": lvl, "anchor": str(anchor) if anchor else "",
                    "cross_tree": bool(anchor and own_anchor and Path(anchor) != Path(own_anchor))}
    return [out[k] for k in sorted(out)]


# ---- new-project seeding (one-time /collect-knowledge bootstrap nudge) ---------------

def seeded_file(proj: _StrPath | None) -> Path:
    """Marker that this project has been seed-nudged (so the bootstrap nudge fires once)."""
    return claude_paths.audit_dir() / (proj_key(proj) + ".seeded")


def mark_seeded(proj: _StrPath | None, now: float | None = None) -> bool:
    f = seeded_file(proj)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(str(time.time() if now is None else now), encoding="utf-8")
        return True
    except OSError:
        return False


def project_unseeded(proj: str) -> bool:
    """True if this project has no REAL facts in EITHER tier yet AND has not been seed-nudged - a fresh
    project that could be bootstrapped from the existing knowledge tree via /collect-knowledge. Counts
    real facts (not a gap-fill scope-only index.md), so the nudge never misfires on an empty store."""
    if seeded_file(proj).exists():
        return False
    return not has_any_facts(proj)


# ---- quality / dwell gate for global promotion (high blast radius) -------------------
# The global layer loads into EVERY session, so a wrong entry there is high-blast. A user-stated
# concrete rule promotes eagerly; a model-INFERRED generalization must be corroborated by >=
# threshold DISTINCT PROJECTS first. The dwell store lives OUT of the dreamed store (here), so
# recording a sighting never bumps the store mtime - the convergence no-op holds.
#
# The dwell counts distinct PROJECTS, not sightings, because the two are not the same evidence: a
# dream re-reads UNCHANGED fact bodies on every run, so a sighting counter let one act of judgement
# corroborate itself simply by being re-derived (a measured crosstree pass recorded 84 sightings of
# the same candidate list in a single run). Repeat sightings inside one project therefore collapse
# to one corroborator, and the mechanism now says what the prose always claimed.


def promotion_file() -> Path:
    """The sighting store: candidate key -> the project keys that have sighted it.

    SHARED across projects, not per-project, because the question it answers is "how many DISTINCT
    projects corroborate this?" - a per-project file structurally cannot see another project's
    sighting, so the count it could offer would only ever be one project's own repeats."""
    return claude_paths.audit_dir() / "promotion-candidates.json"


def _sightings_of(data: Mapping[str, object]) -> dict[str, list[str]]:
    """key -> sorted distinct project keys, for every key whose value is a list; others dropped."""
    return {k: sorted({str(p) for p in v}) for k, v in data.items() if _is_list(v)}


def _read_sightings() -> dict[str, list[str]]:
    """key -> sorted list of project keys that sighted it. Any other shape reads as EMPTY.

    Failing CLOSED is the point. The pre-fix store was per-project and held key -> SIGHTING COUNT,
    which is precisely the evidence this gate no longer accepts; that file is not read at all, and
    a hand-edited or truncated store cannot crash a dream or be reinterpreted as corroboration."""
    try:
        data = _decode_json_file(promotion_file())     # the updater's decoder, BOM included
    except (OSError, ValueError):
        return {}
    if not _is_record(data):
        return {}
    return _sightings_of(data)


def _sightings_for_update() -> dict[str, list[str]]:
    """The sighting store for a read-modify-write: normalised like `_read_sightings`, but a store
    that exists and cannot be READ raises StateWriteError instead of reading as empty, because the
    write that follows would then erase every other key's corroborators."""
    return _sightings_of(_load_json_for_update(promotion_file()))


def _write_sightings(data: Mapping[str, list[str]]) -> None:
    """Persist the sighting store. Raises StateWriteError when the write does not land."""
    _write_json_state(promotion_file(), data)


def note_promotion_candidate(proj: _StrPath | None, key: str) -> int:
    """Record that `proj` sighted promotion-candidate `key`; return its dwell - the number of
    DISTINCT projects that have sighted it. Idempotent within a project: re-recording the same
    project adds no evidence, so N sightings of an unchanged fact body still count as one.

    Raises StateWriteError when the sighting is not recorded: returning the would-be dwell there
    reported corroboration that no later read could find."""
    data = _sightings_for_update()
    seen = set(data.get(key, ()))
    seen.add(proj_key(proj))
    data[key] = sorted(seen)
    _write_sightings(data)
    return len(seen)


def clear_promotion_candidate(proj: _StrPath | None, key: str) -> None:
    """Forget EVERY project's sighting of `key` (call after it is promoted, so it is not re-counted).

    The whole set goes, not the calling project's entry: leaving the other corroborators behind
    would let one single later sighting re-trip a gate that is supposed to need two. `proj` is
    accepted so the three promotion verbs share one call shape (a lone-argument variant here would
    silently take a project path as the key at any call site missed in a rename).

    Raises StateWriteError when the clear is not recorded, so a promoted key cannot be reported
    as cleared while its corroborators still stand."""
    data = _sightings_for_update()
    if key in data:
        del data[key]
        _write_sightings(data)


def promotion_dwell(proj: _StrPath | None, key: str) -> int:
    """How many DISTINCT projects have sighted `key`, WITHOUT recording a new sighting (read-only) -
    so a promote/hold decision can be re-queried without inflating the count. 0 if never seen.

    The answer is a property of the KEY, so it reads the same from whichever project asks; `proj` is
    accepted for the shared call shape described in `clear_promotion_candidate`."""
    return len(_read_sightings().get(key, ()))


def should_promote(source: str, dwell_count: int, mode: str | None = None, threshold: int = 2) -> bool:
    """Whether a generalization may be promoted to the always-everywhere global layer.
    source is "user" (user-stated concrete rule -> eager) or "inferred" (model generalization ->
    needs corroboration from >= threshold distinct projects, per `promotion_dwell`).
    mode comes from the config (`promotion`: corroborated | eager)."""
    effective = load_config().get("promotion", "corroborated") if mode is None else mode
    if effective == "eager" or source == "user":
        return True
    return int(dwell_count) >= threshold


# ---- per-level scope descriptor: a bounded, marked block in a CLAUDE.md --------------
# Each altitude declares "what this level is about" so the classifier can route knowledge. The
# descriptor is a clearly-delimited block so it never touches the user's hand-written content, and
# the upsert is DIFF-FREE (a no-change refresh returns the text unchanged -> convergence holds).

SCOPE_MARK_BEGIN = "<!-- bitranox:self-learning -->"
SCOPE_MARK_END = "<!-- /bitranox:self-learning -->"


def read_scope_block(text: str | None) -> str | None:
    """Return the descriptor inside the bitranox:self-learning markers in `text`, or None."""
    text = text or ""
    b = text.find(SCOPE_MARK_BEGIN)
    if b < 0:
        return None
    e = text.find(SCOPE_MARK_END, b)
    if e < 0:
        return None
    return text[b + len(SCOPE_MARK_BEGIN):e].strip()


def upsert_scope_block(text: str | None, descriptor: str | None) -> str:
    """Return CLAUDE.md `text` with the marked scope block set to `descriptor` (replaced in place if
    present, appended if absent). DIFF-FREE: if the block already holds `descriptor`, return `text`
    unchanged so a no-change refresh writes nothing."""
    text = text or ""
    descriptor = (descriptor or "").strip()
    block = "%s\n%s\n%s" % (SCOPE_MARK_BEGIN, descriptor, SCOPE_MARK_END)
    b = text.find(SCOPE_MARK_BEGIN)
    if b >= 0:
        e = text.find(SCOPE_MARK_END, b)
        if e >= 0:
            if text[b + len(SCOPE_MARK_BEGIN):e].strip() == descriptor:
                return text  # already current -> no write
            return text[:b] + block + text[e + len(SCOPE_MARK_END):]
    sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return text + sep + block + "\n"


def store_changed(memory_dir_path: _StrPath, since_mtime: float) -> bool:
    """True if a memory dir changed since `since_mtime` (a 'store changed under me' guard for the
    dream's read-modify-write; pair with the pre-flight backup)."""
    return _newest_mtime(Path(memory_dir_path)) > float(since_mtime)


# NOTE: there is deliberately NO usage/age/size "forgetting" mechanism. Usage cannot be measured (the
# note sits in context; the model reasons over it silently), and age/size are not valid forget metrics
# (see the "Removal" policy in skills/meta-dream-tree/references/dream-passes.md). Removal happens
# only via dedup, obsolete/superseded pruning (model-judged, propose-first), retiring a pointer whose
# rule a skill states at the only moment it can fire, or a manual request - the dream does that; no
# helper here.


def _model_review_file() -> Path:
    return claude_paths.audit_dir() / "model-review.txt"


def model_review_due(interval_days: float = 30, now: float | None = None) -> bool:
    """True if the periodic model-hierarchy review (run by meta-dream-tree) is due: no prior review, or the
    last one is older than `interval_days`. GLOBAL (not per-project) and OUT of any memory store, so it
    never bumps a store's mtime (convergence holds). Model releases are infrequent -> a monthly default."""
    import time as _time
    now = _time.time() if now is None else now
    try:
        last = float(_model_review_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return True
    return (now - last) >= interval_days * 86400


def mark_model_reviewed(now: float | None = None) -> float:
    """Record that the model-hierarchy review just ran, so it does not re-fire until due again."""
    import time as _time
    now = _time.time() if now is None else now
    f = _model_review_file()
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(str(now), encoding="utf-8")
    except OSError:
        pass
    return now


def _backup_reminder_file() -> Path:
    return claude_paths.audit_dir() / "offsite-backup-reminder.txt"


def backup_reminder_due(interval_days: float = 30, now: float | None = None) -> bool:
    """True if the periodic off-machine-backup reminder (run by meta-dream-tree) is due: no prior
    reminder, or the last one is older than `interval_days`. The curated memory stores are LOCAL git
    repos (durable against rm/reset) but NOT against disk failure - so from time to time the dream
    reminds the user they can push the store repo(s) to a PRIVATE remote. GLOBAL and OUT of any store
    (never bumps a store's mtime, so convergence holds). Monthly default."""
    import time as _time
    now = _time.time() if now is None else now
    try:
        last = float(_backup_reminder_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return True
    return (now - last) >= interval_days * 86400


def mark_backup_reminded(now: float | None = None) -> float:
    """Record that the off-machine-backup reminder just fired, so it does not re-fire until due again."""
    import time as _time
    now = _time.time() if now is None else now
    f = _backup_reminder_file()
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(str(now), encoding="utf-8")
    except OSError:
        pass
    return now


# --- Recall filler words (memory-recall keyword precision) ---------------------------------------
# Generic/conversational words must not become recall search keywords (they match half the store).
# THREE lists, split by who is universal vs a project-specific judgment (so one project's learned
# classification never suppresses another project's recall - see "Filler-word classification" in
# skills/meta-dream-tree/references/dream-passes.md):
#   - GLOBAL baseline blacklist: filler_words.json next to this module (generic English; grows via PRs).
#   - PER-PROJECT learned blacklist: filler the dream classified for THAT project.
#   - PER-PROJECT learned whitelist: topical/known-good words (so they are not re-queued).
# The per-prompt hook only USES these (deterministic, no model), keyed to the CURRENT project (the
# prompt's origin); GROWING them is a slow dream pass. See meta-dream-tree's "Filler-word classification".

def _filler_baseline_path() -> Path:
    return Path(__file__).resolve().parent / "filler_words.json"


def _filler_local_path(proj: _StrPath | None) -> Path:
    """PER-PROJECT learned filler blacklist (out-of-store, machine-local)."""
    return claude_paths.audit_dir() / (proj_key(proj) + ".filler.json")


def _topical_words_path(proj: _StrPath | None) -> Path:
    """PER-PROJECT learned topical whitelist - confirmed genuine topics, not re-queued for classification."""
    return claude_paths.audit_dir() / (proj_key(proj) + ".topical.json")


def _recall_pending_path(proj: _StrPath | None) -> Path:
    """PER-PROJECT queue of as-yet-unclassified recall keywords, drained by the dream classifier."""
    return claude_paths.audit_dir() / (proj_key(proj) + ".recall-unknown.txt")


def _read_word_json(path: _StrPath) -> list[str]:
    """Read a word-list JSON that may be a bare list or {"filler"/"words"/"topical": [...]}. Fail-open []."""
    try:
        data = _decode_json_file(path)
    except (OSError, ValueError):
        return []
    return _words_of(data, path)


def _words_of(data: object, source: _StrPath) -> list[str]:
    """The normalised words of a parsed word-list document (a bare list or a keyed object) read
    from `source`.

    A document of another shape - a keyed value or a whole document that is not a list - holds no
    words: reported on stderr naming `source`, never raised (the recall hook reads these lists
    per prompt), and never iterated as it stands (a string read per character gave one word per
    letter, a number raised TypeError). That is the answer the readers already give a file that
    is not JSON at all, and a read-modify-write then replaces it as it replaces one of those."""
    if data is None:                        # absent or not JSON (`_load_any_json_for_update`)
        words: list[object] = []
    elif _is_list(data):
        words = data
    elif _is_record(data):
        none: list[object] = []
        value = data.get("filler") or data.get("words") or data.get("topical") or none
        words = value if _is_list(value) else _not_a_word_list(source, value)
    else:
        words = _not_a_word_list(source, data)
    return [w.strip().lower() for w in words if isinstance(w, str) and w.strip()]


def _not_a_word_list(source: _StrPath, value: object) -> list[object]:
    """Report on stderr that `source` holds `value` where a list of words belongs; no words."""
    print("self_improve_signals: %s holds a JSON %s where a list of words belongs; read as no "
          "words" % (source, type(value).__name__), file=sys.stderr)
    return []


def _load_words_for_update(path: _StrPath) -> list[str]:
    """A learned word list for a read-modify-write: [] when absent or unparseable. Raises
    StateWriteError when the file exists but cannot be read - the fail-open reader's [] there made
    the write that followed replace every learned word with the new ones."""
    return _words_of(_load_any_json_for_update(path), path)


def _write_word_json(path: _StrPath, words: Iterable[str], key: str = "words") -> None:
    """Persist a learned word list. Raises StateWriteError when the write does not land.

    Raised, not swallowed: no hook writes these lists. The dream's filler pass does, and it clears
    the pending-keyword queue right after, so a write that failed in silence dropped the whole
    classification along with the queue it came from."""
    _write_text_state(path, json.dumps({key: sorted(set(words))}, indent=2) + "\n")


def load_filler_words(proj: _StrPath | None = None) -> frozenset[str]:
    """The effective filler blacklist for `proj`: GLOBAL baseline UNION the project's LEARNED filler.
    Baseline is universal generic-English filler; learned filler is per-project so one project's
    classification never suppresses another's recall. With proj=None, baseline only. Lowercased frozenset."""
    words = list(_read_word_json(_filler_baseline_path()))
    if proj is not None:
        words += _read_word_json(_filler_local_path(proj))
    return frozenset(words)


def add_filler_words(words: Iterable[str], proj: _StrPath | None) -> None:
    """Append classifier-confirmed filler to the PROJECT's learned blacklist (never the shipped baseline).
    Raises StateWriteError when the list cannot be read or written (see `_write_word_json`)."""
    new = {str(w).strip().lower() for w in words if str(w).strip()}
    if not new:
        return
    p = _filler_local_path(proj)
    _write_word_json(p, set(_load_words_for_update(p)) | new, key="filler")


def load_topical_words(proj: _StrPath | None) -> frozenset[str]:
    """The project's learned topical whitelist (genuine topics, not re-queued). Lowercased frozenset."""
    return frozenset(_read_word_json(_topical_words_path(proj)))


def remove_filler_words(words: Iterable[str], proj: _StrPath | None) -> list[str]:
    """Un-classify learned filler for `proj`. Returns the words actually removed, sorted.

    The classification is a JUDGEMENT over ambiguous words, so it is sometimes wrong, and a word
    left as filler is dropped from recall keywords forever. The return value is the point: only the
    project's LEARNED list can be edited, so a word that is filler because the shipped BASELINE says
    so comes back as not-removed rather than silently staying suppressed. Raises StateWriteError
    when the list cannot be read or written.
    """
    drop = {str(w).strip().lower() for w in words if str(w).strip()}
    if not drop:
        return []
    p = _filler_local_path(proj)
    current = set(_load_words_for_update(p))
    removed = current & drop
    if removed:
        _write_word_json(p, current - removed, key="filler")
    return sorted(removed)


def remove_topical_words(words: Iterable[str], proj: _StrPath | None) -> list[str]:
    """Un-classify learned topical words for `proj`. Returns the words actually removed, sorted.
    Raises StateWriteError when the list cannot be read or written."""
    drop = {str(w).strip().lower() for w in words if str(w).strip()}
    if not drop:
        return []
    p = _topical_words_path(proj)
    current = set(_load_words_for_update(p))
    removed = current & drop
    if removed:
        _write_word_json(p, current - removed, key="topical")
    return sorted(removed)


def add_topical_words(words: Iterable[str], proj: _StrPath | None) -> None:
    """Record classifier-confirmed topical words for THIS project so they are not re-queued.

    Calling this on a word currently classified as learned filler RECLASSIFIES it: the word is
    removed from the filler list as well. Recording it in both lists would leave it suppressed,
    because the union of the two is consulted only to decide whether to re-QUEUE a word, never to
    decide whether to DROP one - so the topical entry would have no effect a reader could see.
    Raises StateWriteError when either list cannot be read or written.
    """
    new = {str(w).strip().lower() for w in words if str(w).strip()}
    if not new:
        return
    p = _topical_words_path(proj)
    _write_word_json(p, set(_load_words_for_update(p)) | new, key="topical")
    remove_filler_words(new, proj)


# Leaked identifiers - a tool-use ID (`toolu_...`) or a long hex agent/session ID - ride into prompt
# text (e.g. inside a <task-notification>), so the recall tokenizer would queue them as "keywords".
# They are junk that pollutes the dream's filler-classification pass; drop them at the queue chokepoint.
_LEAKED_ID_RX = re.compile(r"^(?:toolu_[0-9a-z]+|[0-9a-f]{16,})$")
_SHAPE_JUNK_ALLOWLIST = frozenset({"ed25519"})
_UUID_RX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_DATE_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TASK_ID_RX = re.compile(r"^b[0-9a-z]{8}$")
_HEXFRAG_RX = re.compile(r"^[0-9a-f]{6,15}$")
_PURE_DIGITS_RX = re.compile(r"^\d+$")
_NUM_UNIT_RX = re.compile(
    r"^\d+(?:gb|mb|kb|tb|pb|ghz|mhz|khz|hz|ms|ns|us|sec|secs|min|mins|hrs|hr|px|pt|em|rem|"
    r"cm|mm|km|kg|lb|lbs|ft|yr|yrs|mo|wk|pct|deg|k|m|s|x)$"
)


def _is_shape_junk(tok: str) -> bool:
    """True for a machine-token shape that is never a real recall search term.

    A Claude Code background task id (the `task_id` field, shaped `b` plus 8 base36 chars), a hex
    fragment, an ISO date, a uuid and a digit+unit size all ride into prompt text and would
    otherwise be queued for the dream to classify one project at a time, which cannot keep up.
    Checked structurally rather than against a dictionary, so a real term can collide with a junk
    shape - `ed25519` is seven valid hex characters. Add a confirmed collision to the allowlist
    rather than loosening a regex; requiring a digit in the hex-fragment shape already excludes the
    all-hex-letter English words (facade, decade, deadbeef) at no cost to the drop count."""
    if tok in _SHAPE_JUNK_ALLOWLIST:
        return False
    if _LEAKED_ID_RX.match(tok):
        return True
    if _UUID_RX.match(tok) or _DATE_RX.match(tok) or _PURE_DIGITS_RX.match(tok):
        return True
    if _NUM_UNIT_RX.match(tok):
        return True
    if _TASK_ID_RX.match(tok) and any(c.isdigit() for c in tok) and any(c.isalpha() for c in tok[1:]):
        return True
    return bool(_HEXFRAG_RX.match(tok) and any(c.isdigit() for c in tok))


def note_unknown_keywords(words: Iterable[str], proj: _StrPath | None) -> None:
    """Per-prompt: queue this project's recall keywords that are NEITHER known filler NOR known-topical,
    for the dream classifier to judge. Deterministic, append-only, deduped; never calls a model.
    Leaked tool-use / hex identifiers are dropped (they are not real recall terms)."""
    known = load_filler_words(proj) | load_topical_words(proj)
    cur = load_pending_keywords(proj)
    lowered = {str(w).strip().lower() for w in words if str(w).strip()}
    add = {w for w in lowered if not _is_shape_junk(w)} - known - cur
    if not add:
        return
    f = _recall_pending_path(proj)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a", encoding="utf-8") as fh:
            for w in sorted(add):
                fh.write(w + "\n")
    except OSError:
        pass


def load_pending_keywords(proj: _StrPath | None) -> frozenset[str]:
    """The project's queued-but-unclassified recall keywords (for the dream classifier)."""
    try:
        lines = _recall_pending_path(proj).read_text(encoding="utf-8").splitlines()
    except OSError:
        return frozenset()
    return frozenset(w for w in (tok.strip().lower() for tok in lines) if w and not _is_shape_junk(w))


def clear_pending_keywords(proj: _StrPath | None) -> None:
    """Drain THIS project's queue after the dream classifier has processed it."""
    try:
        _recall_pending_path(proj).unlink()
    except OSError:
        pass


def knowledge_store_empty(proj: _StrPath | None = None) -> bool:
    """True if there is nothing to seed a new project FROM. PER-TREE for the curated tier: only
    `proj`'s OWN tree top is consulted (an unrelated tree's facts are not this tree's seed corpus).
    The NATIVE tier scan stays MACHINE-GLOBAL by design - native memories are per-machine raw notes
    and a legitimate seed source across trees. Used to suppress the new-project bootstrap nudge."""
    try:
        if _curated_fact_parts(str(topmost_claude_md_dir(proj) or (proj or os.getcwd()))):
            return False
    except OSError:
        pass
    try:
        for memdir in (claude_paths.config_dir() / "projects").glob("*/memory"):
            for p in memdir.glob("*.md"):
                if p.name != "MEMORY.md":
                    return False
    except OSError:
        pass
    if proj is not None and _curated_fact_parts(proj):
        return False
    return True


# ---- STRICT patterns (the gate fires on these; tuned for precision) -----------------

# USER correction / explicit remember.
USER_PATTERN = re.compile(
    r"no,|nope|that.?s wrong|that is wrong|incorrect|don.?t do|do not do|stop doing"
    r"|you (forgot|missed|should have|shouldn.?t)|not what i|instead of|rather than"
    r"|that.?s not right|isn.?t right"
    r"|remember|note that|keep in mind|for next time|for the future|from now on"
    r"|make a (memory|rule|note)"
    r"|falsch|nein,|stattdessen|anstatt|anstelle|merke? dir|in zukunft|denk dran",
    re.IGNORECASE,
)

# ASSISTANT self-admitted miss (incl. a guard/hook blocking the assistant's own action).
ASST_PATTERN = re.compile(
    r"you(?:'?re| are| were) (?:right|correct)|my mistake|i was wrong|apolog"
    r"|\bmisdiagnos\w+|\bmy\b[^.\n]{0,40}\bwas (?:an? )?(?:misread|mistake|error|wrong|misjudged)\b"
    r"|\bi should(?: have|'?ve)\b|\bi (missed|overlooked|forgot|misread|misunderstood)\b"
    r"|\bi did(?:n'?t| not) (realize|notice|account|consider|catch)\b|\bin hindsight\b"
    r"|\b(from now on|going forward|next time)\b[^.\n]{0,20}\bi('?ll| will| should)\b"
    r"|\bi('?ll| will) (make sure|remember) (to|not)\b"
    r"|\b(hook|guard|gate)\b[^.\n]{0,30}\b(caught|blocked|stopped|flagged|rejected)\b"
    # Verb-first order needs the actor named with "by": "blocked ON a guard" is waiting FOR it,
    # and a backlog item whose SUBJECT is a guard otherwise fires the live gate on every summary.
    r"|\b(caught|blocked|stopped|flagged|rejected)\b[^.\n]{0,20}\bby\b[^.\n]{0,20}\b(hook|guard|gate)\b"
    r"|self.?match(ed|ing|es)?",
    re.IGNORECASE,
)

# ASSISTANT realization/discovery (how something really fits together).
REALIZATION_PATTERN = re.compile(
    r"now i (understand|see|realize|get it)\b"
    r"|i (now|finally) (understand|see|realize)\b"
    r"|i(.?ve| have)? figured (it |this )?out|i figured out\b"
    r"|(?<!not )(?<!n't )\bfound it\b"
    r"|\bfound (the|a|its) (bug|cause|culprit|problem|issue|leak|regression|reason|root cause)\b"
    r"|\bfound out (that|why|how|where)\b|\bthe culprit (is|was)\b"
    r"|the (real|actual) (topolog|architect|structure|setup|layout|wiring|flow|picture|story|design)"
    r"|it turns out\b|turns out (that|the)\b"
    r"|(that|this) explains (the|why|how|what)\b"
    # Require a discovery predicate right after the noun phrase (colon-free window) so a genuine
    # realization ("the real cause IS/WAS/turned out ...") fires, but a retrospective fix-REPORT
    # LABEL ("The real cause: ...") does not trip the live Stop block. The colon-excluding window is
    # what distinguishes an asserted realization from a heading/label of already-shipped work.
    r"|the (key|real|actual) (insight|issue|problem|cause|reason)\b"
    r"(?=[^.\n:]{0,15}\b(?:is|was|were|turned out|ended up|lies|stems)\b)|root cause is\b"
    r"|(actually|really) (runs|lives|sits|resides|is hosted|happens|is served) on\b"
    r"|clear(er)? picture|the (full|whole|complete|bigger) picture"
    r"|\b(now|it all|everything|it)('?s| is| are)? (clear|much clearer)\b"
    r"|\bmakes sense now\b|\bnow [^.\n]{0,20}makes sense\b"
    r"|jetzt (verstehe ich|wird klar|ergibt)|jetzt ist (alles |es )?klar|klares bild"
    r"|stellt sich heraus|herausgefunden"
    r"|\b(fehler|ursache|problem|grund|bug) gefunden\b|\bda (ist|war) (es|der fehler|das problem)\b",
    re.IGNORECASE,
)

# ENDORSEMENT of a good idea, from EITHER side (assistant judging the user's suggestion
# good -> adopt it; or the user endorsing the assistant's proposal -> confirmed approach).
ENDORSE_PATTERN = re.compile(
    r"(good|great|nice|smart|clever|brilliant|excellent) (idea|call|point|catch|thinking|suggestion)"
    r"|i like (that|this|your) (idea|approach|plan|suggestion)|let.?s do (that|it)"
    r"|gute idee|guter (punkt|einfall)|gut(er)? gedacht",
    re.IGNORECASE,
)

# ---- BROAD recall patterns (audit-only: catch likely MISSES the strict set skips) ----
# Deliberately wider and learning-flavoured. A turn that matches BROAD but not STRICT is a
# CANDIDATE MISS for review, never a live block. Tuned to stay off bare acknowledgements.

BROAD_USER_PATTERN = re.compile(
    r"\b(wrong|incorrect|broken|fails?|failing|not working|doesn.?t work|didn.?t work)\b"
    r"|\bwhy (did|are|is|do|does) (you|it|that|this)\b"
    r"|\byou (always|keep|still|again|never)\b"
    r"|\bi (told|asked) you\b|\bas i (said|mentioned|asked)\b"
    r"|\bnot (quite|what i|right|correct)\b|\b(revert|undo|rollback)\b"
    r"|\b(perfect|exactly right|spot on|love it|that.?s it|works now)\b"
    # A request to RE-CHECK and correct challenges a claim just made ("check, correct if
    # neccessary, and push" found a real exec-bit loss in "harmless churn"). Needs both halves:
    # check/verify alone, or fix/correct alone, is an ordinary instruction.
    r"|\b(?:check|verify|review|double.?check)(?: it| this| that)?,?\s+(?:and\s+)?(?:correct|fix)\b"
    r"|\b(?:correct|fix)(?: it| this| that)? if (?:nec+es+ary|needed|required)\b"
    r"|\b(?:prüf|überprüf|kontrollier)\w* und (?:korrigier|berichtig)\w*"
    r"|\b(?:korrigier|berichtig)\w* (?:falls|wenn|soweit) nötig\b"
    # NEUTRAL PREFERENCE: an imperative that sets a durable convention with no correction
    # wording at all ("use httpx2 here", "put it in the application layer"). The strict set
    # keys on correction/remember phrasing, so it never sees these - they are pure audit.
    r"|\b(always|never) (use|name|put|keep|call|write|run|prefer)\b"
    r"|\buse \w+[\w.-]* (here|instead|for|in|not)\b"
    r"|\bput (it|them|that|those) in\b"
    r"|\bwe (use|prefer|keep|call|always|never)\b"
    r"|\bprefer\w*\b[^.\n]{0,40}\b(over|instead of|rather than)\b"
    r"|\b(verwende|nutze|nimm)\b|\bimmer (nutzen|verwenden)\b",
    re.IGNORECASE,
)

BROAD_ASST_PATTERN = re.compile(
    r"\bi (missed|overlooked|forgot|misread|misunderstood|didn.?t (realize|notice|account))\b"
    r"|you(?:'?re| are| were) (?:right|correct)|\bmisdiagnos\w+|\bwas (?:an? )?(?:misread|mistake)\b"
    r"|\bi should (have|.?ve) \w+|\bon reflection\b|\blet me reconsider\b"
    r"|\bgood (point|catch)\b"
    r"|\bthe (issue|problem|bug|root cause|reason) (is|was|turned out|ended up)\b"
    r"|\b(in hindsight|as it turns out)\b"
    r"|\bi see (why|how|what|now|the)\b"
    r"|\bfound (it|the|out)\b|\bthe culprit\b|\bgefunden\b"
    r"|\blet me (stop|inspect|double.?check|re.?check|look (again|closer)|take a closer look)\b"
    r"|\bper the .{1,80}? rule\b|\bthe \".{1,80}?\" rule\b|\bfollowing the .{1,60}? (rule|convention)\b"
    r"|\b(ah|oh|oops|whoops)[, ]"
    # Only a SELF-CORRECTING wait ("wait, that's the main transcript") is a signal. A bare
    # `wait[, ]` also matched ordinary narration ("wait for the agent"), which made 6 of 13
    # candidates noise in one real session - the audit is only read if it stays scannable.
    r"|\bwait\b[\s,.!\-]*(?:that|this|no\b|why\b|i\b|hold on)",
    re.IGNORECASE,
)


# Text the assistant QUOTES rather than says: a fenced code block, an inline code span, and a
# single-line span in double, curly or single quotes. A report citing another turn's "that was
# my mistake" is data about that turn, not an admission in this one. A single quote opens only
# after a non-word character and closes only before one, so the apostrophes of "you're" and
# "users'" never pair up into a span. Spans are bounded so an unclosed quote cannot swallow a
# whole reply.
_QUOTED_SPANS = re.compile(
    r"(?ms)^[ \t]*(```|~~~).*?^[ \t]*\1[^\n]*$"
    r"|`[^`\n]{1,400}`"
    r"|\"[^\"\n]{1,400}\""
    r"|\u201c[^\u201c\u201d\n]{1,400}\u201d"
    r"|(?<![\w'])'[^'\n]{1,400}'(?![\w'])")


def unquoted(text: str | None) -> str:
    """`text` with every quoted span (see _QUOTED_SPANS) blanked to spaces, offsets preserved.

    For the ASSISTANT side of the Stop gate: a self-admission the assistant quotes as data is
    not one it makes. Same length as the input, so an offset into the result is an offset into
    `text`."""
    return _QUOTED_SPANS.sub(lambda m: " " * len(m.group(0)), text or "")


def strict_user_hit(text: str) -> bool:
    """A strict learning signal in a USER message (correction/remember/endorsement)."""
    return bool(USER_PATTERN.search(text) or ENDORSE_PATTERN.search(text))


def strict_asst_hit(text: str) -> bool:
    """A strict learning signal in an ASSISTANT message (admission/realization/endorsement)."""
    return bool(ASST_PATTERN.search(text) or REALIZATION_PATTERN.search(text)
                or ENDORSE_PATTERN.search(text))


def broad_matches(role: str, text: str | None) -> list[str]:
    """Lower-cased, de-duplicated broad-recall matches for a message; [] if none.

    role is "user" or "assistant"; selects the matching broad pattern.
    """
    rx = BROAD_USER_PATTERN if role == "user" else BROAD_ASST_PATTERN
    return sorted({m.group(0).strip().lower() for m in rx.finditer(text or "")})


def asst_signal_offset(text: str | None) -> int | None:
    """Offset in `text` of the EARLIEST assistant learning signal, strict or broad; None if none.

    The same four patterns `strict_asst_hit` and `broad_matches("assistant", ...)` consult, so a
    message those two call a hit always has an offset here. It tells a producer WHERE the learning
    sits, for `inert_snippet(..., around=)`: offsets are into `text` exactly as passed, so pass the
    whitespace-collapsed form when the offset is meant for `inert_snippet`.
    """
    starts = [m.start() for rx in (ASST_PATTERN, REALIZATION_PATTERN, ENDORSE_PATTERN, BROAD_ASST_PATTERN)
              for m in (rx.search(text or ""),) if m]
    return min(starts) if starts else None


def collapsed_offset(text: str | None, offset: int | None) -> int | None:
    """`offset` into `text`, carried over to `" ".join(text.split())`; None stays None.

    Quoted spans are blanked on the RAW text, because a fenced block is only recognisable while
    its newlines are still there, but `inert_snippet` windows the whitespace-collapsed form. This
    maps a signal found in the first onto the second.

    Examples:
        >>> collapsed_offset("a  \\n b", 5)
        2
        >>> collapsed_offset("  b", 2)
        0
        >>> collapsed_offset("x", None) is None
        True
    """
    if offset is None:
        return None
    prefix = (text or "")[:offset]
    kept = len(" ".join(prefix.split()))
    return kept + 1 if kept and prefix[-1].isspace() else kept


def asst_said_offset(text: str | None) -> int | None:
    """Offset in `" ".join(text.split())` of the earliest assistant signal OUTSIDE quoted spans,
    else of the earliest one anywhere; None if there is none.

    The windowing counterpart of matching strict patterns on `unquoted(text)`: a quoted admission
    ahead of the reply's own learning must not take the snippet window from it. The fallback keeps
    a message whose only match sits in a quote (a broad `the "X" rule`) windowed on that match
    rather than on its head.

    Examples:
        >>> t = 'He wrote "my mistake". ' + 'x ' * 5 + 'I was wrong.'
        >>> t[asst_said_offset(t):]
        'I was wrong.'
        >>> asst_said_offset('see "my mistake" here')
        5
    """
    found = asst_signal_offset(unquoted(text))
    if found is None:
        found = asst_signal_offset(text or "")
    return collapsed_offset(text, found)


def user_signal_offset(text: str | None) -> int | None:
    """Offset in `text` of the EARLIEST user learning signal, strict or broad; None if none.

    The user-role counterpart of `asst_signal_offset`: the patterns `strict_user_hit` and
    `broad_matches("user", ...)` consult, with the same offset convention."""
    starts = [m.start() for rx in (USER_PATTERN, ENDORSE_PATTERN, BROAD_USER_PATTERN)
              for m in (rx.search(text or ""),) if m]
    return min(starts) if starts else None


# ---- TOOL signals (audit-only): a learning that never reached prose -------------------------
# The prose scan structurally cannot see these: the whole discovery lives in a tool_use command
# or a tool_result ("unrecognized arguments: --rehome-to" is how a real tooling gap announced
# itself). Keyed on HARD tool-level failures - a wrong flag, a missing binary, a refused auth -
# because those are the ones that change how the tool must be driven next time.

TOOL_SIGNAL_PATTERN = re.compile(
    r"\bcommand not found\b|\bunrecognized (?:arguments?|option)\b"
    r"|\bunknown (?:option|flag|argument|command)\b|\binvalid (?:option|flag|choice)\b"
    r"|\bno such (?:file or directory|option|command)\b"
    r"|\bpermission denied\b|\bnot a git repository\b|\bextra not found\b"
    # Lookaheads, not consuming matches: `error:\s*\S` would eat the first letter of the very
    # phrase that names the gap, so "error: unrecognized arguments" reported only "error: u".
    r"|\bfatal:(?=\s*\S)|\berror:(?=\s*\S)",
    re.IGNORECASE,
)


def tool_matches(text: str | None) -> list[str]:
    """Lower-cased, de-duplicated TOOL-signal matches for tool output/commands; [] if none."""
    return sorted({m.group(0).strip().lower() for m in TOOL_SIGNAL_PATTERN.finditer(text or "")})


# The tool branch of the audit has NO strict gate - every TOOL_SIGNAL_PATTERN hit is a miss. That
# floods the audit when the SESSION'S OWN WORK is signal-detection code: reading a test_*.py or a
# RED pytest tail puts those very phrases into tool text as literal DATA, not a live failure. So
# test data is discounted, by REGION rather than by whole block or whole line - the two coarser
# rules are wrong in opposite directions. Discarding a block that holds one pytest summary throws
# away the NEXT command's genuine error; keeping every line that does not itself name a test file
# keeps the phrases that file's own diff hunk or heredoc body writes.
#
# A pytest run is data from its first marker until a TIMED summary ("12 passed in 0.40s"), which is
# what ends a run: requiring the timing suffix is what stops another tool's own count closing it.
# Replayed over the 250 most recent transcripts, a bare count as the closer let a pyright run's 832
# per-line "error:" lines through, and a bare count as an OPENER is the defect this half fixes -
# "Found 2 errors." from a type checker used to switch off the argparse error on the line after it.
_ANSI = r"(?:\x1b\[[0-9;]*m)*"
_RUN_OPENS = re.compile(
    r"(?<!=)=+ (?:FAILURES|ERRORS|test session starts|short test summary)"
    r"|\bcollected \d+ item"
    r"|::test_\w+"                                                    # a pytest node id
    r"|(?<!-)-{2,} (?:RED|GREEN) -{2,}"                                     # the repo's own TDD-cycle markers
    # The tail's own shapes, which arrive without the banner when only the tail was captured: a
    # summary-list line and pytest's exception detail. Both were read as live tool output.
    r"|^" + _ANSI + r"(?:FAILED|ERROR)" + _ANSI + r"\s+\S+\.py"
    r"|^" + _ANSI + r"E\s{2,}",
    re.IGNORECASE | re.MULTILINE,
)
_RUN_CLOSES = re.compile(
    r"\b(?:\d+ (?:passed|failed|xfailed|xpassed|deselected|errors?)|no tests ran)\b.*?"
    r"\bin \d+(?:\.\d+)?\s*s\b",
    re.IGNORECASE,
)
# A diff's file header: every line until the next header belongs to the file this one names.
_DIFF_FILE_HEADER = re.compile(r"^\s*(?:diff --git \S+ |--- |\+\+\+ )(\S+)")
# ANY heredoc body, not only one whose opener names a test file: the body is literal text being
# WRITTEN, never a tool's report, and the file it lands in is often built inside the body rather
# than named on the opener line (`python3 - <<'PY'` writing three test files).
#
# The delimiter must END the line, give or take a trailing redirection, and an UNQUOTED one must
# abut the `<<`. Both halves are about the shift operator: `<<` unanchored matches `cout << x`, and
# since a body runs to its delimiter, one such line in a source listing swallows every line after
# it. `a << b` is exactly the shape a loose rule reads as a heredoc named b; `cat <<EOF` is not.
# The lookarounds exclude the here-string `<<<word`, which feeds one word on stdin and has no body.
_HEREDOC_OPENS = re.compile(
    r"(?<!<)<<(?!<)-?(?:\s*(?P<q>[\"'])(?P<quoted>\w+)(?P=q)|(?P<bare>\w+))\s*(?:[<>|&]\S*\s*\S*)?$")
_TEST_FILE_TOKEN = re.compile(r"\btest_\w*\.py\b", re.IGNORECASE)
# A line that BEGINS with a test file's path is a grep hit or a listing, so what follows is that
# file's content. A line that merely NAMES one ("fatal: pathspec 'tests/test_x.py' did not match")
# is an error ABOUT the file and is exactly the kind of gap the audit exists to surface.
_TEST_FILE_LINE = re.compile(r"^\s*[\w./\\-]*\btest_\w*\.py\b", re.IGNORECASE)
# A numbered listing line is a file being READ, and a file's content is not a tool's report. No
# tool announces a failure in this shape, so discounting it cannot hide one.
_NUMBERED_LISTING = re.compile(r"^\s*\d+\t")
# A refusal a hook issues ON PURPOSE every time, so it is the design working, never a gap: the
# premise check refuses the first ask of each AskUserQuestion, and its text arrives as a
# `hook error:` tool result. Keyed on the fixed phrase (missing-mechanism-nudge QUESTION_REFUSAL).
_DESIGNED_REFUSAL = re.compile(
    r"QUESTION PREMISES, checked BEFORE the user sees this question")


class _FixtureScan:
    """Walks one tool block line by line, deciding which lines sit inside test data."""

    def __init__(self) -> None:
        self.in_run = False
        self.in_test_diff = False
        self.heredoc_end: str | None = None

    def is_data(self, line: str) -> bool:
        """True when this line is test data rather than live tool output.

        Ordered and deliberately short-circuiting: a heredoc body and a diff hunk are verbatim
        content, so a pytest marker quoted inside one must not open a run that outlives it.
        """
        return (self._in_heredoc(line) or self._in_test_diff(line) or self._in_run(line)
                or bool(_TEST_FILE_LINE.match(line)) or bool(_NUMBERED_LISTING.match(line))
                or bool(_DESIGNED_REFUSAL.search(line)))

    def _in_heredoc(self, line: str) -> bool:
        """A heredoc body, which is written text rather than a report; ends at the delimiter."""
        if self.heredoc_end is not None:
            if line.strip() == self.heredoc_end:
                self.heredoc_end = None
            return True
        opener = _HEREDOC_OPENS.search(line)
        if opener is None:
            return False
        self.heredoc_end = opener.group("quoted") or opener.group("bare")
        return True

    def _in_test_diff(self, line: str) -> bool:
        """A diff section whose file header names a test file."""
        header = _DIFF_FILE_HEADER.match(line)
        if header is not None:
            self.in_test_diff = bool(_TEST_FILE_TOKEN.search(header.group(1)))
        return self.in_test_diff

    def _in_run(self, line: str) -> bool:
        """A pytest run, from its first marker up to and including its summary line."""
        if _RUN_CLOSES.search(line):
            self.in_run = False
            return True
        if _RUN_OPENS.search(line):
            self.in_run = True
        return self.in_run


def tool_matches_outside_fixtures(block: str | None) -> list[str]:
    """TOOL-signal matches in ONE tool block, discounting only what is test data.

    Judge one block at a time: a message carries several (parallel tool calls), and judging their
    joined text let a single test-file name anywhere switch off every signal in the message.
    """
    scan = _FixtureScan()
    live = [line for line in (block or "").splitlines() if not scan.is_data(line)]
    return tool_matches("\n".join(live))


def tool_signal_offset(block: str | None) -> int | None:
    """Offset of the first TOOL signal `tool_matches_outside_fixtures` counts in `block`, as an
    offset into the WHITESPACE-COLLAPSED block (what `inert_snippet` quotes); None if none.

    The same line-by-line fixture discount, so a test-data line that names the phrase first is
    skipped and the offset lands on the live line that made the block a candidate."""
    scan = _FixtureScan()
    lines = (block or "").splitlines()
    for i, line in enumerate(lines):
        if scan.is_data(line):
            continue
        m = TOOL_SIGNAL_PATTERN.search(line)
        if m:
            # Collapsing the text up to and including the match's first character puts that
            # character last, so its index in the collapsed whole is that length minus one.
            prefix = "\n".join(lines[:i] + [line[:m.start() + 1]])
            return len(" ".join(prefix.split())) - 1
    return None


# Invoking a skill (the Skill tool, or a /slash-command) injects the WHOLE SKILL.md as a
# transcript message of type "user" - so the prose scan reads shipped documentation as if the
# user had typed it. A skill that merely CONTAINS "always run" or "wrong" then reports itself
# as a missed learning signal, every session, forever. Measured over 12 transcripts of one
# project: 9 injected bodies, 2 of them producing candidate misses.
#
# Anchored at the START only. A user QUOTING the marker inside a real correction must still be
# scanned, so a substring search here would suppress the very signal the audit exists to catch.
_SKILL_BODY_MARKER = "base directory for this skill:"


def is_injected_skill_body(text: str | None) -> bool:
    """True when a "user" message is really an injected SKILL.md, not something the user wrote."""
    return (text or "").lstrip().lower().startswith(_SKILL_BODY_MARKER)


def skills_invoked(transcript_text: str | None) -> dict[str, int]:
    """{skill_name: count} for every Skill tool call in a raw transcript.

    The skill-gap correlation (a bug that shipped DESPITE a skill) needs to know which skills
    actually ran. The model's in-context recall is not that data - by the time a dream asks, the
    early invocations have scrolled out. Parsed from the transcript, so no extra hook and no
    probe of tool-event shape is required. A caller holding an open transcript file passes it to
    `skill_usage` instead, which streams it.
    """
    return dict(skill_usage((transcript_text or "").splitlines()).invoked)


class SkillUsage(NamedTuple):
    """What one pass over a transcript learned about its Skill tool calls.

    `invoked` counts every call by its full name, a subagent's included; `loaded_since_compaction`
    holds the bare names (no `bitranox:` prefix) of the main agent's calls after the last
    compaction boundary, whose bodies are still whole in context."""

    invoked: Mapping[str, int]
    loaded_since_compaction: frozenset[str]


def skill_usage(lines: Iterable[str]) -> SkillUsage:
    """Both Skill-call views of a transcript, from ONE pass over `lines`.

    `lines` is any iterable of raw transcript lines; an open file streams it, so only the current
    line, the name tally and the name set are held and memory does not grow with the transcript.
    Unparsable lines are skipped, as a transcript being written can end mid-record.
    """
    tally: dict[str, int] = {}
    loaded: set[str] = set()
    for obj in _json_records(lines):
        names = _skill_calls(obj)
        for name in names:
            tally[name] = tally.get(name, 0) + 1
        if not _is_record(obj) or obj.get("isSidechain") is True:
            continue
        if obj.get("type") == "system" and obj.get("subtype") == "compact_boundary":
            loaded.clear()
            continue
        loaded.update(name.rsplit(":", 1)[-1] for name in names)
    return SkillUsage(MappingProxyType(tally), frozenset(loaded))


def _json_records(lines: Iterable[str]) -> Iterator[object]:
    """Each non-blank line of `lines` that parses as JSON, decoded; the rest are skipped."""
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except ValueError:
            continue


def _skill_calls(obj: object) -> list[str]:
    """The skill names an assistant transcript record invokes through the Skill tool, in order.

    A record that is not a JSON object (a stray array or number line) names none, rather than
    raising out of the caller's loop."""
    if not _is_record(obj) or obj.get("type") != "assistant":
        return []
    message = obj.get("message")
    content = message.get("content") if _is_record(message) else None
    if not _is_list(content):
        return []
    names: list[str] = []
    for b in content:
        if not _is_record(b) or b.get("type") != "tool_use" or b.get("name") != "Skill":
            continue
        args = b.get("input")
        name = args.get("skill") if _is_record(args) else None
        if isinstance(name, str) and name:
            names.append(name)
    return names


def skills_loaded_since_compaction(lines: Iterable[str]) -> frozenset[str]:
    """Bare names of the skills invoked after the transcript's LAST compaction boundary.

    A skill invoked since the last compaction still has its whole body in the model's context, so
    a block telling it to invoke that skill again only reloads the same text (a long SKILL.md, on
    every block). One invoked BEFORE the boundary is different: the compaction summary keeps at
    most a truncated copy of its body, so re-invoking it is the right advice there.

    `lines` is any iterable of raw transcript lines (an open file streams it), and only the set of
    names is held, so memory does not grow with the transcript. A `bitranox:` prefix is dropped,
    because callers ask by the bare name. A sidechain record is a subagent's call, which loads
    nothing into this context.
    """
    return skill_usage(lines).loaded_since_compaction
