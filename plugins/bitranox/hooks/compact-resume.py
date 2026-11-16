#!/usr/bin/env python3
"""SessionStart hook: after a compaction, put the saved checkpoint back in front of the model.

The context watcher asks the session to save a checkpoint (`handover.md` plus
`OPEN-WORK.md`) shortly before the harness auto-compacts, and the session then keeps working. The
compaction summary keeps the gist and loses the working detail, so this hook re-injects the
checkpoint the session wrote, and the work resumes from saved state rather than from the summary.

WHY SessionStart. It is the one compaction-time event whose output reaches the model: PreCompact can
block but not inject, and PostCompact's output fields are discarded. A scripted probe on CLI 2.1.310
confirmed both halves this hook rests on: after an automatic compaction the SAME turn continues (tool
calls follow the boundary under the original prompt id, five times in a row), and a SessionStart
`additionalContext` emitted on source "compact" is present in the very next API request.

WHICH checkpoint counts. Only a `handover.md` written AFTER this session's latest save request
(`sig.checkpoint_asked_at`) and not yet marked STALE. An older file describes an earlier moment, and
feeding it in as current is worse than feeding nothing; another session's request does not vouch for
this one, because the request flag is session-keyed. With no qualifying checkpoint the hook says so
and points at the transcript on disk, which compaction never shortens.

WHERE it looks. The git top level of the cwd at compaction, every `handover.md` this session
wrote with Write/Edit (the session-keyed touched-paths record), and every one the session's
transcript shows it writing. The cwd alone is not enough: it is wherever the last `cd` left the
session, so a checkpoint written in a linked worktree while the cwd sat in the main checkout, or at
a parent while the cwd had drifted into a nested repo, was reported as "no checkpoint" (measured: 23
of 106 checkpoints written after the request, across real transcripts).

WHOSE it is. A candidate is handed back as this session's only when the session's own records show
it wrote that file as it now stands: a successful Write/Edit/MultiEdit of the path in the session's
transcript at or after the request, with the file unchanged since (mtime at most _WRITE_SLACK past
that tool result). Without a readable transcript the touched-paths record stands in, which cannot
see a later overwrite. Neither the cwd nor the newest mtime decides: several sessions share one
main checkout and its linked worktrees, each writing its own handover.md, so the cwd's copy and the
newest file can both be a peer's, and a linked worktree's tracked copy is as new as the checkout
that wrote it (measured 2026-11-16: the cwd's tracked copy in a worktree, an older moment, came back
as the session's checkpoint while the real one sat uncommitted in the main checkout). A qualifying
file no record attributes (a peer's, or one this session wrote through Bash) is listed with its path
and age, and the reader is told it is not known to be theirs and not to edit it. A subagent's own
transcript is not read: a checkpoint a subagent wrote is that subagent's, not this session's.

WHICH NAMES. `handover.md`, and a touched file whose name ENDS in `-handover.md` that carries the
line `## Lessons for the next nap` (the heading the meta-context-watcher skill requires in every
checkpoint). Sessions with a worktree outside any repo improvise names such as
`~/wt-vmxnet3-handover.md` (43 writes of three such names across 5497 transcripts, 2026-11-08), and
an exact-name rule never hands those back. The heading keeps out other files that share the suffix:
the one such file in that corpus was a skill checklist without it. `handover.prev.md`, the backup of
an earlier checkpoint, does not end in `-handover.md` and so never counts, heading or not.

WHY its own hook rather than a branch of session-start.py: that hook's essentials are held under a
small byte ceiling so they always land inline, and a checkpoint can be several KB. The harness inlines
an additionalContext up to 10,000 characters and replaces anything larger with a 2,000-character
preview, so the checkpoint is cut to fit below that, naming the file for the rest.

Pure standard library, ASCII only. Every failure path prints nothing and exits 0.
"""

import datetime
import json
import os
import sys
import time
from pathlib import Path

import open_work
import self_improve_signals as sig

#: Below the harness's 10,000-character inline limit, with room for the framing around the body.
MAX_CONTEXT_CHARS = 9000
_STALE_PREFIX = "# STALE"
_CHECKPOINT_NAME = "handover.md"
_IMPROVISED_SUFFIX = "-handover.md"
#: A file with an improvised name counts only when one of its lines is exactly this heading.
_CHECKPOINT_HEADING = "## Lessons for the next nap"
#: The tools whose transcript record attributes a written file to this session.
_WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit"})
#: Seconds a file's mtime may trail the session's own tool result for it before the file counts as
#: changed by something else since. The tool writes the file before its result is recorded, so the
#: margin only absorbs clock rounding.
_WRITE_SLACK = 2.0
#: Unattributed candidates named in the block, newest first.
_MAX_LISTED = 5

