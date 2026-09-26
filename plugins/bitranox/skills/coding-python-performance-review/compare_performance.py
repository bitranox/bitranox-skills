#!/usr/bin/env python3
"""Before/after performance comparison using git history.

Stashes current changes (untracked files included), checks out the previous commit, times
the test suite, restores the branch and the changes, then times it again, and reports the
delta. The restore runs whatever happens in between - a failed checkout, a crash, Ctrl-C.

Usage: python compare_performance.py

Exit codes: 0 both suite runs passed and the delta is reported; 2 no comparison was
possible - not a git repository, no commits, no parent commit, a git step failed, a suite
run failed (a failing suite's timing measures nothing), or the working tree could not be
restored (stderr then names the branch or commit to check out again, the sha of the stash
that holds the uncommitted changes, and the git commands that put both back). When the BEFORE
run created a file where the stash restores an untracked file, the stash is not popped at all
- git would write the tracked changes and then refuse - and stderr names that file first.

Cross-platform (Windows/macOS/Linux): pure standard library, invoked by the agent
as `python compare_performance.py`, so it does not depend on bash (Claude Code
falls back to PowerShell on Windows when Git Bash is absent). Timing uses a
monotonic clock; tests run via `python -m pytest`.
"""
import os
import subprocess
import sys
import time

STASH_MESSAGE = "temp_for_perf_comparison"


class CompareError(Exception):
    """A step failed, so there is no valid before/after comparison."""


def _git(*args):
    # Decisions below read exit codes and refs, never git's messages; LC_ALL=C keeps a
    # localized git from changing anything that is printed or parsed.
    env = {**os.environ, "LC_ALL": "C"}
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, check=False)


def _rev(ref):
    """The commit sha *ref* names, or None."""
    r = _git("rev-parse", "--verify", "-q", ref)
    return r.stdout.strip() if r.returncode == 0 else None


def _pytest_argv():
    """Build the pytest argv, only naming a test dir when one exists.

    If neither ``tests/`` nor ``test/`` is present, omit the path so pytest
    discovers tests itself (honouring any pyproject testpaths). The cache
    provider is off so a run leaves no .pytest_cache behind to collide with the
    untracked files the stash restores."""
    argv = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"]
    testdir = next((d for d in ("tests", "test") if os.path.isdir(d)), None)
    if testdir:
        argv.append(testdir)
    argv.append("-v")
    return argv


