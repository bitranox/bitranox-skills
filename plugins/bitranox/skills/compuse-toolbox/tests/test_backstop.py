"""RED/GREEN tests for backstop.py - the arm-a-deadline-over-async-work jig.

The tool exists because the two decisions it encodes were fumbled repeatedly by hand:
an exit condition satisfiable while the worker is still going, and a deadline with no
way to be cancelled, which fires a false alarm at a job that finished on time.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from backstop import ArmRefused, Outcome, Probe, decide, main, validate_arm, wait


# --- the pure decision core -------------------------------------------------

def test_waits_while_nothing_is_satisfied_and_time_remains() -> None:
    assert decide(Probe(cancelled=False, done=False), elapsed=10.0, deadline=60.0) is Outcome.WAIT


def test_done_when_the_finished_artifact_appears() -> None:
    assert decide(Probe(cancelled=False, done=True), elapsed=10.0, deadline=60.0) is Outcome.DONE


def test_cancel_beats_done_and_beats_the_deadline() -> None:
    """The controller saying 'the subject reported' always wins, even past the deadline -
    otherwise a job that finished on time still produces a timeout."""
    assert decide(Probe(cancelled=True, done=False), elapsed=999.0, deadline=60.0) is Outcome.CANCELLED
    assert decide(Probe(cancelled=True, done=True), elapsed=10.0, deadline=60.0) is Outcome.CANCELLED


def test_timeout_only_when_nothing_is_satisfied_and_the_deadline_passed() -> None:
    assert decide(Probe(cancelled=False, done=False), elapsed=60.0, deadline=60.0) is Outcome.TIMEOUT
    assert decide(Probe(cancelled=False, done=False), elapsed=61.0, deadline=60.0) is Outcome.TIMEOUT


def test_a_finished_worker_at_the_deadline_reports_done_not_timeout() -> None:
    """Both true at once is the race the hand-rolled loops got wrong."""
    assert decide(Probe(cancelled=False, done=True), elapsed=99.0, deadline=60.0) is Outcome.DONE


# --- refusing to arm a backstop that is already satisfied -------------------

def test_refuses_to_arm_when_the_done_file_already_exists(tmp_path: Path) -> None:
    """The defect this tool exists to stop: a backstop whose exit condition is ALREADY
    true provides no coverage and reports success within one poll."""
    report = tmp_path / "report.md"
    report.write_text("stale from a previous run\n", encoding="utf-8")
    with pytest.raises(ArmRefused, match="already exists"):
        validate_arm(done_file=report, repo=None, base=None)


def test_arms_when_the_done_file_is_absent(tmp_path: Path) -> None:
    validate_arm(done_file=tmp_path / "report.md", repo=None, base=None)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "r"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.invalid")
    _git(r, "config", "user.name", "t")
    (r / "a.txt").write_text("one\n", encoding="utf-8")
    _git(r, "add", "a.txt")
    _git(r, "commit", "-q", "-m", "first")
    return r


def test_refuses_to_arm_when_head_already_moved_past_base(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "a.txt").write_text("two\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-a", "-m", "second")
    with pytest.raises(ArmRefused, match="already moved"):
        validate_arm(done_file=None, repo=repo, base=base)


def test_arms_when_head_is_still_at_base(repo: Path) -> None:
    validate_arm(done_file=None, repo=repo, base=_git(repo, "rev-parse", "HEAD"))


def test_refuses_to_arm_with_no_exit_condition_at_all(tmp_path: Path) -> None:
    """A pure sleep is not a backstop over anything - it cannot distinguish finished
    from hung, which is the whole point."""
    with pytest.raises(ArmRefused, match="no exit condition"):
        validate_arm(done_file=None, repo=None, base=None)


# --- the loop, driven with injected time so it runs instantly ---------------

class _Clock:
    """A fake monotonic clock advanced only by the sleeps the loop itself performs."""

    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


def test_wait_times_out_when_the_worker_never_finishes(tmp_path: Path) -> None:
    from backstop import Outcome as O, wait

    clock = _Clock()
    outcome, elapsed = wait(
        deadline=300.0, interval=60.0,
        done_file=tmp_path / "never.md", cancel_file=None, repo=None, base=None,
        label="t", now=clock.now, sleep=clock.sleep,
    )
    assert outcome is O.TIMEOUT
    assert elapsed >= 300.0


def test_wait_returns_done_one_settle_poll_after_the_artifact_appears(tmp_path: Path) -> None:
    """The artifact appears at 120s and the answer comes at 180s, not 120s. A poller watching
    from outside cannot tell a completed write from a first chunk, so one poll of the size
    holding still is the cheapest honest confirmation - and it is the whole cost of never
    standing down over a half-written report."""
    from backstop import Outcome as O, wait

    report = tmp_path / "report.md"
    clock = _Clock()

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        if clock.t >= 120.0:
            report.write_text("finished\n", encoding="utf-8")

    outcome, elapsed = wait(
        deadline=3600.0, interval=60.0,
        done_file=report, cancel_file=None, repo=None, base=None,
        label="t", now=clock.now, sleep=sleep,
    )
    assert outcome is O.DONE
    assert elapsed == pytest.approx(180.0)


def test_settle_zero_answers_on_sight_for_an_atomically_written_artifact(tmp_path: Path) -> None:
    """The escape hatch, and the only condition under which it is sound: a worker that renames
    its report into place is never observable half-written, so waiting a poll buys nothing."""
    from backstop import Outcome as O, wait

    report = tmp_path / "report.md"
    clock = _Clock()

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        if clock.t >= 120.0:
            staged = report.with_suffix(".tmp")
            staged.write_text("finished\n", encoding="utf-8")
            staged.rename(report)

    outcome, elapsed = wait(
        deadline=3600.0, interval=60.0,
        done_file=report, cancel_file=None, repo=None, base=None,
        label="t", settle=0.0, now=clock.now, sleep=sleep,
    )
    assert outcome is O.DONE
    assert elapsed == pytest.approx(120.0)


def test_a_touched_but_empty_report_is_never_finished(tmp_path: Path) -> None:
    """The other half a size floor covers: `touch` produces a file that exists and says nothing.
    Checked even at settle=0, where nothing else stands between it and a DONE."""
    from backstop import DoneFileWatch

    report = tmp_path / "report.md"
    report.write_text("", encoding="utf-8")
    watch = DoneFileWatch(report, settle=0.0)
    assert watch.finished(0.0) is False
    assert watch.finished(600.0) is False

    report.write_text("finished\n", encoding="utf-8")
    assert watch.finished(601.0) is True


def test_the_settle_window_restarts_every_time_the_size_moves(tmp_path: Path) -> None:
    """A worker that pauses between chunks must not bank the pause: each new size starts the
    window over, so only a size that then holds for the full window counts."""
    from backstop import DoneFileWatch

    report = tmp_path / "report.md"
    watch = DoneFileWatch(report, settle=60.0)

    report.write_text("chunk one\n", encoding="utf-8")
    assert watch.finished(0.0) is False
    assert watch.finished(59.0) is False

    with report.open("a", encoding="utf-8") as fh:
        fh.write("chunk two\n")
    assert watch.finished(60.0) is False, "the size moved, so the window restarts here"
    assert watch.finished(119.0) is False
    assert watch.finished(120.0) is True


def test_an_absent_or_unreadable_done_file_is_not_finished(tmp_path: Path) -> None:
    """Absent must contribute False rather than raise - the file legitimately does not exist for
    most of the run, which is the whole point of waiting for it."""
    from backstop import DoneFileWatch

    assert DoneFileWatch(tmp_path / "never.md", settle=0.0).finished(0.0) is False
    assert DoneFileWatch(None, settle=0.0).finished(0.0) is False


def test_wait_cancels_even_after_the_deadline_has_passed(tmp_path: Path) -> None:
    """The false-alarm case: the subject reported, so no timeout may be emitted."""
    from backstop import Outcome as O, wait

    sentinel = tmp_path / ".done"
    sentinel.write_text("", encoding="utf-8")
    clock = _Clock()
    clock.t = 10_000.0
    outcome, _ = wait(
        deadline=60.0, interval=60.0,
        done_file=tmp_path / "never.md", cancel_file=sentinel, repo=None, base=None,
        label="t", now=clock.now, sleep=clock.sleep,
    )
    assert outcome is O.CANCELLED


def test_arms_on_a_cancel_file_alone(tmp_path: Path) -> None:
    """REGRESSION: found on first real use. A TEXT-RETURNING subagent writes no artifact at all,
    and for that case deadline-plus-sentinel is the documented sound shape - the controller
    touches the sentinel when the agent reports. The first version refused it as "no exit
    condition", which rejected exactly the case the rule prescribes."""
    validate_arm(done_file=None, repo=None, base=None, cancel_file=tmp_path / ".done")


