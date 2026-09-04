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
import pathlib
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
    # newline="" keeps the \n we wrote as a literal \n. Text mode translates it to CRLF on
    # Windows, which shifts every byte offset and breaks a byte-identical comparison, while
    # the real artifact this stands in for (a Claude transcript, a markdown file) is LF.
    p.write_text(text, encoding="utf-8", newline="")
    return str(p)


def run_main(payload, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    rc = DRN.main()
    return rc, capsys.readouterr().out


def signals(commands=(), goal_state=DRN.GOAL_NONE, offset=0):
    return DRN.Signals(list(commands), goal_state, offset)


# --------------------------------------------------------------------------
# What counts as work concluding, with no goal in play
# --------------------------------------------------------------------------


def test_a_commit_alone_does_not_conclude_the_work():
    """A commit is a checkpoint, not a conclusion: measured over three weeks of transcripts, firing
    on every commit walked tooling decisions in work projects and each walk ended in a memory
    capture, an engine fix and a plugin release from a project that had nothing to do with it."""
    assert DRN.reached_a_conclusion(signals(["git commit -F msg.txt -- src/"])) is False


def test_a_push_alone_does_not_conclude_the_work():
    assert DRN.reached_a_conclusion(signals(["git push origin master"])) is False


def test_an_opened_pr_concludes_the_work():
    """A PR is the moment the choices become somebody else's to live with."""
    assert DRN.reached_a_conclusion(signals(["gh pr create --fill"])) is True


def test_reading_and_testing_do_not_conclude_anything():
    assert DRN.reached_a_conclusion(signals(["git status", "pytest -q", "ls -la"])) is False


def test_talking_about_a_commit_is_not_committing():
    """Why this reuses the repo gate's predicate: a CHANGELOG line about committing must not fire."""
    assert DRN.reached_a_conclusion(signals(['echo "remember to git commit -- paths"'])) is False


# --------------------------------------------------------------------------
# Block once, then remind: the policy, as one pure decision
# --------------------------------------------------------------------------


def test_nothing_concluded_says_nothing():
    assert DRN.decide(score=0, last_score=0) == DRN.ASK_NONE


def test_the_first_conclusion_blocks():
    """An ask that can be scrolled past is one that gets scrolled past - stop the session once."""
    assert DRN.decide(score=1, last_score=0) == DRN.ASK_BLOCK


def test_the_same_conclusion_seen_again_says_nothing():
    """A commit never leaves the transcript, so without this every later turn would re-fire."""
    assert DRN.decide(score=1, last_score=1) == DRN.ASK_NONE


def test_a_further_conclusion_reminds_without_blocking():
    """A second block would nag, and repeated blocks hit the cap that ends a turn by override."""
    assert DRN.decide(score=2, last_score=1) == DRN.ASK_REMIND


def test_a_goal_going_from_running_to_met_counts_as_new():
    assert DRN.conclusion_score(signals([], DRN.GOAL_MET)) > DRN.conclusion_score(
        signals([], DRN.GOAL_ACTIVE))


def test_each_further_pr_raises_the_score():
    assert DRN.conclusion_score(signals(["gh pr create --fill", "gh pr create -f"])) > (
        DRN.conclusion_score(signals(["gh pr create --fill"])))


def test_commits_and_pushes_never_raise_the_score():
    assert DRN.conclusion_score(signals(["git commit -m a", "git push", "git push -u origin x"])) == 0


def test_the_block_reason_sends_tooling_decisions_to_the_queue():
    """The walk is for the work's decisions. A tooling, memory or skill decision walked here is
    the entry point of the spiral: it goes to the contribution queue, and the dream decides."""
    assert "contrib_queue" in DRN._REASON
    assert "dream" in DRN._REASON


def test_ordinary_commands_never_raise_the_score():
    assert DRN.conclusion_score(signals(["ls", "pytest -q", "git status"])) == 0


# --------------------------------------------------------------------------
# A /goal run
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


# --------------------------------------------------------------------------
# Reading only what is new, so the size cap can never hide a later conclusion
# --------------------------------------------------------------------------


def test_a_scan_reports_how_far_it_read(tmp_path):
    path = transcript(tmp_path, bash_line("ls"))
    assert DRN.transcript_signals(path).offset == len(pathlib.Path(path).read_bytes())


def test_the_offset_is_bytes_not_characters(tmp_path):
    """seek() wants a byte position; counting characters shifts it on any non-ASCII line.

    The line is built with ensure_ascii=False on purpose - json.dumps escapes non-ASCII by default,
    which would leave the fixture pure ASCII and let this test pass without ever exercising it.
    """
    line = json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": "Bash",
                                 "input": {"command": "echo \u20ac\u00fc"}}]},
    }, ensure_ascii=False)
    path = transcript(tmp_path, line)
    raw = pathlib.Path(path).read_bytes()
    assert len(raw) > len(raw.decode("utf-8")), "fixture must actually contain a multi-byte char"
    assert DRN.transcript_signals(path).offset == len(raw)


