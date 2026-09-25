"""Tests for mutation_arm.py - mutate by exact anchor, run one test arm, restore.

The fixtures build a real tiny project and run real pytest against it: the whole value of this
tool is what pytest actually reports, so a stubbed runner would test the wrong thing.
"""

import json
import os
import py_compile
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

import mutation_arm as M

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "mutation_arm.py"


SOURCE = '''\
def classify(value):
    if value < 0:
        return "negative"
    if value == 0:
        return "zero"
    return "positive"
'''

TEST = '''\
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from src import classify


def test_negative():
    assert classify(-1) == "negative"


def test_zero():
    assert classify(0) == "zero"
'''


def make_project(tmp_path):
    (tmp_path / "src.py").write_text(SOURCE, encoding="utf-8")
    (tmp_path / "test_src.py").write_text(TEST, encoding="utf-8")
    return tmp_path


def run(tmp_path, *args):
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(tmp_path),
    )


# --------------------------------------------------------------------------
# The summary line, not a grep of the log
# --------------------------------------------------------------------------


def test_failure_line_reads_the_summary_not_the_traceback():
    """The motivating trap: a pytest.raises(X) SOURCE line echoed in a traceback contains X,
    so a grep for X concludes X was raised. The summary says the opposite."""
    output = (
        "    with pytest.raises(KernelError):\n"
        "E   Failed: DID NOT RAISE <class 'KernelError'>\n"
        "=========================== short test summary info ============================\n"
        "FAILED test_src.py::test_boom - Failed: DID NOT RAISE <class 'KernelError'>\n"
    )
    assert M.failure_reason(output) == "Failed: DID NOT RAISE <class 'KernelError'>"


def test_failure_line_is_none_when_nothing_failed():
    assert M.failure_reason("2 passed in 0.01s\n") is None


def test_failure_line_handles_a_collection_error():
    output = (
        "=========================== short test summary info ============================\n"
        "ERROR test_src.py - ModuleNotFoundError: No module named 'nope'\n"
    )
    assert "ModuleNotFoundError" in M.failure_reason(output)


# --------------------------------------------------------------------------
# End to end against real pytest
# --------------------------------------------------------------------------


def test_a_mutation_the_test_notices_is_killed(tmp_path):
    p = make_project(tmp_path)
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt",
               "--test", "test_src.py::test_zero", "--json")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    data = json.loads(proc.stdout)["data"]
    assert data["verdict"] == "killed"
    assert "assert" in (data["failure"] or "").lower()


def test_a_mutation_the_test_cannot_see_survives(tmp_path):
    """The finding worth having: this arm does not cover that line."""
    p = make_project(tmp_path)
    (p / "old.txt").write_text('return "negative"', encoding="utf-8")
    (p / "new.txt").write_text('return "NEGATIVE"', encoding="utf-8")
    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt",
               "--test", "test_src.py::test_zero", "--json")
    assert proc.returncode == 1, (proc.stdout, proc.stderr)
    assert json.loads(proc.stdout)["data"]["verdict"] == "survived"


def test_the_file_is_restored_byte_for_byte(tmp_path):
    p = make_project(tmp_path)
    before = (p / "src.py").read_bytes()
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    run(p, "--mutate", "src.py", "old.txt", "new.txt", "--test", "test_src.py::test_zero")
    assert (p / "src.py").read_bytes() == before


def test_an_absent_anchor_refuses_and_writes_nothing(tmp_path):
    p = make_project(tmp_path)
    before = (p / "src.py").read_bytes()
    (p / "old.txt").write_text("this text is not in the file", encoding="utf-8")
    (p / "new.txt").write_text("x", encoding="utf-8")
    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt", "--test", "test_src.py::test_zero")
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert (p / "src.py").read_bytes() == before


def test_a_test_that_never_ran_is_inconclusive_not_a_pass(tmp_path):
    """pytest exits 5 when it collects nothing. Reading that as 'survived' would report a
    vacuous test as a covered one."""
    p = make_project(tmp_path)
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt",
               "--test", "test_src.py::test_does_not_exist", "--json")
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert json.loads(proc.stdout)["data"]["verdict"] == "inconclusive"


