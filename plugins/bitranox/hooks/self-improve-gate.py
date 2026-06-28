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
    "kept concrete: useful across projects -> ~/.claude/rules/bitranox/ (the global rules layer); "
    "one project -> its memory; a must-hold intermediate-subtree rule -> that level's CLAUDE.md; "
    "unsure -> ask the user where it belongs. If a project-specific "
    "extension skill exists (a repo-local *-self-improve), follow its bindings too. If on "
    "reflection there is genuinely nothing worth recording, say so in one line and then stop."
)


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

    if (_USER_PATTERN.search(last_user) or _ASST_PATTERN.search(last_asst)
            or _REALIZATION_PATTERN.search(last_asst)
            or _ENDORSE_PATTERN.search(last_user) or _ENDORSE_PATTERN.search(last_asst)):
        try:
            with open(state, "w", encoding="utf-8") as fh:
                fh.write(sig)
        except OSError:
            pass
        sys.stdout.write(json.dumps({"decision": "block", "reason": _REASON}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
