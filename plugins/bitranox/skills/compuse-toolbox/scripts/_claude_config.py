# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Where Claude Code keeps its configuration, for the compuse-toolbox jigs that read it.

Not a tool: a sibling module the jigs import by bare name (`from _claude_config import ...`), the
same way they import `_cli_envelope`. Claude Code moves its whole config dir (settings, plugins,
the `projects/` transcripts) to CLAUDE_CONFIG_DIR when that variable is set, so a jig defaulting
to `~/.claude/projects` reads the wrong corpus inside a sandbox or on a machine that moved it.

The rule is a copy of the plugin's `hooks/claude_paths.config_dir()`: CLAUDE_CONFIG_DIR when set
and not blank, else `~/.claude`, with NO fallback to `~/.claude` when it is set. It is copied
rather than imported because a jig runs on its own with only its sibling scripts beside it; the
compuse-toolbox tests pin the two copies to the same answers. Standard library only, resolved per
call so a test (or a run) that changes HOME or CLAUDE_CONFIG_DIR after import is honoured.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["config_dir", "projects_dir"]


def config_dir() -> Path:
    """Claude Code's config dir: CLAUDE_CONFIG_DIR when set and not blank, else ~/.claude."""
    configured = os.environ.get("CLAUDE_CONFIG_DIR", "")
    return Path(configured) if configured.strip() else Path.home() / ".claude"


def projects_dir() -> Path:
    """The transcript corpus, `<config dir>/projects`."""
    return config_dir() / "projects"
