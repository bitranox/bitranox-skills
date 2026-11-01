"""Tests for chunked_fetch: pure helpers, one ranged attempt, the probe, and the whole download.

Everything runs against fetch_standins (an origin and fault-injecting forward proxies bound to
127.0.0.1) and the real ProxyPool, so the pool's ban/record/eviction paths are the ones exercised.
"""
import chunked_fetch as cfetch
import pytest


@pytest.mark.parametrize("text, want", [("8M", 8 * 1024**2), ("512k", 512 * 1024), ("100", 100),
                                        ("1G", 1024**3)])
def test_parse_size_reads_binary_units(text, want):
    assert cfetch.parse_size(text) == want


@pytest.mark.parametrize("text", ["0", "8X", "", "-1", "1.5M", "8 M"])
def test_parse_size_refuses_junk(text):
    with pytest.raises(ValueError):
        cfetch.parse_size(text)


@pytest.mark.parametrize("total, size, want", [
    (10, 4, [(0, 3), (4, 7), (8, 9)]), (8, 4, [(0, 3), (4, 7)]), (1, 4, [(0, 0)]), (0, 4, [])])
def test_plan_chunks_covers_every_byte_once(total, size, want):
    assert cfetch.plan_chunks(total, size) == want


@pytest.mark.parametrize("value, want", [
    ("bytes 0-9/100", (0, 9, 100)), ("bytes */100", None), ("bytes 0-9/*", None), (None, None),
    ("bytes 0-9/100 ", (0, 9, 100)), ("bytes " + chr(0x0661) + "-9/100", None)])
def test_parse_content_range(value, want):
    assert cfetch.parse_content_range(value) == want


IDENT = {"etag": '"v1"', "last_modified": "Sat, 01 Nov 2026 10:00:00 GMT"}
OK_HEADERS = {"content-range": "bytes 10-19/100", "etag": '"v1"',
              "last-modified": "Sat, 01 Nov 2026 10:00:00 GMT"}


@pytest.mark.parametrize("status, headers, want", [
    (206, OK_HEADERS, None),
    (429, {}, "throttled"), (403, {}, "throttled"), (407, {}, "throttled"), (503, {}, "throttled"),
    (200, OK_HEADERS, "wrong-object"), (404, {}, "wrong-object"),
    (206, {**OK_HEADERS, "content-range": "bytes 0-9/100"}, "wrong-object"),
    (206, {**OK_HEADERS, "content-range": "bytes 10-19/999"}, "wrong-object"),
    (206, {**OK_HEADERS, "etag": '"v2"'}, "identity"),
    (206, {k: v for k, v in OK_HEADERS.items() if k != "etag"}, "identity"),
])
def test_reply_problem_classifies_a_reply_before_any_byte_is_written(status, headers, want):
    assert cfetch.reply_problem(status, headers, 10, 19, 100, IDENT) == want


def test_reply_problem_skips_identity_fields_the_probe_did_not_see():
    headers = {"content-range": "bytes 10-19/100"}
    assert cfetch.reply_problem(206, headers, 10, 19, 100, {"etag": None, "last_modified": None}) is None


@pytest.mark.parametrize("reason, want", [
    ("ok", "ok"), ("dead", "ban"), ("wrong-object", "ban"), ("identity", "ban"),
    ("throttled", "fail"), ("cut", "fail"), ("overrun", "fail")])
def test_action_for_maps_each_reason_to_the_pool_call(reason, want):
    assert cfetch.action_for(reason) == want