def test_several_anchors_mutate_together_in_one_arm(tmp_path):
    """Defence in depth leaves a single-layer mutation green, so an arm must break every layer."""
    p = make_project(tmp_path)
    (p / "a_old.txt").write_text('if value < 0:', encoding="utf-8")
    (p / "a_new.txt").write_text('if value < -10**9:', encoding="utf-8")
    (p / "b_old.txt").write_text('if value == 0:', encoding="utf-8")
    (p / "b_new.txt").write_text('if value == -10**9:', encoding="utf-8")
    proc = run(p, "--mutate", "src.py", "a_old.txt", "a_new.txt",
               "--mutate", "src.py", "b_old.txt", "b_new.txt",
               "--test", "test_src.py::test_zero", "--json")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    data = json.loads(proc.stdout)["data"]
    assert len(data["mutations"]) == 2
    assert (p / "src.py").read_text(encoding="utf-8") == SOURCE


SPINNING_TEST = '''\
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from src import classify


def test_spins_until_classify_reports_zero():
    """Bounded only by the behaviour under test, so a mutation makes it loop forever."""
    seen = []
    while "zero" not in seen:
        seen.append(classify(0))
    assert seen == ["zero"]
'''


def test_a_mutation_that_makes_the_arm_SPIN_is_reported_not_waited_on(tmp_path):
    """The failure this tool exists to prevent, in the tool itself.

    A mutation can make the arm loop forever rather than fail: the test's only exit is the
    behaviour being mutated. Measured 2026-09-02 in agentswarm, twice in one sweep - the arm ran
    at 97% CPU until it was killed by hand, and killing it skipped the restore, leaving a mutated
    file on disk. An unbounded `subprocess.run` here turns one hanging arm into a hanging battery
    and reports nothing at all, which is strictly worse than a wrong verdict.
    """
    p = make_project(tmp_path)
    (p / "test_src.py").write_text(SPINNING_TEST, encoding="utf-8")
    before = (p / "src.py").read_bytes()
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")

    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt",
               "--test", "test_src.py::test_spins_until_classify_reports_zero",
               "--timeout", "5", "--json")

    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    data = json.loads(proc.stdout)["data"]
    assert data["verdict"] == "timeout", data
    assert data["pytest_returncode"] is None, "a killed run has no exit code to report"
    assert data["restored"] is True, "the restore must run even when the arm is killed"
    assert (p / "src.py").read_bytes() == before


def test_a_timeout_is_not_reported_as_the_arm_noticing(tmp_path):
    """The control. A hang says the arm could not answer, never that it answered no - folding it
    into `killed` would report an untested mutation as a covered one, which is the same false
    all-clear `verdict_for` already refuses for pytest's exit 5."""
    assert M.verdict_for(None) == "timeout"
    assert M.exit_code_for("timeout") == 2


def test_an_arm_inside_the_timeout_is_unaffected(tmp_path):
    """A bound set where it can fire during a healthy arm is not a bound, it is a flaky tool."""
    p = make_project(tmp_path)
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt",
               "--test", "test_src.py::test_zero", "--timeout", "120", "--json")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert json.loads(proc.stdout)["data"]["verdict"] == "killed"


# --------------------------------------------------------------------------
# Bytecode: the arm must not read a cache older than the mutation, nor leave
# one holding the mutant behind
# --------------------------------------------------------------------------


LENGTH_PRESERVING = ('return "negative"', 'return "positive"')


def _at_the_start_of_a_second():
    """Wait until a second has just ticked over.

    The whole hazard is an mtime SECOND collision, so a trial that begins mid-second sometimes
    straddles the tick and stops reproducing. Starting fresh gives the compile and the arm's write
    the better part of a second to land together, which is what a fast edit-then-verify loop does
    anyway.
    """
    time.sleep(1.0 - (time.time() % 1.0))


def test_the_arm_leaves_no_bytecode_for_a_mutated_source(tmp_path):
    """Measured 2026-09-03 against the unpatched tool: the arm left `src.cpython-314.pyc` holding
    the MUTANT's constants beside a restored source that reads correctly. It is served whenever the
    source's mtime second equals the arm's write second, which a fast edit-then-verify loop
    produces routinely, and then a later run fails against bytecode no source file contains while
    grep and inspect.getsource both agree the code is right."""
    p = make_project(tmp_path)
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")

    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt", "--test", "test_src.py::test_zero")

    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    leftovers = list((p / "__pycache__").glob("src.*.pyc"))
    assert leftovers == [], f"cached mutant left behind: {leftovers}"


