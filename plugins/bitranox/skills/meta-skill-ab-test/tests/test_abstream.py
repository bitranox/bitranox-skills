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


OPUS_INIT = {"type": "system", "subtype": "init", "model": "claude-opus-5-5"}


def test_forbidden_model_in_usage_is_void_and_haiku_is_not():
    acct = S.StreamAccount()
    # The init record keeps this test about modelUsage alone: without it the stream is also
    # void for having no init record.
    acct.feed(OPUS_INIT)
    acct.feed({"type": "result", "modelUsage": {"claude-haiku-5-5": {}, "claude-fable-5-1": {}}})
    assert acct.void_reasons == ["model claude-fable-5-1 appears in modelUsage, not an opus or haiku id"]


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
    s = S.account_stream_file(p).summary()
    assert (s["total_cost_usd"], s["skipped_lines"]) == (0.25, 1)


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


def _assistant(mid, model, **usage):
    return {"type": "assistant", "message": {"id": mid, "model": model, "usage": usage}}


NO_INIT = "no init record (main model not asserted)"


def test_feed_line_parses_one_line_and_counts_what_it_cannot_use():
    acct = S.StreamAccount()
    for line in ("", "   \n", "garbage", "[1, 2]", "7", json.dumps(OPUS_INIT) + "\n"):
        acct.feed_line(line)
    assert (acct.model, acct.skipped_lines) == ("claude-opus-5-5", 3)


def test_account_stream_file_equals_feeding_every_line(tmp_path):
    text = "garbage\n\n[1]\n" + FIXTURE.read_text(encoding="utf-8")
    p = tmp_path / "s.jsonl"
    p.write_text(text, encoding="utf-8")
    live = S.StreamAccount()
    for line in text.splitlines(keepends=True):
        live.feed_line(line)
    assert S.account_stream_file(p).summary() == live.summary()


def test_a_stream_without_an_init_record_is_void():
    acct = S.StreamAccount()
    acct.feed(_assistant("m1", "claude-opus-5-5", input_tokens=5))
    assert acct.void_reasons == [] and acct.summary()["void_reasons"] == [NO_INIT]
    acct.feed({"type": "result", "modelUsage": {"claude-opus-5-5": {}}})
    assert acct.void_reasons == [NO_INIT] and acct.summary()["void_reasons"] == [NO_INIT]


def test_an_init_record_without_a_model_is_not_reported_as_missing():
    acct = S.StreamAccount()
    acct.feed({"type": "system", "subtype": "init"})
    acct.feed({"type": "result", "modelUsage": {}})
    assert acct.summary()["void_reasons"] == ["session model is None, not an opus id"]


@pytest.mark.parametrize(("record", "reason"), [
    ({"type": "result", "modelUsage": {"claude-sonnet-5-5": {}}},
     "model claude-sonnet-5-5 appears in modelUsage, not an opus or haiku id"),
    ({"type": "result", "modelUsage": {"claude-Fable-5": {}}},
     "model claude-Fable-5 appears in modelUsage, not an opus or haiku id"),
    (_assistant("m1", "claude-fable-5-1"),
     "model claude-fable-5-1 appears in an assistant message, not an opus or haiku id"),
])
def test_a_model_outside_the_allowlist_voids_the_arm(record, reason):
    acct = S.StreamAccount()
    acct.feed(OPUS_INIT)
    acct.feed(record)
    assert acct.void_reasons == [reason]


def test_opus_and_haiku_together_are_clean_and_a_repeat_voids_once():
    acct = S.StreamAccount()
    acct.feed(OPUS_INIT)
    acct.feed(_assistant("m1", "claude-opus-5-5"))
    acct.feed(_assistant("m2", "claude-haiku-5-5"))
    acct.feed({"type": "result", "modelUsage": {"claude-opus-5-5": {}, "claude-haiku-5-5": {}}})
    assert acct.summary()["void_reasons"] == []
    acct.feed(_assistant("m3", "claude-sonnet-5-5"))
    acct.feed(_assistant("m4", "claude-sonnet-5-5"))
    assert len(acct.void_reasons) == 1


