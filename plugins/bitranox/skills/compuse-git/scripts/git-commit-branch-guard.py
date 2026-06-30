#!/usr/bin/env python3
"""OPT-IN PreToolUse(Bash) guard: warn before a `git commit` when the checkout state is risky.

For when multiple agents/sessions share ONE working copy: the branch, HEAD, and index can change under
you between reads, so a commit lands on the wrong branch or on a stale base. This is NOT auto-wired - you
opt in by adding it to your `~/.claude/settings.json` PreToolUse "Bash" hooks (launch it through this
plugin's `run-python.sh` so it works cross-platform):

    {"type": "command", "command": "bash <plugin>/hooks/run-python.sh <plugin>/skills/compuse-git/scripts/git-commit-branch-guard.py"}

Two tiers, to stay low-noise in ANY workflow:
  - ALWAYS: warn if local HEAD is BEHIND / DIVERGED from its upstream (origin advanced under you). Being
    only ahead is normal -> silent.
  - OPT-IN via `GIT_GUARD_STRICT_BRANCH=1`: also warn when not on the default branch (auto-detected from
    `origin/HEAD`) or HEAD is detached. Off by default, because "not on the default branch" is expected
    in a feature-branch workflow and would be pure noise there.

Scope (optional): `GIT_GUARD_REPOS="repoA,repoB"` limits the guard to those repo toplevel basenames;
unset = every repo. WARN only, fail-open: writes to stderr and exits 0 on every path, so it never blocks
a commit and a broken guard never wedges a turn. Pure standard library.
"""
import json
import os
import re
import subprocess
import sys

SEP = re.compile(r"&&|\|\||[;\n|]")
_TRUE = {"1", "true", "yes", "on"}


def _is_git_commit(command):
    for segment in SEP.split(command):
        toks = segment.split()
        if "git" in toks and "commit" in toks:
            return True
    return False


def _git(cwd, *args):
    """Run a git command; return stripped stdout, or None on any failure (fail-open)."""
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5)
    except Exception:  # noqa: BLE001
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _truthy(name):
    return (os.environ.get(name) or "").strip().lower() in _TRUE


def _default_branch(cwd):
    """The remote's default branch (e.g. 'main'), from origin/HEAD; None if undetermined."""
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
    repos = {r.strip() for r in (os.environ.get("GIT_GUARD_REPOS") or "").split(",") if r.strip()}
    if repos and os.path.basename(toplevel) not in repos:
        return 0  # scoped out

    warnings = []
    behind = _behind_count(cwd)
    if behind:  # >0: upstream has commits you don't -> behind or diverged
        warnings.append(
            "local HEAD is %d commit(s) behind/diverged from its upstream - origin advanced (a parallel "
            "session?). Fetch and check ahead/behind before committing." % behind
        )
    if _truthy("GIT_GUARD_STRICT_BRANCH"):
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
