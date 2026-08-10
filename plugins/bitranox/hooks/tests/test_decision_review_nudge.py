"""Tests for decision-review-nudge.py (the Stop hook that asks which decisions are unsettled).

The policy and the transcript reader are pure and are tested directly. The wiring is tested end to
end through the REAL signals module, with HOME redirected to tmp_path so the session scratch dir is
the test's own - no stubbing of the module under test, and the flag file that results is the real
one.

Transcript lines use the shapes Claude Code actually records, taken from real transcripts on disk
rather than from a guess: a Bash tool_use inside `message.content`, and a goal record as
`{"type": "attachment", "attachment": {"type": "goal_status", "met": <bool>, ...}}` - with
`sentinel` present while a goal runs and absent on the record that reports it met.

`Path.home()` reads USERPROFILE on Windows and HOME on POSIX, so both are set; patching only HOME
passes on Linux and writes into the developer's real home on Windows.

All content is ASCII.
"""

import io
import json
import sys

import pytest

import decision_review_nudge as DRN
import self_improve_signals as sig


@pytest.fixture
def scratch_home(tmp_path, monkeypatch):
    """Redirect the machine-local scratch dir at its real edge: the home directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


def bash_line(cmd):
    return json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]},
    })


def goal_line(met, condition="finish everything"):
    attachment = {"type": "goal_status", "met": met, "condition": condition}
    if not met:
        attachment["sentinel"] = True          # present while running, absent on the met record
    return json.dumps({"type": "attachment", "attachment": attachment, "userType": "external"})


def transcript(tmp_path, *lines, name="t.jsonl", trailing_partial=False):
    text = "\n".join(lines) + "\n" if lines else ""
    if trailing_partial:
        text += '{"type": "assistant", "message": {"content": [{"type": "too'
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def run_main(payload, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    rc = DRN.main()
    return rc, capsys.readouterr().out


def signals(commands=(), goal_state=DRN.GOAL_NONE):
    return DRN.Signals(list(commands), goal_state)


# --------------------------------------------------------------------------
# What counts as work concluding, with no goal in play
# --------------------------------------------------------------------------


def test_a_commit_concludes_the_work():
    assert DRN.reached_a_conclusion(signals(["git commit -F msg.txt -- src/"])) is True


def test_a_push_concludes_the_work():
    assert DRN.reached_a_conclusion(signals(["git push origin master"])) is True


def test_an_opened_pr_concludes_the_work():
    assert DRN.reached_a_conclusion(signals(["gh pr create --fill"])) is True


def test_reading_and_testing_do_not_conclude_anything():
    assert DRN.reached_a_conclusion(signals(["git status", "pytest -q", "ls -la"])) is False


def test_talking_about_a_commit_is_not_committing():
    """Why this reuses the repo gate's predicate: a CHANGELOG line about committing must not fire."""
    assert DRN.reached_a_conclusion(signals(['echo "remember to git commit -- paths"'])) is False


# --------------------------------------------------------------------------
# A /goal run: quiet until the objective is met
# --------------------------------------------------------------------------


def test_a_met_goal_concludes_the_work():
    assert DRN.reached_a_conclusion(signals(goal_state=DRN.GOAL_MET)) is True


def test_a_running_goal_also_counts_so_the_ask_is_never_missed():
    """The met verdict is written AFTER this hook reads, so waiting for it costs a whole turn."""
    assert DRN.reached_a_conclusion(signals([], DRN.GOAL_ACTIVE)) is True


def test_a_met_goal_fires_even_with_no_commit_at_all():
    """A goal can be met by work that never touched git - the objective is the conclusion."""
    assert DRN.reached_a_conclusion(signals([], DRN.GOAL_MET)) is True


# --------------------------------------------------------------------------
# Reading the transcript
# --------------------------------------------------------------------------


def test_every_bash_command_is_read_in_order(tmp_path):
    path = transcript(tmp_path, bash_line("ls"), bash_line("git commit -m x"), bash_line("git push"))
    assert DRN.transcript_signals(path).commands == ["ls", "git commit -m x", "git push"]


def test_a_transcript_without_a_goal_reports_none(tmp_path):
    path = transcript(tmp_path, bash_line("ls"))
    assert DRN.transcript_signals(path).goal_state == DRN.GOAL_NONE


def test_a_running_goal_is_read_as_active(tmp_path):
    path = transcript(tmp_path, goal_line(met=False), bash_line("git commit -m wip"))
    assert DRN.transcript_signals(path).goal_state == DRN.GOAL_ACTIVE


def test_the_last_goal_record_wins(tmp_path):
    """A goal reports met=false on every turn it runs, then once with met=true."""
    path = transcript(tmp_path, goal_line(met=False), goal_line(met=False), goal_line(met=True))
    assert DRN.transcript_signals(path).goal_state == DRN.GOAL_MET


def test_a_goal_that_went_back_to_running_is_active_again(tmp_path):
    path = transcript(tmp_path, goal_line(met=True), goal_line(met=False))
    assert DRN.transcript_signals(path).goal_state == DRN.GOAL_ACTIVE


