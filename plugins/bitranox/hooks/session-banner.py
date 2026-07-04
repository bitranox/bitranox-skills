#!/usr/bin/env python3
"""SessionStart hook: inject the meta-using-bitranox-skills skill as session context.

This is the BIG inject (the ~10KB skills-first standing instruction), deliberately emitted by its
OWN hook command, separate from session-start.py's small essentials (retrieval rule, audit, nudges).
The harness persists an oversized additionalContext to a file and injects only a ~2KB preview, so
anything appended AFTER a large banner never reached context - splitting the two means the small
essentials always land inline regardless of the banner's size, and only the banner pays the
persist-preview cost. (Shrinking the banner itself under the cap is the gate skill's own concern.)

Emits the Claude Code SessionStart contract on stdout. Pure standard library. Every failure path
emits nothing and exits 0, so a broken hook never blocks a session.
"""
import json
import os
import sys
from pathlib import Path

BANNER = (
    "<EXTREMELY-IMPORTANT>\n"
    "Below is the full content of your 'bitranox:meta-using-bitranox-skills' skill - your standing "
    "instruction for finding and using skills. It establishes that you MUST invoke a relevant "
    "skill (via the Skill tool) before responding. Follow it for the whole session.\n\n"
)


def skill_path():
    """Locate meta-using-bitranox-skills/SKILL.md from CLAUDE_PLUGIN_ROOT, else from this file."""
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    base = Path(root) if root else Path(__file__).resolve().parent.parent
    return base / "skills" / "meta-using-bitranox-skills" / "SKILL.md"


def build_context():
    """Return the additionalContext string, or None if the skill cannot be read."""
    try:
        text = skill_path().read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 - missing/unreadable skill: inject nothing, never wedge
        return None
    if not text.strip():
        return None
    return BANNER + text + "\n</EXTREMELY-IMPORTANT>"


def main():
    ctx = build_context()
    if not ctx:
        return 0
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx},
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never block a session
        sys.exit(0)
