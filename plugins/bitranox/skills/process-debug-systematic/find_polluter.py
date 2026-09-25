#!/usr/bin/env python3
"""Find which test creates an unwanted file or directory (linear scan).

Usage:   python find_polluter.py <path_to_check> <test_glob>
Example: python find_polluter.py .git "src/**/*.test.ts"

Cross-platform (Windows/macOS/Linux): pure standard library, invoked by the agent
as `python find_polluter.py ...`, so it does not depend on bash (Claude Code falls
back to PowerShell on Windows when Git Bash is absent). Runs each matched test via
the project's test runner (`npm test <file>`), one at a time, and reports the first
one that makes the pollution path appear.

Exit codes:
  0  no test created the path (every matched test ran)
  1  found the polluter
  2  error: bad usage, no test file matched the glob, or the test runner never ran the
     tests (npm missing, no "test" script, or every single run failed)
  3  cannot check: the pollution path already exists before the first test, so no test
     can be seen creating it - remove it and run again
"""
import glob
import shutil
import subprocess
import sys
from pathlib import Path

EXIT_CLEAN, EXIT_FOUND, EXIT_ERROR, EXIT_PREEXISTING = 0, 1, 2, 3

# npm's own failures, as opposed to a test that ran and failed. A polluting test may itself
# fail, so a non-zero exit alone cannot abort the scan; these say the runner never ran it.
NPM_NEVER_RAN_RC = 254
NPM_NEVER_RAN_MARKERS = ("Missing script", "npm ERR! enoent", "npm error enoent",
                         "npm ERR! code ENOENT", "npm error code ENOENT")


class RunnerError(Exception):
    """The test runner could not run the tests at all, so a clean scan would be a lie."""


def _run_test(test_file):
    """Run one test file through npm; return (exit code, combined output).

    npm is npm.cmd on Windows; resolve the real executable so this works without a shell.
    Output is decoded as UTF-8 with replacement: the locale codec raises on POSIX and loses the
    stream on Windows when a test prints bytes it cannot decode.
    """
    npm = shutil.which("npm") or "npm"
    try:
        proc = subprocess.run([npm, "test", test_file], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", check=False)
    except OSError as exc:
        raise RunnerError(f"cannot start the test runner {npm!r}: {exc}") from exc
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _runner_never_ran(rc, output):
    return rc == NPM_NEVER_RAN_RC or any(marker in output for marker in NPM_NEVER_RAN_MARKERS)


def _tail(output, lines=5):
    return "\n".join("   " + line for line in output.strip().split("\n")[-lines:])


def _report_found(test_file, pollution):
    print("\nFOUND POLLUTER")
    print("   Test: %s" % test_file)
    print("   Created: %s" % pollution)
    print("\nTo investigate, run just this test:")
    print("   npm test %s" % test_file)


def _scan(pollution, test_files, run_test):
    """Run each test until one creates `pollution`; return the exit code."""
    total = len(test_files)
    failed_runs = 0
    last_output = ""
    for count, test_file in enumerate(test_files, 1):
        print("[%d/%d] Testing: %s" % (count, total, test_file))
        rc, output = run_test(test_file)
        if _runner_never_ran(rc, output):
            raise RunnerError("the test runner did not run %s (exit %d):\n%s"
                              % (test_file, rc, _tail(output)))
        if rc != 0:
            failed_runs += 1
            last_output = output
            print("   exit %d" % rc)
        if pollution.exists():
            _report_found(test_file, pollution)
            return EXIT_FOUND
    if failed_runs and failed_runs == total:
        raise RunnerError("every one of the %d test runs failed, so a clean scan proves nothing; "
                          "the last one said:\n%s" % (total, _tail(last_output)))
    print("\nNo polluter found - all tests clean.")
    return EXIT_CLEAN


def _tolerate_unencodable_output():
    """Replace, rather than crash on, a character the console cannot encode (cp1252 pipes)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (ValueError, OSError):
                pass


def main(argv, *, run_test=_run_test):
    """CLI entry; `run_test(test_file) -> (rc, output)` is the seam tests inject past npm."""
    _tolerate_unencodable_output()
    if len(argv) != 3:
        print("Usage: python find_polluter.py <path_to_check> <test_glob>", file=sys.stderr)
        print('Example: python find_polluter.py .git "src/**/*.test.ts"', file=sys.stderr)
        return EXIT_ERROR

    pollution = Path(argv[1])
    pattern = argv[2]
    test_files = sorted(glob.glob(pattern, recursive=True))

    print("Searching for the test that creates: %s" % pollution)
    print("Test glob: %s" % pattern)
    print("Found %d test files\n" % len(test_files))

    if not test_files:
        print("find_polluter: no test file matches %r; check the glob" % pattern, file=sys.stderr)
        return EXIT_ERROR
    if pollution.exists():
        # Checked once, up front: with the path already there no test can be seen creating it,
        # and skipping every test would end in "all tests clean".
        print("find_polluter: %s already exists before any test ran; remove it first, "
              "then run again" % pollution, file=sys.stderr)
        return EXIT_PREEXISTING
    try:
        return _scan(pollution, test_files, run_test)
    except RunnerError as exc:
        print("find_polluter: %s" % exc, file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main(sys.argv))
