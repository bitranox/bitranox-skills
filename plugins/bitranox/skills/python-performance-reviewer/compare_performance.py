#!/usr/bin/env python3
"""Before/after performance comparison using git history.

Stashes current changes, checks out the previous commit, times the test suite,
restores, then times it again, and reports the delta.

Usage: python compare_performance.py

Cross-platform (Windows/macOS/Linux): pure standard library, invoked by the agent
as `python compare_performance.py`, so it does not depend on bash (Claude Code
falls back to PowerShell on Windows when Git Bash is absent). Timing uses a
monotonic clock; tests run via `python -m pytest`.
"""
import subprocess
import sys
import time


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def _time_pytest_ms():
    start = time.perf_counter()
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return int((time.perf_counter() - start) * 1000)


def main():
    current = _git("rev-parse", "HEAD").stdout.strip()
    if not current:
        print("Not a git repository, or no commits yet.")
        return 1

    stash = _git("stash", "save", "temp_for_perf_comparison")
    stashed = "No local changes" not in stash.stdout

    _git("checkout", "HEAD~1")
    print("Running tests on BEFORE version...")
    before = _time_pytest_ms()

    _git("checkout", current)
    if stashed:
        _git("stash", "pop")

    print("Running tests on AFTER version...")
    after = _time_pytest_ms()

    if before > 0:
        improvement = (before - after) * 100 // before
        print("Before: %dms" % before)
        print("After: %dms" % after)
        print("Improvement: %d%%" % improvement)
        if improvement < 5:
            print("WARNING: performance improvement under 5%; may not be significant")
    else:
        print("Could not measure performance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