def test_a_cache_predating_the_mutation_is_not_served_in_place_of_it(tmp_path):
    """The opposite direction, and the worse one: a valid cache whose recorded mtime and size still
    match the mutant is served INSTEAD of it, the test passes, and the arm reports SURVIVED - it
    says the test is vacuous when the mutation never ran. Interleaved A/B, 2026-09-03: 6 of 6
    trials SURVIVED before the purge and 6 of 6 KILLED after."""
    p = make_project(tmp_path)
    (p / "old.txt").write_text(LENGTH_PRESERVING[0], encoding="utf-8")
    (p / "new.txt").write_text(LENGTH_PRESERVING[1], encoding="utf-8")
    assert len(LENGTH_PRESERVING[0]) == len(LENGTH_PRESERVING[1]), "the hazard needs an equal size"

    for _ in range(2):
        shutil.rmtree(p / "__pycache__", ignore_errors=True)
        _at_the_start_of_a_second()
        now = int(time.time())
        os.utime(p / "src.py", (now, now))
        py_compile.compile(str(p / "src.py"), doraise=True)
        cached = list((p / "__pycache__").glob("src.*.pyc"))
        assert cached, "the trial needs a cache to be at risk of serving"

        proc = run(p, "--mutate", "src.py", "old.txt", "new.txt",
                   "--test", "test_src.py::test_negative", "--json")

        data = json.loads(proc.stdout)["data"]
        assert data["verdict"] == "killed", f"the mutant never ran: {data}"
        assert [Path(c).name for c in data["bytecode_purged"]] == [c.name for c in cached]


def test_the_child_runs_with_bytecode_writing_off(tmp_path):
    """The braces to the purge's belt. Removing the cache afterwards still leaves a window where
    the mutant is on disk for anything else to import; not writing it is what closes that."""
    p = make_project(tmp_path)
    seen = p / "seen.txt"
    probe = (f"import os, pathlib; pathlib.Path({str(seen)!r}).write_text("
             "os.environ.get('PYTHONDONTWRITEBYTECODE', 'UNSET')); raise SystemExit(1)")
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    planned = M.plan_mutations([[str(p / "src.py"), str(p / "old.txt"), str(p / "new.txt")]])

    M.run_arm(planned, "test_src.py::test_zero", runner=[sys.executable, "-c", probe])

    assert seen.read_text() == "1"


def test_the_cache_search_uses_the_files_real_name_and_covers_every_tag(tmp_path):
    """The miss that deepened the original trap: the cache is named for the SOURCE FILE, so a
    hyphenated hook module caches as `ci-watch-nudge.cpython-314.pyc` while a search by its
    underscored import alias matches only a sibling and reads as "no stale cache present"."""
    source = tmp_path / "ci-watch-nudge.py"
    source.write_text("x = 1\n", encoding="utf-8")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    mine = {"ci-watch-nudge.cpython-313.pyc", "ci-watch-nudge.cpython-314.pyc",
            "ci-watch-nudge.cpython-314.opt-1.pyc"}
    for name in mine | {"ci_watch_nudge.cpython-314.pyc"}:
        (cache / name).write_bytes(b"")

    found = {c.name for c in M.bytecode_caches(source)}

    assert found == mine, "every tag and opt level of THIS file, and no neighbour's"
    assert M.bytecode_caches(tmp_path / "claims.toml") == [], "a data file has no bytecode"


def test_a_cache_that_cannot_be_removed_refuses_the_arm(tmp_path):
    """Refusing beats proceeding: the guarantee is about the state, not about the unlink call, and
    an arm that may be running bytecode nobody wrote answers nothing."""
    p = make_project(tmp_path)
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    cache = p / "__pycache__"
    cache.mkdir()
    (cache / "src.cpython-314.pyc").write_bytes(b"")
    before = (p / "src.py").read_bytes()
    cache.chmod(0o555)
    try:
        try:
            (cache / "src.cpython-314.pyc").unlink()
            pytest.skip("this user can unlink inside a read-only directory, so there is no refusal to test")
        except OSError:
            pass

        proc = run(p, "--mutate", "src.py", "old.txt", "new.txt", "--test", "test_src.py::test_zero")

        assert proc.returncode == 2, (proc.stdout, proc.stderr)
        assert "refused before mutating" in proc.stderr
        assert (p / "src.py").read_bytes() == before, "the refusal must precede the mutation"
    finally:
        cache.chmod(0o755)