_RESUME = (
    "<BITRANOX-COMPACT-RESUME>\n"
    "The conversation was just auto-compacted. Before it, this session saved a checkpoint at "
    "%(path)s - resume the work from it; do not ask the user whether to continue. First check its "
    "next action against the compaction summary and `git log` / `git status`: when that action is "
    "already done, continue from the summary's step instead, and when the checkpoint names work the "
    "summary never mentions, it is another session's - leave it alone and continue from the summary. "
    "Otherwise take its exact next action. Once you have absorbed your own checkpoint, replace its "
    "first line with "
    "`# STALE - read %(today)s, work continued` (a working-tree edit; do not commit just for it), "
    "so a later compaction does not feed this moment back in as current. OPEN-WORK.md is the "
    "standing backlog behind it.%(cut)s\n\n"
    "%(body)s\n"
    "</BITRANOX-COMPACT-RESUME>"
)
_CUT = (" The checkpoint is longer than fits here; it is cut below - Read %(path)s for the rest "
        "before acting on anything it may contain further down.")
_NO_CHECKPOINT = (
    "<BITRANOX-COMPACT-RESUME>\n"
    "The conversation was just compacted and no checkpoint was saved in this session before it "
    "(the compaction came before the save point, it was a manual or idle compaction, or the save "
    "was skipped). The summary above is all that carried over. The full pre-compaction stretch is "
    "still on disk in the transcript %(transcript)s - if the next step depends on detail the "
    "summary does not hold, read it with `dream_state.py session-review` (skill "
    "bitranox:meta-dream-tree) before continuing. OPEN-WORK.md is the standing backlog.\n"
    "</BITRANOX-COMPACT-RESUME>"
)
_UNATTRIBUTED = (
    "<BITRANOX-COMPACT-RESUME>\n"
    "The conversation was just auto-compacted. A checkpoint was requested before it, but no file "
    "this session wrote with the Write or Edit tool after that request holds one, so none is "
    "handed back as this session's. These checkpoint files changed after the request; each may be "
    "another session's (sessions share a checkout and its worktrees), or one this session wrote "
    "through Bash:\n%(listing)s\n"
    "Read one only when the compaction summary names the work it describes, and do not edit it or "
    "mark it STALE unless you can tell it is yours. Otherwise the summary above is what carried "
    "over; the full pre-compaction stretch is in the transcript %(transcript)s - read it with "
    "`dream_state.py session-review` (skill bitranox:meta-dream-tree) when the next step needs "
    "detail the summary lacks. OPEN-WORK.md is the standing backlog.\n"
    "</BITRANOX-COMPACT-RESUME>"
)


def repo_root(cwd) -> Path:
    """The git top level of `cwd`, or `cwd` itself outside a repository. Never raises."""
    try:
        return open_work.backlog_path(cwd).parent
    except Exception:                         # noqa: BLE001 - NotARepo, a missing git: use the cwd
        return Path(cwd)


def fresh_checkpoint(path, asked_at):
    """The checkpoint text when it is this session's latest, else None. IMPURE (reads).

    Latest means written at or after the save request and not yet marked read. A request time of 0
    means this session was never asked, so no file can be its checkpoint. A file with an improvised
    name must also carry the checkpoint heading (see WHICH NAMES).
    """
    if asked_at <= 0:
        return None
    try:
        if os.path.getmtime(path) < asked_at:
            return None
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.strip() or text.lstrip().startswith(_STALE_PREFIX):
        return None
    if Path(path).name != _CHECKPOINT_NAME and not has_checkpoint_heading(text):
        return None
    return text


def is_checkpoint_name(name) -> bool:
    """True for `handover.md` and for an improvised `<anything>-handover.md`. PURE."""
    return name == _CHECKPOINT_NAME or (
        name.endswith(_IMPROVISED_SUFFIX) and len(name) > len(_IMPROVISED_SUFFIX))


def has_checkpoint_heading(text) -> bool:
    """True when a line of `text` is exactly the checkpoint heading. PURE."""
    return any(line.rstrip() == _CHECKPOINT_HEADING for line in text.splitlines())


def resume_context(path, text, today):
    """The block that hands the checkpoint back, cut to fit the inline limit. PURE."""
    fill = {"path": str(path), "today": today, "cut": "", "body": text.rstrip()}
    whole = _RESUME % fill
    if len(whole) <= MAX_CONTEXT_CHARS:
        return whole
    fill["cut"] = _CUT % {"path": str(path)}
    room = MAX_CONTEXT_CHARS - len(_RESUME % dict(fill, body=""))
    body = text[:max(0, room)]
    fill["body"] = body[:body.rfind("\n")] if "\n" in body else body
    return _RESUME % fill


def build(event, today=None, now=None):
    """The additionalContext for this SessionStart event, or None to stay silent. IMPURE (reads)."""
    if not isinstance(event, dict) or event.get("source") != "compact":
        return None
    cwd = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    session = str(event.get("session_id") or "")
    transcript = event.get("transcript_path") or ""
    found = []
    if session:
        asked_at = sig.checkpoint_asked_at(session)
        writes = own_checkpoint_writes(transcript, asked_at) if asked_at > 0 else None
        touched = sig.read_touched_paths(session)
        found = qualifying(candidates(cwd, touched, writes), asked_at)
        own = [c for c in found if is_own(c[0], c[2], writes, touched)]
        if own:
            path, text, _mtime = max(own, key=lambda c: c[2])
            return resume_context(path, text, today or datetime.date.today().isoformat())
    if found:
        return _UNATTRIBUTED % {"listing": listing(found, time.time() if now is None else now),
                                "transcript": transcript or "(unknown)"}
    return _NO_CHECKPOINT % {"transcript": transcript or "(unknown)"}


