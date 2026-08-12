# /// script
# requires-python = ">=3.10"
# ///
"""Report git state for one or more repos: branch, HEAD vs origin (ahead/behind/diverged), dirty
count, and this-session's staged files. Also answers the per-FILE question `--files` mode cannot:
across a tree, which copies of a named file are tracked-and-modified, gitignored, or outside any
repo at all - `git status --porcelain -- <path>` is EMPTY for a gitignored file and for a
tracked-clean file ALIKE, so a naive check silently conflates them and only the tracked one is
restorable with `git checkout`.

Why: the shared-checkout + snapshot-before-bulk-rewrite rules mean every risky commit/bulk op is
preceded by the same hand-typed branch / HEAD==origin / dirty check. This does it once, read-only.

Run:
  uv run scripts/git_state.py                 # the current directory
  uv run scripts/git_state.py repoA repoB     # named repos
  uv run scripts/git_state.py --root ~/src    # every .git repo found under a directory
  uv run scripts/git_state.py --files CLAUDE.md --root ~/src [--json]
      # every CLAUDE.md under ~/src, classified tracked-clean / tracked-modified / ignored /
      # untracked / no-repo - never via `git status`, see classify_files() for why.

Exit status (repo mode) is 1 if any repo is out of sync (behind/ahead/diverged or has no
upstream), so this doubles as a pre-push guard. Exit status (`--files` mode) is
format-independent: 0 at least one file matched the glob, 1 none matched, 2 the walk or every
matched repo's git calls failed outright - because "nothing matched" and "could not classify
anything" must not look alike.
"""
from __future__ import annotations

import argparse
import json
import os
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
    repos = []
    for dirpath, dirs, _files in os.walk(str(root)):
        if ".git" in dirs:
            repos.append(dirpath)
            dirs[:] = [d for d in dirs if d != ".git"]       # don't descend into the repo's own .git
    return sorted(repos)


# --- --files mode: per-file tracked/ignored/untracked/no-repo classification ------------------
#
# The defect this exists to prevent: `git status --porcelain -- <path>` prints nothing for a
# gitignored file AND for a tracked-clean file - the two look identical, and only the tracked one
# is restorable with `git checkout`. So classification never touches `git status`; it is built
# from `git ls-files --error-unmatch` (tracked) and `git check-ignore` (ignored) instead, batched
# ONE call of each per repo (not per file) via `--` pathspecs and `--stdin`.

FILE_STATES = ("tracked-clean", "tracked-modified", "ignored", "untracked", "no-repo")


class _GitBatchError(Exception):
    """A batched git call for a repo failed outright (process could not run, or a real git
    error like a corrupted repo) - distinct from `ls-files --error-unmatch`/`check-ignore`
    returning their ORDINARY non-zero "some paths didn't match" exit status, which is not an
    error here and is read from stdout content, not the exit code."""


def _run_git(repo_root, *args):
    try:
        return subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True,
                              encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise _GitBatchError(str(exc)) from exc


def find_files(root, pattern) -> list[Path]:
    """Every file under `root` whose path matches `pattern` (Path.match semantics: a plain name
    like "CLAUDE.md" matches by exact basename anywhere; "*.md" matches by suffix anywhere).
    Never descends into a repo's own .git, matching find_repos()."""
    root = Path(root)
    if root.is_file():
        return [root] if root.match(pattern) else []
    out = []
    for dirpath, dirs, filenames in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in filenames:
            p = Path(dirpath) / name
            if p.match(pattern):
                out.append(p)
    return sorted(out)


def _ancestor_repo_root(start: Path):
    """Walk upward from `start` for a `.git` entry (a dir, or a worktree's gitdir FILE) using
    only the filesystem - no subprocess. Seeds the enclosing repo for the common case where
    `--root` is itself a subdirectory of a repo rather than a repo (or many repos') parent."""
    for p in (start, *start.parents):
        if (p / ".git").exists():
            return p
    return None


