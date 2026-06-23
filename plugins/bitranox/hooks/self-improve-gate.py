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
import re
import sys
import tempfile

# High-precision learning signals (corrections, "remember", admitted miss),
# English and German. Kept deliberately narrow to favour precision over recall.
_PATTERN = re.compile(
    r"no,|nope|that.?s wrong|that is wrong|incorrect|don.?t do|do not do|stop doing"
    r"|you (forgot|missed|should have|shouldn.?t)|not what i|instead of"
    r"|that.?s not right|isn.?t right|you.?re right|you are right|my mistake"
    r"|i was wrong|apolog|remember|note that|keep in mind|for next time"
    r"|for the future|from now on|make a (memory|rule|note)"
    r"|falsch|nein,|stattdessen|merke? dir|in zukunft|denk dran",
    re.IGNORECASE,
)

_REASON = (
    'A learning signal was detected this turn (a correction, an explicit "remember", or a '
    "self-admitted miss). Before you stop: invoke the self-improve skill (Skill tool, name "
    '"self-improve") to capture this session\'s learnings into memory/CLAUDE.md per its '
    "procedure. If a project-specific extension skill exists (a repo-local *-self-improve), "
    "follow its bindings too. If on reflection there is genuinely nothing worth recording, say "
    "so in one line and then stop."
)


def _text(content):
    """Flatten a transcript message's content (string, or list of blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b["text"] for b in content if isinstance(b, dict) and isinstance(b.get("text"), str))
    return ""


def _last_messages(transcript_path):
    """Return (last_user_text, last_assistant_text) from the JSONL transcript tail."""
    last_user = last_asst = ""
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                kind = obj.get("type")
                if kind == "user":
                    last_user = _text(obj.get("message", {}).get("content"))
                elif kind == "assistant":
                    last_asst = _text(obj.get("message", {}).get("content"))
    except OSError:
        return "", ""
    return last_user, last_asst


def main():
    try:
        event = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        return 0
    if event.get("stop_hook_active"):
        return 0

    transcript = event.get("transcript_path") or ""
    if not transcript or not os.path.isfile(transcript):
        return 0

    proj = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    proj_key = hashlib.sha1(proj.encode("utf-8", "replace")).hexdigest()[:16]
    state = os.path.join(tempfile.gettempdir(), "claude-self-improve-%s.state" % proj_key)

    last_user, last_asst = _last_messages(transcript)
    slice_text = last_user + "\n" + last_asst
    if not slice_text.strip():
        return 0

    sig = hashlib.sha1(last_user.encode("utf-8", "replace")).hexdigest()
    try:
        with open(state, encoding="utf-8") as fh:
            if fh.read().strip() == sig:
                return 0  # already blocked once for this user message
    except OSError:
        pass

    if _PATTERN.search(slice_text):
        try:
            with open(state, "w", encoding="utf-8") as fh:
                fh.write(sig)
        except OSError:
            pass
        sys.stdout.write(json.dumps({"decision": "block", "reason": _REASON}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