def candidates(cwd, touched, writes):
    """Every path that may hold a checkpoint: the cwd's repo root, then this session's records. PURE
    apart from the git lookup of the cwd's top level."""
    paths = [repo_root(cwd) / _CHECKPOINT_NAME]
    seen = {_norm(paths[0])}
    for recorded in [*touched, *(writes or ())]:
        p = Path(recorded)
        if is_checkpoint_name(p.name) and _norm(p) not in seen:
            seen.add(_norm(p))
            paths.append(p)
    return paths


def qualifying(paths, asked_at):
    """[(path, text, mtime)] for each of `paths` holding a fresh checkpoint. IMPURE (reads)."""
    found = []
    for path in paths:
        text = fresh_checkpoint(path, asked_at)
        if text is None:
            continue
        try:
            found.append((path, text, os.path.getmtime(path)))
        except OSError:
            continue
    return found


def is_own(path, mtime, writes, touched) -> bool:
    """True when this session's records show it wrote `path` as it now stands. PURE.

    With a transcript (`writes` not None): a successful write of the path after the request, and
    the file unchanged since. Without one: the path is in the touched-paths record.
    """
    key = _norm(path)
    if writes is None:
        return key in {_norm(t) for t in touched}
    at = writes.get(key)
    return at is not None and mtime <= at + _WRITE_SLACK


def listing(found, now) -> str:
    """One line per unattributed candidate, newest first, with its path and age. PURE."""
    rows = sorted(found, key=lambda c: c[2], reverse=True)[:_MAX_LISTED]
    return "\n".join(
        f"- {path} (changed {_age(now - mtime)}, "
        f"{datetime.datetime.fromtimestamp(mtime):%Y-%m-%d %H:%M})"
        for path, _text, mtime in rows)


def _age(seconds) -> str:
    """`seconds` as a short age: '2 min ago', '3 h 5 min ago', '2 d ago'. PURE."""
    minutes = max(0, int(seconds // 60))
    if minutes < 120:
        return f"{minutes} min ago"
    if minutes < 48 * 60:
        return f"{minutes // 60} h {minutes % 60} min ago"
    return f"{minutes // (24 * 60)} d ago"


def _norm(path) -> str:
    """An absolute, normalised spelling of `path`, for comparing recorded paths. PURE."""
    return os.path.normpath(os.path.abspath(str(path)))


def own_checkpoint_writes(transcript, asked_at):
    """{path: epoch} of this session's successful checkpoint writes at or after `asked_at`. IMPURE.

    Read from the session's own transcript: a Write/Edit/MultiEdit tool_use naming a checkpoint
    file, and its tool_result without is_error; the epoch is the result's timestamp, the latest per
    path. None when the transcript cannot be read. Memory stays flat: one line at a time, holding
    only the ids of checkpoint writes still awaiting their result.
    """
    if not transcript:
        return None
    pending, writes = {}, {}
    try:
        with open(transcript, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "tool_use" in line:           # also the prefix of every tool_result's tool_use_id
                    _scan_record(line, pending, writes, asked_at)
    except OSError:
        return None
    return writes


def _scan_record(line, pending, writes, asked_at):
    """Fold one transcript line into `pending` (tool_use id -> path) and `writes`. Mutates both."""
    try:
        record = json.loads(line)
    except ValueError:
        return
    message = record.get("message") if isinstance(record, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use":
            target = _checkpoint_write_target(block)
            if target:
                pending[str(block.get("id"))] = target
        elif block.get("type") == "tool_result" and str(block.get("tool_use_id")) in pending:
            target = pending.pop(str(block.get("tool_use_id")))
            at = _epoch(record.get("timestamp"))
            if not block.get("is_error") and at is not None and at >= asked_at:
                writes[target] = max(at, writes.get(target, at))


def _checkpoint_write_target(block):
    """The normalised path a Write/Edit tool_use writes, when it names a checkpoint file. PURE."""
    tool_input = block.get("input")
    if block.get("name") not in _WRITE_TOOLS or not isinstance(tool_input, dict):
        return None
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not is_checkpoint_name(Path(path).name):
        return None
    return _norm(path)


def _epoch(stamp):
    """Epoch seconds of a transcript ISO-8601 timestamp, or None. PURE."""
    try:
        return datetime.datetime.fromisoformat(str(stamp)).timestamp()
    except (TypeError, ValueError):
        return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:                         # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    try:
        context = build(event)
    except Exception:                         # noqa: BLE001 - a broken hook must never block a session
        return 0
    if context:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": context}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                         # noqa: BLE001 - fail open
        sys.exit(0)
