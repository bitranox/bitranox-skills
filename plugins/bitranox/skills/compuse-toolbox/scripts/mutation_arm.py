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

Run:
  `uv run scripts/mutation_arm.py --mutate src/x.py old.txt new.txt --test tests/t.py::test_y`
  `... --mutate a.py o1.txt n1.txt --mutate b.py o2.txt n2.txt --test tests/t.py::test_y`
  add `--json` for an envelope

Exit codes: 0 = KILLED (the arm noticed the mutation), 1 = SURVIVED (it did not - the finding),
2 = INCONCLUSIVE or usage error (an absent anchor, or a test that never ran).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from anchor_edit import AnchorError, replace_exact, require_unique

_SUMMARY_HEADER = "short test summary info"


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


def verdict_for(returncode: int) -> str:
    """What a pytest exit code means for a mutation arm.

    5 is the one that matters: pytest collected NOTHING, so the arm never ran. Folding that into
    "passed" would report an untested line as a covered one, which is the exact false all-clear a
    mutation battery exists to prevent.
    """
    return {0: "survived", 1: "killed"}.get(returncode, "inconclusive")


def exit_code_for(verdict: str) -> int:
    return {"killed": 0, "survived": 1}.get(verdict, 2)


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


def run_arm(planned, nodeid, *, runner=None):
    """Apply every mutation, run the arm, restore from copies taken first. Returns a report."""
    runner = runner or [sys.executable, "-m", "pytest"]
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
            proc = subprocess.run(
                [*runner, nodeid, "-q", "--no-header", "-rfE", "--tb=no",
                 "-p", "no:cacheprovider"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
        finally:
            restored = True
            for path, copy in saved.items():
                shutil.copy2(copy, path)
                if path.read_bytes() != copy.read_bytes():
                    restored = False
    output = proc.stdout + proc.stderr
    verdict = verdict_for(proc.returncode)
    return {
        "mutations": [{"path": str(p)} for p, _, _ in planned],
        "test": nodeid,
        "pytest_returncode": proc.returncode,
        "verdict": verdict,
        "failure": failure_reason(output),
        "restored": restored,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Mutate by exact anchor, run one test arm, restore from a copy taken first.")
    ap.add_argument("--mutate", nargs=3, action="append", metavar=("FILE", "OLD_FILE", "NEW_FILE"),
                    help="repeatable; every mutation is applied together as ONE arm")
    ap.add_argument("--test", required=True, metavar="NODEID", help="the pytest node id to run")
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

    report = run_arm(planned, args.test)

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
    return 2 if not report["restored"] else exit_code_for(report["verdict"])


if __name__ == "__main__":
    sys.exit(main())