# The ARM leaves behind something named like a cache for the mutated source that cannot be
# unlinked: a DIRECTORY. unlink() refuses a directory on every platform, so the after-arm purge
# fails the same way a read-only __pycache__ would, with no chmod and no root caveat.
_LEAVES_UNREMOVABLE_CACHE = TEST + '''

def test_leaves_cache():
    here = __import__("pathlib").Path(__file__).parent
    (here / "__pycache__" / "src.cpython-399.pyc").mkdir(parents=True)
'''


def test_a_cache_that_survives_the_arm_is_not_reported_as_refused_before_mutating(tmp_path):
    """The purge after the arm raised the same error as the purge before it, so main() said
    "refused before mutating" about an arm that had mutated, run and restored."""
    p = make_project(tmp_path)
    (p / "test_src.py").write_text(_LEAVES_UNREMOVABLE_CACHE, encoding="utf-8")
    before = (p / "src.py").read_bytes()
    (p / "old.txt").write_text('return "negative"', encoding="utf-8")
    (p / "new.txt").write_text('return "NEGATIVE"', encoding="utf-8")

    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt",
               "--test", "test_src.py::test_leaves_cache", "--json")

    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "refused before mutating" not in proc.stderr
    assert "the arm ran" in proc.stderr and "restored" in proc.stderr
    assert "src.cpython-399.pyc" in proc.stderr
    data = json.loads(proc.stdout)["data"]
    assert data["verdict"] == "survived", "the verdict the arm earned is still reported"
    assert data["restored"] is True
    assert data["bytecode_left"] and data["bytecode_left"][0].endswith("src.cpython-399.pyc")
    assert (p / "src.py").read_bytes() == before, "restored even though the purge failed"


def test_an_arm_that_cannot_start_is_an_error_after_restoring_not_a_refusal(tmp_path):
    """Sibling of the above: the runner fails to START after the mutation is on disk. Raised, it
    reached main() as "refused before mutating" about a file that had been mutated."""
    p = make_project(tmp_path)
    before = (p / "src.py").read_bytes()
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    planned = M.plan_mutations([[str(p / "src.py"), str(p / "old.txt"), str(p / "new.txt")]])

    report = M.run_arm(planned, "test_src.py::test_zero",
                       runner=[str(tmp_path / "no-such-interpreter")])

    assert report["verdict"] == "error"
    assert "could not start the arm" in report["failure"]
    assert report["restored"] is True
    assert (p / "src.py").read_bytes() == before
    assert M.exit_code_for(report["verdict"]) == 2


def test_a_clean_arm_reports_no_bytecode_left(tmp_path):
    """Control: the field is empty when the after-arm purge succeeded."""
    p = make_project(tmp_path)
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt",
               "--test", "test_src.py::test_zero", "--json")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert json.loads(proc.stdout)["data"]["bytecode_left"] == []


# --------------------------------------------------------------------------
# An exit 1 is KILLED only when pytest actually reported a failure
# --------------------------------------------------------------------------


def test_a_runner_without_pytest_is_inconclusive_not_killed(tmp_path):
    """The documented `uv run scripts/mutation_arm.py` gives an interpreter with no pytest:
    `python -m pytest` then exits 1 with "No module named pytest", which read as KILLED for
    every arm - a whole battery reporting perfect tests that never ran."""
    p = make_project(tmp_path)
    (p / "old.txt").write_text('return "negative"', encoding="utf-8")
    (p / "new.txt").write_text('return "NEGATIVE"', encoding="utf-8")
    planned = M.plan_mutations([[str(p / "src.py"), str(p / "old.txt"), str(p / "new.txt")]])

    report = M.run_arm(planned, "test_src.py::test_zero",
                       runner=[sys.executable, "-m", "no_such_module_pytest_zz"])

    assert report["pytest_returncode"] == 1
    assert report["verdict"] == "inconclusive"
    assert M.exit_code_for(report["verdict"]) == 2


def test_the_cli_reports_a_pytest_that_never_ran_as_inconclusive(tmp_path):
    """End to end: a `pytest` module that exits 1 without running anything, as a missing or
    broken pytest does, must not be scored as the arm noticing the mutation."""
    p = make_project(tmp_path)
    (p / "pytest.py").write_text(
        "import sys\nprint('No module named pytest', file=sys.stderr)\nraise SystemExit(1)\n",
        encoding="utf-8")
    (p / "old.txt").write_text('return "negative"', encoding="utf-8")
    (p / "new.txt").write_text('return "NEGATIVE"', encoding="utf-8")
    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt", "--test", "test_src.py::test_zero",
               "--json")
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert json.loads(proc.stdout)["data"]["verdict"] == "inconclusive"


