"""Tests for decision-review-nudge.py (the Stop hook that asks which decisions are unsettled).

The policy is a pure function and is tested directly. The wiring is tested end to end through the
REAL signals module, with HOME redirected to tmp_path so the session scratch dir is the test's
own - no stubbing of the module under test, and the flag file that results is the real one.

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


def run_main(payload, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    rc = DRN.main()
    return rc, capsys.readouterr().out


# --------------------------------------------------------------------------
# The policy, as a pure decision
# --------------------------------------------------------------------------


def test_a_quiet_session_is_not_asked():
    assert DRN.should_ask(touched_count=2, was_asked=False, min_paths=3) is False


def test_a_session_that_wrote_enough_is_asked():
    assert DRN.should_ask(touched_count=3, was_asked=False, min_paths=3) is True


def test_the_ask_does_not_repeat_once_it_has_fired():
    """The whole point of the guard: three entry points must produce one ask, not three."""
    assert DRN.should_ask(touched_count=99, was_asked=True, min_paths=3) is False


# --------------------------------------------------------------------------
# End to end through the real signals module
# --------------------------------------------------------------------------


def test_a_working_session_is_asked_before_it_stops(scratch_home, monkeypatch, capsys):
    for name in ("a.py", "b.py", "c.py"):
        sig.record_touched_path("sess-1", "/repo/" + name)
    rc, out = run_main({"session_id": "sess-1"}, monkeypatch, capsys)
    assert rc == 0
    assert json.loads(out)["decision"] == "block"


def test_a_trivial_turn_stays_silent(scratch_home, monkeypatch, capsys):
    """The false-positive side: a gate that fires on a question is one the user turns off."""
    sig.record_touched_path("sess-2", "/repo/only.py")
    rc, out = run_main({"session_id": "sess-2"}, monkeypatch, capsys)
    assert rc == 0 and out == ""


def test_a_session_is_asked_once_not_on_every_later_turn(scratch_home, monkeypatch, capsys):
    for name in ("a.py", "b.py", "c.py"):
        sig.record_touched_path("sess-3", "/repo/" + name)
    _, first = run_main({"session_id": "sess-3"}, monkeypatch, capsys)
    _, second = run_main({"session_id": "sess-3"}, monkeypatch, capsys)
    assert json.loads(first)["decision"] == "block"
    assert second == "", "the second turn must not re-ask"


def test_another_sessions_flag_does_not_suppress_this_one(scratch_home, monkeypatch, capsys):
    """A per-PROJECT flag outlives its session and silences the next one; a session-keyed flag cannot."""
    DRN.mark_asked("an-older-session")
    for name in ("a.py", "b.py", "c.py"):
        sig.record_touched_path("sess-4", "/repo/" + name)
    _, out = run_main({"session_id": "sess-4"}, monkeypatch, capsys)
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


def test_an_event_without_a_session_id_is_ignored(scratch_home, monkeypatch, capsys):
    rc, out = run_main({}, monkeypatch, capsys)
    assert rc == 0 and out == ""


# --------------------------------------------------------------------------
# What the nudge actually says
# --------------------------------------------------------------------------


def test_the_reason_names_the_skill_to_invoke():
    assert "process-review-uncertain-decisions" in DRN._REASON


def test_the_reason_carries_the_suppression_rule(scratch_home):
    """Without this line the ask degrades into one more exhaustive finding list."""
    assert "clearly right" in DRN._REASON