def _repo_roots_for(root: Path) -> list[Path]:
    """Every repo root that can own a file under `root`: repos found BY WALKING DOWN from
    `root` (find_repos - covers `root` holding many nested repos), plus `root`'s own enclosing
    repo if it has one (covers `root` being a subdirectory INSIDE a repo). A repo whose .git
    lives outside both of those is out of scope, matching find_repos()'s own reach."""
    roots = {Path(r) for r in find_repos(root)}
    ancestor = _ancestor_repo_root(root if root.is_dir() else root.parent)
    if ancestor is not None:
        roots.add(ancestor)
    return sorted(roots, key=lambda p: len(p.parts))


def _owning_repo(path: Path, repo_roots: list[Path]):
    """The deepest repo root that is an ancestor of `path`, or None (no-repo)."""
    best = None
    for r in repo_roots:
        try:
            path.relative_to(r)
        except ValueError:
            continue
        if best is None or len(r.parts) > len(best.parts):
            best = r
    return best


def _batch_tracked(repo_root, rel_paths: list[str]) -> set[str]:
    """The subset of rel_paths git considers tracked, via ONE `ls-files --error-unmatch` call
    regardless of how many paths are given. Reads the TRACKED set off stdout (the paths that
    matched) rather than the exit code, because with several pathspecs the exit code only says
    "were they ALL tracked", not which ones - and stdout still lists every one that matched even
    when others did not (verified: it does not stop at the first miss)."""
    if not rel_paths:
        return set()
    res = _run_git(repo_root, "ls-files", "--error-unmatch", "-z", "--", *rel_paths)
    if res.returncode not in (0, 1):
        raise _GitBatchError((res.stderr or "git ls-files failed").strip())
    return {p for p in res.stdout.split("\0") if p}


