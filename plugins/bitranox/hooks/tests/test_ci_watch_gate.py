"""Tests for ci-watch-gate - the Stop hook that refuses to end a turn with unwatched CI."""
from __future__ import annotations

import json
import time
from pathlib import Path

import ci_watch_gate as hook
import ci_watch_state as state
import pytest


@pytest.fixture(autouse=True)
def opted_in(tmp_path, monkeypatch):
    """Most tests here are about blocking, which requires the opt-in marker to exist."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    hook.sentinel_path().touch()
    return home


def _event(cwd, session="sess-1", stop_hook_active=False):
    return json.dumps({"cwd": str(cwd), "session_id": session,
                       "stop_hook_active": stop_hook_active})


def test_a_pending_push_blocks_and_names_the_sha(tmp_path, capsys):
    state.record_push(str(tmp_path), "sess-1", "a" * 40, branch="master")
    assert hook.main(_event(tmp_path)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "a" * 12 in payload["reason"]
    assert "master" in payload["reason"]
    assert "ci_wait.py" in payload["reason"]


def test_nothing_pending_is_silent(tmp_path, capsys):
    assert hook.main(_event(tmp_path)) == 0
    assert capsys.readouterr().out == ""


def test_stop_hook_active_never_blocks(tmp_path, capsys):
    """The anti-loop guard. Without it a session with broken gh can never stop."""
    state.record_push(str(tmp_path), "sess-1", "a" * 40)
    assert hook.main(_event(tmp_path, stop_hook_active=True)) == 0
    assert capsys.readouterr().out == ""
    # The trigger is still present, so the test above is about the flag, not about emptiness.
    assert hook.main(_event(tmp_path, stop_hook_active=False)) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "block"


def test_the_bypass_env_never_blocks(tmp_path, capsys, monkeypatch):
    state.record_push(str(tmp_path), "sess-1", "a" * 40)
    monkeypatch.setenv("BITRANOX_CI_WATCH", "1")
    assert hook.main(_event(tmp_path)) == 0
    assert capsys.readouterr().out == ""
    # Same entry, bypass lifted: it must speak, or this proves nothing about the bypass.
    monkeypatch.delenv("BITRANOX_CI_WATCH")
    assert hook.main(_event(tmp_path)) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "block"


def test_another_session_push_does_not_block_this_one(tmp_path, capsys):
    state.record_push(str(tmp_path), "sess-old", "a" * 40)
    assert hook.main(_event(tmp_path, session="sess-new")) == 0
    assert capsys.readouterr().out == ""


def test_an_expired_push_does_not_block(tmp_path, capsys):
    state.record_push(str(tmp_path), "sess-1", "a" * 40)
    path = state.state_path(str(tmp_path))
    data = json.loads(path.read_text(encoding="utf-8"))
    data["pending"][0]["at"] = time.time() - state.MAX_AGE_SECONDS - 1
    path.write_text(json.dumps(data), encoding="utf-8")
    assert hook.main(_event(tmp_path)) == 0
    assert capsys.readouterr().out == ""


def test_several_pending_pushes_report_the_newest_and_the_count(tmp_path, capsys):
    state.record_push(str(tmp_path), "sess-1", "a" * 40)
    time.sleep(0.01)
    state.record_push(str(tmp_path), "sess-1", "b" * 40, branch="topic")
    assert hook.main(_event(tmp_path)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "b" * 12 in payload["reason"]
    assert "2 pushes" in payload["reason"]


def test_a_missing_session_id_is_silent(tmp_path, capsys):
    state.record_push(str(tmp_path), "", "a" * 40)
    assert hook.main(json.dumps({"cwd": str(tmp_path)})) == 0
    assert capsys.readouterr().out == ""


def test_malformed_input_never_raises(capsys):
    for raw in ("", "{not json", json.dumps([1, 2]), json.dumps({})):
        assert hook.main(raw) == 0
    assert capsys.readouterr().out == ""


def test_verdict_is_none_for_an_entry_with_no_sha():
    assert hook.verdict([{"at": time.time()}]) is None
    assert hook.verdict([]) is None


def test_without_the_opt_in_marker_it_never_blocks(tmp_path, capsys):
    """The shipped default: the blocking half waits to be asked for."""
    state.record_push(str(tmp_path), "sess-1", "a" * 40)
    hook.sentinel_path().unlink()
    assert hook.enabled() is False
    assert hook.main(_event(tmp_path)) == 0
    assert capsys.readouterr().out == ""
    # Same entry, marker restored: it must speak, or this proves nothing about the marker.
    hook.sentinel_path().touch()
    assert hook.main(_event(tmp_path)) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "block"


def test_it_blocks_up_to_the_cap_then_releases_loudly(tmp_path, capsys):
    """Bounded repeat: pressure that cannot become a wedge."""
    state.record_push(str(tmp_path), "sess-1", "a" * 40, branch="master")
    for n in range(state.MAX_BLOCKS):
        assert hook.main(_event(tmp_path)) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["decision"] == "block", "attempt %d should still block" % (n + 1)
    # One past the cap: it gives up, says so, and stops blocking.
    assert hook.main(_event(tmp_path)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "decision" not in payload
    assert "released" in payload["hookSpecificOutput"]["additionalContext"]
    # And it stays quiet afterwards rather than starting over.
    assert hook.main(_event(tmp_path)) == 0
    assert capsys.readouterr().out == ""


def test_the_last_reminder_says_it_is_the_last(tmp_path, capsys):
    state.record_push(str(tmp_path), "sess-1", "a" * 40)
    for _ in range(state.MAX_BLOCKS - 1):
        hook.main(_event(tmp_path))
        capsys.readouterr()
    hook.main(_event(tmp_path))
    assert "last reminder" in json.loads(capsys.readouterr().out)["reason"]


def test_watching_the_ci_stops_the_countdown(tmp_path, capsys):
    """Clearing the record must reset the pressure, not leave a spent counter behind."""
    state.record_push(str(tmp_path), "sess-1", "a" * 40)
    hook.main(_event(tmp_path))
    capsys.readouterr()
    state.clear_sha(str(tmp_path), "a" * 40)
    assert hook.main(_event(tmp_path)) == 0
    assert capsys.readouterr().out == ""
