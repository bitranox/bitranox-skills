"""Where this plugin keeps its machine-local state: the Claude config dir, then the audit dir.

Claude Code moves its whole configuration (settings, plugins, transcripts) to `CLAUDE_CONFIG_DIR`
when that variable is set, and A/B arms and install tests set it to a throwaway directory. Every
reader and writer of the plugin's own state resolves its root here, so a sandbox neither reads
nor writes the real `~/.claude/self-improve-audit`. Resolved per call, so a test (or a hook run)
that changes `HOME` or `CLAUDE_CONFIG_DIR` is honoured.

Decisions
---------
- Decision: follow CLAUDE_CONFIG_DIR with NO fallback to ~/.claude.
  Why: a fallback read would let every sandbox read the real state (an owed-nap flag, shadow
  logs), the leak this module closes, in the other direction. The user chose this on 2026-11-08
  after first picking a fallback (OPEN-WORK [25], queue entry 19).
  Evidence: tests/test_claude_paths.py.
  Reopen if: a user who sets CLAUDE_CONFIG_DIR permanently needs the old history migrated; do that
  with an explicit one-time copy, never a read fallback.

Pure standard library, no imports from this plugin, so any hook or skill script can use it.
"""

import os
from pathlib import Path

__all__ = ["audit_dir", "config_dir"]


def config_dir():
    """The Claude config dir: CLAUDE_CONFIG_DIR when set and non-empty, else ~/.claude.

    Examples:
        >>> import os
        >>> os.environ["CLAUDE_CONFIG_DIR"] = "/opt/claude-arm"
        >>> str(config_dir()).replace(os.sep, "/")
        '/opt/claude-arm'
        >>> del os.environ["CLAUDE_CONFIG_DIR"]
    """
    override = os.environ.get("CLAUDE_CONFIG_DIR", "")
    return Path(override) if override.strip() else Path.home() / ".claude"


def audit_dir():
    """The plugin's audit and state dir, `<config dir>/self-improve-audit`."""
    return config_dir() / "self-improve-audit"
