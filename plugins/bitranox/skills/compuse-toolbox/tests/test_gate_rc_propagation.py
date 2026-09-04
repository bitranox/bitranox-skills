"""A single failing gate's OWN exit code must survive the runner.

Collapsing every failure to 1 re-creates, one layer out, the exact masking this tool exists
to prevent. A pipe masks with its last element's status; a runner masks with its own. It bites
hardest on a gate whose codes are a TAXONOMY rather than pass/fail: the provmm Leg 3 perf gate
uses 0 = clean, 2 = a metric regressed, 1 = no metrics measured, so a run reported as 1 reads as
"the measurement crashed" when it actually returned a verdict. Measured 2026-09-04: a background
task notification said "exit code 1" and four tool calls went into hunting a defect in the gate's
exit plumbing that did not exist.
"""

import os
import shlex
import subprocess
import sys

import gate


def quoted(*argv):
    """One command string that gate's splitter parses back to exactly `argv`, on either platform.

    Duplicated from test_gate rather than imported: a sibling TEST module is not importable by
    bare name from here (only the skill's scripts/ dir is put on sys.path), and coupling one test
    file's fixtures to another's buys nothing for six lines.
    """
    if os.name == "nt":
        return subprocess.list2cmdline(list(argv))
    return " ".join(shlex.quote(a) for a in argv)


def code(n):
    """One shell-quoted command string that exits with `n`, on either platform."""
    return quoted(sys.executable, "-c", f"raise SystemExit({n})")


def emits(text):
    """A gate that exits 0 while printing `text` - the zero-test refusal's shape."""
    return quoted(sys.executable, "-c", f"print({text!r})")


class TestASingleFailedGateHandsBackItsOwnCode:
    def test_a_gate_exiting_2_makes_the_runner_exit_2(self, tmp_path):
        rc = gate.main(["--gate", code(2), "--log", str(tmp_path / "g.log")])
        assert rc == 2, "the runner collapsed a taxonomy code into a generic failure"

    def test_a_gate_exiting_3_makes_the_runner_exit_3(self, tmp_path):
        rc = gate.main(["--gate", code(3), "--log", str(tmp_path / "g.log")])
        assert rc == 3

    def test_a_gate_exiting_1_still_exits_1(self, tmp_path):
        """The common case must not move."""
        rc = gate.main(["--gate", code(1), "--log", str(tmp_path / "g.log")])
        assert rc == 1

    def test_a_passing_gate_still_exits_0(self, tmp_path):
        rc = gate.main(["--gate", code(0), "--log", str(tmp_path / "g.log")])
        assert rc == 0


class TestAmbiguityFallsBackToOne:
    """Propagating is only honest when there is ONE code to propagate."""

    def test_two_gates_failing_with_different_codes_exit_1(self, tmp_path):
        rc = gate.main(["--gate", code(2), "--gate", code(3),
                        "--log", str(tmp_path / "g.log")])
        assert rc == 1, "two different codes have no single answer; 1 is the honest one"

    def test_two_gates_failing_with_the_SAME_code_propagate_it(self, tmp_path):
        rc = gate.main(["--gate", code(2), "--gate", code(2),
                        "--log", str(tmp_path / "g.log")])
        assert rc == 2


class TestAZeroExitRefusalNeverPropagatesZero:
    """The zero-test refusal is the dangerous edge: the gate EXITED 0 and is still red, so
    handing back its own code would report success for the one failure mode that is invisible
    to an exit code in the first place."""

    def test_a_gate_that_exited_zero_but_ran_no_tests_exits_1_not_0(self, tmp_path):
        rc = gate.main(["--gate", emits("running 0 tests"), "--log", str(tmp_path / "g.log")])
        assert rc == 1, "a zero-test refusal must never hand back the gate's own 0"

    def test_a_zero_test_refusal_beside_a_code_2_failure_exits_1(self, tmp_path):
        rc = gate.main(["--gate", emits("running 0 tests"), "--gate", code(2),
                        "--log", str(tmp_path / "g.log")])
        assert rc == 1