def test_a_half_written_last_line_is_tolerated(tmp_path):
    """A transcript is appended to live, so the tail can be mid-write when the hook reads it."""
    path = transcript(tmp_path, bash_line("git commit -m x"), trailing_partial=True)
    assert DRN.transcript_signals(path).commands == ["git commit -m x"]


def test_a_missing_transcript_reads_as_nothing(tmp_path):
    s = DRN.transcript_signals(str(tmp_path / "nope.jsonl"))
    assert s.commands == [] and s.goal_state == DRN.GOAL_NONE


def test_non_bash_tool_uses_are_ignored(tmp_path):
    line = json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/x"}}]},
    })
    assert DRN.transcript_signals(transcript(tmp_path, line)).commands == []


# --------------------------------------------------------------------------
# End to end through the real signals module
# --------------------------------------------------------------------------


def test_a_session_that_committed_is_asked_before_it_stops(scratch_home, monkeypatch, capsys):
    path = transcript(scratch_home, bash_line("pytest -q"), bash_line("git commit -m 'ship it'"))
    rc, out = run_main({"session_id": "s1", "transcript_path": path}, monkeypatch, capsys)
    assert rc == 0
    assert json.loads(out)["decision"] == "block"


def test_a_session_still_in_progress_stays_silent(scratch_home, monkeypatch, capsys):
    """The false-positive side: a gate that fires mid-edit is one the user turns off."""
    path = transcript(scratch_home, bash_line("ls"), bash_line("pytest -q"), bash_line("git status"))
    rc, out = run_main({"session_id": "s2", "transcript_path": path}, monkeypatch, capsys)
    assert rc == 0 and out == ""


def test_a_goal_run_is_asked_when_the_objective_is_met(scratch_home, monkeypatch, capsys):
    path = transcript(scratch_home, goal_line(met=False), bash_line("git commit -m step"),
                      goal_line(met=True))
    _, out = run_main({"session_id": "s3", "transcript_path": path}, monkeypatch, capsys)
    assert json.loads(out)["decision"] == "block"


def test_a_one_turn_goal_is_asked_without_waiting_a_turn(scratch_home, monkeypatch, capsys):
    """The lag this fixes: at Stop time the record still reads met=false, and met=true lands after."""
    path = transcript(scratch_home, goal_line(met=False))
    _, out = run_main({"session_id": "s4", "transcript_path": path}, monkeypatch, capsys)
    assert json.loads(out)["decision"] == "block"


def test_a_session_is_asked_once_not_after_every_later_commit(scratch_home, monkeypatch, capsys):
    path = transcript(scratch_home, bash_line("git commit -m one"))
    _, first = run_main({"session_id": "s5", "transcript_path": path}, monkeypatch, capsys)
    _, second = run_main({"session_id": "s5", "transcript_path": path}, monkeypatch, capsys)
    assert json.loads(first)["decision"] == "block"
    assert second == "", "the second turn must not re-ask"


def test_another_sessions_flag_does_not_suppress_this_one(scratch_home, monkeypatch, capsys):
    """A per-PROJECT flag outlives its session and silences the next one; a session-keyed flag cannot."""
    DRN.mark_asked("an-older-session")
    path = transcript(scratch_home, bash_line("git commit -m x"))
    _, out = run_main({"session_id": "s6", "transcript_path": path}, monkeypatch, capsys)
    assert json.loads(out)["decision"] == "block"


def test_the_flag_path_is_keyed_by_session(scratch_home):
    assert DRN.asked_flag("one") != DRN.asked_flag("two")


# --------------------------------------------------------------------------
# A nudge must never wedge a turn
# --------------------------------------------------------------------------


def test_garbage_on_stdin_never_wedges_the_turn(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json at all"))
    assert DRN.main() == 0
    assert capsys.readouterr().out == ""


def test_an_event_without_a_transcript_is_ignored(scratch_home, monkeypatch, capsys):
    rc, out = run_main({"session_id": "s7"}, monkeypatch, capsys)
    assert rc == 0 and out == ""


def test_an_event_without_a_session_id_is_ignored(scratch_home, monkeypatch, capsys, tmp_path):
    path = transcript(tmp_path, bash_line("git commit -m x"))
    rc, out = run_main({"transcript_path": path}, monkeypatch, capsys)
    assert rc == 0 and out == ""


# --------------------------------------------------------------------------
# What the nudge actually says
# --------------------------------------------------------------------------


def test_the_reason_names_the_skill_to_invoke():
    assert "process-review-uncertain-decisions" in DRN._REASON


def test_the_reason_carries_the_suppression_rule():
    """Without this line the ask degrades into one more exhaustive finding list."""
    assert "clearly right" in DRN._REASON


def test_the_detector_is_the_repo_gates_own_predicate():
    """One definition, so the gate and this hook cannot disagree about what counts as concluding."""
    import repo_gate
    import shell_text
    assert repo_gate.is_gated_command is shell_text.is_gated_command
