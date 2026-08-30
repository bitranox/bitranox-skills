#!/usr/bin/env python3
"""PreToolUse(Bash) guard: warn before a `git commit` when the checkout state is risky.

For when multiple agents/sessions share ONE working copy: branch/HEAD/index can change under you between
reads, so a commit lands on the wrong branch or on a stale base. Always active (wired in hooks.json), but
tuned to stay silent in normal solo / feature-branch work:

  - ALWAYS (every repo): warn if local HEAD is BEHIND / DIVERGED from its upstream - origin advanced under
    you. Being only ahead, or having no upstream, is normal -> silent. (In feature-branch work you push
    your own branch, so you are ahead, not behind: this effectively fires only when something moved your
    upstream under you - the shared-checkout hazard.)
  - PER-REPO, off by default: warn when not on the default branch (auto-detected from `origin/HEAD`) or
    HEAD is detached - ONLY for repos whose toplevel basename is in `GIT_GUARD_STRICT_REPOS` (comma list).
    Off by default because "not on the default branch" is expected in a feature-branch workflow and would
    be pure noise there; enable it for repos you work on a single branch directly.

WARN only, fail-open: writes to stderr and exits 0 on every path, so it never blocks a commit and a broken
guard never wedges a turn. Standard library plus the sibling shell_text helper; launched via run-python.sh
so it works on Windows too.
"""
import json
import os
import subprocess
import sys

from shell_text import is_git_verb, iter_segments, strip_heredoc_bodies

_COMMIT_VERBS = frozenset({"commit"})


def _is_git_commit(command):
    """True when a STATEMENT in `command` is a git commit - not merely text mentioning one.

    This asks shell_text the same question the repo gate asks, rather than keeping a second
    matcher here. The bag-of-tokens test it replaces split on separators and then checked only
    whether both words appeared ANYWHERE in a segment, so `echo "run git commit later"`, a
    trailing `# ... commit ...` comment on a read-only `git log`, and a heredoc body all counted:
    each spent 2-4 git subprocesses and warned about a commit that was not happening.
    """
    for _at, segment in iter_segments(strip_heredoc_bodies(command or "")):
        if is_git_verb(segment.strip().lstrip("(").strip(), _COMMIT_VERBS):
            return True
    return False


def _git(cwd, *args):
    """Run a git command; return stripped stdout, or None on any failure (fail-open)."""
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5)
    except Exception:  # noqa: BLE001
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _strict_repos():
    return {r.strip() for r in (os.environ.get("GIT_GUARD_STRICT_REPOS") or "").split(",") if r.strip()}


def _default_branch(cwd):
    """The remote's default branch (e.g. 'main') from origin/HEAD; None if undetermined."""
    ref = _git(cwd, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")  # 'origin/main'
    return ref.split("/", 1)[1] if ref and "/" in ref else None


def _behind_count(cwd):
    """Commits in the upstream not in HEAD (origin advanced under you); None if no upstream."""
    out = _git(cwd, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")  # 'ahead\tbehind'
    if not out:
        return None
    parts = out.replace("\t", " ").split()
    try:
        return int(parts[1])
    except (IndexError, ValueError):
        return None


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if not command or not _is_git_commit(command):
        return 0
    cwd = event.get("cwd") or os.getcwd()

    toplevel = _git(cwd, "rev-parse", "--show-toplevel")
    if not toplevel:
        return 0  # not a git repo

    warnings = []
    behind = _behind_count(cwd)
    if behind:  # >0: upstream has commits you don't -> behind or diverged
        warnings.append(
            "local HEAD is %d commit(s) behind/diverged from its upstream - origin advanced (a parallel "
            "session?). Fetch and check ahead/behind before committing." % behind
        )
    if os.path.basename(toplevel) in _strict_repos():
        branch = _git(cwd, "symbolic-ref", "--short", "-q", "HEAD")  # '' / None if detached
        default = _default_branch(cwd)
        if not branch:
            warnings.append("HEAD is DETACHED - committing here will not advance any branch.")
        elif default and branch != default:
            warnings.append(
                "you are on branch '%s', not the default '%s'. A parallel session may have switched the "
                "checkout; this commit may land on the wrong branch." % (branch, default)
            )
    if not warnings:
        return 0
    sys.stderr.write(
        "SHARED-CHECKOUT CHECK: %s\nStage only your own files (not `git add -A`) and confirm branch/HEAD "
        "before committing.\n" % " ".join(warnings)
    )
    return 0  # warn only, never block


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        sys.exit(0)