def test_a_partial_last_line_is_not_consumed(tmp_path):
    """Consuming it would lose whatever it records: the rest arrives as an unparseable fragment."""
    whole = bash_line("git commit -m done")
    path = transcript(tmp_path, whole, trailing_partial=True)
    assert DRN.transcript_signals(path).offset == len(whole.encode()) + 1


def test_a_line_that_was_mid_write_is_seen_once_it_completes(tmp_path):
    """The regression this guards: advancing past a partial line loses it for good."""
    first = bash_line("ls")
    p = tmp_path / "live.jsonl"
    p.write_text(first + "\n" + bash_line("git commit -m late")[:20], encoding="utf-8")
    partial = DRN.transcript_signals(str(p))
    assert not any("git commit" in c for c in partial.commands)
    p.write_text(first + "\n" + bash_line("git commit -m late") + "\n", encoding="utf-8")
    resumed = DRN.transcript_signals(str(p), start=partial.offset)
    assert any("git commit" in c for c in resumed.commands), "the completed line must be read"


def test_an_offset_past_the_end_starts_over(tmp_path):
    """A shrunk or replaced transcript would otherwise read nothing, silently, forever."""
    path = transcript(tmp_path, bash_line("git commit -m x"))
    resumed = DRN.transcript_signals(path, start=10_000_000)
    assert resumed.commands == ["git commit -m x"]


def test_a_scan_that_starts_late_sees_only_what_follows(tmp_path):
    first, second = bash_line("git commit -m one"), bash_line("git push")
    path = transcript(tmp_path, first, second)
    resumed = DRN.transcript_signals(path, start=len(first) + 1)
    assert resumed.commands == ["git push"], "a resumed scan must not re-read what it already saw"


def test_a_window_without_a_goal_record_keeps_the_goal_it_was_given(tmp_path):
    """Absence of a record means the goal did not change, not that it went away."""
    path = transcript(tmp_path, bash_line("ls"))
    assert DRN.transcript_signals(path, goal_state=DRN.GOAL_MET).goal_state == DRN.GOAL_MET


def test_a_commit_past_the_size_cap_is_still_reached_on_a_later_run(tmp_path):
    """The bug this fixes: a scan that always restarted at byte 0 truncated at the same place
    every time, so in a session longer than the cap NO later commit could ever be seen."""
    filler = [bash_line("echo %d" % i) for i in range(40)]
    path = transcript(tmp_path, *(filler + [bash_line("git commit -m past-the-cap")]))
    cap = 400                                   # far smaller than the file, to force truncation
    first = DRN.transcript_signals(path, start=0, max_bytes=cap)
    assert first.commands and "git commit" not in " ".join(first.commands), "cap must truncate here"
    seen, guard = first.offset, 0
    while guard < 50:                           # later runs resume where the previous one stopped
        nxt = DRN.transcript_signals(path, start=seen, max_bytes=cap)
        if any("git commit" in c for c in nxt.commands):
            return
        if nxt.offset <= seen:
            break
        seen, guard = nxt.offset, guard + 1
    raise AssertionError("the commit past the cap was never reached")


def test_the_score_accumulates_across_windows():
    """Recomputing per window instead would let the score FALL, and a fallen score never fires."""
    window = signals(["gh pr create --fill"])
    assert DRN.conclusion_score(window, previous=5) == 6


def test_a_goal_already_counted_is_not_counted_again():
    already_met = signals([], DRN.GOAL_MET)
    assert DRN.conclusion_score(already_met, previous=2, previous_goal=DRN.GOAL_MET) == 2


def test_non_bash_tool_uses_are_ignored(tmp_path):
    line = json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/x"}}]},
    })
    assert DRN.transcript_signals(transcript(tmp_path, line)).commands == []


# --------------------------------------------------------------------------
# End to end through the real signals module
# --------------------------------------------------------------------------


