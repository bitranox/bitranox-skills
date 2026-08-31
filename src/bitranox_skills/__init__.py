"""The bitranox Claude Code skill collection, installable without the plugin marketplace.

The wheel carries the whole plugin tree as package data under `bitranox_skills/plugin`,
so the version a user installs and the skills they get are always the same build.
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = ["PLUGIN_DIR", "SKILLS_DIR", "plugin_version", "skill_names"]

PLUGIN_DIR = Path(__file__).resolve().parent / "plugin"
SKILLS_DIR = PLUGIN_DIR / "skills"


def plugin_version() -> str:
    """The version recorded in the bundled plugin manifest.

    Read from the manifest rather than from package metadata so it still answers when the
    package is run from a source checkout, where no distribution is installed.
    """
    manifest = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
    return str(json.loads(manifest.read_text(encoding="utf-8"))["version"])


def skill_names() -> list[str]:
    """Every bundled skill name, sorted. A directory counts only when it has a SKILL.md."""
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(d.name for d in SKILLS_DIR.iterdir() if (d / "SKILL.md").is_file())
