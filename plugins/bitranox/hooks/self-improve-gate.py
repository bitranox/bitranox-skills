#!/usr/bin/env python3
"""Gated Stop hook for the self-improve skill. Cross-platform (Windows/macOS/Linux).

Runs after every turn. It does a CHEAP check: did the just-finished turn likely
produce a learning (a user correction, an explicit "remember", a self-admitted
miss)? Only then does it block the stop and nudge the model to run the
self-improve skill. On a normal turn it exits silently at near-zero cost. Every
failure path exits 0, so a broken hook never wedges a turn.

Loop safety: it blocks at most once per user message. It records the processed
message's hash in a per-project state file and also honors stop_hook_active, so
the follow-up stop (after the model runs the skill) is allowed through.

Pure standard library: no jq, no cksum, no shell. Reads the Stop event JSON on
stdin and, when it fires, prints a {"decision":"block",...} JSON on stdout.
"""

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

# Learning-signal patterns live in the shared self_improve_signals module (single source
# of truth, also used by the SessionEnd audit hook). Re-bound to the private names this
# module and its tests use. Signals cluster in FAMILIES (user correction / "remember";
# endorsement either side; assistant self-admission / realization); extend the family in
# self_improve_signals, not here.
import self_improve_signals as _sig
from self_improve_signals import (
    USER_PATTERN as _USER_PATTERN,
    ASST_PATTERN as _ASST_PATTERN,
    REALIZATION_PATTERN as _REALIZATION_PATTERN,
    ENDORSE_PATTERN as _ENDORSE_PATTERN,
)

_REASON = (
    'A learning signal was detected this turn (a correction, an explicit "remember", a good idea '
    "endorsed by either side - you judging the user's suggestion good (adopt it), or the user "
    'endorsing yours (a confirmed approach) - a self-admitted miss, or a realization such as '
    '"now I understand the real ..."). Before you '
    'stop: invoke the self-improve skill (Skill tool, name "meta-self-improve") to capture this '
    "session's learnings per its procedure. A discovered fact goes at the right altitude BY SCOPE, "
    "kept concrete: useful across projects -> the highest-altitude curated store (.claude-bx-selflearning/ "
    "at the TOPMOST ancestor directory that has a CLAUDE.md - share-visible, not ~/.claude); "
    "one project -> its memory; a must-hold intermediate-subtree rule -> that level's CLAUDE.md; "
    "unsure -> ask the user where it belongs. If a project-specific "
    "extension skill exists (a repo-local *-self-improve), follow its bindings too. If on "
    "reflection there is genuinely nothing worth recording, say so in one line and then stop."
)


def _routing_hint(event, proj):
    """Prose naming the OTHER repos/levels this turn actually edited, or '' when the subject IS cwd.

    Capture is cwd-keyed, so a learning about a repo you edited from somewhere else is misplaced from
    birth (and cross-tree the dream can never re-home it). The `touched-paths` PostToolUse recorder
    logs what the turn wrote; this turns it into EVIDENCE for the capture step's `--proj` choice. It
    never decides - the model still judges whether the learning is about that repo or about the cwd
    workflow itself."""
    try:
        session = event.get("session_id") or ""
        if not session:
            return ""
        levels = _sig.subject_levels(_sig.read_touched_paths(session), proj)
        if not levels:
            return ""
        bits = ["%s%s" % (lv["level"], " (a DIFFERENT tree - the dream can NEVER re-home a fact "
                                       "misfiled across trees)" if lv["cross_tree"] else
                          " (a sibling project in this tree)") for lv in levels]
        return (" ROUTING EVIDENCE - this turn also edited files under: " + "; ".join(bits) +
                ". Capture defaults to the cwd, which is WRONG when the learning is ABOUT one of "
                "those repos: in that case pass `--proj <that level>` to `memory_engine.py add`, not "
                "the cwd. If the learning is really about the cwd's own workflow, keep the cwd.")
    except Exception:                                     # noqa: BLE001 - a hint must never wedge a turn
        return ""


def _nap_owed_hint(proj):
    """Prose demanding the post-compaction consolidation, or '' when none is owed.

    A compaction clears the model's CONTEXT but NOT the transcript file, so the pre-compaction
    stretch is still recoverable - by a pass that reads from DISK. Hooks have no model and cannot run
    that pass, so PostCompact records the obligation and this turns it into a Stop-block."""
    try:
        if not _sig.is_nap_owed(proj):
            return ""
        return ("A CONTEXT COMPACTION happened and the consolidation has not run since. Compaction "
                "cleared your context but NOT the session transcript on disk, so this session's "
                "earlier learnings are still recoverable - but ONLY from the file. Before you stop: "
                'run the nap (Skill tool, name "meta-dream-nap"). Read the session from DISK '
                "(dream_state.py session-review), not from what you still remember - what you "
                "remember is the compacted summary. It is incremental: only the part no reviewer has "
                "consumed yet comes back. ")
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return ""


