"""Tests for transcript_tail.py. Fixtures mirror the real Claude Code JSONL shape. ASCII only."""
import json

import pytest

import transcript_tail as T


def _write(tmp_path, records):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return str(p)


def test_tail_returns_last_user_and_last_assistant_visible_text(tmp_path):
    recs = [
        {"type": "user", "message": {"role": "user", "content": "first user"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "hmm"}, {"type": "text", "text": "first assistant"}]}},
        {"type": "user", "message": {"role": "user", "content": "second user"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "final assistant"}, {"type": "tool_use", "name": "Bash", "input": {}}]}},
    ]
    out = T.tail_messages(_write(tmp_path, recs))
    assert out["user"] == "second user"
    assert out["assistant"] == "final assistant"   # thinking + tool_use excluded


def test_skips_sidechain_and_meta_by_default(tmp_path):
    recs = [
        {"type": "user", "message": {"role": "user", "content": "real user"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "real asst"}]}},
        {"type": "user", "isSidechain": True, "message": {"role": "user", "content": "subagent prompt"}},
        {"type": "assistant", "isSidechain": True, "message": {"role": "assistant", "content": [{"type": "text", "text": "subagent reply"}]}},
        {"type": "user", "isMeta": True, "message": {"role": "user", "content": "meta note"}},
    ]
    out = T.tail_messages(_write(tmp_path, recs))
    assert out["user"] == "real user"
    assert out["assistant"] == "real asst"


def test_user_content_can_be_a_tool_result_list(tmp_path):
    recs = [{"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "result text"}]}}]
    out = T.tail_messages(_write(tmp_path, recs))
    assert "result text" in out["user"]


def test_include_sidechain_flag_keeps_them(tmp_path):
    recs = [
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "main"}]}},
        {"type": "assistant", "isSidechain": True, "message": {"role": "assistant", "content": [{"type": "text", "text": "sub"}]}},
    ]
    out = T.tail_messages(_write(tmp_path, recs), skip_sidechain=False)
    assert out["assistant"] == "sub"


# --- whole-transcript modes -------------------------------------------------------------

FOUR_TURNS = [
    {"type": "user", "message": {"role": "user", "content": "first user"}},
    {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "thinking", "thinking": "hmm"}, {"type": "text", "text": "first assistant"}]}},
    {"type": "user", "message": {"role": "user", "content": "second user"}},
    {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": "final assistant"}, {"type": "tool_use", "name": "Bash", "input": {}}]}},
]


def test_all_messages_returns_every_turn_not_just_the_last(tmp_path):
    """The control: an empty or last-only return fails this, so a silent no-op cannot pass."""
    rows = T.all_messages(_write(tmp_path, FOUR_TURNS))
    assert rows == [
        {"line": 1, "role": "user", "text": "first user"},
        {"line": 2, "role": "assistant", "text": "first assistant"},
        {"line": 3, "role": "user", "text": "second user"},
        {"line": 4, "role": "assistant", "text": "final assistant"},
    ]
    # and it really is MORE than the tail returns, which is the whole point of the mode
    tail = T.tail_messages(_write(tmp_path, FOUR_TURNS))
    assert len(rows) > len([t for t in tail.values() if t])


def test_all_messages_role_filter_keeps_one_side(tmp_path):
    rows = T.all_messages(_write(tmp_path, FOUR_TURNS), role="user")
    assert [r["text"] for r in rows] == ["first user", "second user"]
    assert all(r["role"] == "user" for r in rows)


def test_all_messages_line_numbers_address_the_real_file_line(tmp_path):
    """Line numbers count blank and unparseable lines too, so `sed -n '<n>p'` finds the record."""
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join([
        json.dumps({"type": "user", "message": {"role": "user", "content": "one"}}),
        "",
        "{not json at all",
        json.dumps({"type": "assistant", "message": {"role": "assistant",
                                                     "content": [{"type": "text", "text": "two"}]}}),
    ]) + "\n", encoding="utf-8")
    rows = T.all_messages(str(p))
    assert [(r["line"], r["text"]) for r in rows] == [(1, "one"), (4, "two")]
    physical = p.read_text(encoding="utf-8").splitlines()
    for row in rows:                                     # the number really indexes that line
        assert json.loads(physical[row["line"] - 1])["type"] == row["role"]


