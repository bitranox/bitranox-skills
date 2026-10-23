"""Tests for sibling_ledger.py and its recorder hook sibling-ledger.py.

The incident: on Claude Code 2.1.309 a later sibling's PreToolUse hook runs before the earlier
siblings are written to the transcript, so block-commit-beside-sibling-gate let a commit beside a
gate through live (probed 2026-10-23), and block-write-after-sibling-cd is blind the same way. The
ledger is the record the hook events themselves keep, in step with the calls.
"""
import io
import json
import os
import stat
import sys
import tempfile

import pytest

import block_commit_beside_sibling_gate as commit_guard
import block_write_after_sibling_cd as cd_guard
import sibling_ledger
import sibling_ledger_hook as recorder
import transcript_siblings

SESSION = "5e5510n-0001"


@pytest.fixture(autouse=True)
def _own_tempdir(monkeypatch, tmp_path):
    # tempfile.gettempdir() is the only edge the ledger touches; point it at this test's dir.
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))


def _pre(tool_use_id, command, *, tool="Bash", agent=None, session=SESSION):
    event = {"hook_event_name": "PreToolUse", "session_id": session, "tool_name": tool,
             "tool_use_id": tool_use_id, "tool_input": {"command": command}}
    if agent:
        event["agent_id"] = agent
    return event


def _hook(monkeypatch, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    return recorder.main()


# --- the ledger ------------------------------------------------------------------------------------


def test_a_later_call_sees_the_earlier_shell_calls_of_its_message_in_order():
    for i, command in enumerate(["cd /w/a", "make test"]):
        sibling_ledger.record(_pre("t%d" % i, command))
    sibling_ledger.record(_pre("t9", "git commit -F m"))

    assert sibling_ledger.earlier(_pre("t9", "git commit -F m")) == ["cd /w/a", "make test"]


def test_the_call_s_own_entry_is_left_out_whichever_hook_ran_first():
    sibling_ledger.record(_pre("t1", "git push"))

    assert sibling_ledger.earlier(_pre("t1", "git push")) == []


def test_without_a_ledger_nothing_is_known():
    assert sibling_ledger.earlier(_pre("t1", "git push")) is None


def test_other_tools_are_not_recorded():
    sibling_ledger.record({**_pre("t1", ""), "tool_name": "Edit", "tool_input": {"file_path": "/w/x"}})

    assert sibling_ledger.earlier(_pre("t2", "git push")) is None


def test_a_cleared_ledger_knows_nothing_of_the_previous_message():
    sibling_ledger.record(_pre("t1", "make test"))
    sibling_ledger.clear(_pre("t1", "make test"))

    assert sibling_ledger.earlier(_pre("t2", "git push")) is None


def test_a_subagent_and_the_main_session_keep_separate_ledgers():
    sibling_ledger.record(_pre("t1", "make test", agent="a1b2"))

    assert sibling_ledger.earlier(_pre("t2", "git push")) is None
    assert sibling_ledger.earlier(_pre("t2", "git push", agent="a1b2")) == ["make test"]
    assert sibling_ledger.earlier(_pre("t2", "git push", agent="zz99")) is None


def test_an_entry_left_by_a_batch_that_never_resolved_expires():
    sibling_ledger.record(_pre("t1", "make test"), now=1000.0)

    later = 1000.0 + sibling_ledger.MAX_AGE_SECONDS + 1
    assert sibling_ledger.earlier(_pre("t2", "git push"), now=later) == []
    assert sibling_ledger.earlier(_pre("t2", "git push"), now=1000.0 + 60) == ["make test"]


@pytest.mark.parametrize("bad", [{"session_id": "../etc"}, {"session_id": None}, {"agent_id": "a/../b"}])
def test_an_id_that_is_not_a_plain_name_never_names_a_file(bad):
    event = {**_pre("t1", "make test"), **bad}

    assert sibling_ledger.ledger_path(event) is None
    sibling_ledger.record(event)
    assert sibling_ledger.earlier(event) is None


def test_a_damaged_line_is_skipped_not_fatal():
    sibling_ledger.record(_pre("t1", "make test"))
    with open(sibling_ledger.ledger_path(_pre("t1", "")), "a", encoding="utf-8") as handle:
        handle.write('{"id": "cut\n')

    assert sibling_ledger.earlier(_pre("t2", "git push")) == ["make test"]


# --- the shared temp dir: another user must not redirect or plant entries --------------------------

_POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="the Windows temp dir is already per user")


@_POSIX_ONLY
def test_the_ledger_lives_in_an_owner_only_dir_and_file(tmp_path):
    sibling_ledger.record(_pre("t1", "make test"))
    path = sibling_ledger.ledger_path(_pre("t1", ""))

    assert path.parent.parent == tmp_path
    assert stat.S_IMODE(os.lstat(path.parent).st_mode) == 0o700
    assert stat.S_IMODE(os.lstat(path).st_mode) == 0o600


