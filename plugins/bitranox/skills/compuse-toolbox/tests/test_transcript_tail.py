"""Tests for transcript_tail.py. Fixtures mirror the real Claude Code JSONL shape. ASCII only."""
import json
from pathlib import Path

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