def test_verdict_needs_a_summary_line_for_killed():
    assert M.verdict_for(1, "FAILED t.py::x - AssertionError\n") == "inconclusive"
    summary =("=== short test summary info ===\n"
               "FAILED t.py::x - AssertionError: boom\n")
    assert M.verdict_for(1, summary) == "killed"
    assert M.verdict_for(1, "No module named pytest\n") == "inconclusive"
    assert M.verdict_for(0, "") == "survived"
    assert M.verdict_for(None, "") == "timeout"


# --------------------------------------------------------------------------
# Every failure to read or write is exit 2, never a traceback read as SURVIVED
# --------------------------------------------------------------------------


def test_no_mutate_is_a_usage_error(tmp_path):
    proc = run(make_project(tmp_path), "--test", "test_src.py::test_zero")
    assert proc.returncode == 2
    assert "no --mutate" in proc.stderr


def test_a_non_utf8_source_is_refused_before_anything_is_written(tmp_path):
    p = make_project(tmp_path)
    latin = b"# -*- coding: latin-1 -*-\n" + SOURCE.replace("zero", "z\xe9ro").encode("latin-1")
    (p / "src.py").write_bytes(latin)
    (p / "old.txt").write_text('return "negative"', encoding="utf-8")
    (p / "new.txt").write_text('return "NEGATIVE"', encoding="utf-8")
    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt", "--test", "test_src.py::test_zero")
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "Traceback" not in proc.stderr
    assert "nothing written" in proc.stderr
    assert (p / "src.py").read_bytes() == latin


def test_a_non_utf8_anchor_file_is_refused(tmp_path):
    p = make_project(tmp_path)
    (p / "old.txt").write_bytes(b'return "z\xe9ro"')
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt", "--test", "test_src.py::test_zero")
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "Traceback" not in proc.stderr


def test_a_bom_anchor_file_still_matches(tmp_path):
    """Notepad writes a BOM; read as plain utf-8 it becomes part of the anchor, which then
    appears 0 times in the source."""
    p = make_project(tmp_path)
    (p / "old.txt").write_bytes(b'\xef\xbb\xbfreturn "zero"')
    (p / "new.txt").write_bytes(b'\xef\xbb\xbfreturn "ZERO"')
    proc = run(p, "--mutate", "src.py", "old.txt", "new.txt", "--test", "test_src.py::test_zero",
               "--json")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert (p / "src.py").read_text(encoding="utf-8") == SOURCE


def _cannot_write(path):
    """True when making `path` read-only really stops this user writing it (not root)."""
    path.chmod(0o444)
    try:
        with open(path, "ab"):
            pass
    except OSError:
        return True
    return False


def test_an_unwritable_source_is_exit_2_not_a_traceback(tmp_path):
    p = make_project(tmp_path)
    before = (p / "src.py").read_bytes()
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    try:
        if not _cannot_write(p / "src.py"):
            pytest.skip("this user can write a read-only file, so there is no failure to test")
        proc = run(p, "--mutate", "src.py", "old.txt", "new.txt",
                   "--test", "test_src.py::test_zero", "--json")
    finally:
        (p / "src.py").chmod(0o644)
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "Traceback" not in proc.stderr
    data = json.loads(proc.stdout)["data"]
    assert data["verdict"] == "error" and data["restored"] is True
    assert "RESTORE FAILED" not in proc.stderr, "an untouched file is not a failed restore"
    assert (p / "src.py").read_bytes() == before


def test_a_restore_that_cannot_write_is_reported_loudly(tmp_path):
    """The arm leaves the mutant on disk and makes it unwritable, so the restore fails. That must
    be exit 2 and RESTORE FAILED, never a traceback."""
    p = make_project(tmp_path)
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    probe = p / "probe.txt"
    probe.write_text("x", encoding="utf-8")
    if not _cannot_write(probe):
        pytest.skip("this user can write a read-only file, so there is no failure to test")
    lock = f"import os; os.chmod({str(p / 'src.py')!r}, 0o444); raise SystemExit(1)"
    planned = M.plan_mutations([[str(p / "src.py"), str(p / "old.txt"), str(p / "new.txt")]])
    try:
        report = M.run_arm(planned, "test_src.py::test_zero", runner=[sys.executable, "-c", lock])
    finally:
        (p / "src.py").chmod(0o644)
    assert report["restored"] is False
    assert 'return "ZERO"' in (p / "src.py").read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Several mutations: each anchor is checked against the text the earlier ones leave
