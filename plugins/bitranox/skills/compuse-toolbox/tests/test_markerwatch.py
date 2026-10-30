"""Tests for markerwatch.py - follow a log, answer only on a producer-owned line prefix.

The follow loop runs against a REAL file; the clock and sleep are the injected seams, so a test
appends to the file "between polls" by doing it inside the fake sleep.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import markerwatch as M

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "markerwatch.py"
_CLI_TIMEOUT = 60


class FakeTime:
    """A clock that advances only when slept, running `actions` one per sleep."""

    def __init__(self, actions=()):
        self.now = 0.0
        self.actions = list(actions)

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds
        if self.actions:
            self.actions.pop(0)()


def _append(path: Path, text: str):
    def act():
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)
    return act


# ---- what a marker may be ----------------------------------------------------------------------

@pytest.mark.parametrize("marker", ["", "   ", " ALL PASSED", "^ALL", "PASS.*", "====", "---"])
def test_a_marker_that_cannot_identify_the_producer_is_refused(marker):
    assert M.marker_problem(marker) is not None
    with pytest.raises(M.MarkerError):
        M.Markers((marker,))


@pytest.mark.parametrize("marker", ["ALL GATES PASSED", "==== done", "[PASS]", "Job completed"])
def test_a_worded_marker_is_accepted(marker):
    assert M.marker_problem(marker) is None


def test_a_marker_is_a_case_sensitive_line_prefix_not_a_substring():
    markers = M.Markers(("FAIL",))
    assert M.match("FAIL: test_x", markers) == ("terminal", "FAIL")
    assert M.match("Event FailureReason=3", markers) is None          # case-folded substring
    assert M.match("  FAIL quoted in an indented echo", markers) is None
    assert M.match("run: grep FAIL log", markers) is None              # the waiter's own echo


def test_a_timestamp_is_stripped_only_when_asked():
    line = "2026-10-29T12:00:01.1234567Z Job completed"
    assert M.match(line, M.Markers(("Job completed",))) is None
    assert M.match(line, M.Markers(("Job completed",), strip=True)) == ("terminal",
                                                                         "Job completed")
    assert M.strip_timestamp("[12:00:01] ALL GATES PASSED") == "ALL GATES PASSED"


def test_a_terminal_marker_wins_over_a_progress_marker_it_extends():
    markers = M.Markers(("GATE RED",), ("GATE",))
    assert M.match("GATE RED - follow-up NOT run", markers) == ("terminal", "GATE RED")
    assert M.match("GATE 2 of 3", markers) == ("marker", "GATE")


# ---- calibration -------------------------------------------------------------------------------

def test_calibrate_counts_each_marker_on_a_finished_run():
    text = "==== start\nALL GATES PASSED? not yet\nstep\nALL GATES PASSED\n"
    counts = M.calibrate(text, M.Markers(("ALL GATES PASSED",), ("step",)))
    assert counts == {"ALL GATES PASSED": 2, "step": 1}


def test_cli_calibrate_refuses_a_terminal_marker_seen_twice_or_never(tmp_path):
    log = tmp_path / "done.log"
    log.write_text("==== gates\nALL GATES PASSED\n", encoding="utf-8")
    ok = M.execute(["calibrate", str(log), "--terminal", "ALL GATES PASSED"])
    assert ok == 0
    assert M.execute(["calibrate", str(log), "--terminal", "==== gates done"]) == 1
    log.write_text("ALL GATES PASSED (expected)\nALL GATES PASSED\n", encoding="utf-8")
    assert M.execute(["calibrate", str(log), "--terminal", "ALL GATES PASSED"]) == 1


# ---- following a real file ---------------------------------------------------------------------

def test_watch_answers_on_a_terminal_line_appended_later(tmp_path, capsys):
    log = tmp_path / "gate.log"
    log.write_text("old run\nALL GATES PASSED\n", encoding="utf-8")
    t = FakeTime([_append(log, "[PASS] make test (rc=0)\nnoise\n"),
                  _append(log, "ALL GATES PASSED\n")])
    code = M.execute(["watch", str(log), "--from", "end", "--marker", "[PASS]",
                      "--terminal", "ALL GATES PASSED", "--timeout", "30"],
                     clock=t.clock, sleep=t.sleep)
    assert code == 0
    assert capsys.readouterr().out.splitlines() == ["[PASS] make test (rc=0)", "ALL GATES PASSED"]


def test_watch_from_start_answers_on_what_is_already_there(tmp_path):
    log = tmp_path / "gate.log"
    log.write_text("ALL GATES PASSED\n", encoding="utf-8")
    t = FakeTime()
    assert M.execute(["watch", str(log), "--from", "start", "--terminal", "ALL GATES PASSED",
                      "--timeout", "5"], clock=t.clock, sleep=t.sleep) == 0
    assert t.now == 0.0


def test_watch_times_out_with_exit_1(tmp_path, capsys):
    log = tmp_path / "gate.log"
    log.write_text("", encoding="utf-8")
    t = FakeTime()
    assert M.execute(["watch", str(log), "--from", "start", "--terminal", "DONE",
                      "--timeout", "3"], clock=t.clock, sleep=t.sleep) == 1
    assert "no terminal marker within 3s" in capsys.readouterr().err


def test_a_half_written_line_is_not_matched_until_it_is_complete(tmp_path):
    log = tmp_path / "gate.log"
    log.write_text("", encoding="utf-8")
    t = FakeTime([_append(log, "ALL GATES PAS"), _append(log, "SED\n")])
    lines = list(M.follow(log, start="start", deadline=10, clock=t.clock, sleep=t.sleep))
    assert lines == ["ALL GATES PASSED"]


def test_a_log_that_does_not_exist_yet_is_waited_for_and_read_whole(tmp_path):
    log = tmp_path / "later.log"
    t = FakeTime([lambda: None, _append(log, "DONE\n")])
    assert M.execute(["watch", str(log), "--from", "end", "--terminal", "DONE",
                      "--timeout", "10"], clock=t.clock, sleep=t.sleep) == 0


def test_a_truncated_log_is_read_again_from_its_start(tmp_path):
    log = tmp_path / "gate.log"
    log.write_text("a long first run that the next run truncates\n", encoding="utf-8")

    def truncate_and_write():
        log.write_text("DONE\n", encoding="utf-8")

    t = FakeTime([truncate_and_write])
    cursor = M._Cursor()
    lines = list(M.follow(log, start="end", deadline=2, clock=t.clock, sleep=t.sleep,
                          cursor=cursor))
    assert lines == ["DONE"] and cursor.reopened == 1


def test_a_rotated_log_is_followed_under_its_name(tmp_path):
    log = tmp_path / "gate.log"
    log.write_text("first\n", encoding="utf-8")

    def rotate():
        log.rename(tmp_path / "gate.log.1")
        log.write_text("second run, longer than the first\nDONE\n", encoding="utf-8")

    t = FakeTime([rotate])
    lines = list(M.follow(log, start="end", deadline=2, clock=t.clock, sleep=t.sleep))
    assert lines == ["second run, longer than the first", "DONE"]


def test_watch_refuses_to_start_when_calibration_fails(tmp_path):
    log, done = tmp_path / "gate.log", tmp_path / "done.log"
    log.write_text("", encoding="utf-8")
    done.write_text("DONE early\nDONE\n", encoding="utf-8")
    t = FakeTime()
    assert M.execute(["watch", str(log), "--from", "start", "--terminal", "DONE",
                      "--calibrate", str(done), "--timeout", "5"],
                     clock=t.clock, sleep=t.sleep) == 2


# ---- the CLI -----------------------------------------------------------------------------------

def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          encoding="utf-8", check=False, timeout=_CLI_TIMEOUT)


def test_cli_ignore_case_is_refused_with_the_reason(tmp_path):
    log = tmp_path / "x.log"
    log.write_text("FAIL\n", encoding="utf-8")
    r = run_cli("calibrate", str(log), "--terminal", "FAIL", "-i")
    assert r.returncode == 2
    assert "-i is refused" in r.stderr


def test_cli_a_refused_marker_prints_an_envelope(tmp_path):
    log = tmp_path / "x.log"
    log.write_text("x\n", encoding="utf-8")
    r = run_cli("watch", str(log), "--from", "start", "--terminal", "====", "--json")
    assert r.returncode == 2
    env = json.loads(r.stdout)
    assert env["ok"] is False and "decoration" in env["error"]


def test_cli_watch_json_reports_the_terminal_line(tmp_path):
    log = tmp_path / "x.log"
    log.write_text("2026-10-29 10:00:00 step one\n2026-10-29 10:00:05 DONE ok\n",
                   encoding="utf-8")
    r = run_cli("watch", str(log), "--from", "start", "--strip-timestamp", "--marker", "step",
                "--terminal", "DONE", "--json")
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(r.stdout)["data"]
    assert data["terminal_line"] == "2026-10-29 10:00:05 DONE ok"
    assert data["matched"] == ["2026-10-29 10:00:00 step one", "2026-10-29 10:00:05 DONE ok"]


def test_cli_a_missing_from_is_a_usage_error(tmp_path):
    r = run_cli("watch", str(tmp_path / "x.log"), "--terminal", "DONE", "--json")
    assert r.returncode == 2
    assert json.loads(r.stdout)["ok"] is False


# ---- an unterminated last line -----------------------------------------------------------------

def test_a_terminal_marker_on_an_unterminated_last_line_answers_as_calibrate_counts_it(tmp_path):
    log = tmp_path / "gate.log"
    log.write_bytes(b"start\nALL GATES PASSED")                  # the producer wrote no final \n
    assert M.execute(["calibrate", str(log), "--terminal", "ALL GATES PASSED"]) == 0
    t = FakeTime()
    assert M.execute(["watch", str(log), "--from", "start", "--terminal", "ALL GATES PASSED",
                      "--timeout", "3"], clock=t.clock, sleep=t.sleep) == 0


def test_a_half_written_tail_that_stalls_never_fires_the_marker_it_is_a_prefix_of(tmp_path):
    log = tmp_path / "gate.log"
    log.write_bytes(b"start\nALL GATES PAS")
    t = FakeTime()
    assert M.execute(["watch", str(log), "--from", "start", "--terminal", "ALL GATES PASSED",
                      "--timeout", "3"], clock=t.clock, sleep=t.sleep) == 1


def test_a_stalled_tail_is_judged_again_once_the_producer_completes_it(tmp_path, capsys):
    # A tail read as `GATE` (a progress marker) must not hide the `GATE RED` it becomes.
    log = tmp_path / "gate.log"
    log.write_bytes(b"GATE")
    t = FakeTime([lambda: None, lambda: None, _append(log, " RED - stop\n")])
    code = M.execute(["watch", str(log), "--from", "start", "--marker", "GATE",
                      "--terminal", "GATE RED", "--timeout", "10"], clock=t.clock, sleep=t.sleep)
    assert code == 0
    assert capsys.readouterr().out.splitlines() == ["GATE", "GATE RED - stop"]


# ---- the timeout -------------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["nan", "inf", "-1", "0", "soon"])
def test_cli_a_timeout_that_is_not_a_finite_positive_number_is_a_usage_error(tmp_path, value):
    log = tmp_path / "x.log"
    log.write_text("", encoding="utf-8")
    r = run_cli("watch", str(log), "--from", "start", "--terminal", "DONE",
                "--timeout", value, "--json")
    assert r.returncode == 2, r.stdout + r.stderr
    assert json.loads(r.stdout)["ok"] is False
