#!/usr/bin/env python3
"""SessionStart hook: inject the meta-using-bitranox-skills skill as session context.

Bitranox's counterpart to what the superpowers plugin does for using-superpowers:
on session startup, /clear, and after compaction, load
skills/meta-using-bitranox-skills/SKILL.md and return it as additionalContext, so the
skills-first discipline is active from the first turn and survives compaction -
without the user having to invoke the skill manually. This is what lets the
superpowers marketplace be dropped while keeping its bootstrap behaviour.

Emits the Claude Code SessionStart contract on stdout:
  {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}
plus an optional top-level "systemMessage" - a one-line, self-silencing reminder to enable
marketplace auto-update when it is off (it cannot set it; only the user/admin can).
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


def _read_event():
    try:
        return json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: fall back, never wedge
        return {}


def _proj(event):
    return event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def audit_context(proj):
    """Surface (and consume) a pending SessionEnd miss-audit for this project, if any.

    The SessionEnd hook (self-improve-audit.py) writes candidate gate-misses to a per-project
    file; here we inject it once so the model reviews them, then delete it so it is not
    resurfaced.
    """
    try:
        path = audit_file(proj)
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8").strip()
        path.unlink()  # consume once
    except Exception:  # noqa: BLE001 - unreadable/undeletable: skip, never wedge
        return None
    return text or None


_NUDGE = (
    "bitranox-skills: marketplace auto-update is OFF, so you will not get fixes and new skills "
    "automatically. Enable it: /plugin > Marketplaces > bitranox-skills > Enable auto-update, or "
    'add "autoUpdate": true to the "bitranox-skills" entry under extraKnownMarketplaces in '
    "~/.claude/settings.json. (Auto-update runs at startup; a running session still needs "
    "/reload-plugins or a restart to load an update.) To silence this without enabling, create "
    "~/.claude/.bitranox-no-autoupdate-nudge"
)


def _autoupdate_enabled(proj):
    """True if extraKnownMarketplaces['bitranox-skills'].autoUpdate is set in user/project settings."""
    candidates = [
        Path.home() / ".claude" / "settings.json",
        Path(proj) / ".claude" / "settings.json",
        Path(proj) / ".claude" / "settings.local.json",
    ]
    for c in candidates:
        try:
            data = json.loads(c.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - missing/invalid: skip this source
            continue
        entry = (data.get("extraKnownMarketplaces") or {}).get("bitranox-skills") or {}
        if entry.get("autoUpdate") is True:
            return True
    return False


def autoupdate_nudge(proj):
    """A one-line, self-silencing reminder to enable marketplace auto-update; None when off."""
    try:
        optout = Path.home() / ".claude" / ".bitranox-no-autoupdate-nudge"
        if optout.exists() or _autoupdate_enabled(proj):
            return None
    except Exception:  # noqa: BLE001 - never let detection wedge the session
        return None
    return _NUDGE


def main():
    event = _read_event()
    proj = _proj(event)
    ctx = [p for p in (build_context(), audit_context(proj)) if p]
    nudge = autoupdate_nudge(proj)
    if not ctx and not nudge:
        return 0
    out = {}
    if ctx:
        out["hookSpecificOutput"] = {
            "hookEventName": "SessionStart",
            "additionalContext": "\n\n".join(ctx),
        }
    if nudge:
        out["systemMessage"] = nudge
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never block a session
        sys.exit(0)
