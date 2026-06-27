#!/usr/bin/env python3
"""SessionStart hook: inject the using-bitranox-skills skill as session context.

Bitranox's counterpart to what the superpowers plugin does for using-superpowers:
on session startup, /clear, and after compaction, load
skills/using-bitranox-skills/SKILL.md and return it as additionalContext, so the
skills-first discipline is active from the first turn and survives compaction -
without the user having to invoke the skill manually. This is what lets the
superpowers marketplace be dropped while keeping its bootstrap behaviour.

Emits the Claude Code SessionStart contract on stdout:
  {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}
json.dumps does the escaping (newlines/quotes), so no hand-rolled JSON escaping.

Pure standard library. Every failure path emits nothing and exits 0, so a broken
or slow hook never blocks or delays a session.
"""
import json
import os
import sys
from pathlib import Path

from self_improve_signals import audit_file

BANNER = (
    "<EXTREMELY-IMPORTANT>\n"
    "Below is the full content of your 'bitranox:using-bitranox-skills' skill - your standing "
    "instruction for finding and using skills. It establishes that you MUST invoke a relevant "
    "skill (via the Skill tool) before responding. Follow it for the whole session.\n\n"
)


def skill_path():
    """Locate using-bitranox-skills/SKILL.md from CLAUDE_PLUGIN_ROOT, else from this file."""
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    base = Path(root) if root else Path(__file__).resolve().parent.parent
    return base / "skills" / "using-bitranox-skills" / "SKILL.md"


def build_context():
    """Return the additionalContext string, or None if the skill cannot be read."""
    try:
        text = skill_path().read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 - missing/unreadable skill: inject nothing, never wedge
        return None
    if not text.strip():
        return None
    return BANNER + text + "\n</EXTREMELY-IMPORTANT>"


def audit_context():
    """Surface (and consume) a pending SessionEnd miss-audit for this project, if any.

    The SessionEnd hook (self-improve-audit.py) writes candidate gate-misses to a per-project
    file; here we inject it once so the model reviews them, then delete it so it is not
    resurfaced. cwd comes from the SessionStart event (stdin), else the env / cwd fallback.
    """
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: fall back, never wedge
        event = {}
    proj = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        path = audit_file(proj)
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8").strip()
        path.unlink()  # consume once
    except Exception:  # noqa: BLE001 - unreadable/undeletable: skip, never wedge
        return None
    return text or None


def main():
    parts = [p for p in (build_context(), audit_context()) if p]
    if not parts:
        return 0
    out = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n\n".join(parts),
        }
    }
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never block a session
        sys.exit(0)