def _time_pytest_ms():
    """Run the suite; return (elapsed milliseconds, pytest exit code)."""
    # No bytecode writes: a __pycache__ created while the old commit is checked out would
    # collide with the untracked __pycache__ the stash puts back.
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    start = time.perf_counter()
    rc = subprocess.run(_pytest_argv(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        env=env, check=False).returncode
    return int((time.perf_counter() - start) * 1000), rc


def _current_ref():
    """The branch HEAD is on, or its sha when HEAD is detached."""
    branch = _git("symbolic-ref", "-q", "--short", "HEAD")
    return branch.stdout.strip() if branch.returncode == 0 else _rev("HEAD")


def _stash_changes():
    """Stash tracked AND untracked changes; return the new stash's sha, or None if clean.

    Whether anything was stashed is decided by comparing refs/stash before and after, never
    by git's "No local changes" text: that text is translated, and misreading it would pop
    an unrelated stash the user already had."""
    before = _rev("refs/stash")
    pushed = _git("stash", "push", "-u", "-m", STASH_MESSAGE)
    if pushed.returncode != 0:
        raise CompareError(f"git stash push failed: {pushed.stderr.strip()}")
    after = _rev("refs/stash")
    return after if after and after != before else None


def _stash_entries():
    return _git("stash", "list", "--format=%H").stdout.split()


def _stash_untracked_paths(sha):
    """Repository-relative paths of the untracked files stash *sha* holds (its third parent)."""
    if _rev(f"{sha}^3") is None:
        return []
    listed = _git("ls-tree", "-r", "-z", "--name-only", f"{sha}^3")
    return [path for path in listed.stdout.split("\0") if path]


def _blocking_path(top, path):
    """The working-tree path that stops git from writing *path*, or None.

    That is *path* itself when anything exists there, or a parent that exists as something
    other than a real directory (git cannot create the directory the file needs)."""
    parts = path.split("/")
    for depth in range(1, len(parts)):
        parent = "/".join(parts[:depth])
        full = os.path.join(top, *parts[:depth])
        if os.path.islink(full) or (os.path.lexists(full) and not os.path.isdir(full)):
            return parent
    return path if os.path.lexists(os.path.join(top, *parts)) else None


def _untracked_in_the_way(sha):
    """Working-tree paths that block restoring the untracked files of stash *sha*.

    git restores a stash's tracked changes BEFORE its untracked files, and refuses an untracked
    file it cannot write only after the tracked part is written: popping over one of these
    half-applies the stash and still keeps the entry."""
    top = _git("rev-parse", "--show-toplevel").stdout.strip()
    blocked = (_blocking_path(top, path) for path in _stash_untracked_paths(sha))
    return sorted({path for path in blocked if path})


def _worktree_state():
    """Everything a stash pop can change: tracked content against HEAD and the file list."""
    status = _git("status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    return status, _git("diff", "HEAD", "--binary").stdout


_PARTIAL = "git re-applied PART of your changes before it failed"


def _pop_stash(sha):
    """Re-apply and drop OUR stash entry (found by sha, whatever its position now).

    Returns None on success, else (why the changes are not back, whether PART of them was
    applied anyway). The known half-apply - an untracked file of the stash that exists again -
    is refused before git touches anything; any other failure is judged by comparing the
    working tree before and after the attempt, never by git's message."""
    entries = _stash_entries()
    if sha not in entries:
        return f"stash {sha} is gone; nothing to re-apply", False
    blockers = _untracked_in_the_way(sha)
    if blockers:
        return (f"the BEFORE test run created {len(blockers)} file(s) your stash also holds as "
                f"untracked files ({', '.join(blockers)}), so nothing was re-applied"), False
    ref = f"stash@{{{entries.index(sha)}}}"
    before = _worktree_state()
    for args in (("--index", ref), (ref,)):
        if _git("stash", "pop", *args).returncode == 0:
            return None
        if _worktree_state() != before:
            return _PARTIAL, True
    return "could not re-apply your changes; nothing was re-applied", False


def _first_line(text):
    """git's first message line, without the colon that introduces its file list."""
    line = next((line.strip() for line in text.splitlines() if line.strip()), "no message")
    return line.rstrip(":")


def _unrestored_report(ref, stash_sha, reason, *, on_ref, partial=False):
    """The lines that tell the user where they are and exactly how to get back.

    The stash is named by its sha, never stash@{n}: that position shifts the moment anything
    else pushes or drops a stash, and a stale position would apply somebody else's work."""
    lines = [f"the repository was NOT restored: {reason}."]
    if not on_ref:
        lines.append(f"HEAD is left DETACHED at {_rev('HEAD')}; you started on '{ref}'.")
    stashed = bool(stash_sha) and stash_sha in _stash_entries()
    if stashed and partial:
        lines.append(f"ALL of your uncommitted changes are still in stash {stash_sha} "
                     f"('{STASH_MESSAGE}'); the working tree holds only part of them, so applying "
                     "the stash again would collide with that part.")
        lines.append(f"to recover, compare git status with git stash show -p --include-untracked "
                     f"{stash_sha}, finish the restore by hand, and drop the '{STASH_MESSAGE}' "
                     "entry only once every change is back.")
        return lines
    if stashed:
        lines.append(f"your uncommitted changes are safe in stash {stash_sha} ('{STASH_MESSAGE}').")
    elif not stash_sha:
        lines.append("you had no uncommitted changes, so nothing was stashed.")
    blockers = _untracked_in_the_way(stash_sha) if stashed else []
    if blockers:
        lines.append("first move these files out of the way - the BEFORE test run made them, and "
                     f"your own versions are in the stash: {', '.join(blockers)}")
    lines.append("to recover, review what the BEFORE test run left behind (git status), then run:")
    if not on_ref:
        lines.append(f"  git checkout {ref}")
    if stashed:
        lines.append(f"  git stash apply --index {stash_sha}")
        lines.append(f"(if --index refuses, apply without it; afterwards drop the '{STASH_MESSAGE}' "
                     "entry that git stash list shows)")
    return lines


def _restore(ref, stash_sha):
    """Put back the branch and the stashed changes; return the error report (empty = restored)."""
    checkout = _git("checkout", "-q", ref, "--")
    if checkout.returncode != 0:
        reason = f"could not check out '{ref}' again (git: {_first_line(checkout.stderr)})"
        return _unrestored_report(ref, stash_sha, reason, on_ref=False)
    failure = _pop_stash(stash_sha) if stash_sha else None
    if failure:
        reason, partial = failure
        return _unrestored_report(ref, stash_sha, reason, on_ref=True, partial=partial)
    return []


def _time_before(before_sha):
    """Check out *before_sha* and time the suite there; raises CompareError on failure."""
    checkout = _git("checkout", "-q", before_sha, "--")
    if checkout.returncode != 0:
        raise CompareError(f"git checkout of the previous commit failed: {checkout.stderr.strip()}")
    print("Running tests on BEFORE version...")
    return _time_pytest_ms()


def _compare():
    """Run both timings; return (before ms, before rc, after ms, after rc)."""
    if _rev("HEAD^{commit}") is None:
        raise CompareError("Not a git repository, or no commits yet.")
    before_sha = _rev("HEAD~1^{commit}")
    if before_sha is None:
        raise CompareError("HEAD has no parent commit to compare against.")

    start_ref = _current_ref()
    stash_sha = _stash_changes()
    problems = []
    try:
        before, before_rc = _time_before(before_sha)
    finally:
        problems = _restore(start_ref, stash_sha)
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
    if problems:
        raise CompareError("the working tree was not fully restored (see above)")

    print("Running tests on AFTER version...")
    after, after_rc = _time_pytest_ms()
    return before, before_rc, after, after_rc


def _report(before, before_rc, after, after_rc):
    print(f"Before: {before}ms")
    print(f"After: {after}ms")
    if before_rc or after_rc:
        print(f"ERROR: the test suite failed (BEFORE: pytest exit {before_rc}, AFTER: pytest "
              f"exit {after_rc}); timings of a failing suite are not a comparison.")
        return 2
    if before <= 0:
        print("Could not measure performance")
        return 2
    improvement = (before - after) * 100 // before
    print(f"Improvement: {improvement}%")
    if improvement < 5:
        print("WARNING: performance improvement under 5%; may not be significant")
    return 0


def _utf8_output():
    # Branch names and git's stderr can be non-ASCII, which a cp1252 console cannot encode.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (ValueError, OSError):
            pass


def main():
    _utf8_output()
    try:
        return _report(*_compare())
    except CompareError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