def _subagent_hint(session):
    """Prose naming learnings a SUBAGENT found this session, or '' when none are buffered.

    A subagent's learning never reaches the main transcript unless the main agent restates it (and a
    named/background agent's report is not returned at all), so the SubagentStop hook buffers the
    signal and the main capture is the one that can route + write it. Surfacing it here is what makes
    those learnings capturable at all."""
    try:
        recs = _sig.read_subagent_learnings(session)
        if not recs:
            return ""
        bits = ["[%s] %s" % (r.get("agent_type") or "subagent", r.get("snippet") or "") for r in recs]
        return (" SUBAGENT LEARNINGS (found by a subagent this session - they are NOT in your "
                "transcript and die unless you capture them): " + " | ".join(bits) +
                ". Judge each: capture the durable ones (routing `--proj` by SUBJECT as above), "
                "ignore the task-local noise.")
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return ""


def _text(content):
    """Flatten a transcript message's content (string, or list of blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b["text"] for b in content if isinstance(b, dict) and isinstance(b.get("text"), str))
    return ""


# Read only the JSONL tail: we just need the last user + last assistant line, and
# transcripts grow to many MB in long sessions. 64 KiB sits comfortably above any
# normal final turn; bump it if a final turn is ever larger and gets truncated for
# matching (a truncated tail only costs recall, never a wedged turn).
_TAIL_BYTES = 65536


def _last_messages(transcript_path, tail_bytes=_TAIL_BYTES):
    """Return (last_user_text, last_assistant_text) from the JSONL transcript tail."""
    last_user = last_asst = ""
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as fh:
            if size > tail_bytes:
                fh.seek(size - tail_bytes)
                fh.readline()  # drop the partial first line after the seek
            data = fh.read()
    except OSError:
        return "", ""
    for raw in data.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line.decode("utf-8", "replace"))
        except ValueError:
            continue
        kind = obj.get("type")
        if kind == "user":
            last_user = _text(obj.get("message", {}).get("content"))
        elif kind == "assistant":
            last_asst = _text(obj.get("message", {}).get("content"))
    return last_user, last_asst


def main():
    try:
        event = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        return 0
    if event.get("stop_hook_active"):
        return 0

    transcript = event.get("transcript_path") or ""
    if not transcript or not Path(transcript).is_file():
        return 0

    proj = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    proj_key = hashlib.sha1(proj.encode("utf-8", "replace")).hexdigest()[:16]
    state = Path(tempfile.gettempdir()) / ("claude-self-improve-%s.state" % proj_key)

    # The dream is a model pass and never receives `transcript_path`; this hook gets it every turn,
    # so record it (with the session id) for the dream to look up by cwd and read from DISK.
    try:
        _sig.record_session_meta(proj, event.get("session_id") or "", transcript)
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        pass

    last_user, last_asst = _last_messages(transcript)
    if not (last_user.strip() or last_asst.strip()):
        return 0

    sig = hashlib.sha1(last_user.encode("utf-8", "replace")).hexdigest()
    try:
        with open(state, encoding="utf-8") as fh:
            if fh.read().strip() == sig:
                return 0  # already blocked once for this user message
    except OSError:
        pass

    # A SUBAGENT's learning is reason enough to capture even when the MAIN turn is quiet - it is not
    # in this transcript, so no main-turn pattern can ever fire for it.
    sub_hint = _subagent_hint(event.get("session_id") or "")

    # A compaction cleared the CONTEXT (the transcript file survives). A hook cannot run the
    # consolidation pass, so PostCompact records an obligation and we refuse to stop while it stands.
    nap_hint = _nap_owed_hint(proj)

    if (nap_hint or sub_hint or _USER_PATTERN.search(last_user) or _ASST_PATTERN.search(last_asst)
            or _REALIZATION_PATTERN.search(last_asst)
            or _ENDORSE_PATTERN.search(last_user) or _ENDORSE_PATTERN.search(last_asst)):
        try:
            with open(state, "w", encoding="utf-8") as fh:
                fh.write(sig)
        except OSError:
            pass
        sys.stdout.write(json.dumps({"decision": "block",
                                     "reason": (nap_hint + _REASON + _routing_hint(event, proj)
                                                + sub_hint) if nap_hint else
                                               (_REASON + _routing_hint(event, proj) + sub_hint)}))
        if sub_hint:
            # Consumed once, like the SessionStart audit: a non-empty hint ALWAYS blocks, so the
            # model has now seen the findings verbatim and owns the judgement. Leaving them queued
            # would re-nag every later turn of the session.
            try:
                _sig.drain_subagent_learnings(event.get("session_id") or "")
            except Exception:                             # noqa: BLE001 - never wedge a turn
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