def _batch_ignored(repo_root, rel_paths: list[str]) -> set[str]:
    """The subset of rel_paths matched by a gitignore pattern, via ONE `check-ignore --stdin`
    call. Uses `--no-index`, which matches patterns regardless of tracked status - so a tracked
    file WOULD come back "ignored" if asked about (verified: without `--no-index`, git itself
    quietly excludes tracked files from check-ignore's output, which would make the precedence
    below true by accident rather than by this tool's own decision). Callers must therefore only
    ever pass paths `_batch_tracked` did NOT report tracked - that filtering, not git's default
    behaviour, is what deliberately makes TRACKED WIN the tracked-vs-ignored precedence here."""
    if not rel_paths:
        return set()
    try:
        res = subprocess.run(["git", "-C", str(repo_root), "check-ignore", "--stdin", "-z",
                             "--no-index"],
                             input="\0".join(rel_paths), capture_output=True,
                             encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise _GitBatchError(str(exc)) from exc
    if res.returncode not in (0, 1):
        raise _GitBatchError((res.stderr or "git check-ignore failed").strip())
    return {p for p in res.stdout.split("\0") if p}


def _has_head(repo_root) -> bool:
    res = _run_git(repo_root, "rev-parse", "--verify", "-q", "HEAD")
    return res.returncode == 0


def _batch_modified(repo_root, rel_paths: list[str]) -> set[str]:
    """The subset of rel_paths (already known tracked) that differ from HEAD - staged or
    unstaged, since `git diff HEAD` compares the worktree straight to HEAD. A repo with no
    commits yet has no HEAD to diff against, so every tracked candidate is reported modified
    outright: nothing is committed, so everything necessarily differs from its (nonexistent)
    history."""
    if not rel_paths:
        return set()
    if not _has_head(repo_root):
        return set(rel_paths)
    res = _run_git(repo_root, "diff", "--name-only", "-z", "HEAD", "--", *rel_paths)
    if res.returncode != 0:
        raise _GitBatchError((res.stderr or "git diff failed").strip())
    return {p for p in res.stdout.split("\0") if p}


def classify_files(pattern, root=".") -> dict:
    """Find every file under `root` matching `pattern` and classify each as tracked-clean,
    tracked-modified, ignored, untracked, or no-repo (see FILE_STATES; mutually exclusive and
    exhaustive for any hit).

    Bounded git-process count: at most 4 subprocess calls PER REPO (`ls-files`, `check-ignore`
    on the non-tracked remainder, an optional HEAD-existence probe, `diff` on the tracked
    remainder) no matter how many candidate files that repo contributes - never 2 per file.

    Returns {"pattern", "root", "candidates" (files matched before classification), "files"
    ([{"path", "repo", "state"}, ...]), "skipped" (repo-level failures, as strings)}.
    """
    root_path = Path(root).absolute()
    files = find_files(root_path, pattern)
    repo_roots = _repo_roots_for(root_path)

    by_repo: dict = {}
    for f in files:
        by_repo.setdefault(_owning_repo(f, repo_roots), []).append(f)

    results = []
    skipped = []
    for repo_root, group in by_repo.items():
        if repo_root is None:
            results.extend({"path": str(f), "repo": None, "state": "no-repo"} for f in group)
            continue
        rel = {f: str(f.relative_to(repo_root)) for f in group}
        try:
            tracked = _batch_tracked(repo_root, list(rel.values()))
            remainder = [rel[f] for f in group if rel[f] not in tracked]
            ignored = _batch_ignored(repo_root, remainder)
            tracked_rel = [rel[f] for f in group if rel[f] in tracked]
            modified = _batch_modified(repo_root, tracked_rel)
        except _GitBatchError as exc:
            skipped.append("%s: %s" % (repo_root, exc))
            continue
        for f in group:
            r = rel[f]
            if r in tracked:
                state = "tracked-modified" if r in modified else "tracked-clean"
            elif r in ignored:
                state = "ignored"
            else:
                state = "untracked"
            results.append({"path": str(f), "repo": str(repo_root), "state": state})

    results.sort(key=lambda d: d["path"])
    return {"pattern": pattern, "root": str(root_path), "candidates": len(files),
            "files": results, "skipped": skipped}


def _print_files_result(pattern, root, data, as_json) -> None:
    if as_json:
        print(json.dumps({"ok": bool(data["files"]), "command": "git-state",
                          "data": data, "skipped": data["skipped"]}, indent=2))
    else:
        for f in data["files"]:
            print("%-16s %s" % (f["state"], f["path"]))
    for s in data["skipped"]:
        print("git_state: skipped %s" % s, file=sys.stderr)
    print("git_state: %d file(s) matched %r under %s" % (data["candidates"], pattern, root),
          file=sys.stderr)


def _main_files(pattern, root, as_json) -> int:
    root = root or "."
    if not Path(root).exists():
        msg = "--root path does not exist: %s" % root
        print("git_state: %s" % msg, file=sys.stderr)
        if as_json:
            print(json.dumps({"ok": False, "command": "git-state",
                              "data": {"pattern": pattern, "root": root, "candidates": 0,
                                       "files": [], "skipped": []},
                              "skipped": [], "error": msg}, indent=2))
        return 2
    data = classify_files(pattern, root)
    _print_files_result(pattern, root, data, as_json)
    if data["candidates"] == 0:
        return 1
    if not data["files"]:                    # matched something, classified nothing
        return 2
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Report git branch / sync / dirty state for repos, "
                                              "or (--files) classify every matching file under a "
                                              "tree as tracked-clean/tracked-modified/ignored/"
                                              "untracked/no-repo.")
    ap.add_argument("repos", nargs="*", default=["."], help="repo paths (default: cwd)")
    ap.add_argument("--root", help="walk this dir for .git repos, or (with --files) for matches "
                                   "(default in --files mode: cwd)")
    ap.add_argument("--files", metavar="GLOB",
                    help="switch modes: classify every file under --root matching GLOB "
                         "(e.g. 'CLAUDE.md' or '*.md') instead of reporting repo state")
    ap.add_argument("--json", action="store_true", help="machine-readable envelope")
    args = ap.parse_args(argv)
    if args.files:
        return _main_files(args.files, args.root, args.json)
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
