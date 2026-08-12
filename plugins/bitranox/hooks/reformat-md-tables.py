#!/usr/bin/env python3
"""PostToolUse(Write|Edit|MultiEdit|Bash) hook: auto-realign markdown tables after a write.

Formatter-on-save for markdown tables (Mode A). When a markdown file is written or edited, reuse the
docs-md-table-formatting skill's `reformat_tables.reformat_file()` to realign its tables in place, so a
table can never ship misaligned and the "reformat after editing a table" rule cannot be skipped.

Bash is covered too, and that is the point: Write and Edit declare their target, so the rule held
for them, while a heredoc, a `python3 -` script or `sed -i` wrote markdown with no declared path
and slipped past entirely. For a Bash event the hook looks at which markdown actually changed
under the working directory instead of parsing the command, which cannot see a runtime path.

Silent by design: it just fixes the file. `reformat_tables` is safe-by-design (it bails on tables
with inconsistent column counts and skips non-markdown fenced code blocks), so a normal edit is left
alone. Pure standard library plus the shipped reformat script. Every failure path exits 0, so a
broken hook never wedges a turn.
"""
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

_MD_SUFFIXES = (".md", ".markdown", ".mdown", ".mkd")

# Bash writes markdown without declaring a path, so the fallback looks at what
# changed. Bounded so a big tree cannot make the hook slow: only files touched
# inside the window, only this many of them, and never inside a vendored tree.
_BASH_WINDOW_SECONDS = 120
_BASH_FILE_CAP = 40
_SKIP_DIRS = frozenset({".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})

# git subcommands that rewrite tracked files wholesale. Every markdown they touch
# gets a fresh mtime and so looks just-written to the scan below, but none of it
# was authored by the operator - it is whatever the target revision holds.
_GIT_TREE_WRITERS = frozenset({
    "checkout", "switch", "merge", "rebase", "pull", "clone", "reset",
    "stash", "cherry-pick", "revert", "am", "apply", "restore", "worktree",
})
_GIT_CALL_RE = re.compile(r"\bgit\b(?:\s+-[^\s]+(?:\s+[^\s]+)?)*\s+([a-z-]+)")


def _rewrites_the_tree(command: str) -> bool:
    """Whether a shell command runs a git subcommand that rewrites tracked files.

    The path-guessing fallback below must not fire for these. Reformatting a file
    git just wrote is never what was asked for, and mid-operation it is
    destructive: a `git merge` in a re-cut sequence aborted with "your local
    changes would be overwritten" because this hook had modified the files the
    next merge needed, leaving a half-assembled integration branch.

    Matched on the SUBCOMMAND, so read-only git (log, status, diff) still allows
    the fallback - a doc written beside `git log` is the operator's.
    """
    return any(sub in _GIT_TREE_WRITERS for sub in _GIT_CALL_RE.findall(command))


def _reformat_file_fn():
    """Import reformat_file() from the docs-md-table-formatting skill (resolved from the plugin root)."""
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    base = Path(root) if root else Path(__file__).resolve().parent.parent
    script = base / "skills" / "docs-md-table-formatting" / "reformat_tables.py"
    spec = importlib.util.spec_from_file_location("_bx_reformat_tables", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.reformat_file


def _markdown_paths_from_bash(event) -> list[str]:
    """Return markdown files a Bash command just wrote, newest-first.

    Write and Edit announce their target in ``file_path``; Bash does not. A
    heredoc, a ``python3 -`` script or a ``sed -i`` writes markdown with no
    declared path at all, so the formatter-on-save silently did not apply to any
    of them and a table written that way shipped misaligned.

    Rather than parse the command, which cannot see a path built at runtime, look
    at what actually changed: markdown under the working directory whose mtime
    falls inside the window this command ran in. Reformatting is idempotent, so
    catching a neighbouring file costs nothing.

    A NESTED REPOSITORY is the exception, and it is not a cosmetic one. mtime says
    a file was written, never by whom: a `git checkout`, `merge` or `clone` inside
    a checkout vendored under the working directory restamps every file it touches,
    and the fallback then reads someone else's source as ours and restyles it.
    Measured 2026-08-07: seven docs in a vendored microsoft/openvmm mirror carried
    alignment-only churn nobody made, unnoticed until `git merge --ff-only` refused
    to run. Committing that churn would be permanent divergence from upstream for a
    style they never adopted, so any directory below the working directory that
    holds its own `.git` is pruned. The working directory's own repo stays in scope.
    """
    if _rewrites_the_tree((event.get("tool_input") or {}).get("command") or ""):
        return []
    cwd = Path(event.get("cwd") or ".")
    if not cwd.is_dir():
        return []
    cutoff = time.time() - _BASH_WINDOW_SECONDS
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(cwd):
        if len(found) >= _BASH_FILE_CAP:
            break
        here = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not (here / d / ".git").exists()]
        for name in filenames:
            if len(found) >= _BASH_FILE_CAP:
                break
            if not name.lower().endswith(_MD_SUFFIXES):
                continue
            path = here / name
            try:
                if path.stat().st_mtime >= cutoff:
                    found.append(str(path))
            except OSError:
                continue
    return found


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    reformat = None
    path = (event.get("tool_input") or {}).get("file_path") or ""
    if path.lower().endswith(_MD_SUFFIXES) and Path(path).is_file():
        targets = [path]
    elif event.get("tool_name") == "Bash":
        targets = _markdown_paths_from_bash(event)
    else:
        return 0  # not a markdown file -> nothing to align
    for target in targets:
        try:
            if reformat is None:
                reformat = _reformat_file_fn()
            reformat(target)  # in-place realign; bails safely on malformed tables
        except Exception:  # noqa: BLE001 - reformat/import failure must never wedge a turn
            return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        sys.exit(0)
