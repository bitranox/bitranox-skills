#!/usr/bin/env python3
"""SessionStart hook: after a compaction, put the saved checkpoint back in front of the model.

In compact mode the context watcher asks the session to save a checkpoint (`handover.md` plus
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
    means this session was never asked, so no file can be its checkpoint.
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
    return text


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
    path = repo_root(cwd) / "handover.md"
    text = fresh_checkpoint(path, sig.checkpoint_asked_at(session)) if session else None
    if text is None:
        return _NO_CHECKPOINT % {"transcript": event.get("transcript_path") or "(unknown)"}
    today = today or datetime.date.today().isoformat()
    return resume_context(path, text, today)


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
