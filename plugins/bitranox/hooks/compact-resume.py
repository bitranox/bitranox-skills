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

WHERE it looks. The git top level of the cwd at compaction, AND every `handover.md` this session
wrote with Write/Edit (the session-keyed touched-paths record); the newest qualifying one wins. The
cwd alone is not enough: it is wherever the last `cd` left the session, so a checkpoint written in a
linked worktree while the cwd sat in the main checkout, or at a parent while the cwd had drifted
into a nested repo, was reported as "no checkpoint" (measured: 23 of 106 checkpoints written after
the request, across real transcripts). The cwd candidate stays because a checkpoint written through
Bash never reaches touched-paths.

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

_RESUME = (
    "<BITRANOX-COMPACT-RESUME>\n"
    "The conversation was just auto-compacted. Before it, this session saved a checkpoint at "
    "%(path)s - resume the work from it, starting with its exact next action; do not ask the user "
    "whether to continue. Once you have absorbed it, replace its first line with "
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


def build(event, today=None):
    """The additionalContext for this SessionStart event, or None to stay silent. IMPURE (reads)."""
    if not isinstance(event, dict) or event.get("source") != "compact":
        return None
    cwd = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    session = str(event.get("session_id") or "")
    found = latest_checkpoint(candidates(cwd, session), sig.checkpoint_asked_at(session)) \
        if session else None
    if found is None:
        return _NO_CHECKPOINT % {"transcript": event.get("transcript_path") or "(unknown)"}
    today = today or datetime.date.today().isoformat()
    return resume_context(found[0], found[1], today)


def candidates(cwd, session):
    """Every path that may hold this session's checkpoint, the cwd's repo root first. IMPURE."""
    paths = [repo_root(cwd) / _CHECKPOINT_NAME]
    for touched in sig.read_touched_paths(session):
        p = Path(touched)
        if is_checkpoint_name(p.name) and p not in paths:
            paths.append(p)
    return paths


def latest_checkpoint(paths, asked_at):
    """(path, text) of the newest qualifying checkpoint among `paths`, else None. IMPURE (reads)."""
    best = None
    for path in paths:
        text = fresh_checkpoint(path, asked_at)
        if text is None:
            continue
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if best is None or mtime > best[0]:
            best = (mtime, path, text)
    return (best[1], best[2]) if best else None


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
