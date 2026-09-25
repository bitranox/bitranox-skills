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

Usage: python3 sdd_workspace.py      (takes no arguments; exit 0 printed, 2 could not)
"""
import subprocess
import sys
from pathlib import Path

USAGE = "usage: python3 sdd_workspace.py  (takes no arguments; prints the workspace path)"


class WorkspaceError(RuntimeError):
    """The workspace could not be resolved or made; str() is the one-line reason for stderr.

    workspace_dir() raises only this family, so a caller has ONE thing to catch; an OSError from
    mkdir used to escape beside RepoRootError and each caller had to remember both.
    """


class RepoRootError(WorkspaceError):
    """git could not name the working tree: not a repository, or git could not be run."""


def repo_root(cwd=None):
    """The working tree's top directory, EXACTLY as git names it.

    Only the one trailing newline git appends is removed: .strip() also ate a trailing space in
    the directory name and put the workspace in a sibling OUTSIDE the repo. Decoded as UTF-8
    (what git prints) with surrogateescape, never the locale codec: on a cp1252 Windows machine
    that turned a non-ASCII path into a different, wrong one.
    """
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, check=True,
            text=True, encoding="utf-8", errors="surrogateescape",
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        raise RepoRootError("cannot resolve the git working tree: %s" % exc) from exc
    return done.stdout.removesuffix("\n")


def workspace_dir(cwd=None):
    """Ensure <repo-root>/.bitranox/sdd exists (self-ignoring) and return its resolved Path.

    Raises WorkspaceError (RepoRootError when there is no working tree) and nothing else.
    """
    d = Path(repo_root(cwd)) / ".bitranox" / "sdd"
    try:
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitignore").write_text("*\n", encoding="utf-8")
    except OSError as exc:
        raise WorkspaceError("cannot create the workspace: %s" % exc) from exc
    return d.resolve()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        # --help included: nothing may be created by a run that was only asking how to run it.
        print(USAGE, file=sys.stderr)
        return 2
    try:
        path = workspace_dir()
    except WorkspaceError as exc:
        print(exc, file=sys.stderr)
        return 2
    try:
        print(path)
    except UnicodeEncodeError:
        # Printing an escaped or replaced path would hand the caller a directory that does not
        # exist; refusing is the only safe answer on a console that cannot encode it.
        print("cannot print the workspace path in this console's encoding; set "
              "PYTHONIOENCODING=utf-8 or call workspace_dir() from Python", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
