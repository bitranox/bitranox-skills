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
that tool result). A later Bash call of the same session that names the path and can change it (an
in-place `sed -i`, a redirect onto it, a Python write in a heredoc, a copy, move or removal)
continues that record: its result time becomes the file's own-write time. Sessions re-stamp the
time in a checkpoint through `sed -i` right after writing it, mostly answering the CLOCK CHECK
nudge, and that moved the mtime past the Write (measured: 25 own checkpoints resumed as
unattributed). Widening the slack instead would also cover a peer's edit in the same window, while
a Bash call in THIS transcript is this session's by construction; only a call that follows the own
Write counts, so a shell edit alone never attributes a file. The path is resolved against the
call's recorded cwd and any `cd` before it; a path built from a variable is not resolved. Without a
readable transcript the touched-paths record stands in, which cannot see a later overwrite. Neither the cwd nor the newest mtime decides: several sessions share one
main checkout and its linked worktrees, each writing its own handover.md, so the cwd's copy and the
newest file can both be a peer's, and a linked worktree's tracked copy is as new as the checkout
that wrote it (measured 2026-11-16: the cwd's tracked copy in a worktree, an older moment, came back
as the session's checkpoint while the real one sat uncommitted in the main checkout). A qualifying
file no record attributes (a peer's, or one this session wrote through Bash) is listed with its path
and age, and the reader is told it is not known to be theirs and not to edit it. A subagent's own
transcript is not read: a checkpoint a subagent wrote is that subagent's, not this session's.

WHICH NAMES. `handover.md`, and a touched file whose name ENDS in `-handover.md` or STARTS with
`handover-` (and ends in `.md`) that carries the line `## Lessons for the next nap` (the heading the
meta-context-watcher skill requires in every checkpoint). Sessions with a worktree outside any repo
improvise names such as `~/wt-vmxnet3-handover.md` (43 writes of three such names across 5497
transcripts, 2026-11-08), and a session kept its checkpoint in the scratchpad as
`handover-<topic>.md` across five compactions; an exact-name rule never hands those back. The
heading keeps out other files that share the suffix: the one such file in that corpus was a skill
checklist without it. `handover.prev.md`, the backup of an earlier checkpoint, matches neither form
and so never counts, heading or not.

WHAT ELSE IT SAYS. Two cases used to read as "no checkpoint was saved" and were not. A session that
finished the work after its checkpoint retires it itself - a `# STALE` first line, by Edit or by
`sed -i`, or the file removed - before the compaction lands (10 of 47 such compactions measured);
the block then says the session retired its own checkpoint and the summary carries the current
step. A session in plan mode can write only its plan file, and wrote its checkpoint there (3 of
47); the harness attaches the plan file after a compaction itself, so the block names that file
and says not to mark it STALE. Both are attributed the same way as a checkpoint: from this
session's own transcript, after the request.

WHY its own hook rather than a branch of session-start.py: that hook's essentials are held under a
small byte ceiling so they always land inline, and a checkpoint can be several KB. The harness inlines
an additionalContext up to 10,000 characters and replaces anything larger with a 2,000-character
preview, so the checkpoint is cut to fit below that, naming the file for the rest.

Pure standard library, ASCII only. Every failure path prints nothing and exits 0.
"""

import dataclasses
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import NamedTuple, cast

import open_work
import self_improve_signals as sig
import shell_text

#: Below the harness's 10,000-character inline limit, with room for the framing around the body.
MAX_CONTEXT_CHARS = 9000
_STALE_PREFIX = "# STALE"
_CHECKPOINT_NAME = "handover.md"
_IMPROVISED_SUFFIX = "-handover.md"
_IMPROVISED_PREFIX = "handover-"
_MD = ".md"
#: One shell statement (or a heredoc script) that can change a file it names: an in-place editor, a
#: redirect onto a checkpoint-like name, tee, a Python write, a copy, move or removal. A statement
#: that only reads (`head -1 handover.md`) does not match, so it never vouches for a change.
_BASH_CHANGES = re.compile(
    r"\b(?:sed|perl)\b[^\n]*\s(?:-[A-Za-z]*i|--in-place)"
    r"|>>?\s*['\"]?[^\s'\"<>|;&]*handover[^\s'\"<>|;&]*\.md"
    r"|\btee\b|\.write_(?:text|bytes)\(|\.write\(|\bopen\("
    r"|\b(?:cp|mv|rm|unlink|truncate|install)\b")
#: Programs that change only the last file they name.
_COPY_PROGRAMS = frozenset({"cp", "install"})
#: The statement removes or moves away a file it names.
_BASH_REMOVES = re.compile(r"\b(?:rm|mv|unlink)\b")
#: A word in a command naming a checkpoint-like file, with any directory part in front of it.
#: Matched only from where the word starts (the leftmost match always did): a start anywhere inside
#: a long word rescanned it from each character.
_BASH_PATH = re.compile(
    r"""(?<![^\s'"`;|&<>()=,])[^\s'"`;|&<>()=,]*handover[^\s'"`;|&<>()=,/]*\.md(?![\w.-])""")
#: A backslash escape in an unquoted shell word: bash keeps only the escaped character.
_BASH_ESCAPE = re.compile(r"\\(.)", re.DOTALL)
#: The harness attachments that name the session's plan file while plan mode is on or ending.
_PLAN_ATTACHMENTS = frozenset({"plan_mode", "plan_mode_reentry", "plan_mode_exit"})
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
_RETIRED = (
    "<BITRANOX-COMPACT-RESUME>\n"
    "The conversation was just compacted. After the save request this session wrote a checkpoint "
    "at %(path)s and then retired it itself before the compaction (it set the first line to "
    "`# STALE` or removed the file), which says the work that checkpoint described was finished. "
    "So nothing is handed back and no save was lost: the compaction summary above names the "
    "current step, and the work continues from it. If that step needs detail the summary lacks, "
    "read the transcript %(transcript)s with `dream_state.py session-review` (skill "
    "bitranox:meta-dream-tree). OPEN-WORK.md is the standing backlog.\n"
    "</BITRANOX-COMPACT-RESUME>"
)
_PLAN = (
    "<BITRANOX-COMPACT-RESUME>\n"
    "The conversation was just compacted. After the save request this session wrote its plan file "
    "%(path)s - in plan mode the one file a session may write - so a checkpoint saved before the "
    "compaction is in that plan file, not in a handover.md. The harness attaches the plan file "
    "after a compaction while plan mode is on (look for it above); otherwise Read it. Resume from "
    "its checkpoint section, checking that section's next action against the compaction summary "
    "first. The plan file is not a handover: do not mark it STALE or rewrite its plan to say it "
    "was read. The full pre-compaction stretch is in the transcript %(transcript)s. OPEN-WORK.md "
    "is the standing backlog.\n"
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


def is_checkpoint_name(name: str) -> bool:
    """True for `handover.md` and an improvised `<anything>-handover.md` or `handover-<topic>.md`.
    PURE."""
    if name == _CHECKPOINT_NAME:
        return True
    if name.endswith(_IMPROVISED_SUFFIX) and len(name) > len(_IMPROVISED_SUFFIX):
        return True
    return (name.startswith(_IMPROVISED_PREFIX) and name.endswith(_MD)
            and len(name) > len(_IMPROVISED_PREFIX) + len(_MD))


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
    shown = transcript or "(unknown)"
    found = []
    if session:
        asked_at = sig.checkpoint_asked_at(session)
        record = scan_transcript(transcript, asked_at) if asked_at > 0 else None
        writes = record.writes if record is not None else None
        touched = sig.read_touched_paths(session)
        found = qualifying(candidates(cwd, touched, writes), asked_at)
        own = [c for c in found if is_own(c[0], c[2], writes, touched)]
        if own:
            path, text, _mtime = max(own, key=lambda c: c[2])
            return resume_context(path, text, today or datetime.date.today().isoformat())
        own_note = _own_note(record, shown)
        if own_note:
            return own_note
    if found:
        return _UNATTRIBUTED % {"listing": listing(found, time.time() if now is None else now),
                                "transcript": shown}
    return _NO_CHECKPOINT % {"transcript": shown}


def _own_note(record: TranscriptRecord | None, shown: str) -> str | None:
    """The block for a checkpoint this session retired itself, or for one it put in its plan file;
    None when neither applies. IMPURE (reads)."""
    if record is None:
        return None
    retired = retired_checkpoint(record)
    if retired is not None:
        return _RETIRED % {"path": retired, "transcript": shown}
    if record.plan_writes:
        plan = max(record.plan_writes, key=lambda p: record.plan_writes[p])
        return _PLAN % {"path": plan, "transcript": shown}
    return None


def retired_checkpoint(record: TranscriptRecord) -> str | None:
    """The checkpoint this session wrote after the request and then retired itself, or None.
    IMPURE (reads).

    Retired means its first line now reads `# STALE` and nothing but this session changed it since
    its last own write, or it is gone and this session's own Bash call removed or moved it.
    """
    retired: list[tuple[float, str]] = []
    for path, at in record.writes.items():
        try:
            mtime = os.path.getmtime(path)
        except FileNotFoundError:
            if path in record.removed:
                retired.append((at, path))
            continue
        except OSError:
            continue
        if mtime > at + _WRITE_SLACK:
            continue
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if text.lstrip().startswith(_STALE_PREFIX):
            retired.append((at, path))
    return max(retired)[1] if retired else None


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


def _norm(path: object) -> str:
    """An absolute, normalised spelling of `path`, for comparing recorded paths. PURE."""
    return os.path.normpath(os.path.abspath(str(path)))


#: A decoded transcript record or block: JSON keys to JSON values.
_Json = dict[str, object]


class _Pending(NamedTuple):
    """A tool call awaiting its result: what kind of change, and to which paths. For a Bash call
    each path maps to whether the statement removes or moves the file; otherwise to False."""

    kind: str
    paths: dict[str, bool]


@dataclasses.dataclass
class TranscriptRecord:
    """What this session's own transcript shows it did to checkpoint and plan files after the save
    request. Every map is keyed by a normalised path and holds the latest result epoch.

    `writes`: checkpoint files it wrote with Write/Edit/MultiEdit, each kept current by its later
    Bash calls that name the path and can change it. `removed`: those of them a later own Bash call
    removed or moved away. `plan_writes`: plan files it wrote. `pending` and `plan_paths` are scan
    state: tool calls still awaiting their result, and the plan files the harness has named.
    """

    asked_at: float
    writes: dict[str, float] = dataclasses.field(default_factory=dict[str, float])
    removed: set[str] = dataclasses.field(default_factory=set[str])
    plan_writes: dict[str, float] = dataclasses.field(default_factory=dict[str, float])
    plan_paths: set[str] = dataclasses.field(default_factory=set[str])
    pending: dict[str, _Pending] = dataclasses.field(default_factory=dict[str, _Pending])


def own_checkpoint_writes(transcript: str, asked_at: float) -> dict[str, float] | None:
    """{path: epoch} of this session's successful checkpoint writes at or after `asked_at`. IMPURE.

    `scan_transcript(...).writes`; None when the transcript cannot be read.
    """
    record = scan_transcript(transcript, asked_at)
    return None if record is None else record.writes


def scan_transcript(transcript: str, asked_at: float) -> TranscriptRecord | None:
    """The TranscriptRecord of this session's transcript, or None when it cannot be read. IMPURE.

    A Write/Edit/MultiEdit tool_use naming a checkpoint file, with its tool_result without
    is_error at or after `asked_at`, is an own write; the epoch is the result's timestamp. A Bash
    tool_use whose command can change a checkpoint file it names continues the record of a file
    already written that way (see WHOSE); its exit status does not matter, since a command chained
    after the edit can fail while the edit stood. Memory stays flat: one line at a time, holding
    only checkpoint and plan paths and the ids of their calls still awaiting a result.
    """
    if not transcript:
        return None
    record = TranscriptRecord(asked_at)
    try:
        with open(transcript, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                # "tool_use" is also the prefix of every tool_result's tool_use_id
                if "tool_use" in line or "planFilePath" in line:
                    _scan_line(line, record)
    except OSError:
        return None
    return record


def _scan_line(line: str, record: TranscriptRecord) -> None:
    """Fold one transcript line into `record`. Mutates it."""
    try:
        entry: object = json.loads(line)
    except ValueError:
        return
    if not isinstance(entry, dict):
        return
    entry_map = cast(_Json, entry)
    _note_plan_file(entry_map, record)
    message = entry_map.get("message")
    content = cast(_Json, message).get("content") if isinstance(message, dict) else None
    if not isinstance(content, list):
        return
    cwd = entry_map.get("cwd")
    for item in cast(list[object], content):
        if not isinstance(item, dict):
            continue
        block = cast(_Json, item)
        if block.get("type") == "tool_use":
            _note_tool_use(block, cwd if isinstance(cwd, str) else None, record)
        elif block.get("type") == "tool_result" and str(block.get("tool_use_id")) in record.pending:
            pending = record.pending.pop(str(block.get("tool_use_id")))
            _note_result(pending, bool(block.get("is_error")), _epoch(entry_map.get("timestamp")),
                         record)


def _note_plan_file(entry: _Json, record: TranscriptRecord) -> None:
    """Remember the plan file a plan-mode attachment names. Mutates `record`."""
    attachment = entry.get("attachment")
    if not isinstance(attachment, dict):
        return
    attachment_map = cast(_Json, attachment)
    if attachment_map.get("type") not in _PLAN_ATTACHMENTS:
        return
    path = attachment_map.get("planFilePath")
    if isinstance(path, str) and path:
        record.plan_paths.add(_norm(path))


def _note_tool_use(block: _Json, cwd: str | None, record: TranscriptRecord) -> None:
    """Queue a tool call that writes a checkpoint or plan file, or a Bash call that can change a
    checkpoint file. Mutates `record`."""
    tid = str(block.get("id"))
    target = _write_target(block)
    if target and is_checkpoint_name(Path(target).name):
        record.pending[tid] = _Pending("write", {target: False})
    elif target and target in record.plan_paths:
        record.pending[tid] = _Pending("plan", {target: False})
    elif block.get("name") == "Bash":
        tool_input = block.get("input")
        command = cast(_Json, tool_input).get("command") if isinstance(tool_input, dict) else None
        changed = bash_targets(command, cwd)
        if changed:
            record.pending[tid] = _Pending("bash", changed)


def _note_result(pending: _Pending, is_error: bool, at: float | None,
                 record: TranscriptRecord) -> None:
    """Fold a queued call's result into `record`. Mutates it."""
    if at is None or at < record.asked_at:
        return
    if pending.kind == "bash":
        for path, removes in pending.paths.items():
            if path in record.writes:
                record.writes[path] = max(at, record.writes[path])
                if removes:
                    record.removed.add(path)
        return
    if is_error:
        return
    into = record.writes if pending.kind == "write" else record.plan_writes
    for path in pending.paths:
        into[path] = max(at, into.get(path, at))
        record.removed.discard(path)


def _write_target(block: _Json) -> str | None:
    """The normalised path a Write/Edit/MultiEdit tool_use writes, or None. PURE."""
    tool_input = block.get("input")
    if block.get("name") not in _WRITE_TOOLS or not isinstance(tool_input, dict):
        return None
    path = cast(_Json, tool_input).get("file_path")
    return _norm(path) if isinstance(path, str) and path else None


def bash_targets(command: object, cwd: str | None) -> dict[str, bool]:
    """{normalised path: removes} of the checkpoint-named files a Bash command can change. PURE
    apart from the directory checks a `cd` is resolved with.

    Judged per statement, so a read of the checkpoint chained to an edit of another file does not
    count; a heredoc body (a script fed to an interpreter) is judged whole, against every directory
    the command's statements ran in. A relative path is resolved against the call's cwd as moved
    by a preceding `cd`; one built from a variable, or after a `cd` no static read can follow, is
    skipped. `removes` is True when the statement removes or moves the file.

    A statement's words are read the way Git Bash reads them: `/c/temp` is drive C on Windows,
    and an unquoted backslash is an escape. A heredoc body keeps its interpreter's reading.
    """
    if not isinstance(command, str) or "handover" not in command:
        return {}
    out: dict[str, bool] = {}
    here: str | None = cwd or None
    bases: set[str | None] = set()
    for statement in _statements(shell_text.strip_heredoc_bodies(command)):
        changed, landing = cast(tuple[bool, str | None],
                                shell_text.directory_change(statement, here,
                                                            msys_drives=os.name == "nt"))
        if changed:
            here = landing
            continue
        if here:
            bases.add(here)
        _collect_targets(statement, here, out, shell=True)
    lines = command.split("\n")
    heredocs = cast(list[tuple[int, object, tuple[int, int]]],
                    list(shell_text.iter_heredocs(command)))
    for _line, _opener, (start, end) in heredocs:
        body = "\n".join(lines[start:end])
        for base in bases or {None}:
            _collect_targets(body, base, out, shell=False)
    return out


def _statements(text: str) -> list[str]:
    """`text` cut at the list and pipe operators (`;`, `&`, `&&`, `||`, `|`, newline) that sit
    outside quotes and outside a `$(...)` or backtick substitution. PURE.

    shell_text.iter_segments also cuts INSIDE a substitution, which a guard needs and this reader
    does not: `sed -i "1s/x/$(date +%H:%M)/" handover.md` must stay one statement, or its edit and
    the path it edits land in different pieces and the call reads as changing nothing.
    """
    out: list[str] = []
    start, depth, quote, i = 0, 0, "", 0
    while i < len(text):
        ch = text[i]
        if quote:
            # a quoted string is one word whatever it holds, a substitution inside it included
            if ch == "\\" and quote == '"':
                i += 1
            elif ch == quote:
                quote = ""
        elif ch == "\\":
            i += 1
        elif ch in "'\"`" and not (ch == "`" and depth):
            quote = ch
        elif text.startswith("$(", i):
            depth += 1
            i += 1
        elif ch == ")" and depth:
            depth -= 1
        elif ch in ";&|\n" and not depth:
            out.append(text[start:i])
            start = i + 1
        i += 1
    out.append(text[start:])
    return [s for s in out if s.strip()]


def _collect_targets(text: str, base: str | None, out: dict[str, bool], *, shell: bool) -> None:
    """Add the checkpoint files `text` (one statement or script) can change to `out`. Mutates it.

    `shell` is True for a shell statement, whose words get Git Bash's reading (`_as_bash_reads`),
    and False for a script body, whose paths reach a native interpreter as written.
    """
    if not _BASH_CHANGES.search(text):
        return
    removes = bool(_BASH_REMOVES.search(text))
    words = cast(list[str], shell_text.argv_for_match(text.strip(), "Bash"))
    program = next((w for w in words if "=" not in w), "")
    raw = shell                      # the text still carries the shell's quotes and escapes
    if os.path.basename(program) in _COPY_PROGRAMS and len(words) > 1:
        # a copy changes only its destination: `cp handover.md handover.prev.md` reads the file
        text, raw = words[-1], False
    for match in _BASH_PATH.finditer(text):
        token = match.group(0)
        if shell:
            quoted = text[match.start() - 1:match.start()] in ("'", '"')
            token = _as_bash_reads(token, escaped=raw and not quoted)
        if "$" in token or not is_checkpoint_name(os.path.basename(token)):
            continue
        token = os.path.expanduser(token)
        if not shell_text.is_rooted(token):
            if not base:
                continue
            token = os.path.join(base, token)
        key = _norm(token)
        out[key] = out.get(key, False) or removes


def _as_bash_reads(token: str, *, escaped: bool) -> str:
    """The path Git Bash reaches for a word of a statement. PURE apart from the host check.

    `escaped` is True for an unquoted word as written, whose backslashes bash drops as escapes
    (`C:\\temp\\x` is `C:tempx`, measured in Git Bash): the word then names another file than
    the one a Windows path parse would find. A quoted word, or one the shell already read, keeps
    them. On Windows a `/c/...` drive path is drive C (see `shell_text.msys_drive_path`).
    """
    if escaped:
        token = _BASH_ESCAPE.sub(r"\1", token)
    return cast(str, shell_text.msys_drive_path(token, os.name == "nt"))


def _epoch(stamp: object) -> float | None:
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