def test_a_session_that_opened_a_pr_is_asked_before_it_stops(scratch_home, monkeypatch, capsys):
    path = transcript(scratch_home, bash_line("pytest -q"), bash_line("gh pr create --fill"))
    rc, out = run_main({"session_id": "s1", "transcript_path": path}, monkeypatch, capsys)
    assert rc == 0
    assert json.loads(out)["decision"] == "block"


def test_a_session_that_only_committed_and_pushed_is_never_asked(scratch_home, monkeypatch, capsys):
    """The commit-only session is the ordinary one, and it is where the walk did its damage."""
    path = transcript(scratch_home, bash_line("pytest -q"), bash_line("git commit -m 'ship it'"),
                      bash_line("git push origin master"))
    rc, out = run_main({"session_id": "s1c", "transcript_path": path}, monkeypatch, capsys)
    assert rc == 0 and out == ""


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


def test_a_session_is_blocked_once_not_after_every_later_turn(scratch_home, monkeypatch, capsys):
    path = transcript(scratch_home, bash_line("gh pr create --fill"))
    _, first = run_main({"session_id": "s5", "transcript_path": path}, monkeypatch, capsys)
    _, second = run_main({"session_id": "s5", "transcript_path": path}, monkeypatch, capsys)
    assert json.loads(first)["decision"] == "block"
    assert second == "", "the same PR must not re-fire on every later turn"


def test_a_later_pr_reminds_without_blocking(scratch_home, monkeypatch, capsys):
    """The repeat channel: non-blocking, so it rides next to the result instead of stopping it."""
    one = transcript(scratch_home, bash_line("gh pr create --fill"), name="a.jsonl")
    _, first = run_main({"session_id": "s8", "transcript_path": one}, monkeypatch, capsys)
    two = transcript(scratch_home, bash_line("gh pr create --fill"), bash_line("gh pr create -f"),
                     name="b.jsonl")
    _, second = run_main({"session_id": "s8", "transcript_path": two}, monkeypatch, capsys)
    assert json.loads(first)["decision"] == "block"
    out = json.loads(second)
    assert "decision" not in out, "a repeat must never block"
    assert out["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert "process-review-uncertain-decisions" in out["hookSpecificOutput"]["additionalContext"]


def test_another_sessions_flag_does_not_suppress_this_one(scratch_home, monkeypatch, capsys):
    """A per-PROJECT flag outlives its session and silences the next one; a session-keyed flag cannot."""
    DRN.write_state("an-older-session", DRN.State(0, 99, DRN.GOAL_NONE))
    path = transcript(scratch_home, bash_line("gh pr create --fill"))
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


# The walk rule is stated twice: here in the hook, which is injected at the end of a turn without
# the skill being loaded, and in the skill body, which loads only on invocation. Both are needed -
# the hook is what an agent acts on when it does not load the skill, and the skill is all there is
# on the manual path, where no hook fires. That makes them a drift pair, and the hook is the
# dangerous half: it fires unattended, so a stale promise there steers an agent toward behaviour
# the skill no longer describes, which surfaces as wrong behaviour rather than a failing check.
_WALK_TERMS = (
    "AskUserQuestion",
    "hardest-to-reverse",
    "upside",
    "downside",
    "never the next before this one is answered",
)


def test_the_hook_and_the_skill_state_the_same_walk_rule():
    """Editing either copy without the other must fail here, not in front of a user."""
    from pathlib import Path

    skill = (
        Path(__file__).resolve().parents[2]
        / "skills"
        / "process-review-uncertain-decisions"
        / "SKILL.md"
    )
    assert skill.is_file(), "the skill this hook names must exist at the path the test resolves"
    body = skill.read_text(encoding="utf-8")
    missing_here = [t for t in _WALK_TERMS if t not in DRN._REASON]
    missing_there = [t for t in _WALK_TERMS if t not in body]
    assert not missing_here, "hook reason dropped: %s" % missing_here
    assert not missing_there, "SKILL.md dropped: %s" % missing_there


def test_the_reason_carries_the_one_at_a_time_walk():
    """The automatic entry point must describe the behaviour the skill actually has.

    Without this the nudge stops the session, gets a flat list, and the points the reader most
    needs to answer are the ones a list is worst at putting to them.
    """
    assert "AskUserQuestion" in DRN._REASON
    assert "one" in DRN._REASON and "per point" in DRN._REASON
    assert "never the next before this one is answered" in DRN._REASON


def test_the_detector_is_the_repo_gates_own_predicate():
    """One definition, so the gate and this hook cannot disagree about what counts as concluding."""
    import repo_gate
    import shell_text
    assert repo_gate.is_gated_command is shell_text.is_gated_command
