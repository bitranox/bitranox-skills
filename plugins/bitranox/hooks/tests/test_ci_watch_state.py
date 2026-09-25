"""Tests for ci_watch_state - the pending-push record shared by the nudge and the Stop gate."""
from __future__ import annotations

import json
import threading
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


def test_two_sessions_pushing_the_same_sha_each_keep_their_entry(tmp_path):
    # Two sessions in one project can push the same commit; B's record must not erase A's.
    proj, sha = str(tmp_path), "a" * 40
    state.record_push(proj, "sess-a", sha)
    state.record_push(proj, "sess-b", sha)
    assert [e["sha"] for e in state.pending_for(proj, "sess-a")] == [sha]
    assert [e["sha"] for e in state.pending_for(proj, "sess-b")] == [sha]


def test_re_recording_a_sha_keeps_its_block_count(tmp_path):
    # A second push of the same commit to the same repo starts no new CI; resetting the count
    # would let one push block past the cap.
    proj, sha = str(tmp_path), "a" * 40
    state.record_push(proj, "sess-a", sha, repo="r")
    state.bump_session_blocks(proj, "sess-a")
    state.bump_session_blocks(proj, "sess-a")
    state.record_push(proj, "sess-a", sha, repo="r")
    assert [e["blocks"] for e in state.bump_session_blocks(proj, "sess-a")] == [3]


def test_the_same_sha_pushed_to_another_repo_counts_afresh(tmp_path):
    # Control: a push to a DIFFERENT remote does start new CI, so it earns its own reminders.
    proj, sha = str(tmp_path), "a" * 40
    state.record_push(proj, "sess-a", sha, repo="r1")
    state.bump_session_blocks(proj, "sess-a")
    state.record_push(proj, "sess-a", sha, repo="r2")
    assert [e["blocks"] for e in state.bump_session_blocks(proj, "sess-a")] == [1]


def test_bump_counts_every_entry_of_this_session_and_no_other(tmp_path):
    proj = str(tmp_path)
    state.record_push(proj, "sess-a", "a" * 40)
    state.record_push(proj, "sess-a", "b" * 40)
    state.record_push(proj, "sess-b", "a" * 40)
    state.bump_session_blocks(proj, "sess-a")
    bumped = state.bump_session_blocks(proj, "sess-a")
    assert sorted((e["sha"][0], e["blocks"]) for e in bumped) == [("a", 2), ("b", 2)]
    assert [e["blocks"] for e in state.bump_session_blocks(proj, "sess-b")] == [1]


def test_clear_sha_for_one_session_leaves_the_other_sessions_entry(tmp_path):
    proj, sha = str(tmp_path), "a" * 40
    state.record_push(proj, "sess-a", sha)
    state.record_push(proj, "sess-b", sha)
    state.clear_sha(proj, sha, session="sess-a")
    assert state.pending_for(proj, "sess-a") == []
    assert len(state.pending_for(proj, "sess-b")) == 1
    state.clear_sha(proj, sha)   # control: without a session it is cleared for everyone
    assert state.pending_for(proj, "sess-b") == []


def test_concurrent_writers_lose_no_entry(tmp_path):
    # Read-modify-write through one fixed .tmp name lost entries when writers overlapped.
    proj = str(tmp_path)
    start = threading.Barrier(20)

    def push(i):
        start.wait()
        state.record_push(proj, "sess-a", "%040x" % i)

    workers = [threading.Thread(target=push, args=(i,)) for i in range(20)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    assert len(state.pending_for(proj, "sess-a")) == 20
    leftovers = [p.name for p in state.state_path(proj).parent.glob(state.state_path(proj).name + "*")
                 if p.name != state.state_path(proj).name]
    assert leftovers == []


def test_session_key_falls_back_to_the_project_dir_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/proj/x")
    assert state.session_key({"session_id": "s"}) == "/proj/x"
    assert state.session_key({"cwd": "/here"}) == "/here"   # the event's cwd wins
    assert state.session_key("not a dict") == ""
    monkeypatch.delenv("CLAUDE_PROJECT_DIR")
    assert state.session_key({}) == ""
