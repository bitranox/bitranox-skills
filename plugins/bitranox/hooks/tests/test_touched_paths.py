"""Tests for the touched-paths PostToolUse recorder (capture-routing evidence). ASCII only."""
import io
import json

import pytest

import self_improve_signals as S
import touched_paths as T


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _run(monkeypatch, event):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    return T.main()


def _event(path, session="s1", tool="Write"):
    # shape probe-verified on the live harness: tool_input.file_path + a stable session_id
    return {"hook_event_name": "PostToolUse", "tool_name": tool, "session_id": session,
            "cwd": "/some/cwd", "tool_input": {"file_path": path}}


def test_records_the_edited_path_for_the_session(monkeypatch):
    assert _run(monkeypatch, _event("/repo/a/x.py")) == 0
    assert S.read_touched_paths("s1") == ["/repo/a/x.py"]


def test_records_each_distinct_path_and_isolates_sessions(monkeypatch):
    _run(monkeypatch, _event("/repo/a/x.py", session="sA"))
    _run(monkeypatch, _event("/repo/b/y.py", session="sA"))
    _run(monkeypatch, _event("/repo/c/z.py", session="sB"))
    assert S.read_touched_paths("sA") == ["/repo/a/x.py", "/repo/b/y.py"]
    assert S.read_touched_paths("sB") == ["/repo/c/z.py"]


def test_noop_without_file_path_or_session(monkeypatch):
    assert _run(monkeypatch, {"hook_event_name": "PostToolUse", "session_id": "s2",
                              "tool_input": {}}) == 0
    assert S.read_touched_paths("s2") == []
    assert _run(monkeypatch, {"tool_input": {"file_path": "/x/y.py"}}) == 0   # no session_id


def test_never_wedges_a_turn_on_bad_input(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json at all"))
    assert T.main() == 0                       # fail-open: a recorder must never block a turn