def test_all_messages_reports_unparseable_lines_instead_of_dropping_them(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text('{"type": "user", "message": {"role": "user", "content": "ok"}}\n'
                 "{broken\n"
                 "[1, 2, 3]\n", encoding="utf-8")
    malformed = []
    rows = T.all_messages(str(p), malformed=malformed)
    assert [r["text"] for r in rows] == ["ok"]
    assert malformed == [2, 3]                           # a JSON non-object counts as malformed


def test_all_messages_skips_sidechain_and_meta_by_default(tmp_path):
    recs = [
        {"type": "user", "message": {"role": "user", "content": "real"}},
        {"type": "user", "isSidechain": True, "message": {"role": "user", "content": "sub"}},
        {"type": "user", "isMeta": True, "message": {"role": "user", "content": "meta"}},
    ]
    path = _write(tmp_path, recs)
    assert [r["text"] for r in T.all_messages(path)] == ["real"]
    assert [r["text"] for r in T.all_messages(path, skip_sidechain=False)] == ["real", "sub"]
    assert [r["text"] for r in T.all_messages(path, skip_meta=False)] == ["real", "meta"]


def test_tool_uses_lists_every_call_of_one_tool_with_its_input(tmp_path):
    recs = [
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "dispatching"},
            {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "Explore", "model": "sonnet"}},
            {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "Plan", "model": "opus"}}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "Plan", "model": "haiku"}}]}},
    ]
    rows = T.tool_uses(_write(tmp_path, recs), "Agent")
    assert rows == [
        {"line": 1, "name": "Agent", "input": {"subagent_type": "Explore", "model": "sonnet"}},
        {"line": 1, "name": "Agent", "input": {"subagent_type": "Plan", "model": "opus"}},
        {"line": 3, "name": "Agent", "input": {"subagent_type": "Plan", "model": "haiku"}},
    ]


def test_tool_uses_of_an_absent_tool_is_empty_while_a_present_one_is_not(tmp_path):
    """Paired so an always-empty implementation cannot pass the negative half alone."""
    recs = [{"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}]
    path = _write(tmp_path, recs)
    assert T.tool_uses(path, "Agent") == []
    assert len(T.tool_uses(path, "Bash")) == 1


def test_tool_uses_skips_sidechain_by_default(tmp_path):
    recs = [
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "main"}}]}},
        {"type": "assistant", "isSidechain": True, "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "sub"}}]}},
    ]
    path = _write(tmp_path, recs)
    assert [r["input"]["command"] for r in T.tool_uses(path, "Bash")] == ["main"]
    assert [r["input"]["command"] for r in T.tool_uses(path, "Bash", skip_sidechain=False)] == ["main", "sub"]


# --- CLI --------------------------------------------------------------------------------

def test_cli_default_output_is_unchanged_when_no_new_flag_is_passed(tmp_path, capsys):
    """Pins the pre-existing contract byte for byte: the new modes must be opt-in only."""
    rc = T.main([_write(tmp_path, FOUR_TURNS)])
    assert rc == 0
    assert capsys.readouterr().out == "== last user ==\nsecond user\n== last assistant ==\nfinal assistant\n"


def test_cli_all_prints_a_header_per_turn_and_exits_zero(tmp_path, capsys):
    rc = T.main([_write(tmp_path, FOUR_TURNS), "--all"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out == ("== line 1 user ==\nfirst user\n"
                   "== line 2 assistant ==\nfirst assistant\n"
                   "== line 3 user ==\nsecond user\n"
                   "== line 4 assistant ==\nfinal assistant\n")


def test_cli_reports_no_match_with_exit_1_so_an_empty_result_is_never_silent(tmp_path, capsys):
    rc = T.main([_write(tmp_path, FOUR_TURNS), "--tool", "NoSuchTool"])
    assert rc == 1
    assert capsys.readouterr().out == ""


def test_cli_json_envelope_carries_the_rows_and_the_skipped_lines(tmp_path, capsys):
    p = tmp_path / "t.jsonl"
    p.write_text('{"type": "assistant", "message": {"role": "assistant", "content": '
                 '[{"type": "tool_use", "name": "Agent", "input": {"subagent_type": "Explore"}}]}}\n'
                 "{broken\n", encoding="utf-8")
    rc = T.main([str(p), "--tool", "Agent", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    envelope = json.loads(captured.out)
    assert envelope["ok"] is True
    assert envelope["command"] == "tool_uses"
    assert envelope["skipped"] == [2]
    assert envelope["data"] == [{"line": 1, "name": "Agent", "input": {"subagent_type": "Explore"}}]
    assert "unparseable" in captured.err            # the warning never pollutes the JSON stdout


def test_cli_refuses_both_modes_at_once(tmp_path, capsys):
    path = _write(tmp_path, FOUR_TURNS)
    assert T.main([path, "--all"]) == 0                  # each flag alone is accepted, so the
    assert T.main([path, "--tool", "Bash"]) == 0         # exit 2 below can only be the exclusion
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        T.main([path, "--all", "--tool", "Agent"])
    assert exc.value.code == 2
