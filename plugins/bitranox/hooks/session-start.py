#!/usr/bin/env python3
"""SessionStart hook: inject the SMALL session essentials - the memory-retrieval standing rule,
a pending miss-audit, and the self-silencing nudges.

The big skills-first banner is emitted by its OWN hook command (session-banner.py). The split is
load-bearing: the harness persists an oversized additionalContext to a file and injects only a
~2KB preview, so anything appended AFTER a ~10KB banner (this hook's essentials, before the split)
never reached context. Emitted separately and kept SMALL (see the size test), the essentials always
land inline.

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

from self_improve_signals import (
    audit_file,
    dream_due,
    knowledge_store_empty,
    load_config,
    mark_seeded,
    project_unseeded,
)


_RETRIEVAL_TMPL = (
    "<BITRANOX-MEMORY-RETRIEVAL>\n"
    "Your loaded context includes a memory index: lines of the form\n"
    "  - [Title](mem:<slug>) - hook\n"
    "in the CLAUDE.local.md cascade. Those are always-loaded POINTERS - the Title + hook are present, "
    "but the full fact BODY is NOT preloaded. When a hook is relevant to your CURRENT task and you need "
    "the detail behind it, retrieve that body ON DEMAND by Reading:\n"
    "  %(anchor)s/.claude-memory/facts/<slug>.md\n"
    "(example: mem:no-em-dashes -> %(anchor)s/.claude-memory/facts/no-em-dashes.md)\n"
    "Do this mid-task whenever a relevant hook needs its body; the per-prompt recall hook only surfaces "
    "keyword matches at prompt time, so pull anything else yourself. Read a body ONLY when its hook is "
    "genuinely relevant - never bulk-read the index.\n"
    "</BITRANOX-MEMORY-RETRIEVAL>"
)


def retrieval_context(proj):
    """A standing rule teaching the model to fetch a fact body ON DEMAND from the central UUID store,
    with the concrete anchor path baked in. Returns None when there is no anchor or no store yet (so a
    fresh project with no facts is not told to retrieve from an empty store). Fail-open."""
    try:
        import uuid_store as us
        anchor = us.resolve_anchor(proj)
        if anchor is None or not us.central_facts_dir(anchor).is_dir():
            return None
        return _RETRIEVAL_TMPL % {"anchor": str(anchor)}
    except Exception:  # noqa: BLE001 - a hook must never wedge a session
        return None


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


_DREAM_NUDGE = (
    "<BITRANOX-DREAM-DUE>\n"
    "A memory consolidation is due. Run bitranox:meta-dream-tree to dedup / merge / generalize / prune "
    "the memory store (it backs up first), or say 'skip'. Adjust via bitranox:meta-memory-settings: "
    "dream_mode 'off' silences this, 'auto' stops the per-change asking.\n"
    "</BITRANOX-DREAM-DUE>"
)


def dream_nudge(proj):
    """Self-silencing nudge to run meta-dream-tree when a consolidation is due (off when mode=off)."""
    try:
        if not dream_due(proj):
            return None
    except Exception:  # noqa: BLE001 - detection must never wedge the session
        return None
    return _DREAM_NUDGE


_NEWPROJECT_NUDGE = (
    "<BITRANOX-NEW-PROJECT>\n"
    "This project has no memory yet. Run bitranox:meta-collect-knowledge (/collect-knowledge) to seed "
    "it from your existing knowledge tree, so it starts informed. Say 'skip' to ignore.\n"
    "</BITRANOX-NEW-PROJECT>"
)


def _collect_skill_available():
    """True if the meta-collect-knowledge skill is installed (Phase 2). The new-project nudge stays
    dormant until it is, so it never points at a missing skill."""
    try:
        root = os.environ.get("CLAUDE_PLUGIN_ROOT")
        base = Path(root) if root else Path(__file__).resolve().parent.parent
        return (base / "skills" / "meta-collect-knowledge" / "SKILL.md").is_file()
    except Exception:  # noqa: BLE001
        return False


def newproject_nudge(proj):
    """Fire ONCE for a fresh, unseeded project - only when the collect skill is installed AND there
    is knowledge elsewhere to seed from. Marks the project seeded so it self-silences."""
    try:
        if not _collect_skill_available():
            return None
        if not project_unseeded(proj) or knowledge_store_empty(proj):
            return None
        mark_seeded(proj)  # fire once
    except Exception:  # noqa: BLE001 - never wedge the session
        return None
    return _NEWPROJECT_NUDGE


def _nudges_on():
    """Honor the user's config: nudges can be switched off (decision recorded, not re-asked)."""
    try:
        return bool(load_config().get("nudges", True))
    except Exception:  # noqa: BLE001
        return True


def _self_heal(proj):
    """Best-effort repair of the project's memory chain every session (missing/malformed stores,
    markers, index files). Fail-open: any error is swallowed so a broken store never wedges a start."""
    try:
        import memory_engine
        memory_engine.heal(proj)
    except Exception:  # noqa: BLE001 - a hook must never block a session
        pass


def main():
    event = _read_event()
    proj = _proj(event)
    _self_heal(proj)
    parts = [retrieval_context(proj), audit_context(proj)]
    if _nudges_on():  # the user can switch session nudges off (recorded in config)
        parts += [dream_nudge(proj), newproject_nudge(proj)]
    ctx = [p for p in parts if p]
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
