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
  - UNLESS this session holds a fresh meta-skill-writer receipt: `skill_receipt.is_fresh`, keyed by the
    event's `session_id`, valid for 8 hours. Step 0 of meta-skill-writer arms it by running
    `skill_receipt.py start meta-skill-writer`, so entering the procedure is what allows the edit, and
    a receipt from another session never does.
  - UNLESS the env `BITRANOX_SKILL_WRITER` is set: the emergency bypass. NOTE: a shell `export` in a
    Bash tool call does NOT reach this hook (separate process) - the env must be set at SESSION start.

Errors split by direction. Unparseable stdin and any error escaping `main` fail OPEN (exit 0): a broken
guard must never wedge a turn. An error while consulting the receipt store fails CLOSED: it counts as
no receipt and the edit is blocked, because a store that cannot be read must not disarm the guard.
Pure standard library; launched via run-python.sh so it works on Windows too.
"""
import json
import os
import posixpath
import re
import sys

# IGNORECASE because macOS and Windows filesystems are case-insensitive: there `Skills/x/skill.md`
# opens the real SKILL.md, and the guard cannot tell from a path string which filesystem it names.
_SKILL_MD = re.compile(r"(?:^|/)skills/[^/]+/SKILL\.md$", re.IGNORECASE)
_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_BYPASS_ENV = "BITRANOX_SKILL_WRITER"


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
    try:
        import skill_receipt
        # The EVENT's session id, so the receipt must belong to THIS session. Without it the
        # check answered "somebody on this machine started the procedure recently" - a different
        # claim, and routinely true on a machine running several sessions at once.
        if skill_receipt.is_fresh("meta-skill-writer", session_id=event.get("session_id")):
            return None                                # the skill-writer procedure was ENTERED
    except Exception:  # noqa: BLE001 - a broken receipt store must not wedge; fall through to deny
        pass
    return (
        "Editing a SKILL.md directly is blocked. Skills change ONLY through bitranox:meta-skill-writer "
        "(RED-GREEN-REFACTOR + its checklist); invoke that skill via the Skill tool - its step 0 issues "
        "the session receipt this guard checks. Emergency bypass: relaunch with %s=1 set in the "
        "environment (a shell `export` in a Bash tool call does NOT reach this hook). "
        "File: %s" % (_BYPASS_ENV, path))


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
