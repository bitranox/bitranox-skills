#!/usr/bin/env python3
"""Bisection helper to find which test creates an unwanted file or directory.

Usage:   python find_polluter.py <path_to_check> <test_glob>
Example: python find_polluter.py .git "src/**/*.test.ts"

Cross-platform (Windows/macOS/Linux): pure standard library, invoked by the agent
as `python find_polluter.py ...`, so it does not depend on bash (Claude Code falls
back to PowerShell on Windows when Git Bash is absent). Runs each matched test via
the project's test runner and reports the first one that makes the pollution path
appear.
"""
import glob
import shutil
import subprocess
import sys
from pathlib import Path


def _run_test(test_file):
    # npm is npm.cmd on Windows; resolve the real executable so this works without a shell.
    npm = shutil.which("npm") or "npm"
    subprocess.run([npm, "test", test_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def main(argv):
    if len(argv) != 3:
        print("Usage: python find_polluter.py <path_to_check> <test_glob>")
        print('Example: python find_polluter.py .git "src/**/*.test.ts"')
        return 1

    pollution = Path(argv[1])
    pattern = argv[2]
    test_files = sorted(glob.glob(pattern, recursive=True))
    total = len(test_files)

    print("Searching for the test that creates: %s" % pollution)
    print("Test glob: %s" % pattern)
    print("Found %d test files\n" % total)

    for count, test_file in enumerate(test_files, 1):
        if pollution.exists():
            print("Pollution already exists before test %d/%d; skipping: %s" % (count, total, test_file))
            continue
        print("[%d/%d] Testing: %s" % (count, total, test_file))
        _run_test(test_file)
        if pollution.exists():
            print("\nFOUND POLLUTER")
            print("   Test: %s" % test_file)
            print("   Created: %s" % pollution)
            print("\nTo investigate, run just this test:")
            print("   npm test %s" % test_file)
            return 1

    print("\nNo polluter found - all tests clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
