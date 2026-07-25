# /// script
# requires-python = ">=3.10"
# ///
"""Report git state for one or more repos: branch, HEAD vs upstream (ahead/behind/diverged), dirty
count, and staged files - read-only.

Why: before a risky commit, push, or bulk multi-repo operation you want the same check every time -
which branch, is HEAD in sync with its upstream, is the working tree dirty, what is staged. This
runs those checks once across one or many repos instead of hand-typing `git status` / `git rev-list`
per repo. Exit status is 1 if any repo is out of sync (behind/ahead/diverged or has no upstream), so
it doubles as a pre-push guard.

Run: `uv run scripts/git_state.py [REPO ...] [--root DIR]`
  git_state.py                 # the current directory
  git_state.py repoA repoB     # named repos
  git_state.py --root ~/src    # every .git repo found under a directory
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_branch_status(text: str) -> dict:
    """Parse `git status --porcelain=v2 --branch` output into a state dict (pure; unit-testable)."""
    branch = upstream = None
    ahead = behind = dirty = 0
    staged: list[str] = []
    for line in text.splitlines():
        if line.startswith("# branch.head "):
            branch = line.split(" ", 2)[2].strip()
        elif line.startswith("# branch.upstream "):
            upstream = line.split(" ", 2)[2].strip()
        elif line.startswith("# branch.ab "):
            for tok in line.split()[2:]:
                if tok.startswith("+"):
                    ahead = int(tok[1:])
                elif tok.startswith("-"):
                    behind = int(tok[1:])
        elif line[:2] in ("1 ", "2 "):                       # a tracked change (ordinary / renamed)
            dirty += 1
            fields = line.split(" ")
            if fields[1][0] != ".":                          # index (staged) status is not "."
                staged.append(fields[8] if line[0] == "1" else fields[9].split("\t")[0])
        elif line[:2] in ("u ", "? "):                       # unmerged or untracked
            dirty += 1
    in_sync = upstream is not None and ahead == 0 and behind == 0
    return {"branch": branch, "upstream": upstream, "ahead": ahead, "behind": behind,
            "dirty": dirty, "staged": staged, "in_sync": in_sync}


def git_state(repo) -> dict:
    """Run git in `repo` and return its parsed state (adds "repo" + "error")."""
    try:
        out = subprocess.run(["git", "-C", str(repo), "status", "--porcelain=v2", "--branch"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"repo": str(repo), "error": str(exc)}
    if out.returncode != 0:
        return {"repo": str(repo), "error": (out.stderr or "not a git repo").strip()}
    state = parse_branch_status(out.stdout)
    state["repo"] = str(repo)
    return state


def find_repos(root) -> list[str]:
    """Walk `root` and return every directory that contains a .git (does not descend into .git)."""
    import os
    repos = []
    for dirpath, dirs, _files in os.walk(str(root)):
        if ".git" in dirs:
            repos.append(dirpath)
            dirs[:] = [d for d in dirs if d != ".git"]       # don't descend into the repo's own .git
    return sorted(repos)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Report git branch / sync / dirty state for repos.")
    ap.add_argument("repos", nargs="*", default=["."], help="repo paths (default: cwd)")
    ap.add_argument("--root", help="walk this dir for .git repos instead of listing paths")
    args = ap.parse_args(argv)
    targets = find_repos(args.root) if args.root else args.repos
    rc = 0
    for repo in targets:
        s = git_state(repo)
        if "error" in s:
            print(f"{s['repo']:40} ERROR: {s['error']}")
            rc = 1
            continue
        flags = []
        if not s["in_sync"]:
            flags.append(f"ahead {s['ahead']}/behind {s['behind']}" if s["upstream"] else "no-upstream")
            rc = 1
        if s["dirty"]:
            flags.append(f"dirty {s['dirty']}")
        print(f"{s['repo']:40} {str(s['branch']):20} {'OK' if not flags else ' '.join(flags)}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
