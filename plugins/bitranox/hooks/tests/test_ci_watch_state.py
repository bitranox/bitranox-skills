"""Tests for ci_watch_state - the pending-push record shared by the nudge and the Stop gate."""
from __future__ import annotations

import json
import os
import threading
import time

import pytest

import ci_watch_state as state
import self_improve_signals


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


@pytest.mark.skipif(os.name != "nt", reason="a rename refused over an open reader is Windows semantics")
def test_a_rename_refused_by_an_open_reader_is_retried_not_dropped(tmp_path, monkeypatch):
    # The OS edge: the publishing rename fails once the way Windows fails it while a reader
    # (pending_for runs unlocked) holds the state file open.
    proj = str(tmp_path)
    state.record_push(proj, "sess-a", "a" * 40)
    real_replace, refused = os.replace, []

    def clashing_replace(src, dst):
        if not refused:
            refused.append(dst)
            raise PermissionError(13, "The process cannot access the file")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", clashing_replace)
    state.record_push(proj, "sess-a", "b" * 40)
    assert refused
    assert sorted(e["sha"][0] for e in state.pending_for(proj, "sess-a")) == ["a", "b"]


def test_session_key_falls_back_to_the_project_dir_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/proj/x")
    assert state.session_key({"session_id": "s"}) == "/proj/x"
    assert state.session_key({"cwd": "/here"}) == "/here"   # the event's cwd wins
    assert state.session_key("not a dict") == ""
    monkeypatch.delenv("CLAUDE_PROJECT_DIR")
    assert state.session_key({}) == ""


def test_a_write_that_did_not_land_returns_the_default_not_the_unsaved_result(tmp_path, monkeypatch):
    """`_update` handed back the post-change entries even when the rename failed, so a caller
    acted on a block count that was never stored."""
    proj = str(tmp_path)
    state.record_push(proj, "sess-a", "a" * 40)
    refused = []

    def refusing_replace(src, dst):
        refused.append(dst)
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "replace", refusing_replace)
    assert state.bump_session_blocks(proj, "sess-a") == []
    assert refused
    monkeypatch.undo()
    # Control: the same call with the rename working reports the charge it stored.
    assert [e["blocks"] for e in state.bump_session_blocks(proj, "sess-a")] == [1]


@pytest.mark.parametrize(("raw", "expected"), [
    (12.5, 12.5), ("7", 7.0), (None, 0.0), ("x", 0.0), ([1], 0.0), (10 ** 400, 0.0),
    ("inf", 0.0), ("-inf", 0.0), ("nan", 0.0),
])
def test_entry_at_coerces_every_unreadable_value_to_long_expired(raw, expected):
    assert state.entry_at({"at": raw}) == expected


# ---- stale state files of OTHER projects are pruned when this one saves --------------------------
# Every project a session ever ran in leaves one claude-ci-watch-<hash>.json in the temp dir, and
# the generic temp pruner skips every claude-* name, so nothing else ever removes them.

@pytest.fixture
def temp_dir(tmp_path, monkeypatch):
    """A temp dir of this test's own, so the scan sees only the files the test planted."""
    root = tmp_path / "tmp"
    root.mkdir()
    monkeypatch.setattr(state.tempfile, "tempdir", str(root))
    return root


def _plant(root, name, age_seconds):
    path = root / name
    path.write_text(json.dumps({"pending": []}), encoding="utf-8")
    moment = time.time() - age_seconds
    os.utime(path, (moment, moment))
    return path


def test_the_horizon_never_reaches_a_file_that_can_still_hold_a_pending_entry():
    assert state.STALE_FILE_SECONDS > state.MAX_AGE_SECONDS


def test_a_save_removes_another_projects_stale_state_file(tmp_path, temp_dir):
    stale = _plant(temp_dir, "claude-ci-watch-0123456789abcdef.json", state.STALE_FILE_SECONDS + 60)
    state.record_push(str(tmp_path / "proj"), "sess-a", "a" * 40)
    assert not stale.exists()
    assert state.state_path(str(tmp_path / "proj")).exists()


def test_a_save_keeps_a_state_file_younger_than_the_horizon(tmp_path, temp_dir):
    # older than MAX_AGE_SECONDS (nothing in it is pending) but inside the stale horizon
    young = _plant(temp_dir, "claude-ci-watch-fedcba9876543210.json", state.MAX_AGE_SECONDS + 60)
    state.record_push(str(tmp_path / "proj"), "sess-a", "a" * 40)
    assert young.exists()


def test_a_save_never_removes_its_own_file_or_files_it_does_not_own(tmp_path, temp_dir):
    proj = str(tmp_path / "proj")
    own = state.state_path(proj)
    state.record_push(proj, "sess-a", "a" * 40)
    old = time.time() - state.STALE_FILE_SECONDS - 60
    os.utime(own, (old, old))
    others = [_plant(temp_dir, name, state.STALE_FILE_SECONDS + 60)
              for name in ("claude-other-state.json", "claude-ci-watch-x.json.lock",
                           "claude-ci-watch-x.json.123.tmp", "ci-watch-x.json")]
    state.clear_sha(proj, "b" * 40)
    assert own.exists()
    assert all(p.exists() for p in others)


def test_a_candidate_that_vanishes_mid_scan_does_not_stop_the_prune_or_the_write(tmp_path, temp_dir):
    # a dangling link fails stat exactly as a file removed by another session between the
    # directory listing and the age check does
    vanished = temp_dir / "claude-ci-watch-aaaaaaaaaaaaaaaa.json"
    try:
        vanished.symlink_to(temp_dir / "gone.json")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks need privileges on this platform")
    stale = _plant(temp_dir, "claude-ci-watch-bbbbbbbbbbbbbbbb.json", state.STALE_FILE_SECONDS + 60)
    proj = str(tmp_path / "proj")
    state.record_push(proj, "sess-a", "a" * 40)
    assert [e["sha"] for e in state.pending_for(proj, "sess-a")] == ["a" * 40]
    assert not stale.exists()


def test_a_stale_file_another_writer_has_locked_is_left_alone(tmp_path, temp_dir):
    held = _plant(temp_dir, "claude-ci-watch-cccccccccccccccc.json", state.STALE_FILE_SECONDS + 60)
    with self_improve_signals.memory_lock(held, timeout=1.0):
        state.record_push(str(tmp_path / "proj"), "sess-a", "a" * 40)
    assert held.exists()