def test_refuses_a_cancel_file_that_already_exists(tmp_path: Path) -> None:
    """A stale sentinel cancels on the first poll, which is the same no-coverage trap."""
    sentinel = tmp_path / ".done"
    sentinel.write_text("", encoding="utf-8")
    with pytest.raises(ArmRefused, match="already exists"):
        validate_arm(done_file=None, repo=None, base=None, cancel_file=sentinel)


# --- a done-file still being written is not a finished one ------------------

def test_wait_does_not_report_done_while_the_report_is_still_being_written(tmp_path: Path) -> None:
    """A worker that creates its report early and appends to it satisfies a bare exists() test
    mid-write, so the backstop stands down and the controller reads a truncated artifact. This
    must hold with no extra flag: the safe reading is the default, not something to opt into."""
    from backstop import Outcome as O, wait

    report = tmp_path / "report.md"
    clock = _Clock()

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        if 60.0 <= clock.t <= 300.0:
            with report.open("a", encoding="utf-8") as fh:
                fh.write("a paragraph the controller must not miss\n")

    outcome, elapsed = wait(
        deadline=3600.0, interval=60.0,
        done_file=report, cancel_file=None, repo=None, base=None,
        label="t", now=clock.now, sleep=sleep,
    )
    assert outcome is O.DONE
    assert elapsed > 300.0, f"stood down at {elapsed}s while the worker wrote until 300s"
    assert report.read_text(encoding="utf-8").count("a paragraph") == 5


