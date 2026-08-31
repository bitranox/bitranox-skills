"""Tests for mutation_arm.py - mutate by exact anchor, run one test arm, restore.

The fixtures build a real tiny project and run real pytest against it: the whole value of this
tool is what pytest actually reports, so a stubbed runner would test the wrong thing.
"""

import json
import subprocess
import sys
from pathlib import Path

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
