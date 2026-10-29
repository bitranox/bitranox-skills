# /// script
# requires-python = ">=3.14"
# ///
"""Did a leftover worktree or branch already land on the target branch? Read-only.

Before deleting a worktree or a branch, the question is whether its work is already on master,
and `git cherry` answers it badly: it matches commits by patch-id, so work that landed SQUASHED,
rebased with conflicts, or re-applied by hand reads as unlanded, and a dirty worktree's
uncommitted files are not commits at all. This answers it from content instead:

* WORKTREE MODE (the target is a directory): each changed, deleted or untracked file is hashed
  as git would store it (`git hash-object --path`, so line-ending filters apply) and compared
  with the target's blob, then with the blob at every target commit since the merge-base that
  touched the path - a file the target changed AGAIN after the work landed still counts. The
  worktree's own commits are then checked as in branch mode.
* BRANCH MODE (the target is a ref): commits are first matched by patch-id, as `git cherry`
  does; then each line the branch ADDED (blank lines aside) is looked up in the target's copy of
  the file, as a multiset, so two added copies need two copies there. A branch is landed when
  every commit is patch-equivalent or every added line is present.

`--also-into REF` (repeatable) names a ref you already know landed - a kept integration or backup
branch that carried a fix-round sequence (x1..x24) into the target. A branch whose lines a LATER
branch rewrote has no added line left in the target, so the line check reads it as unlanded; when
its tip is an ancestor of such a ref, its commits count as landed. It only vouches for commits: a
worktree's uncommitted files are still compared with the target. The ref is taken on your word,
so check it first (run this tool on it).

Version numbers named in the branch's commit subjects (`1.2.3`) are listed with whether the
target's CHANGELOG.md has a heading naming them. They inform; they do not decide the verdict.

Nothing is written: git runs with `--no-optional-locks`, so even `status` leaves the index
alone, and `hash-object` is run without `-w`. Inherited GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE
are dropped, so the target directory decides which repository is read.

Run:
  `uv run scripts/landed.py .claude/worktrees/mytopic`         # a worktree, into origin/HEAD
  `uv run scripts/landed.py feature --into main`               # a branch, into main
  `uv run scripts/landed.py feature --json`
  `uv run scripts/landed.py x3 --also-into backup/integration`  # x3 was rewritten by x4..x9

`--into` defaults to the first of origin/HEAD, origin/main, origin/master, main, master that
resolves. Exit codes: 0 = landed, 1 = not landed, 2 = could not run (a target or `--into` that
or `--also-into` that does not resolve, no common history, git missing). `--json` emits {ok, command, data, skipped}
on every exit, ok false only on exit 2; errors go to stderr in text mode.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

__all__ = ["added_lines", "main", "versions_in"]

DEFAULT_INTO = ("origin/HEAD", "origin/main", "origin/master", "main", "master")
LANDED_FILE_STATES = frozenset({"in_target", "in_history", "deleted_in_target"})
_SCOPING_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")
# Not part of a longer dotted number on either side; a sentence's closing period is allowed.
_VERSION = re.compile(r"(?<![\d.])\d+\.\d+\.\d+(?!\.?\d)")
_TIMEOUT = 120


class CannotRun(Exception):
    """The question could not be asked: exit 2."""


# ---------------------------------------------------------------------------------------------
# git access
# ---------------------------------------------------------------------------------------------


def _git_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _SCOPING_VARS}
    env["LC_ALL"] = "C"
    return env


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    """Run git read-only in `cwd`; bytes out, because file content is compared exactly."""
    exe = shutil.which("git")
    if exe is None:
        raise CannotRun("git is not installed or not on PATH")
    done = subprocess.run(
        [exe, "--no-optional-locks", *args], cwd=str(cwd), capture_output=True,
        timeout=_TIMEOUT, check=False, env=_git_env(),
    )
    if check and done.returncode != 0:
        err = done.stderr.decode("utf-8", "replace").strip()
        raise CannotRun(f"git {' '.join(args)} failed: {err}")
    return done


def _text(done: subprocess.CompletedProcess[bytes]) -> str:
    return done.stdout.decode("utf-8", "replace")


def _resolve(cwd: Path, ref: str) -> str | None:
    done = git(cwd, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}", check=False)
    return _text(done).strip() if done.returncode == 0 else None


def _blob(cwd: Path, rev: str, path: str) -> str | None:
    done = git(cwd, "rev-parse", "--verify", "-q", f"{rev}:{path}", check=False)
    return _text(done).strip() if done.returncode == 0 else None


def _blob_text(cwd: Path, rev: str, path: str) -> str:
    done = git(cwd, "cat-file", "-p", f"{rev}:{path}", check=False)
    return _text(done) if done.returncode == 0 else ""


# ---------------------------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------------------------


def added_lines(diff: str) -> list[str]:
    """The non-blank lines a unified diff adds, header lines excluded."""
    out = []
    for line in diff.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            body = line[1:].rstrip("\r")
            if body.strip():
                out.append(body)
    return out


def versions_in(subjects: list[str]) -> list[str]:
    """Every distinct X.Y.Z named in the subjects, in first-seen order."""
    seen: list[str] = []
    for subject in subjects:
        for found in _VERSION.findall(subject):
            if found not in seen:
                seen.append(found)
    return seen


def _lines_of(text: str) -> Counter[str]:
    # split("\n"), never splitlines(): that also breaks on form feed and U+2028, which a diff
    # line can contain, so the two sides would be cut differently.
    return Counter(line.rstrip("\r") for line in text.split("\n"))


def _match(added: list[str], available: Counter[str]) -> list[str]:
    """Consume `available` for each added line; return the lines it could not supply."""
    missing = []
    for line in added:
        if available[line] > 0:
            available[line] -= 1
        else:
            missing.append(line)
    return missing


# ---------------------------------------------------------------------------------------------
# Worktree files
# ---------------------------------------------------------------------------------------------


def _porcelain_entries(cwd: Path) -> list[tuple[str, str]]:
    """(XY, path) for every changed, deleted or untracked path; a rename yields its new path."""
    raw = _text(git(cwd, "status", "--porcelain=v1", "-z", "--untracked-files=all"))
    fields = raw.split("\0")
    entries = []
    i = 0
    while i < len(fields) and fields[i]:
        xy, path = fields[i][:2], fields[i][3:]
        entries.append((xy, path))
        i += 2 if xy[0] in "RC" else 1
    return entries


def _history_has(cwd: Path, base: str, into: str, path: str, sha: str | None) -> bool:
    """Did any target commit since `base` that touched `path` hold exactly `sha` (None = absent)?"""
    revs = _text(git(cwd, "rev-list", f"{base}..{into}", "--", path)).split()
    return any(_blob(cwd, rev, path) == sha for rev in revs)


def _file_status(cwd: Path, xy: str, path: str, base: str, into: str) -> str:
    target_sha = _blob(cwd, into, path)
    if "D" in xy:
        return "deleted_in_target" if target_sha is None else "deleted_here_only"
    sha = _text(git(cwd, "hash-object", f"--path={path}", "--", path)).strip()
    if sha == target_sha:
        return "in_target"
    if _history_has(cwd, base, into, path, sha):
        return "in_history"
    return "differs" if target_sha is not None else "absent_in_target"


def worktree_files(cwd: Path, base: str, into: str) -> list[dict[str, str]]:
    return [
        {"path": path, "status": _file_status(cwd, xy, path, base, into)}
        for xy, path in _porcelain_entries(cwd)
    ]


# ---------------------------------------------------------------------------------------------
# Branch commits
# ---------------------------------------------------------------------------------------------


def _changed_paths(cwd: Path, base: str, head: str) -> list[tuple[str, str]]:
    raw = _text(git(cwd, "diff", "--name-status", "-z", "--no-renames", base, head))
    fields = [f for f in raw.split("\0") if f]
    return list(zip(fields[0::2], fields[1::2]))


def _branch_file(cwd: Path, status: str, path: str, base: str, head: str, into: str) -> dict:
    if status == "D":
        gone = _blob(cwd, into, path) is None
        return {"path": path, "added": 0, "present": 0,
                "missing": [] if gone else ["(deleted on the branch, still in the target)"]}
    diff = _text(git(cwd, "diff", "--no-color", "--no-ext-diff", "-U0", base, head, "--", path))
    if diff.startswith("Binary files") or "\nBinary files " in diff:
        same = _blob(cwd, head, path) == _blob(cwd, into, path)
        return {"path": path, "added": 1, "present": int(same),
                "missing": [] if same else ["(binary content differs)"]}
    added = added_lines(diff)
    missing = _match(added, _lines_of(_blob_text(cwd, into, path)))
    return {"path": path, "added": len(added), "present": len(added) - len(missing),
            "missing": missing}


def _patch_equivalent(cwd: Path, into: str, head: str) -> int:
    out = _text(git(cwd, "cherry", into, head))
    return sum(1 for line in out.split("\n") if line.startswith("- "))


def _versions(cwd: Path, base: str, head: str, into: str) -> list[dict]:
    subjects = _text(git(cwd, "log", "--format=%s", f"{base}..{head}")).split("\n")
    headings = [line for line in _blob_text(cwd, into, "CHANGELOG.md").split("\n")
                if line.startswith("#")]
    return [{"version": v, "in_changelog": any(v in h for h in headings)}
            for v in versions_in(subjects)]


def branch_report(cwd: Path, base: str, head: str, into: str) -> dict:
    total = len(_text(git(cwd, "rev-list", f"{base}..{head}")).split())
    files = [_branch_file(cwd, st, p, base, head, into) for st, p in _changed_paths(cwd, base, head)]
    added = sum(f["added"] for f in files)
    present = sum(f["present"] for f in files)
    equivalent = _patch_equivalent(cwd, into, head) if total else 0
    return {
        "commits": {"total": total, "patch_equivalent": equivalent},
        "lines": {"added": added, "present": present,
                  "share": round(present / added, 4) if added else 1.0},
        "branch_files": files,
        "versions": _versions(cwd, base, head, into),
        "landed": total == 0 or equivalent == total or all(not f["missing"] for f in files),
    }


# ---------------------------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------------------------


def _resolve_into(cwd: Path, requested: str | None) -> str:
    candidates = (requested,) if requested else DEFAULT_INTO
    for ref in candidates:
        if _resolve(cwd, ref):
            return ref
    raise CannotRun(f"--into {requested!r} does not resolve to a commit" if requested
                    else "no default target resolves: " + ", ".join(DEFAULT_INTO))


def _also_into(cwd: Path, head: str, refs: list[str]) -> list[dict]:
    """For each named ref: does it contain `head` (is the tip an ancestor of it)?"""
    found = []
    for ref in refs:
        if _resolve(cwd, ref) is None:
            raise CannotRun(f"--also-into {ref!r} does not resolve to a commit")
        done = git(cwd, "merge-base", "--is-ancestor", head, ref, check=False)
        found.append({"ref": ref, "contains": done.returncode == 0})
    return found


def _locate(target: str) -> tuple[str, Path, str]:
    """(mode, the directory git runs in, the ref whose commits are judged)."""
    path = Path(target)
    if path.is_dir():
        inside = git(path, "rev-parse", "--is-inside-work-tree", check=False)
        if _text(inside).strip() != "true":
            raise CannotRun(f"{target} is a directory but not inside a git work tree")
        return "worktree", path, "HEAD"
    cwd = Path.cwd()
    if _resolve(cwd, target) is None:
        raise CannotRun(f"{target} is neither a worktree directory nor a ref that resolves here")
    return "branch", cwd, target


def report(target: str, into_ref: str | None, also_into: list[str] | None = None) -> dict:
    mode, cwd, head = _locate(target)
    into = _resolve_into(cwd, into_ref)
    containers = _also_into(cwd, head, also_into or [])
    base_done = git(cwd, "merge-base", head, into, check=False)
    base = _text(base_done).strip()
    if base_done.returncode != 0 or not base:
        raise CannotRun(f"{target} and {into} share no history")
    files = worktree_files(cwd, base, into) if mode == "worktree" else []
    branch = branch_report(cwd, base, head, into)
    branch_landed = branch.pop("landed") or any(c["contains"] for c in containers)
    landed = branch_landed and all(f["status"] in LANDED_FILE_STATES for f in files)
    return {"target": target, "mode": mode, "into": into,
            "verdict": "landed" if landed else "not_landed", "files": files,
            "also_into": containers, **branch}


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------


def _envelope(ok: bool, data: dict) -> str:
    return json.dumps({"ok": ok, "command": "landed", "data": data, "skipped": []}, indent=2)


def _render(data: dict) -> str:
    verdict = "LANDED" if data["verdict"] == "landed" else "NOT LANDED"
    lines = [f"{verdict}: {data['target']} into {data['into']} ({data['mode']})"]
    for f in data["files"]:
        if f["status"] not in LANDED_FILE_STATES:
            lines.append(f"  file {f['status']}: {f['path']}")
    c, n = data["commits"], data["lines"]
    lines.append(f"  commits: {c['total']} ({c['patch_equivalent']} patch-equivalent); "
                 f"added lines present: {n['present']}/{n['added']}")
    for c in data["also_into"]:
        state = "contained in" if c["contains"] else "NOT contained in"
        lines.append(f"  commits: {state} {c['ref']} (--also-into)")
    for f in data["branch_files"]:
        for missing in f["missing"][:5]:
            lines.append(f"  missing in {f['path']}: {missing}")
    for v in data["versions"]:
        lines.append(f"  version {v['version']}: {'in' if v['in_changelog'] else 'NOT in'} "
                     "the target's CHANGELOG.md")
    return "\n".join(lines)


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="landed", description="Did a worktree or branch already land on the target branch?")
    parser.add_argument("target", help="a worktree directory or a branch/ref")
    parser.add_argument("--into", help="the branch to check against (default: origin/HEAD, "
                        "origin/main, origin/master, main, master - the first that resolves)")
    parser.add_argument("--also-into", action="append", default=[], metavar="REF",
                        help="a ref already known to have landed (a kept integration or backup "
                        "branch); a branch whose tip is its ancestor counts as landed. Repeatable")
    parser.add_argument("--json", action="store_true", help="emit the JSON envelope")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    try:
        data = report(args.target, args.into, args.also_into)
    except (CannotRun, OSError, subprocess.TimeoutExpired) as exc:
        if args.json:
            print(_envelope(False, {"error": str(exc)}))
        else:
            print(f"landed: {exc}", file=sys.stderr)
        return 2
    print(_envelope(True, data) if args.json else _render(data))
    return 0 if data["verdict"] == "landed" else 1


if __name__ == "__main__":
    sys.exit(main())
