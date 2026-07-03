#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit) guard: a SKILL.md edit must go through the skill-writer process.

Editing a shipped `SKILL.md` by hand - skipping `bitranox:meta-skill-writer`'s RED-GREEN-REFACTOR / Iron
Law (baseline test first, sibling tests for any bundled script) - is the exact miss this guard prevents.
A skill grows into a mess by accretion when edits bypass that process; the standing "use the applicable
skill" rule is advisory prose that loses under momentum, so this is the deterministic backstop.

Decision on an `Edit`/`Write`/`MultiEdit` whose target is a `.../skills/<name>/SKILL.md`:
  - BLOCK (exit 2): the tool call is denied and the reason is fed back to the MODEL, which then redirects
    itself to meta-skill-writer. The user is NOT prompted (enforced, not asked).
  - UNLESS the env `BITRANOX_SKILL_WRITER` is set: a deliberately-declared skill-authoring session opts
    out. NOTE: a shell `export` in a Bash tool call does NOT reach this hook (separate process) - the env
    must be set at SESSION start.

Fail-open: any parse/IO error -> exit 0 (a broken guard must never wedge a turn). Pure standard library;
launched via run-python.sh so it works on Windows too.
"""
import json
import os
import re
import sys

_SKILL_MD = re.compile(r"(?:^|/)skills/[^/]+/SKILL\.md$")
_TOOLS = {"Edit", "Write", "MultiEdit"}
_BYPASS_ENV = "BITRANOX_SKILL_WRITER"


def decide(event, env):
    """Pure: (event, env) -> a block-reason string (deny the tool call), or None to allow silently."""
    if (event.get("tool_name") or "") not in _TOOLS:
        return None
    path = ((event.get("tool_input") or {}).get("file_path") or "").replace("\\", "/")
    if not _SKILL_MD.search(path):
        return None
    if env.get(_BYPASS_ENV):
        return None                                    # deliberately-declared skill-authoring session
    return (
        "Editing a SKILL.md directly is blocked. Skills change ONLY through bitranox:meta-skill-writer "
        "(RED-GREEN-REFACTOR: baseline test first, sibling tests for any script). Invoke that skill. For "
        "a deliberate skill-authoring session, relaunch with %s=1 set in the environment (a shell "
        "`export` in a Bash tool call does NOT reach this hook - it must be set at session start). "
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
