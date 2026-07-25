"""Tests for jsonl_grep.py - filter a JSONL stream by type/role, extract a field or regex. ASCII."""
import json

import jsonl_grep as J


def _mk(recs):
    return "\n".join(json.dumps(r) for r in recs) + "\n"


def test_filter_by_type():
    text = _mk([{"type": "user", "message": {"role": "user", "content": "hi"}},
                {"type": "assistant", "message": {"role": "assistant", "content": "yo"}}])
    out = J.filter_records(text, type_="assistant")
    assert len(out) == 1 and out[0]["type"] == "assistant"


def test_filter_by_role():
    text = _mk([{"type": "user", "message": {"role": "user"}},
                {"type": "x", "message": {"role": "assistant"}}])
    out = J.filter_records(text, role="assistant")
    assert len(out) == 1 and out[0]["message"]["role"] == "assistant"


def test_extract_dotted_field():
    text = _mk([{"type": "x", "message": {"role": "r", "model": "opus"}}])
    assert J.filter_records(text, field="message.model") == ["opus"]


def test_regex_over_raw_line():
    text = _mk([{"type": "assistant", "message": {"content": [{"input": {"command": "cargo build"}}]}},
                {"type": "assistant", "message": {"content": "nope"}}])
    assert len(J.filter_records(text, pattern="cargo")) == 1


def test_malformed_line_skipped():
    out = J.filter_records('{"type":"user"}\nNOT JSON\n{"type":"assistant"}\n')
    assert len(out) == 2
