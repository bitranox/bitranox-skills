"""Tests for ci_watch_state - the pending-push record shared by the nudge and the Stop gate."""
from __future__ import annotations

import json
import time

import ci_watch_state as state


def test_record_then_pending_round_trips(tmp_path):
    proj = str(tmp_path)
    state.record_push(proj, "sess-a", "a" * 40, branch="master")
    pending = state.pending_for(proj, "sess-a")
    assert [e["sha"] for e in pending] == ["a" * 40]
    assert pending[0]["branch"] == "master"


def test_a_second_push_of_the_same_sha_does_not_duplicate(tmp_path):
    proj = str(tmp_path)
    state.record_push(proj, "sess-a", "a" * 40)
    state.record_push(proj, "sess-a", "a" * 40)
    assert len(state.pending_for(proj, "sess-a")) == 1


def test_clear_sha_drops_only_that_sha(tmp_path):
    proj = str(tmp_path)
    state.record_push(proj, "sess-a", "a" * 40)
    state.record_push(proj, "sess-a", "b" * 40)
    state.clear_sha(proj, "a" * 40)
    assert [e["sha"] for e in state.pending_for(proj, "sess-a")] == ["b" * 40]


def test_clear_session_drops_only_that_session(tmp_path):
    proj = str(tmp_path)
    state.record_push(proj, "sess-a", "a" * 40)
    state.record_push(proj, "sess-b", "b" * 40)
    state.clear_session(proj, "sess-a")
    assert state.pending_for(proj, "sess-a") == []
    assert [e["sha"] for e in state.pending_for(proj, "sess-b")] == ["b" * 40]


def test_another_session_pending_is_invisible_to_this_one(tmp_path):
    """The stale-flag failure mode: an earlier session's push must not block a later one."""
    proj = str(tmp_path)
    state.record_push(proj, "sess-old", "a" * 40)
    assert state.pending_for(proj, "sess-new") == []


def test_an_entry_past_the_horizon_is_not_pending(tmp_path):
    proj = str(tmp_path)
    state.record_push(proj, "sess-a", "a" * 40)
    later = time.time() + state.MAX_AGE_SECONDS + 1
    assert state.pending_for(proj, "sess-a", now=later) == []
    # ... and is still pending just inside it, so the test above is not vacuous.
    assert state.pending_for(proj, "sess-a", now=time.time() + 1) != []


def test_two_projects_do_not_share_a_state_file(tmp_path):
    one, two = str(tmp_path / "one"), str(tmp_path / "two")
    state.record_push(one, "sess-a", "a" * 40)
    assert state.pending_for(two, "sess-a") == []
    assert state.state_path(one) != state.state_path(two)


def test_a_corrupt_state_file_reads_as_nothing_pending(tmp_path):
    """Fail safe: an unreadable record is not evidence that a push needs watching."""
    proj = str(tmp_path)
    state.record_push(proj, "sess-a", "a" * 40)
    state.state_path(proj).write_text("{not json", encoding="utf-8")
    assert state.pending_for(proj, "sess-a") == []


def test_a_state_file_of_the_wrong_shape_reads_as_nothing_pending(tmp_path):
    proj = str(tmp_path)
    state.record_push(proj, "sess-a", "a" * 40)
    state.state_path(proj).write_text(json.dumps({"pending": "not-a-list"}), encoding="utf-8")
    assert state.pending_for(proj, "sess-a") == []