def test_output_tokens_take_the_largest_reading_per_message_id():
    acct = S.StreamAccount()
    acct.feed(_assistant("m1", "claude-opus-5-5", input_tokens=5, output_tokens=1))
    acct.feed(_assistant("m1", "claude-opus-5-5", input_tokens=5, output_tokens=400))
    acct.feed(_assistant("m1", "claude-opus-5-5", input_tokens=5, output_tokens=3))
    acct.feed(_assistant("m2", "claude-opus-5-5", output_tokens=7))
    s = acct.summary()
    assert (s["main_output_tokens"], s["main_new_tokens"], s["assistant_messages"]) == (407, 5, 2)


def test_a_null_or_non_dict_model_usage_entry_is_skipped():
    acct = S.StreamAccount()
    acct.feed(OPUS_INIT)
    acct.feed({"type": "result", "modelUsage": {"claude-opus-5-5": None, "claude-haiku-5-5": [1],
                                                 "claude-opus-5-6": {"inputTokens": 3}}})
    assert list(acct.per_model()) == ["claude-opus-5-6"] and acct.summary()["void_reasons"] == []


@pytest.mark.parametrize("message", ["x", [1], None, 3])
def test_a_non_dict_assistant_message_is_skipped_and_counted(message):
    acct = S.StreamAccount()
    acct.feed({"type": "assistant", "message": message})
    assert (acct.skipped_lines, acct.assistant_messages, acct.per_message_model) == (1, 0, {})


def test_a_partial_cache_creation_split_puts_the_remainder_in_the_5m_class():
    u = S.input_usage({"cache_creation_input_tokens": 30, "cache_creation": {"ephemeral_1h_input_tokens": 20}})
    assert (u["cache_write_5m"], u["cache_write_1h"]) == (10, 20)


def test_per_message_model_counts_two_interleaved_models():
    acct = S.StreamAccount()
    for i, model in enumerate(["claude-opus-5-5", "claude-haiku-5-5", "claude-opus-5-5", "claude-haiku-5-5",
                               "claude-opus-5-5"]):
        acct.feed(_assistant(f"m{i}", model))
    assert acct.per_message_model == {"claude-opus-5-5": 3, "claude-haiku-5-5": 2}


def _synthetic(mid, text):
    return {"type": "assistant", "message": {
        "id": mid, "model": "<synthetic>", "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 9, "cache_creation_input_tokens": 9, "cache_read_input_tokens": 9,
                  "output_tokens": 9}}}


def test_a_cli_synthetic_message_voids_with_its_text_and_charges_nothing():
    acct = S.StreamAccount()
    acct.feed(OPUS_INIT)
    acct.feed(_assistant("m1", "claude-opus-5-5", input_tokens=5, cache_read_input_tokens=7, output_tokens=3))
    acct.feed(_synthetic("s1", "You've hit your weekly limit - resets Monday"))
    acct.feed(_synthetic("s2", "You've hit your weekly limit - resets Monday"))
    s = acct.summary()
    assert len(s["void_reasons"]) == 1
    (reason,) = s["void_reasons"]
    assert reason.startswith(S.SYNTHETIC_REASON_PREFIX) and "weekly limit" in reason
    assert S.SYNTHETIC_REASON_PREFIX == "CLI synthetic message: "
    assert not any("<synthetic>" in r for r in s["void_reasons"])
    assert (s["main_new_tokens"], s["main_cache_read"], s["main_output_tokens"]) == (5, 7, 3)
    assert (s["assistant_messages"], s["per_message_model"], s["first_cache_read"]) == (1, {"claude-opus-5-5": 1}, 7)


def test_a_synthetic_reason_is_cut_to_80_characters_and_tolerates_no_text():
    acct = S.StreamAccount()
    acct.feed(_synthetic("s1", "x" * 200))
    acct.feed({"type": "assistant", "message": {"id": "s2", "model": "<synthetic>"}})
    assert acct.void_reasons == ["CLI synthetic message: " + "x" * 80, "CLI synthetic message: "]
    assert (acct.first_cache_read, acct.new_tokens, acct.output_tokens) == (None, 0, 0)
