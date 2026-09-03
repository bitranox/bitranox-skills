# /// script
# requires-python = ">=3.10"
# ///
"""Break the code on purpose, run ONE test arm, and report whether the arm noticed - then restore.

A mutation battery is the only way to know a test asserts anything. Hand-rolling one is where it
goes wrong, and it went wrong the same three ways often enough to be worth a tool:

* **The verdict came from a grep of the log.** A `with pytest.raises(KernelError):` SOURCE line is
  echoed in the traceback, so grepping the output for `KernelError` finds it and concludes the
  exception was raised - while the summary line one row down says `DID NOT RAISE`. This reads the
  SHORT TEST SUMMARY, which carries the exception pytest actually caught, never the traceback body.
* **The arm failed somewhere else.** A test can fail on a boot precondition, a fixture, or an
  earlier assertion, which looks exactly as red as the assertion you meant to test. The reported
  reason is the summary line, so you can see WHICH assertion failed rather than only that one did.
* **One mutation was not enough.** Layered validation absorbs a single-layer break: a short field
  zero-fills and a later check catches it anyway, so the arm stays green and reads as a weak test.
  `--mutate` repeats, and every mutation is applied together as ONE arm.

Restoring is from a COPY taken before the first edit, never `git checkout -- <file>`, which
restores from HEAD and so discards any uncommitted work in that file. The restore runs whatever
happens, and the bytes are compared afterwards - a failed restore is reported loudly, because it
is the one outcome worse than a wrong verdict.

* **The arm's bytecode outlived the arm.** CPython validates a `.pyc` against the source's
  mtime SECOND and SIZE, so a length-preserving mutation applied in the same second the file was
  last edited leaves a cached mutant that the RESTORED source does not invalidate: the next run
  executes bytecode no source file contains, while grep and `inspect.getsource` agree the code is
  correct. That agreement is the trap - it reads as confirmation and sends you looking at fixtures
  and test isolation. Every arm therefore runs with bytecode writing OFF and purges the cache for
  each mutated source both before and after, so neither a stale read nor a leftover mutant is
  possible; a cache that cannot be removed REFUSES the arm rather than risking it.

* **The arm SPUN instead of failing.** A mutation can make a test loop forever rather than go
  red, when the test's only exit is the behaviour being mutated. Unbounded, that hangs this tool
  and the whole battery behind it, and killing it by hand skips the restore. `--timeout` bounds
  the arm and reports the hang as its own verdict, never as `killed`. The restore still runs when
  the timeout fires: the copy is taken before the first edit and put back in a `finally`.

Run:
  `uv run scripts/mutation_arm.py --mutate src/x.py old.txt new.txt --test tests/t.py::test_y --timeout 90`
  `... --mutate a.py o1.txt n1.txt --mutate b.py o2.txt n2.txt --test tests/t.py::test_y`
  add `--json` for an envelope

Exit codes: 0 = KILLED (the arm noticed the mutation), 1 = SURVIVED (it did not - the finding),
2 = INCONCLUSIVE, TIMEOUT, a failed restore, or a usage error (an absent anchor, a test that never
ran, or an arm still running at --timeout).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from anchor_edit import AnchorError, replace_exact, require_unique

_SUMMARY_HEADER = "short test summary info"


def _partial_output(expired) -> str:
    """Whatever a killed run managed to emit, as text.

    `TimeoutExpired.stdout` is bytes even when the call asked for text, and either stream can be
    None, so a bare concatenation raises inside the timeout handler and loses the verdict.
    """
    parts = []
    for stream in (expired.stdout, expired.stderr):
        if stream is None:
            continue
        parts.append(stream.decode("utf-8", "replace") if isinstance(stream, bytes) else stream)
    return "".join(parts)


def failure_reason(output: str) -> str | None:
    """The reason pytest recorded for the first failure, or None when nothing failed.

    Read from the SHORT TEST SUMMARY, which pytest builds from the exception it actually caught.
    The traceback body is not consulted at all: it contains the test's own source, so a
    `pytest.raises(X)` line makes a grep for X report that X was raised when the run says the
    opposite.
    """
    lines = output.splitlines()
    start = next((i for i, line in enumerate(lines) if _SUMMARY_HEADER in line), None)
    if start is None:
        return None
    for line in lines[start + 1:]:
        if not line.startswith(("FAILED ", "ERROR ")):
            continue
        _, _, reason = line.partition(" - ")
        return reason.strip() or line.strip()
    return None


def verdict_for(returncode: int | None) -> str:
    """What a pytest exit code means for a mutation arm.

    5 is the one that matters: pytest collected NOTHING, so the arm never ran. Folding that into
    "passed" would report an untested line as a covered one, which is the exact false all-clear a
    mutation battery exists to prevent.

    `None` means the arm was KILLED at the timeout, which is its own verdict and not a failure to
    notice: a mutation can make a test loop forever rather than fail, when the test's only exit is
    the behaviour being mutated. Reporting that as "killed" would credit the arm with catching
    something it never reached.
    """
    if returncode is None:
        return "timeout"
    return {0: "survived", 1: "killed"}.get(returncode, "inconclusive")


def exit_code_for(verdict: str) -> int:
    return {"killed": 0, "survived": 1}.get(verdict, 2)


def bytecode_caches(path):
    """Every cached-bytecode file that could be served for `path`.

    Globbed on the SOURCE file's real stem, so it covers every interpreter tag and optimisation
    level rather than only the one running now, and it finds a hyphenated name: a hook module
    loaded from `ci-watch-nudge.py` caches as `ci-watch-nudge.cpython-314.pyc`, which a search by
    the underscored import alias misses while reading as "no stale cache present".
    """
    if path.suffix != ".py":
        return []
    # PYTHONPYCACHEPREFIX relocates the cache and drops the __pycache__ component entirely, so the
    # sibling directory alone is not the whole answer; cache_from_source resolves whichever layout
    # is in force, and both are swept because the ambient setting need not match the arm's.
    directories = {
        path.parent / "__pycache__",
        Path(importlib.util.cache_from_source(str(path.resolve()))).parent,
    }
    found = []
    for directory in sorted(directories):
        found.extend(sorted(directory.glob(f"{path.stem}.*.pyc")))
    return found


def purge_bytecode(paths):
    """Remove the cached bytecode for each source, then REFUSE if any survived.

    The check is on the resulting state rather than on the unlink calls: a cache left behind by a
    read-only directory or a permission error would silently defeat the guarantee, and an arm that
    may be running bytecode nobody wrote is worth refusing outright.
    """
    removed = []
    for path in paths:
        for cache in bytecode_caches(path):
            try:
                cache.unlink()
            except OSError:
                continue
            removed.append(str(cache))
    remaining = [str(cache) for path in paths for cache in bytecode_caches(path)]
    if remaining:
        raise AnchorError(
            "cached bytecode survived removal, the arm could run it: " + ", ".join(remaining))
    return removed


def plan_mutations(specs):
    """Validate every anchor BEFORE writing anything, returning (path, old, new) triples.

    All or nothing: one absent or ambiguous anchor refuses the whole arm. A partly-applied arm
    would run the tests against a state nobody described.
    """
    planned = []
    for path_arg, old_file, new_file in specs:
        path = Path(path_arg)
        if not path.is_file():
            raise AnchorError(f"not a file: {path}")
        text = path.read_text(encoding="utf-8")
        old = Path(old_file).read_text(encoding="utf-8")
        new = Path(new_file).read_text(encoding="utf-8")
        require_unique(text, old, label=f"anchor for {path}")
        planned.append((path, old, new))
    return planned


def run_arm(planned, nodeid, *, runner=None, timeout=None):
    """Apply every mutation, run the arm, restore from copies taken first. Returns a report.

    `timeout` bounds the arm in SECONDS. Without one a mutation that makes the test spin hangs
    this tool instead of being reported, and a battery of arms stops dead on the first such
    mutation - measured 2026-09-02, where killing the hung run by hand also skipped the restore
    and left a mutated file on disk. The restore is in a `finally`, so a killed arm still
    restores.
    """
    runner = runner or [sys.executable, "-m", "pytest"]
    # Before anything is written: a cache predating the mutation can be served IN PLACE of it when
    # the mutation preserves the file's size and lands in the same second, which reports a test as
    # SURVIVED though the mutant never ran.
    purged = purge_bytecode([path for path, _, _ in planned])
    with tempfile.TemporaryDirectory(prefix="mutation-arm-") as tmp:
        saved = {}
        for index, (path, _, _) in enumerate(planned):
            # Index-prefixed: two mutations may target the same file, and two files in different
            # directories may share a basename. Either collision would restore the wrong bytes.
            copy = Path(tmp) / f"{index}-{path.name}"
            shutil.copy2(path, copy)
            saved.setdefault(path, copy)
        try:
            for path, old, new in planned:
                text = path.read_text(encoding="utf-8")
                path.write_text(replace_exact(text, old, new), encoding="utf-8")
            try:
                proc = subprocess.run(
                    [*runner, nodeid, "-q", "--no-header", "-rfE", "--tb=no",
                     "-p", "no:cacheprovider"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=timeout,
                    # Merged onto the real environment, never a fresh dict: on Windows a child
                    # without SystemRoot loses Winsock and dies with EMPTY output.
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                returncode, output = proc.returncode, proc.stdout + proc.stderr
            except subprocess.TimeoutExpired as expired:
                # A killed run has no exit code. Its partial output is bytes when the process was
                # killed before the text wrapper saw it, so it is decoded defensively rather than
                # concatenated blindly.
                returncode, output = None, _partial_output(expired)
        finally:
            restored = True
            for path, copy in saved.items():
                shutil.copy2(copy, path)
                if path.read_bytes() != copy.read_bytes():
                    restored = False
            # Belt and braces: the flag above stops this arm writing bytecode, but a caller
            # supplying its own runner can put the writing back.
            purged += purge_bytecode(list(saved))
    verdict = verdict_for(returncode)
    return {
        "mutations": [{"path": str(p)} for p, _, _ in planned],
        "test": nodeid,
        "pytest_returncode": returncode,
        "timeout_s": timeout,
        "verdict": verdict,
        "failure": failure_reason(output),
        "restored": restored,
        "bytecode_purged": purged,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Mutate by exact anchor, run one test arm, restore from a copy taken first.")
    ap.add_argument("--mutate", nargs=3, action="append", metavar=("FILE", "OLD_FILE", "NEW_FILE"),
                    help="repeatable; every mutation is applied together as ONE arm")
    ap.add_argument("--test", required=True, metavar="NODEID", help="the pytest node id to run")
    ap.add_argument("--timeout", type=float, default=None, metavar="SECONDS",
                    help="bound the arm; a mutation can make a test SPIN rather than fail")
    ap.add_argument("--json", action="store_true", help="machine-readable envelope")
    args = ap.parse_args(argv)

    if not args.mutate:
        print("mutation_arm: no --mutate given", file=sys.stderr)
        return 2

    try:
        planned = plan_mutations(args.mutate)
    except (AnchorError, OSError) as exc:
        print(f"mutation_arm: refused, nothing written - {exc}", file=sys.stderr)
        return 2

    try:
        report = run_arm(planned, args.test, timeout=args.timeout)
    except AnchorError as exc:
        print(f"mutation_arm: refused before mutating - {exc}", file=sys.stderr)
        return 2

    if not report["restored"]:
        print("mutation_arm: RESTORE FAILED - the files on disk are NOT the originals",
              file=sys.stderr)
    if args.json:
        print(json.dumps({"ok": True, "command": "mutation_arm", "data": report}, indent=2))
    else:
        print(f"{report['verdict'].upper()}: {args.test}")
        if report["failure"]:
            print(f"  reason: {report['failure']}")
        if report["verdict"] == "inconclusive":
            print(f"  pytest exit {report['pytest_returncode']} - the arm did not run",
                  file=sys.stderr)
        if report["verdict"] == "timeout":
            print(f"  killed at {report['timeout_s']}s - the arm did not finish, so this says "
                  "nothing about whether it would have noticed; the mutation may make it SPIN",
                  file=sys.stderr)
    return 2 if not report["restored"] else exit_code_for(report["verdict"])


if __name__ == "__main__":
    sys.exit(main())
