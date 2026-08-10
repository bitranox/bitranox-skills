"""Tests for decision-review-nudge.py (the Stop hook that asks which decisions are unsettled).

The policy and the transcript reader are pure and are tested directly. The wiring is tested end to
end through the REAL signals module, with HOME redirected to tmp_path so the session scratch dir is
the test's own - no stubbing of the module under test, and the flag file that results is the real
one. Transcripts are written as real JSONL in the shape Claude Code records.

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


def transcript(tmp_path, *commands, name="t.jsonl", trailing_partial=False):
    """A transcript holding one Bash tool_use per command, in Claude Code's recorded shape."""
    lines = []
    for cmd in commands:
        lines.append(json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]},
        }))
    text = "\n".join(lines) + "\n"
    if trailing_partial:
        text += '{"type": "assistant", "message": {"content": [{"type": "too'
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def run_main(payload, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    rc = DRN.main()
    return rc, capsys.readouterr().out


# --------------------------------------------------------------------------
# What counts as work concluding
# --------------------------------------------------------------------------


def test_a_commit_concludes_the_work():
    assert DRN.reached_a_conclusion(["git commit -F msg.txt -- src/"]) is True


def test_a_push_concludes_the_work():
    assert DRN.reached_a_conclusion(["git push origin master"]) is True


def test_an_opened_pr_concludes_the_work():
    assert DRN.reached_a_conclusion(["gh pr create --fill"]) is True


def test_reading_and_testing_do_not_conclude_anything():
    assert DRN.reached_a_conclusion(["git status", "pytest -q", "ls -la"]) is False


def test_talking_about_a_commit_is_not_committing():
    """Why this reuses the repo gate's predicate: a CHANGELOG line about committing must not fire."""
    assert DRN.reached_a_conclusion(['echo "remember to git commit -- paths"']) is False


# --------------------------------------------------------------------------
# The policy, as a pure decision
# --------------------------------------------------------------------------


def test_nothing_concluded_means_no_ask():
    assert DRN.should_ask(concluded=False, was_asked=False) is False


def test_concluded_and_not_yet_asked_means_ask():
    assert DRN.should_ask(concluded=True, was_asked=False) is True


def test_the_ask_does_not_repeat_once_it_has_fired():
    """The whole point of the guard: three entry points must produce one ask, not three."""
    assert DRN.should_ask(concluded=True, was_asked=True) is False


# --------------------------------------------------------------------------
# Reading the transcript
# --------------------------------------------------------------------------


def test_every_bash_command_is_read_in_order(tmp_path):
    path = transcript(tmp_path, "ls", "git commit -m x", "git push")
    assert DRN.bash_commands(path) == ["ls", "git commit -m x", "git push"]


def test_a_half_written_last_line_is_tolerated(tmp_path):
    """A transcript is appended to live, so the tail can be mid-write when the hook reads it."""
    path = transcript(tmp_path, "git commit -m x", trailing_partial=True)
    assert DRN.bash_commands(path) == ["git commit -m x"]


def test_a_missing_transcript_reads_as_no_commands(tmp_path):
    assert DRN.bash_commands(str(tmp_path / "nope.jsonl")) == []


def test_non_bash_tool_uses_are_ignored(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text(json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/x"}}]},
    }) + "\n", encoding="utf-8")
    assert DRN.bash_commands(str(p)) == []


# --------------------------------------------------------------------------
# End to end through the real signals module
# --------------------------------------------------------------------------


def test_a_session_that_committed_is_asked_before_it_stops(scratch_home, monkeypatch, capsys):
    path = transcript(scratch_home, "pytest -q", "git commit -m 'ship it'")
    rc, out = run_main({"session_id": "s1", "transcript_path": path}, monkeypatch, capsys)
    assert rc == 0
    assert json.loads(out)["decision"] == "block"


def test_a_session_still_in_progress_stays_silent(scratch_home, monkeypatch, capsys):
    """The false-positive side: a gate that fires mid-edit is one the user turns off."""
    path = transcript(scratch_home, "ls", "pytest -q", "git status")
    rc, out = run_main({"session_id": "s2", "transcript_path": path}, monkeypatch, capsys)
    assert rc == 0 and out == ""


def test_a_session_is_asked_once_not_after_every_later_commit(scratch_home, monkeypatch, capsys):
    path = transcript(scratch_home, "git commit -m one")
    _, first = run_main({"session_id": "s3", "transcript_path": path}, monkeypatch, capsys)
    _, second = run_main({"session_id": "s3", "transcript_path": path}, monkeypatch, capsys)
    assert json.loads(first)["decision"] == "block"
    assert second == "", "the second turn must not re-ask"


def test_another_sessions_flag_does_not_suppress_this_one(scratch_home, monkeypatch, capsys):
    """A per-PROJECT flag outlives its session and silences the next one; a session-keyed flag cannot."""
    DRN.mark_asked("an-older-session")
    path = transcript(scratch_home, "git commit -m x")
    _, out = run_main({"session_id": "s4", "transcript_path": path}, monkeypatch, capsys)
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
    rc, out = run_main({"session_id": "s5"}, monkeypatch, capsys)
    assert rc == 0 and out == ""


def test_an_event_without_a_session_id_is_ignored(scratch_home, monkeypatch, capsys, tmp_path):
    rc, out = run_main({"transcript_path": transcript(tmp_path, "git commit -m x")}, monkeypatch, capsys)
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
