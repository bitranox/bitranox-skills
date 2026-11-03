"""abstream: one stream.jsonl becomes an account (tokens per model, cost, void reasons)."""
import json
from pathlib import Path

import abstream as S
import pytest

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "stream-control.jsonl"


def test_control_fixture_accounts_cleanly():
    acct = S.account_stream_file(FIXTURE)
    s = acct.summary()
    assert s["model"] == "claude-opus-5-5" and s["void_reasons"] == []
    assert (s["main_new_tokens"], s["main_cache_read"], s["main_output_tokens"]) == (20010, 11000, 50)
    assert s["total_cost_usd"] == 0.25 and s["per_model"]["claude-opus-5-5"]["new_tokens"] == 20010
    assert acct.first_cache_read == 11000


def test_non_opus_main_model_is_void():
    acct = S.StreamAccount()
    acct.feed({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5"})
    assert acct.void_reasons == ["session model is 'claude-sonnet-5-5', not an opus id"]


def test_forbidden_model_in_usage_is_void_and_haiku_is_not():
    acct = S.StreamAccount()
    acct.feed({"type": "result", "modelUsage": {"claude-haiku-5-5": {}, "claude-fable-5-1": {}}})
    assert acct.void_reasons == ["model claude-fable-5-1 appears in modelUsage"]


def test_assistant_messages_are_counted_once_per_id():
    acct = S.StreamAccount()
    msg = {"type": "assistant", "message": {"id": "m1", "model": "claude-opus-5-5",
                                            "usage": {"input_tokens": 5, "cache_read_input_tokens": 7}}}
    acct.feed(msg)
    acct.feed(msg)
    assert (acct.new_tokens, acct.cache_read, acct.assistant_messages) == (5, 7, 1)


def test_input_usage_prefers_the_split_and_prices_exactly():
    u = S.input_usage({"input_tokens": 1, "cache_read_input_tokens": 2, "cache_creation_input_tokens": 30,
                       "cache_creation": {"ephemeral_5m_input_tokens": 10, "ephemeral_1h_input_tokens": 20}})
    assert u == {"input": 1, "cache_read": 2, "cache_write_5m": 10, "cache_write_1h": 20}
    assert S.input_usage({"cache_creation_input_tokens": 30}) == {"input": 0, "cache_read": 0, "cache_write_5m": 30, "cache_write_1h": 0}
    units = S.input_units("claude-opus-5-5", u)
    assert units == 1 * 4000 + 2 * 200 + 10 * 5000 + 20 * 8000
    with pytest.raises(S.UnknownModel):
        S.input_units("claude-unknown", u)


def test_non_json_lines_are_skipped(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text("garbage\n" + FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    assert S.account_stream_file(p).summary()["total_cost_usd"] == 0.25


def test_a_torn_last_line_is_counted_not_fatal(tmp_path):
    # A killed arm leaves its final record half-written: the stream still accounts, the torn
    # line is counted rather than silently dropped, and the missing result stays visible.
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    p = tmp_path / "torn.jsonl"
    p.write_text("\n".join(lines[:-1] + [lines[-1][: len(lines[-1]) // 2]]), encoding="utf-8")
    s = S.account_stream_file(p).summary()
    assert (s["skipped_lines"], s["has_result"], s["total_cost_usd"]) == (1, False, None)
    assert s["main_new_tokens"] == 20010 and s["void_reasons"] == []


def test_a_json_line_that_is_not_an_object_is_counted_as_skipped(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text(json.dumps([1, 2]) + "\n\n" + FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    s = S.account_stream_file(p).summary()
    assert (s["skipped_lines"], s["total_cost_usd"]) == (1, 0.25)


def test_clean_control_fixture_skips_nothing():
    assert S.account_stream_file(FIXTURE).summary()["skipped_lines"] == 0


def test_price_input_is_the_units_in_dollars():
    u = {"input": 1_000_000, "cache_read": 0, "cache_write_5m": 0, "cache_write_1h": 0}
    assert S.price_input("claude-opus-5-5", u) == 4.0
    assert S.price_input("claude-haiku-5-5", u) == 0.1
