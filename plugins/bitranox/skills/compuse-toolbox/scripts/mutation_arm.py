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

Run it with the PROJECT's interpreter - the one that has pytest and the project installed - since
the arm is `<this interpreter> -m pytest`. `uv run scripts/mutation_arm.py` gives an interpreter
with neither; an arm whose pytest exits 1 without naming a failure is reported INCONCLUSIVE, never
KILLED, so that mistake shows as a column of exit-2 arms rather than a battery of perfect tests.
  `.venv/bin/python scripts/mutation_arm.py --mutate src/x.py old.txt new.txt --test tests/t.py::test_y --timeout 90`
  `... --mutate a.py o1.txt n1.txt --mutate b.py o2.txt n2.txt --test tests/t.py::test_y`
  add `--json` for an envelope; its "ok" is false exactly when the exit code is 2, and a
  refusal prints one too (`"data": null` and an `"error"`)

Sources and anchor files are UTF-8 (an anchor file's BOM is ignored); a CRLF source keeps its
CRLF while mutated, and an LF anchor file matches it.

Exit codes: 0 = KILLED (the arm noticed the mutation), 1 = SURVIVED (it did not - the finding),
2 = INCONCLUSIVE, TIMEOUT, ERROR (a source that could not be written, or an arm that could not
be started), a failed restore, cached bytecode that survived the purge AFTER the arm (the arm ran
and was restored; the verdict is still reported, and the leftover files are named), or a
usage error (an absent anchor, a file that is not UTF-8, a test that never ran, a pytest that
exited 1 without reporting a failure, or an arm still running at --timeout).
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

#: How this tool must be launched, read by hooks/toolbox-nudge.py from the source without importing
#: it: the arm is `<this interpreter> -m pytest`, so only the PROJECT's interpreter (which has
#: pytest and the project) gives a verdict - under `uv run` every arm is INCONCLUSIVE.
LAUNCH_WITH = "project-python"

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
    # Split on newlines only: splitlines() also cuts at form feed and U+2028, which an assertion
    # message can carry, and that would truncate the reason mid-sentence.
    lines = [line.rstrip("\r") for line in output.split("\n")]
    start = next((i for i, line in enumerate(lines) if _SUMMARY_HEADER in line), None)
    if start is None:
        return None
    for line in lines[start + 1:]:
        if not line.startswith(("FAILED ", "ERROR ")):
            continue
        rest = line.split(" ", 1)[1]
        return _reason_after_nodeid(rest) or line.strip()
    return None


def _reason_after_nodeid(rest: str) -> str:
    """The text after `<nodeid> - `.

    A parametrize id may itself contain ` - ` and brackets (`test_x[a - b]`, `test_x[a[1] - b]`),
    so the id's end is found by walking its brackets to the one that closes the first: a search
    for the first `] - ` stops at a NESTED bracket and hands part of the id back as the reason.
    An id whose brackets do not balance falls back to that search.
    """
    balanced = _reason_after_balanced_id(rest)
    if balanced is not None:
        return balanced
    search_from = 0
    bracket, first_sep = rest.find("["), rest.find(" - ")
    if bracket != -1 and (first_sep == -1 or bracket < first_sep):
        close = rest.find("] - ", bracket)
        if close != -1:
            search_from = close + 1
    _, sep, reason = rest[search_from:].partition(" - ")
    return reason.strip() if sep else ""


def _reason_after_balanced_id(rest: str) -> str | None:
    """The reason after a `path::name[...]` id whose brackets balance, else None.

    The name part after `::` is Python identifiers joined by `::`, so the first `[` after the
    first `::` opens the parametrize id. The id ends where that bracket closes, and a well-formed
    line continues with ` - ` there; anything else is left to the caller's fallback.
    """
    names = rest.find("::")
    bracket = rest.find("[", names) if names != -1 else -1
    if bracket == -1 or " " in rest[names:bracket]:
        return None
    depth = 0
    for index in range(bracket, len(rest)):
        depth += {"[": 1, "]": -1}.get(rest[index], 0)
        if depth == 0:
            before, sep, reason = rest[index + 1:].partition(" - ")
            if sep and not before:
                return reason.strip()
            return None
    return None


def verdict_for(returncode: int | None, output: str | None = None) -> str:
    """What a pytest exit code means for a mutation arm.

    5 is the one that matters: pytest collected NOTHING, so the arm never ran. Folding that into
    "passed" would report an untested line as a covered one, which is the exact false all-clear a
    mutation battery exists to prevent.

    1 is KILLED only when pytest's summary names a failure. An interpreter with no pytest exits 1
    too (`No module named pytest`), and so does a runner that dies before collecting; scoring
    that as the arm noticing reported every arm of a battery as a perfect test that never ran.
    When `output` is given, an exit 1 without a FAILED/ERROR summary line is INCONCLUSIVE.

    `None` means the arm was KILLED at the timeout, which is its own verdict and not a failure to
    notice: a mutation can make a test loop forever rather than fail, when the test's only exit is
    the behaviour being mutated. Reporting that as "killed" would credit the arm with catching
    something it never reached.
    """
    if returncode is None:
        return "timeout"
    if returncode == 1 and output is not None and failure_reason(output) is None:
        return "inconclusive"
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


def remove_bytecode(paths):
    """Remove the cached bytecode for each source; return (removed, remaining). Never raises.

    `remaining` is read from the resulting state rather than from the unlink calls: a cache left
    behind by a read-only directory or a permission error is still there whatever unlink said.
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
    return removed, remaining


def purge_bytecode(paths):
    """Remove the cached bytecode for each source, then REFUSE if any survived.

    For the purge BEFORE the arm: an arm that may be running bytecode nobody wrote is worth
    refusing outright. The purge after the arm must not raise - by then the mutation was applied
    and restored, and refusing would misreport that - so it uses remove_bytecode and reports.
    """
    removed, remaining = remove_bytecode(paths)
    if remaining:
        raise AnchorError(
            "cached bytecode survived removal, the arm could run it: " + ", ".join(remaining))
    return removed


def _read_source(path: Path) -> str:
    """The source exactly as stored - newline="" keeps CRLF, so writing it back keeps it too."""
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def _write_source(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _read_anchor(path_arg, crlf: bool) -> str:
    """An anchor file, BOM dropped (Notepad writes one) and line endings matched to the source."""
    text = Path(path_arg).read_text(encoding="utf-8-sig")
    return text.replace("\n", "\r\n") if crlf else text


def plan_mutations(specs):
    """Validate every anchor BEFORE writing anything, returning (path, old, new) triples.

    All or nothing: one absent or ambiguous anchor refuses the whole arm. A partly-applied arm
    would run the tests against a state nobody described. Each anchor is checked against the text
    as the EARLIER mutations to the same file leave it, which is the text the arm will edit -
    checking against the original accepted a chain that then failed half-way through writing.
    """
    planned = []
    texts: dict[Path, str] = {}
    for path_arg, old_file, new_file in specs:
        path = Path(path_arg)
        if not path.is_file():
            raise AnchorError(f"not a file: {path}")
        key = path.resolve()
        if key not in texts:
            texts[key] = _read_source(path)
        crlf = "\r\n" in texts[key]
        old, new = _read_anchor(old_file, crlf), _read_anchor(new_file, crlf)
        require_unique(texts[key], old, label=f"anchor for {path}")
        texts[key] = replace_exact(texts[key], old, new)
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
    # ignore_cleanup_errors: the cleanup runs AFTER the arm, and a raise there would reach main()
    # as "refused before mutating" about an arm that mutated, ran and restored.
    with tempfile.TemporaryDirectory(prefix="mutation-arm-", ignore_cleanup_errors=True) as tmp:
        saved = {}
        for index, (path, _, _) in enumerate(planned):
            # Index-prefixed: two mutations may target the same file, and two files in different
            # directories may share a basename. Either collision would restore the wrong bytes.
            copy = Path(tmp) / f"{index}-{path.name}"
            shutil.copy2(path, copy)
            saved.setdefault(path, copy)
        returncode, output, error = None, "", None
        try:
            try:
                for path, old, new in planned:
                    _write_source(path, replace_exact(_read_source(path), old, new))
            except OSError as exc:
                # An unwritable source must not escape as a traceback: its exit 1 reads as
                # SURVIVED. The restore below still runs for whatever was already written.
                error = f"could not apply the mutation: {exc}"
            else:
                try:
                    returncode, output = _run_pytest(runner, nodeid, timeout)
                except OSError as exc:
                    # The mutation is ON DISK by now, so this must not escape to main(), whose
                    # handler says the arm was refused before mutating.
                    error = f"could not start the arm: {exc}"
        finally:
            restored = _restore(saved)
            # Belt and braces: the flag above stops this arm writing bytecode, but a caller
            # supplying its own runner can put the writing back. Reported, never raised: the
            # arm has run and been restored, and a raise here reached main() as "refused
            # before mutating" and dropped the verdict the arm earned.
            removed, left = remove_bytecode(list(saved))
            purged += removed
    verdict = "error" if error else verdict_for(returncode, output)
    return {
        "mutations": [{"path": str(p)} for p, _, _ in planned],
        "test": nodeid,
        "pytest_returncode": returncode,
        "timeout_s": timeout,
        "verdict": verdict,
        "failure": error or failure_reason(output),
        "restored": restored,
        "bytecode_purged": purged,
        "bytecode_left": left,
    }


def _run_pytest(runner, nodeid, timeout):
    """(returncode, merged output) of the arm; returncode None when it hit the timeout.

    `-vv`, not `-q`: below that verbosity pytest trims each summary line to the terminal width
    and drops the message entirely when the node id alone fills it, and a captured child sees a
    narrow default width. Widening COLUMNS instead would reach the tests themselves, whose
    rendering can depend on it.
    """
    try:
        proc = subprocess.run(
            [*runner, nodeid, "-vv", "--no-header", "-rfE", "--tb=no", "-p", "no:cacheprovider"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
            # Merged onto the real environment, never a fresh dict: on Windows a child without
            # SystemRoot loses Winsock and dies with EMPTY output.
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired as expired:
        # A killed run has no exit code. Its partial output is bytes when the process was killed
        # before the text wrapper saw it, so it is decoded defensively rather than concatenated.
        return None, _partial_output(expired)
    return proc.returncode, proc.stdout + proc.stderr


def _restore(saved) -> bool:
    """Put every saved copy back; True only when every file now matches its copy byte for byte.

    A file that already matches is left alone, so a source that could never be written (and so
    was never changed) is not reported as a failed restore. A copy that cannot be written back is
    reported as False rather than raised: raising here would replace the verdict with a
    traceback and skip the loud RESTORE FAILED that this outcome needs.
    """
    restored = True
    for path, copy in saved.items():
        try:
            if path.read_bytes() != copy.read_bytes():
                shutil.copy2(copy, path)
            restored = restored and path.read_bytes() == copy.read_bytes()
        except OSError:
            restored = False
    return restored


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
    _tolerate_unencodable_output()

    if not args.mutate:
        return _refuse("no --mutate given", as_json=args.json)

    try:
        planned = plan_mutations(args.mutate)
    except UnicodeDecodeError as exc:
        return _refuse(f"refused, nothing written - a source or anchor file is not UTF-8 "
                       f"({exc.reason} at byte {exc.start})", as_json=args.json)
    except (AnchorError, OSError) as exc:
        return _refuse(f"refused, nothing written - {exc}", as_json=args.json)

    try:
        report = run_arm(planned, args.test, timeout=args.timeout)
    except (AnchorError, OSError) as exc:
        return _refuse(f"refused before mutating - {exc}", as_json=args.json)

    if not report["restored"]:
        print("mutation_arm: RESTORE FAILED - the files on disk are NOT the originals",
              file=sys.stderr)
    if report["bytecode_left"]:
        print("mutation_arm: the arm ran and the sources were restored, but cached bytecode "
              "survived removal and a later run could execute it instead of the source - delete "
              "it before the next run: " + ", ".join(report["bytecode_left"]), file=sys.stderr)
    if args.json:
        print(json_envelope(report))
    else:
        print(f"{report['verdict'].upper()}: {args.test}")
        if report["failure"]:
            print(f"  reason: {report['failure']}")
        if report["verdict"] == "inconclusive":
            print(f"  pytest exit {report['pytest_returncode']} - the arm did not run",
                  file=sys.stderr)
            if report["pytest_returncode"] == 1:
                print("  no FAILED/ERROR line in pytest's summary: is pytest installed for "
                      f"{sys.executable}? Run this tool with the project's own interpreter.",
                      file=sys.stderr)
        if report["verdict"] == "timeout":
            print(f"  killed at {report['timeout_s']}s - the arm did not finish, so this says "
                  "nothing about whether it would have noticed; the mutation may make it SPIN",
                  file=sys.stderr)
    return outcome_code(report)


def outcome_code(report) -> int:
    """The exit code a finished arm earns: its verdict's, unless the restore or the purge failed.

    The one place the code is decided, so the envelope's "ok" and the process exit cannot disagree.
    """
    if not report["restored"] or report["bytecode_left"]:
        return 2
    return exit_code_for(report["verdict"])


def json_envelope(report) -> str:
    """The --json envelope. "ok" is false exactly when the exit code is 2 (an error): SURVIVED
    exits 1 as the FINDING, so it is still ok. Derived from outcome_code, never set on its own -
    a literal true here reported every inconclusive, timed-out and unrestored arm as ok."""
    return json.dumps({"ok": outcome_code(report) != 2, "command": "mutation_arm",
                       "data": report}, indent=2)


def _refuse(message: str, *, as_json: bool) -> int:
    """Report a refusal (exit 2) on stderr, and on stdout too as an envelope under --json:
    a caller parsing stdout would otherwise read an empty string, which fails as a JSON error
    rather than as the refusal it was."""
    print(f"mutation_arm: {message}", file=sys.stderr)
    if as_json:
        print(json.dumps({"ok": False, "command": "mutation_arm", "data": None,
                          "error": message}, indent=2))
    return 2


def _tolerate_unencodable_output() -> None:
    """A cp1252 console must not crash the report: that traceback exits 1, which reads SURVIVED."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (ValueError, OSError):
            continue


if __name__ == "__main__":
    sys.exit(main())
