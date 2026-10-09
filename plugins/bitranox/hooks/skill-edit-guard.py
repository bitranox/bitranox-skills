#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit|NotebookEdit) guard: a SKILL.md edit must go through the skill-writer process.

Editing a shipped `SKILL.md` by hand - skipping `bitranox:meta-skill-writer`'s RED-GREEN-REFACTOR / Iron
Law (baseline test first, sibling tests for any bundled script) - is the exact miss this guard prevents.
A skill grows into a mess by accretion when edits bypass that process; the standing "use the applicable
skill" rule is advisory prose that loses under momentum, so this is the deterministic backstop.

Decision on an `Edit`/`Write`/`MultiEdit`/`NotebookEdit` whose target (`file_path`, or
`notebook_path` for NotebookEdit) is a `.../skills/<name>/SKILL.md`, matched ignoring letter case and
after backslashes become `/` and `.`/`..` segments collapse:
  - BLOCK (exit 2): the tool call is denied and the reason is fed back to the MODEL, which then redirects
    itself to meta-skill-writer. The user is NOT prompted (enforced, not asked).
  - UNLESS BOTH of these hold:
    1. this session holds a fresh meta-skill-writer receipt: `skill_receipt.is_fresh`, keyed by the
       event's `session_id`, valid for 8 hours. Step 0 of meta-skill-writer arms it by running
       `skill_receipt.py start meta-skill-writer`, and its last step's `end` disarms it.
    2. the EDITING AGENT loaded meta-skill-writer: its own transcript holds the record the harness
       writes when a skill loads - a `type: user`, `isMeta: true` message whose text starts
       `Base directory for this skill: <dir>`, with `<dir>`'s last segment `meta-skill-writer`.
       Written the same way for a Skill tool call and a typed slash command.
    The receipt alone is not proof, because it is keyed by session and a subagent shares its
    parent's: probed on Claude Code 2.1.295, a subagent's PreToolUse event carries the MAIN
    session's `session_id` and `transcript_path` plus its own `agent_id`, and its Bash sees the
    parent's CLAUDE_CODE_SESSION_ID. So a subagent running `start` by hand armed every agent in the
    session without any of them loading the skill. The editing agent's transcript is the main one,
    or `<transcript_path minus .jsonl>/subagents/agent-<agent_id>.jsonl` when `agent_id` is set.
  - UNLESS the env `BITRANOX_SKILL_WRITER` is set: the emergency bypass. NOTE: a shell `export` in a
    Bash tool call does NOT reach this hook (separate process) - the env must be set at SESSION start.

Errors split by direction. Unparseable stdin and any error escaping `main` fail OPEN (exit 0): a broken
guard must never wedge a turn. An error while consulting the receipt store, a transcript that cannot
be read, and an `agent_id` that is not a plain name all fail CLOSED: they count as no evidence and the
edit is blocked, because evidence that cannot be read must not disarm the guard.
Pure standard library; launched via run-python.sh so it works on Windows too.
"""
import json
import os
import posixpath
import re
import sys
from pathlib import Path

# IGNORECASE because macOS and Windows filesystems are case-insensitive: there `Skills/x/skill.md`
# opens the real SKILL.md, and the guard cannot tell from a path string which filesystem it names.
_SKILL_MD = re.compile(r"(?:^|/)skills/[^/]+/SKILL\.md$", re.IGNORECASE)
_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_BYPASS_ENV = "BITRANOX_SKILL_WRITER"
_SKILL = "meta-skill-writer"
_LOAD_PREFIX = "Base directory for this skill:"
# agent_id becomes a file-name segment; anything but a plain name could leave subagents/.
_AGENT_ID = re.compile(r"[A-Za-z0-9_-]+")


def _agent_transcript(event):
    """The editing agent's own transcript path, or None when it cannot be named safely."""
    main = event.get("transcript_path")
    if not main:
        return None
    if "agent_id" not in event or event["agent_id"] is None:
        return Path(main)
    agent = event["agent_id"]
    if not isinstance(agent, str) or not _AGENT_ID.fullmatch(agent):
        return None
    return Path(main).with_suffix("") / "subagents" / ("agent-%s.jsonl" % agent)


