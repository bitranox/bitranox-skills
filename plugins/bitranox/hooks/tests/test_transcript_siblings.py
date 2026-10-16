"""Tests for transcript_siblings.py: the shell calls sent earlier in the same assistant message.

Probed on Claude Code 2.1.296: sibling Bash calls of one message run one after another, each
tool_use is its own transcript record carrying the message's `message.id`, and every record of the
message is on disk before the second call's PreToolUse hook runs. The first call's hook sees none.
"""
import json

import transcript_siblings as ts


def _record(message_id, tool_use_id, command, name="Bash"):
    return {"type": "assistant", "message": {"id": message_id, "content": [
        {"type": "tool_use", "id": tool_use_id, "name": name, "input": {"command": command}}]}}


def _write(path, records):
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def test_earlier_siblings_are_the_shell_calls_of_the_same_message_before_this_one():
    records = [_record("m0", "t0", "old"), _record("m1", "t1", "first"),
               _record("m1", "t2", "read", name="Read"), _record("m1", "t3", "this"),
               _record("m1", "t4", "later")]

    assert ts.earlier_siblings(records, "t3") == ["first"]


def test_a_call_missing_from_the_records_has_no_known_siblings():
    assert ts.earlier_siblings([_record("m", "t1", "x")], "t9") is None


def test_the_main_transcript_is_read_when_no_agent_id_is_given(tmp_path):
    main = _write(tmp_path / "s.jsonl", [_record("m", "t1", "pytest -q"), _record("m", "t2", "git commit")])
    event = {"transcript_path": str(main), "tool_use_id": "t2"}

    assert ts.siblings_for_event(event) == ["pytest -q"]


def test_a_subagent_call_is_looked_up_in_the_subagent_s_own_transcript(tmp_path):
    # A subagent's event carries the PARENT's transcript_path plus agent_id; its own records sit in
    # <parent minus .jsonl>/subagents/agent-<agent_id>.jsonl (probed on 2.1.295).
    main = _write(tmp_path / "s.jsonl", [_record("m", "p1", "echo parent")])
    sub_dir = tmp_path / "s" / "subagents"
    sub_dir.mkdir(parents=True)
    _write(sub_dir / "agent-a7.jsonl", [_record("n", "c1", "make test"), _record("n", "c2", "git push")])
    event = {"transcript_path": str(main), "tool_use_id": "c2", "agent_id": "a7"}

    assert ts.siblings_for_event(event) == ["make test"]


def test_a_workflow_agent_call_is_looked_up_under_subagents_workflows(tmp_path):
    # A Workflow agent's event has the same shape, but its own records sit one level deeper, in
    # <parent minus .jsonl>/subagents/workflows/<wf_id>/agent-<agent_id>.jsonl.
    main = _write(tmp_path / "s.jsonl", [_record("m", "p1", "echo parent")])
    wf_dir = tmp_path / "s" / "subagents" / "workflows" / "wf_928ebb87-156"
    wf_dir.mkdir(parents=True)
    _write(wf_dir / "agent-a7.jsonl", [_record("n", "c1", "make test"), _record("n", "c2", "git push")])
    event = {"transcript_path": str(main), "tool_use_id": "c2", "agent_id": "a7"}

    assert ts.siblings_for_event(event) == ["make test"]


def test_an_agent_id_in_two_workflows_names_no_transcript(tmp_path):
    """Two candidates cannot both be the agent's own file, so neither is evidence."""
    main = _write(tmp_path / "s.jsonl", [])
    for wf in ("wf_1", "wf_2"):
        (tmp_path / "s" / "subagents" / "workflows" / wf).mkdir(parents=True)
        _write(tmp_path / "s" / "subagents" / "workflows" / wf / "agent-a7.jsonl", [])

    assert ts.agent_transcript(str(main), "a7") is None


def test_an_agent_id_that_is_not_a_plain_name_names_no_transcript(tmp_path):
    main = _write(tmp_path / "s.jsonl", [])

    assert ts.agent_transcript(str(main), "../x") is None
    assert ts.agent_transcript(str(main), "*") is None


def test_an_unreadable_or_missing_transcript_yields_none(tmp_path):
    assert ts.siblings_for_event({"transcript_path": str(tmp_path / "nope.jsonl"), "tool_use_id": "t"}) is None
    assert ts.siblings_for_event({"tool_use_id": "t"}) is None
    assert ts.siblings_for_event({"transcript_path": str(tmp_path / "x.jsonl")}) is None


def test_only_the_tail_of_a_long_transcript_is_needed(tmp_path):
    filler = [_record(f"old{i}", f"o{i}", "x" * 2000) for i in range(300)]
    path = _write(tmp_path / "s.jsonl", [*filler, _record("m", "t1", "ruff check src"), _record("m", "t2", "git commit")])

    assert ts.siblings_from_transcript(str(path), "t2") == ["ruff check src"]