# --- timing arguments that would silently disarm the backstop --------------

@pytest.mark.parametrize("deadline", ["nan", "inf", "-5", "0"])
def test_main_refuses_a_deadline_that_is_not_a_positive_finite_number(tmp_path: Path, deadline: str) -> None:
    rc = main(["--deadline", deadline, "--interval", "1", "--cancel-file", str(tmp_path / "c")],
              now=_Clock().now, sleep=_boom)
    assert rc == 2


@pytest.mark.parametrize("interval", ["0", "-1", "nan", "inf"])
def test_main_refuses_an_interval_that_is_not_a_positive_finite_number(tmp_path: Path, interval: str) -> None:
    rc = main(["--deadline", "10", "--interval", interval, "--cancel-file", str(tmp_path / "c")],
              now=_Clock().now, sleep=_boom)
    assert rc == 2


@pytest.mark.parametrize("settle", ["-1", "nan", "inf"])
def test_main_refuses_a_bad_settle(tmp_path: Path, settle: str) -> None:
    rc = main(["--deadline", "10", "--interval", "1", "--settle", settle,
               "--done-file", str(tmp_path / "r.md")], now=_Clock().now, sleep=_boom)
    assert rc == 2


def _boom(seconds: float) -> None:
    raise AssertionError("the loop must not start when the arguments are refused")


# --- --base must name a commit ------------------------------------------------

@pytest.mark.parametrize("base", ["", "HEAD", "abc", "zzzzzzzz"])
def test_refuses_a_base_that_is_not_an_abbreviated_or_full_sha(repo: Path, base: str) -> None:
    """An empty base compares zero characters, so HEAD never 'moves' and a finished commit
    reads as a TIMEOUT."""
    with pytest.raises(ArmRefused, match="is not a commit sha"):
        validate_arm(done_file=None, repo=repo, base=base)