def _texts(record):
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [b.get("text") or "" for b in content if isinstance(b, dict) and b.get("type") == "text"]
    return []


def _is_load_of(record, skill):
    if not isinstance(record, dict) or record.get("type") != "user" or record.get("isMeta") is not True:
        return False
    for text in _texts(record):
        if not text.startswith(_LOAD_PREFIX):
            continue
        skill_dir = text[len(_LOAD_PREFIX):].split("\n", 1)[0].strip().replace("\\", "/").rstrip("/")
        if skill_dir.rsplit("/", 1)[-1] == skill:
            return True
    return False


def skill_loaded(transcript, skill=_SKILL):
    """Whether `transcript` records the harness loading `skill`. Raises OSError when unreadable."""
    with open(transcript, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            # Cheap prefilter first: a transcript runs to many MB and almost no line is a load.
            if skill not in line or _LOAD_PREFIX not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue                               # a torn or truncated line is not evidence
            if _is_load_of(record, skill):
                return True
    return False


def _receipt_fresh(event):
    try:
        import skill_receipt
        # The EVENT's session id, so the receipt must belong to THIS session. Without it the
        # check answered "somebody on this machine started the procedure recently" - a different
        # claim, and routinely true on a machine running several sessions at once.
        return bool(skill_receipt.is_fresh(_SKILL, session_id=event.get("session_id")))
    except Exception:  # noqa: BLE001 - a broken receipt store must not wedge; count it as no receipt
        return False


def _loaded_by_editing_agent(event):
    transcript = _agent_transcript(event)
    if transcript is None:
        return False
    try:
        return skill_loaded(transcript)
    except OSError:
        return False                                   # unreadable evidence is no evidence


def decide(event, env):
    """Pure: (event, env) -> a block-reason string (deny the tool call), or None to allow silently."""
    if (event.get("tool_name") or "") not in _TOOLS:
        return None
    # posixpath.normpath, not os.path: the separators are already forward slashes, and
    # os.path would put Windows ones back. Without collapsing "." and ".." first, the
    # tail-anchored regex missed .../skills/<name>/./SKILL.md - the same file, unguarded.
    # NotebookEdit names its target `notebook_path`; without the fallback that registration
    # could never produce a decision.
    tool_input = event.get("tool_input") or {}
    raw = (tool_input.get("file_path") or tool_input.get("notebook_path") or "").replace("\\", "/")
    path = posixpath.normpath(raw) if raw else raw
    if not _SKILL_MD.search(path):
        return None
    if env.get(_BYPASS_ENV):
        return None                                    # emergency bypass (env at session launch)
    receipt = _receipt_fresh(event)
    if receipt and _loaded_by_editing_agent(event):
        return None                                    # this agent ENTERED the skill-writer procedure
    if receipt:
        why = ("A meta-skill-writer receipt is armed, but THIS agent never loaded the skill: a receipt "
               "is shared by every agent in the session, so a subagent cannot ride its parent's. "
               "Invoke bitranox:meta-skill-writer via the Skill tool in this agent first.")
    else:
        why = ("Skills change ONLY through bitranox:meta-skill-writer (RED-GREEN-REFACTOR + its "
               "checklist); invoke that skill via the Skill tool - its step 0 issues the session "
               "receipt this guard checks.")
    return (
        "Editing a SKILL.md directly is blocked. %s Emergency bypass: relaunch with %s=1 set in the "
        "environment (a shell `export` in a Bash tool call does NOT reach this hook). "
        "File: %s" % (why, _BYPASS_ENV, path))


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    reason = decide(event, os.environ)
    if reason is not None:
        sys.stderr.write("SKILL-EDIT GUARD: " + reason + "\n")
        return 2  # PreToolUse: non-zero blocks the tool call and feeds stderr back to the model
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        sys.exit(0)
