#!/usr/bin/env python3
"""Resolve and ensure the working-tree directory SDD uses for its short-lived
artifacts: task briefs, implementer reports, review packages, and the progress
ledger. Print the directory's absolute path.

The workspace lives in the working tree (not under .git/) because Claude Code
treats .git/ as a protected path and denies agent writes there - which blocks
an implementer subagent from writing its report file. A self-ignoring
.gitignore keeps the workspace out of `git status` and out of accidental
commits without modifying any tracked file.

Single source of truth for the workspace location, so task_brief and
review_package cannot drift to different directories.

Usage: python3 sdd_workspace.py
"""
import subprocess
import sys
from pathlib import Path


def workspace_dir(cwd=None):
    """Ensure <repo-root>/.bitranox/sdd exists (self-ignoring) and return its resolved Path."""
    root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd, capture_output=True, text=True, check=True,
    ).stdout.strip()
    d = Path(root) / ".bitranox" / "sdd"
    d.mkdir(parents=True, exist_ok=True)
    (d / ".gitignore").write_text("*\n", encoding="utf-8")
    return d.resolve()


def main(argv=None):
    try:
        print(workspace_dir())
    except (subprocess.CalledProcessError, OSError) as exc:
        print("cannot resolve the git working tree: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