# --------------------------------------------------------------------------


def test_an_anchor_consumed_by_an_earlier_mutation_is_refused_before_writing(tmp_path):
    p = make_project(tmp_path)
    (p / "a_old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "a_new.txt").write_text('return "ZERO"', encoding="utf-8")
    specs = [[str(p / "src.py"), str(p / "a_old.txt"), str(p / "a_new.txt")],
             [str(p / "src.py"), str(p / "a_old.txt"), str(p / "a_new.txt")]]
    with pytest.raises(M.AnchorError):
        M.plan_mutations(specs)
    proc = run(p, "--mutate", "src.py", "a_old.txt", "a_new.txt",
               "--mutate", "src.py", "a_old.txt", "a_new.txt", "--test", "test_src.py::test_zero")
    assert proc.returncode == 2
    assert "nothing written" in proc.stderr


def test_a_second_anchor_created_by_the_first_mutation_is_accepted(tmp_path):
    """The control: validation sees the text as the arm will, so a chain that only makes sense
    in order is planned, not refused."""
    p = make_project(tmp_path)
    (p / "a_old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "a_new.txt").write_text('return "ZERO"', encoding="utf-8")
    (p / "b_old.txt").write_text('return "ZERO"', encoding="utf-8")
    (p / "b_new.txt").write_text('return "Zero"', encoding="utf-8")
    planned = M.plan_mutations([[str(p / "src.py"), str(p / "a_old.txt"), str(p / "a_new.txt")],
                                [str(p / "src.py"), str(p / "b_old.txt"), str(p / "b_new.txt")]])
    assert len(planned) == 2


# --------------------------------------------------------------------------
# CRLF sources stay CRLF while the arm runs
# --------------------------------------------------------------------------


def test_a_crlf_source_keeps_its_line_endings_during_the_arm(tmp_path):
    p = make_project(tmp_path)
    crlf = SOURCE.replace("\n", "\r\n").encode("utf-8")
    (p / "src.py").write_bytes(crlf)
    (p / "old.txt").write_text('if value == 0:\n        return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('if value == 0:\n        return "ZERO"', encoding="utf-8")
    seen = p / "seen.bin"
    probe = (f"import pathlib; pathlib.Path({str(seen)!r}).write_bytes("
             f"pathlib.Path({str(p / 'src.py')!r}).read_bytes()); raise SystemExit(0)")
    planned = M.plan_mutations([[str(p / "src.py"), str(p / "old.txt"), str(p / "new.txt")]])
    M.run_arm(planned, "test_src.py::test_zero", runner=[sys.executable, "-c", probe])
    during = seen.read_bytes()
    assert b'return "ZERO"\r\n' in during
    assert during.count(b"\n") == during.count(b"\r\n")
    assert (p / "src.py").read_bytes() == crlf


# --------------------------------------------------------------------------
# The reported reason, and output a console cannot encode
# --------------------------------------------------------------------------


def test_a_parametrize_id_containing_the_separator_does_not_cut_the_reason():
    output = ("=========================== short test summary info ============================\n"
              "FAILED test_src.py::test_x[a - b] - AssertionError: assert 'ZERO' == 'zero'\n")
    assert M.failure_reason(output) == "AssertionError: assert 'ZERO' == 'zero'"


def test_a_line_separator_inside_the_reason_does_not_cut_it():
    output = ("=========================== short test summary info ============================\n"
              "FAILED test_src.py::test_x - AssertionError: a b\n")
    assert M.failure_reason(output) == "AssertionError: a b"


def test_a_non_cp1252_node_id_does_not_crash_a_cp1252_console(tmp_path):
    """A traceback here exits 1, which reads as SURVIVED - a false finding."""
    p = make_project(tmp_path)
    (p / "test_src.py").write_text(TEST + "\n\ndef test_日本():\n"
                                   "    assert classify(0) == 'zero'\n", encoding="utf-8")
    (p / "old.txt").write_text('return "zero"', encoding="utf-8")
    (p / "new.txt").write_text('return "ZERO"', encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--mutate", "src.py", "old.txt", "new.txt",
         "--test", "test_src.py::test_日本"],
        capture_output=True, cwd=str(p), check=False,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"})
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert b"Traceback" not in proc.stderr
    assert proc.stdout.startswith(b"KILLED")