def test_accepts_an_abbreviated_base(repo: Path) -> None:
    validate_arm(done_file=None, repo=repo, base=_git(repo, "rev-parse", "--short", "HEAD"))


def test_a_path_that_is_not_a_repo_is_refused_at_arm_time(tmp_path: Path) -> None:
    with pytest.raises(ArmRefused, match="cannot read HEAD"):
        validate_arm(done_file=None, repo=tmp_path, base="a" * 40)


def test_main_exits_2_when_the_repo_is_not_a_repo(tmp_path: Path) -> None:
    rc = main(["--deadline", "10", "--interval", "1", "--repo", str(tmp_path), "--base", "a" * 40],
              now=_Clock().now, sleep=_boom)
    assert rc == 2


def test_main_refuses_repo_without_base(repo: Path) -> None:
    assert main(["--deadline", "10", "--repo", str(repo)], now=_Clock().now, sleep=_boom) == 2


# --- the repo branch of the loop, against a real repo ------------------------

def test_wait_reports_done_when_a_commit_lands(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    clock = _Clock()

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        if clock.t == 120.0:
            (repo / "a.txt").write_text("two\n", encoding="utf-8")
            _git(repo, "commit", "-q", "-a", "-m", "second")

    outcome, elapsed = wait(deadline=600.0, interval=60.0, done_file=None, cancel_file=None,
                            repo=repo, base=base, label="t", now=clock.now, sleep=sleep)
    assert outcome is Outcome.DONE
    assert elapsed == 120.0


def test_a_repo_that_vanishes_mid_run_is_a_lost_signal_not_a_crash(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    clock = _Clock()

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        if clock.t == 60.0:
            _remove_repo(repo)

    outcome, elapsed = wait(deadline=600.0, interval=60.0, done_file=None, cancel_file=None,
                            repo=repo, base=base, label="t", now=clock.now, sleep=sleep)
    assert outcome is Outcome.LOST
    assert elapsed == 60.0


def _remove_repo(path: Path) -> None:
    """git marks object files read-only and Windows refuses to delete those, so clear the bit and
    retry. `onexc` replaced the deprecated `onerror` in 3.12; 3.11 is still in the CI matrix."""
    def retry(func, target, _exc) -> None:
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=retry)
    else:
        shutil.rmtree(path, onerror=retry)


def test_a_cancel_still_wins_over_a_lost_repo(repo: Path, tmp_path: Path) -> None:
    probe = Probe(cancelled=True, done=False, lost="gone")
    assert decide(probe, elapsed=1.0, deadline=60.0) is Outcome.CANCELLED


# --- main(): exit codes and the line it prints ------------------------------

def test_main_exits_0_and_says_finished_when_the_done_file_settles(tmp_path: Path, capsys) -> None:
    report = tmp_path / "r.md"
    clock = _Clock()

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        if clock.t == 10.0:
            report.write_text("done\n", encoding="utf-8")

    rc = main(["--deadline", "100", "--interval", "10", "--done-file", str(report), "--label", "x"],
              now=clock.now, sleep=sleep)
    assert rc == 0
    assert "BACKSTOP [x]: work finished at 20s" in capsys.readouterr().out


def test_main_exits_0_when_cancelled(tmp_path: Path, capsys) -> None:
    cancel = tmp_path / "c"
    clock = _Clock()

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        cancel.touch()

    assert main(["--deadline", "100", "--interval", "10", "--cancel-file", str(cancel)],
                now=clock.now, sleep=sleep) == 0
    assert "cancelled by the controller" in capsys.readouterr().out


def test_main_exits_1_on_timeout(tmp_path: Path, capsys) -> None:
    clock = _Clock()
    assert main(["--deadline", "30", "--interval", "10", "--cancel-file", str(tmp_path / "c")],
                now=clock.now, sleep=clock.sleep) == 1
    assert "TIMEOUT after 30s" in capsys.readouterr().out


def test_main_exits_2_when_the_repo_is_lost(repo: Path, capsys) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    clock = _Clock()

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        _remove_repo(repo)

    rc = main(["--deadline", "100", "--interval", "10", "--repo", str(repo), "--base", base],
              now=clock.now, sleep=sleep)
    assert rc == 2
    assert "lost" in capsys.readouterr().out.lower()


def test_main_exits_2_when_already_satisfied(tmp_path: Path, capsys) -> None:
    report = tmp_path / "r.md"
    report.write_text("stale\n", encoding="utf-8")
    assert main(["--deadline", "10", "--done-file", str(report)], now=_Clock().now, sleep=_boom) == 2
    assert "BACKSTOP REFUSED" in capsys.readouterr().err


def test_a_non_cp1252_label_does_not_crash_a_cp1252_stdout(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parent.parent / "scripts" / "backstop.py"
    cancel = tmp_path / "c"
    res = subprocess.run(
        [sys.executable, str(script), "--deadline", "0.2", "--interval", "0.05",
         "--cancel-file", str(cancel), "--label", "task \u2717"],
        capture_output=True, env={**os.environ, "PYTHONIOENCODING": "cp1252"}, timeout=60,
    )
    assert res.returncode == 1, res.stderr
    assert b"TIMEOUT" in res.stdout


# --- a --repo must be the repository ROOT git resolves, never a directory inside another repo ---
#
# git -C <dir> walks UP until it finds a repository. A --repo that is only a subdirectory - or a
# nested repo whose .git was removed mid-run - answers with the ENCLOSING repo's HEAD, which is a
# different sha from --base, so the backstop reported DONE for work it never watched.

@pytest.fixture()
def nested(tmp_path: Path) -> tuple[Path, Path]:
    """(parent repo, child repo inside it), each with one commit of its own."""
    parent = tmp_path / "parent"
    for r in (parent, parent / "child"):
        r.mkdir()
        _git(r, "init", "-q", "-b", "main")
        _git(r, "config", "user.email", "t@example.invalid")
        _git(r, "config", "user.name", "t")
        (r / "f.txt").write_text(r.name + "\n", encoding="utf-8")
        _git(r, "add", "f.txt")
        _git(r, "commit", "-q", "-m", r.name)
    return parent, parent / "child"


def test_a_nested_repo_whose_git_dir_vanishes_mid_run_is_lost_not_done(nested) -> None:
    parent, child = nested
    base = _git(child, "rev-parse", "HEAD")
    assert base != _git(parent, "rev-parse", "HEAD")
    clock = _Clock()

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        if clock.t == 60.0:
            _remove_repo(child / ".git")

    outcome, elapsed = wait(deadline=600.0, interval=60.0, done_file=None, cancel_file=None,
                            repo=child, base=base, label="t", now=clock.now, sleep=sleep)
    assert outcome is Outcome.LOST, "the enclosing repo's HEAD said nothing about this one"
    assert elapsed == 60.0


def test_a_subdirectory_of_a_repo_is_refused_at_arm_time(nested) -> None:
    parent, _child = nested
    sub = parent / "plain"
    sub.mkdir()
    with pytest.raises(ArmRefused, match="not the root"):
        validate_arm(done_file=None, repo=sub, base=_git(parent, "rev-parse", "HEAD"))


def test_the_nested_repo_root_itself_still_arms(nested) -> None:
    """Control: a nested repo that IS a root is watched on its own HEAD, not the parent's."""
    _parent, child = nested
    validate_arm(done_file=None, repo=child, base=_git(child, "rev-parse", "HEAD"))


def test_main_exits_2_for_a_subdirectory_repo(nested, capsys) -> None:
    parent, _child = nested
    sub = parent / "plain"
    sub.mkdir()
    rc = main(["--deadline", "10", "--repo", str(sub), "--base", _git(parent, "rev-parse", "HEAD")],
              now=_Clock().now, sleep=_boom)
    assert rc == 2
    assert "not the root" in capsys.readouterr().err