@_POSIX_ONLY
def test_a_ledger_dir_others_can_write_is_not_used(tmp_path):
    shared = tmp_path / ("claude-siblings-%d" % os.getuid())
    shared.mkdir(mode=0o700)
    shared.chmod(0o777)

    assert sibling_ledger.ledger_path(_pre("t1", "make test")) is None
    sibling_ledger.record(_pre("t1", "make test"))
    assert list(shared.iterdir()) == []
    assert sibling_ledger.earlier(_pre("t2", "git push")) is None


@_POSIX_ONLY
def test_a_ledger_dir_that_is_a_link_is_not_used(tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir(mode=0o700)
    (tmp_path / ("claude-siblings-%d" % os.getuid())).symlink_to(elsewhere)

    assert sibling_ledger.ledger_path(_pre("t1", "make test")) is None


@_POSIX_ONLY
def test_a_planted_link_at_the_ledger_path_is_neither_written_through_nor_read(tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("planted: make test\n", encoding="utf-8")
    path = sibling_ledger.ledger_path(_pre("t1", ""))
    path.symlink_to(victim)

    with pytest.raises(OSError):
        sibling_ledger.record(_pre("t1", "git push"))
    assert victim.read_text(encoding="utf-8") == "planted: make test\n"
    assert sibling_ledger.earlier(_pre("t2", "git push")) is None


# --- the recorder hook -----------------------------------------------------------------------------


@pytest.mark.parametrize("clearing", ["PostToolBatch", "UserPromptSubmit", "Stop"])
def test_the_hook_records_at_pretooluse_and_clears_when_the_message_is_over(monkeypatch, capsys, clearing):
    assert _hook(monkeypatch, _pre("t1", "make test")) == 0
    assert sibling_ledger.earlier(_pre("t2", "git push")) == ["make test"]

    assert _hook(monkeypatch, {"hook_event_name": clearing, "session_id": SESSION}) == 0

    assert sibling_ledger.earlier(_pre("t2", "git push")) is None
    assert capsys.readouterr() == ("", "")


def test_a_subagent_s_batch_end_clears_only_its_own_ledger(monkeypatch):
    _hook(monkeypatch, _pre("t1", "make test"))
    _hook(monkeypatch, _pre("s1", "pytest -q", agent="a1b2"))

    _hook(monkeypatch, {"hook_event_name": "PostToolBatch", "session_id": SESSION, "agent_id": "a1b2"})

    assert sibling_ledger.earlier(_pre("t2", "git push")) == ["make test"]
    assert sibling_ledger.earlier(_pre("s2", "git push", agent="a1b2")) is None


def test_the_hook_ignores_bad_input(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert recorder.main() == 0
    monkeypatch.setattr(sys, "stdin", io.StringIO("[1, 2]"))
    assert recorder.main() == 0
    assert capsys.readouterr() == ("", "")


# --- the guards read it: what was blind live on 2.1.309 ------------------------------------------


def _empty_transcript(tmp_path):
    # What the hook found live: the transcript ends before the current message.
    path = tmp_path / "t.jsonl"
    path.write_text(json.dumps({"type": "user", "message": {"content": "earlier turn"}}) + "\n", encoding="utf-8")
    return str(path)


def test_siblings_come_from_the_ledger_when_the_transcript_has_none_yet(tmp_path):
    sibling_ledger.record(_pre("t1", "make test"))
    event = {**_pre("t2", "git push"), "transcript_path": _empty_transcript(tmp_path)}

    assert transcript_siblings.siblings_for_event(event) == ["make test"]


def test_the_transcript_still_answers_when_the_ledger_is_empty(tmp_path):
    records = [{"type": "assistant", "message": {"id": "m", "content": [
        {"type": "tool_use", "id": i, "name": "Bash", "input": {"command": c}}]}}
        for i, c in (("t1", "make test"), ("t2", "git push"))]
    path = tmp_path / "t.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    event = {**_pre("t2", "git push"), "transcript_path": str(path)}

    assert transcript_siblings.siblings_for_event(event) == ["make test"]


def test_the_commit_guard_refuses_a_commit_beside_a_gate_seen_only_in_the_ledger(monkeypatch, capsys, tmp_path):
    _hook(monkeypatch, _pre("t1", "ruff --version"))
    commit = "git -C /w/repo commit --allow-empty -q -F /w/msg.txt"
    event = {**_pre("t2", commit), "transcript_path": _empty_transcript(tmp_path)}
    _hook(monkeypatch, event)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))

    assert commit_guard.main() == 2
    assert "ruff --version" in capsys.readouterr().err


def test_the_cd_guard_sees_a_sibling_cd_seen_only_in_the_ledger(monkeypatch, capsys, tmp_path):
    _hook(monkeypatch, _pre("t1", "cd /w/other && git status"))
    event = {**_pre("t2", "git push"), "transcript_path": _empty_transcript(tmp_path)}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))

    assert cd_guard.main() == 2
    assert "cd /w/other" in capsys.readouterr().err
