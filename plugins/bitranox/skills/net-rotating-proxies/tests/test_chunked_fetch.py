"""Tests for chunked_fetch: pure helpers, one ranged attempt, the probe, and the whole download.

Everything runs against fetch_standins (an origin and fault-injecting forward proxies bound to
127.0.0.1) and the real ProxyPool, so the pool's ban/record/eviction paths are the ones exercised.
"""
import hashlib
import json
import os
import time

import chunked_fetch as cfetch
import proxy_pool as pp
import pytest
from fetch_standins import Standins


@pytest.mark.parametrize("text, want", [("8M", 8 * 1024**2), ("512k", 512 * 1024), ("100", 100),
                                        ("1G", 1024**3)])
def test_parse_size_reads_binary_units(text, want):
    assert cfetch.parse_size(text) == want


@pytest.mark.parametrize("text", ["0", "8X", "", "-1", "1.5M", "8 M", "8" + chr(0x0661) + "M"])
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
    (502, {}, "throttled"),
    (200, OK_HEADERS, "wrong-object"), (404, {}, "wrong-object"),
    (206, {**OK_HEADERS, "content-range": "bytes 0-9/100"}, "wrong-object"),
    (206, {**OK_HEADERS, "content-range": "bytes 10-18/100"}, "wrong-object"),
    (206, {**OK_HEADERS, "content-range": "bytes 10-19/999"}, "wrong-object"),
    (206, {**OK_HEADERS, "etag": '"v2"'}, "identity"),
    (206, {**OK_HEADERS, "last-modified": "Sun, 02 Nov 2026 10:00:00 GMT"}, "identity"),
    (206, {k: v for k, v in OK_HEADERS.items() if k != "etag"}, "identity"),
    # A proxy ignoring Accept-Encoding: identity would have compressed bytes written as content.
    (206, {**OK_HEADERS, "content-encoding": "gzip"}, "wrong-object"),
    (206, {**OK_HEADERS, "content-encoding": " GZIP "}, "wrong-object"),
    (206, {**OK_HEADERS, "content-encoding": "identity"}, None),
    (206, {**OK_HEADERS, "content-encoding": " Identity "}, None),
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


def test_action_for_refuses_an_unknown_reason():
    with pytest.raises(ValueError, match="unknown attempt reason"):
        cfetch.action_for("wrong_object")


SIZE = 300_000
CHUNK = 64 * 1024


@pytest.fixture
def stand():
    s = Standins()
    yield s
    s.close()


def _part(tmp_path, total):
    path = tmp_path / "f.bin.part"
    path.write_bytes(b"\x00" * total)
    return str(path)


@pytest.mark.parametrize("mode, want", [
    ("clean", ("ok", 1000)), ("refuse", ("dead", 0)), ("429", ("throttled", 0)),
    ("403", ("throttled", 0)), ("html", ("wrong-object", 0)), ("wrong-range", ("wrong-object", 0)),
    ("etag", ("identity", 0)), ("cut:300", ("cut", 300)), ("overrun", ("overrun", 1000)),
    ("stall", ("cut", 0))])
def test_attempt_classifies_each_proxy_behaviour(stand, tmp_path, mode, want):
    origin = stand.origin(SIZE)
    path = _part(tmp_path, SIZE)
    ident = {"etag": '"v1"', "last_modified": "Sat, 01 Nov 2026 10:00:00 GMT"}
    got = cfetch.attempt(origin.url, stand.proxy(mode), 5000, 5999, SIZE, ident, path, timeout=0.5)
    assert got == want
    with open(path, "rb") as f:
        on_disk = f.read()
    written = want[1]
    assert on_disk[5000:5000 + written] == origin.data[5000:5000 + written]
    assert on_disk[5000 + written:6001] == b"\x00" * (6001 - 5000 - written)   # nothing past it


def test_attempt_resumes_inside_a_chunk_at_the_offset_it_is_given(stand, tmp_path):
    origin = stand.origin(SIZE)
    path = _part(tmp_path, SIZE)
    ident = cfetch.identity_of({"etag": '"v1"'})
    assert cfetch.attempt(origin.url, stand.proxy(), 5300, 5999, SIZE, ident, path, 2.0) == ("ok", 700)
    assert origin.log[-1] == "bytes=5300-5999"


def _pool(tmp_path, proxies, name="store", fail_ratio=0.5):
    store = tmp_path / name
    store.mkdir()
    (store / "live.txt").write_text("\n".join(proxies) + "\n", encoding="utf-8")
    return str(store), pp.ProxyPool(str(store), None, cooldown=0, flaky_max_fail_ratio=fail_ratio)


def _fetch(origin, out, pool, **kw):
    url = kw.pop("url", origin.url)
    kw.setdefault("chunk_size", CHUNK)
    kw.setdefault("workers", 4)
    kw.setdefault("timeout", 1.0)
    kw.setdefault("log", lambda *a: None)
    kw.setdefault("warn", lambda *a: None)
    return cfetch.fetch(url, str(out), pool, **kw)


def _starts_per_chunk(origin):
    """Range starts the origin saw, grouped by chunk index, probe excluded."""
    starts = {}
    for value in origin.log:
        if value and value != "bytes=0-0":
            first = int(value.removeprefix("bytes=").split("-")[0])
            starts.setdefault(first // CHUNK, []).append(first)
    return starts


def test_clean_pool_writes_an_identical_file_and_cleans_up(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy(), stand.proxy()])
    out = tmp_path / "f.bin"
    result = _fetch(origin, out, pool, sha256=hashlib.sha256(origin.data).hexdigest())
    assert result.ok and result.done == result.chunks == 5
    assert out.read_bytes() == origin.data
    assert not (tmp_path / "f.bin.part").exists() and not (tmp_path / "f.bin.part.json").exists()


def test_mixed_pool_still_writes_an_identical_file_and_bans_only_the_bannable(stand, tmp_path):
    origin = stand.origin(SIZE)
    bannable = {stand.proxy(m) for m in ("refuse", "html", "wrong-range", "etag")}
    kept = {stand.proxy(m) for m in ("clean", "429", "cut:5000", "stall")}
    store, pool = _pool(tmp_path, sorted(bannable | kept))
    out = tmp_path / "f.bin"
    assert _fetch(origin, out, pool, max_attempts=40).ok
    assert out.read_bytes() == origin.data
    banned = pp._read(os.path.join(store, "bad.txt"))      # tolerates a missing file
    assert banned <= bannable
    # The probe bans only on a refused connect, so a served bannable proxy is banned exactly
    # when a CHUNK request reached it; "nothing banned" passes only if none was reached.
    served = {p for p in bannable if p in stand.proxies}
    reached = {p for p in served if any(r != "bytes=0-0" for r in stand.proxies[p].log)}
    assert banned & served == reached


def test_a_cut_chunk_resumes_from_its_offset_never_from_its_start(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy("cut:10000")], fail_ratio=1.0)   # never evicted
    out = tmp_path / "f.bin"
    assert _fetch(origin, out, pool, workers=1).ok
    assert out.read_bytes() == origin.data
    for index, starts in _starts_per_chunk(origin).items():
        first = index * CHUNK
        assert starts == list(range(first, min(first + CHUNK, SIZE), 10000))


def test_a_stopped_run_resumes_from_its_manifest(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, cutting = _pool(tmp_path, [stand.proxy("cut:10000")], fail_ratio=1.0)
    out = tmp_path / "f.bin"
    first = _fetch(origin, out, cutting, workers=1, max_attempts=1)
    assert not first.ok and first.done == 0
    manifest = json.loads((tmp_path / "f.bin.part.json").read_text(encoding="utf-8"))
    assert manifest["received"] == [10000] * 5
    origin.log.clear()
    _, clean = _pool(tmp_path, [stand.proxy()], name="store2")
    assert _fetch(origin, out, clean).ok
    assert out.read_bytes() == origin.data
    assert {i: s[0] for i, s in _starts_per_chunk(origin).items()} == {
        i: i * CHUNK + 10000 for i in range(5)}


@pytest.mark.parametrize("key, change", [
    ("url", lambda origin, kw: kw.update(url=origin.url + "?v=2")),
    ("total", lambda origin, kw: setattr(origin, "data", origin.data + b"x")),
    ("chunk_size", lambda origin, kw: kw.update(chunk_size=CHUNK * 2)),
    ("identity", lambda origin, kw: setattr(origin, "etag", '"v2"')),
])
def test_a_manifest_for_another_download_is_refused(stand, tmp_path, key, change):
    origin = stand.origin(SIZE)
    _, cutting = _pool(tmp_path, [stand.proxy("cut:10000")], fail_ratio=1.0)
    out = tmp_path / "f.bin"
    _fetch(origin, out, cutting, workers=1, max_attempts=1)
    kw = {}
    change(origin, kw)
    _, clean = _pool(tmp_path, [stand.proxy()], name="store2")
    with pytest.raises(cfetch.ManifestMismatch) as refused:
        _fetch(origin, out, clean, **kw)
    # Read the key list out of '(a, b differ)', not the whole message: the path holds the test name.
    listed = str(refused.value).rsplit("(", 1)[1].split(" differ")[0].split(", ")
    assert key in listed


def test_a_wrong_hash_removes_the_manifest_and_keeps_the_part(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy()])
    out = tmp_path / "f.bin"
    with pytest.raises(cfetch.HashMismatch):
        _fetch(origin, out, pool, sha256="0" * 64)
    assert not out.exists() and not (tmp_path / "f.bin.part.json").exists()
    assert (tmp_path / "f.bin.part").read_bytes() == origin.data


def test_spent_attempts_leave_the_part_and_manifest_for_a_later_run(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy("cut:10000")], fail_ratio=1.0)
    result = _fetch(origin, tmp_path / "f.bin", pool, max_attempts=2)
    assert not result.ok and result.counts["cut"] == 10
    assert (tmp_path / "f.bin.part").exists() and (tmp_path / "f.bin.part.json").exists()


def test_an_empty_object_needs_no_chunks(stand, tmp_path):
    origin = stand.origin(0)
    _, pool = _pool(tmp_path, [stand.proxy()])
    out = tmp_path / "f.bin"
    assert _fetch(origin, out, pool).ok and out.read_bytes() == b""


def test_one_etag_rewriting_proxy_cannot_plant_the_identity(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy("etag"), stand.proxy(), stand.proxy()])
    info = cfetch.probe(origin.url, pool, 1.0, 20, warn=lambda *a: None)
    assert info.ranged and info.total == SIZE and info.identity["etag"] == '"v1"'


def test_a_proxy_answering_another_range_cannot_plant_the_size(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy("wrong-range"), stand.proxy()])
    info = cfetch.probe(origin.url, pool, 1.0, 20, warn=lambda *a: None)
    assert info.ranged and info.total == SIZE


class _InOrder(pp.ProxyPool):
    """The real pool, but acquire() hands proxies out in a fixed order (skipping evicted ones),
    so a test can make a lying proxy answer the probe FIRST instead of hoping the random pick
    does."""

    def __init__(self, store, order):
        super().__init__(store, None, cooldown=0)
        self._order, self._turn = list(order), 0

    def acquire(self, n):
        active = self.active()
        for _ in range(len(self._order)):
            proxy = self._order[self._turn % len(self._order)]
            self._turn += 1
            if proxy in active:
                return [proxy]
        return []


def test_the_first_probe_answer_alone_does_not_decide(stand, tmp_path):
    origin = stand.origin(SIZE)
    order = [stand.proxy("etag"), stand.proxy(), stand.proxy()]
    store, _ = _pool(tmp_path, order)
    info = cfetch.probe(origin.url, _InOrder(store, order), 1.0, 20, warn=lambda *a: None)
    assert info.ranged and info.total == SIZE and info.identity["etag"] == '"v1"'


@pytest.mark.parametrize("liar_first", [True, False])
def test_a_tie_between_two_different_views_refuses_instead_of_guessing(stand, tmp_path, liar_first):
    origin = stand.origin(SIZE)
    liar, honest = stand.proxy("etag"), stand.proxy()
    order = [liar, honest] if liar_first else [honest, liar]
    store, _ = _pool(tmp_path, order)
    warnings = []
    assert cfetch.probe(origin.url, _InOrder(store, order), 1.0, 20, warn=warnings.append) is None
    assert warnings == [("probe: proxies disagree about the object (2 distinct views); "
                         "refusing to guess - rerun later or use --sha256")]
    store2, _ = _pool(tmp_path, order, name="store2")
    result = _fetch(origin, tmp_path / "f.bin", _InOrder(store2, order))
    assert not result.ok and result.done == 0
    assert not (tmp_path / "f.bin.part.json").exists()
    assert pp._read(os.path.join(store2, "bad.txt")) == set()


def test_on_a_tie_a_ranged_answer_still_beats_a_whole_file_one(stand, tmp_path):
    origin = stand.origin(SIZE)
    order = [stand.proxy("html"), stand.proxy()]
    store, _ = _pool(tmp_path, order)
    warnings = []
    info = cfetch.probe(origin.url, _InOrder(store, order), 1.0, 20, warn=warnings.append)
    assert info.ranged and info.total == SIZE and info.identity["etag"] == '"v1"'
    # Two proxies answered, but the winning view has one voter: it is warned as not cross-checked.
    assert warnings == [("probe: proxies disagreed; took the ranged view of one proxy, not "
                         "cross-checked - pass --sha256 to verify the result")]


def test_a_single_answering_proxy_decides_with_a_warning(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy()])
    warnings = []
    info = cfetch.probe(origin.url, pool, 1.0, 20, warn=warnings.append)
    assert info.ranged and info.total == SIZE
    assert len(warnings) == 1 and warnings[0].startswith("probe: only one proxy answered")


def test_attempt_gives_up_a_trickling_proxy_at_its_wall_time_budget(stand, tmp_path):
    origin = stand.origin(SIZE)
    path = _part(tmp_path, SIZE)
    began = time.monotonic()
    reason, written = cfetch.attempt(origin.url, stand.proxy("trickle:0.05"), 5000, 14999, SIZE,
                                     IDENT, path, timeout=0.5)
    assert time.monotonic() - began < 2.0
    assert reason == "cut" and 0 < written < 10000
    with open(path, "rb") as f:
        on_disk = f.read()
    assert on_disk[5000:5000 + written] == origin.data[5000:5000 + written]
    assert on_disk[5000 + written:15000] == b"\x00" * (10000 - written)


def test_an_attempt_asks_for_identity_encoding(stand, tmp_path):
    origin = stand.origin(SIZE)
    path = _part(tmp_path, SIZE)
    assert cfetch.attempt(origin.url, stand.proxy(), 0, 999, SIZE, IDENT, path, 2.0)[0] == "ok"
    assert origin.ae_log == ["identity"]


def test_every_client_ignores_the_environment():
    # Measured on httpx2 2.16: with an explicit proxy= the env proxy variables are not read even
    # under trust_env=True, so no env-based test can fail; trust_env=False still keeps .netrc
    # credentials and SSL_CERT_* overrides out. Pin the setting on the one factory both the
    # probe and attempt use.
    with cfetch._client("127.0.0.1:9", 1.0) as client:
        assert client.trust_env is False


def test_the_probe_asks_for_identity_encoding(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy(), stand.proxy()])
    assert cfetch.probe(origin.url, pool, 2.0, 20, warn=lambda *a: None) is not None
    assert origin.ae_log and set(origin.ae_log) == {"identity"}


def test_a_pool_that_runs_dry_stops_the_run_instead_of_spinning(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy("probe-only")])     # banned on its first chunk
    lines = []
    began = time.monotonic()
    result = _fetch(origin, tmp_path / "f.bin", pool, chunk_size=16 * 1024, log=lines.append)
    assert time.monotonic() - began < 2.0
    assert not result.ok and result.done == 0 and result.chunks == 19
    attempts = {k: v for k, v in result.counts.items() if k != "pool-dry"}
    assert result.counts["pool-dry"] == 1
    assert set(attempts) == {"wrong-object"} and 1 <= attempts["wrong-object"] <= 4   # one per worker
    assert "pool ran dry: 19 chunk(s) left" in lines
    assert any(line.startswith(f"chunks 0/19, attempts {attempts['wrong-object']}:") for line in lines)
    assert (tmp_path / "f.bin.part").exists() and (tmp_path / "f.bin.part.json").exists()


def _stopped_run(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, cutting = _pool(tmp_path, [stand.proxy("cut:10000")], fail_ratio=1.0)
    _fetch(origin, tmp_path / "f.bin", cutting, workers=1, max_attempts=1)
    return origin, tmp_path / "f.bin.part.json"


def _with_received(received):
    def damage(text):
        state = json.loads(text)
        state["received"] = received
        return json.dumps(state)
    return damage


@pytest.mark.parametrize("damage", [
    lambda text: text[:len(text) // 2],              # a truncated write
    lambda text: "[]",                               # valid JSON, not an object
    _with_received([10000] * 4),                     # one chunk short
    _with_received([10000] * 6),
    _with_received([10000] * 4 + [CHUNK + 1]),       # more than the chunk holds
    _with_received([-1] + [10000] * 4),
    _with_received(["x"] + [10000] * 4),
    _with_received([True] + [10000] * 4),
    _with_received({"0": 10000}),
], ids=["truncated", "not-object", "short", "long", "over", "negative", "text", "bool", "dict"])
def test_a_damaged_manifest_is_refused_with_a_reason(stand, tmp_path, damage):
    origin, manifest = _stopped_run(stand, tmp_path)
    manifest.write_text(damage(manifest.read_text(encoding="utf-8")), encoding="utf-8")
    _, clean = _pool(tmp_path, [stand.proxy()], name="store2")
    with pytest.raises(cfetch.ManifestMismatch, match="delete it and the .part file"):
        _fetch(origin, tmp_path / "f.bin", clean)


def _flaky_op(failures):
    calls = []

    def op():
        calls.append(1)
        if len(calls) <= failures:
            raise PermissionError(13, "The process cannot access the file")
        return "replaced"
    return op, calls


def test_a_windows_sharing_violation_on_replace_is_retried():
    op, calls = _flaky_op(2)
    assert cfetch._retry_sharing_violation(op, windows=True, sleep=lambda s: None) == "replaced"
    assert len(calls) == 3


def test_a_permission_error_off_windows_is_raised_at_once():
    op, calls = _flaky_op(1)
    with pytest.raises(PermissionError):
        cfetch._retry_sharing_violation(op, windows=False, sleep=lambda s: None)
    assert len(calls) == 1


def test_a_server_without_range_support_takes_the_whole_file_fallback(stand, tmp_path):
    origin = stand.origin(SIZE)
    origin.ignore_range = True
    _, pool = _pool(tmp_path, [stand.proxy(), stand.proxy()])
    out = tmp_path / "f.bin"
    result = _fetch(origin, out, pool)
    assert result.ok and out.read_bytes() == origin.data
    assert None in origin.log                 # the download itself sent no Range header
    assert set(origin.ae_log) == {"identity"}
    assert not (tmp_path / "f.bin.part").exists() and not (tmp_path / "f.bin.part.json").exists()


def test_one_injecting_proxy_cannot_switch_the_download_to_whole_file(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy("html"), stand.proxy()])
    out = tmp_path / "f.bin"
    assert _fetch(origin, out, pool, max_attempts=40).ok
    assert out.read_bytes() == origin.data
    assert None not in origin.log             # every origin request was ranged


def test_a_single_proxy_on_a_rangeless_server_still_falls_back_after_its_budget(stand, tmp_path):
    origin = stand.origin(SIZE)
    origin.ignore_range = True
    _, pool = _pool(tmp_path, [stand.proxy()])
    lines = []
    result = cfetch.fetch(origin.url, str(tmp_path / "f.bin"), pool, chunk_size=CHUNK, timeout=1.0,
                          max_attempts=3, log=lambda *a: None, warn=lines.append)
    assert result.ok and (tmp_path / "f.bin").read_bytes() == origin.data
    assert any("only one proxy" in line for line in lines)


WHOLE_HEADERS = {"content-length": "100", "etag": '"v1"',
                 "last-modified": "Sat, 01 Nov 2026 10:00:00 GMT"}


@pytest.mark.parametrize("status, headers, want", [
    (200, WHOLE_HEADERS, None),
    (200, {k: v for k, v in WHOLE_HEADERS.items() if k != "content-length"}, None),
    (429, {}, "throttled"), (403, {}, "throttled"), (407, {}, "throttled"), (503, {}, "throttled"),
    (206, {**WHOLE_HEADERS, "content-range": "bytes 0-99/100"}, "wrong-object"),
    (404, {}, "wrong-object"),
    # An injected page answers 200 too; only its length gives it away before a byte is written.
    (200, {**WHOLE_HEADERS, "content-length": "20"}, "wrong-object"),
    (200, {**WHOLE_HEADERS, "content-encoding": "gzip"}, "wrong-object"),
    (200, {**WHOLE_HEADERS, "content-encoding": " Identity "}, None),
    (200, {**WHOLE_HEADERS, "etag": '"v2"'}, "identity"),
    (200, {k: v for k, v in WHOLE_HEADERS.items() if k != "last-modified"}, "identity"),
])
def test_whole_reply_problem_classifies_a_plain_reply_before_any_byte_is_written(status, headers, want):
    assert cfetch.whole_reply_problem(status, headers, 100, IDENT) == want


def test_whole_reply_problem_takes_any_length_when_the_probe_saw_none():
    assert cfetch.whole_reply_problem(200, {"content-length": "7"}, None,
                                      {"etag": None, "last_modified": None}) is None


def _rangeless(stand):
    origin = stand.origin(SIZE)
    origin.ignore_range = True
    return origin


def test_a_cut_whole_file_attempt_restarts_from_byte_zero(stand, tmp_path):
    origin = _rangeless(stand)
    order = [stand.proxy("cut:10000"), stand.proxy()]
    store, _ = _pool(tmp_path, order)
    out = tmp_path / "f.bin"
    result = _fetch(origin, out, _InOrder(store, order))
    assert result.ok and result.counts == {"cut": 1, "ok": 1}
    assert out.read_bytes() == origin.data     # an appended second stream would be 10000 too long


def test_a_page_serving_proxy_on_a_rangeless_server_is_banned_not_written(stand, tmp_path):
    origin = _rangeless(stand)
    liar = stand.proxy("html")
    order = [stand.proxy(), stand.proxy(), liar]
    store, _ = _pool(tmp_path, order)
    out = tmp_path / "f.bin"
    result = _fetch(origin, out, _InOrder(store, order))
    assert result.ok and out.read_bytes() == origin.data
    assert result.counts == {"wrong-object": 1, "ok": 1}
    assert pp._read(os.path.join(store, "bad.txt")) == {liar}


def test_a_trickling_whole_file_attempt_ends_at_its_wall_time_budget(stand, tmp_path):
    # 100 bytes at one per 50 ms: 5 s without a budget, so a regression completes and fails
    # rather than hanging the suite.
    origin = stand.origin(100)
    origin.ignore_range = True
    _, pool = _pool(tmp_path, [stand.proxy("trickle:0.05")], fail_ratio=1.0)
    began = time.monotonic()
    result = _fetch(origin, tmp_path / "f.bin", pool, timeout=0.5, max_attempts=2)
    assert time.monotonic() - began < 4.0
    assert not result.ok and result.counts == {"cut": 2}


@pytest.mark.parametrize("mode, reason", [("unsized-cut:10000", "cut"), ("unsized-overrun", "overrun")])
def test_an_unsized_whole_reply_is_judged_by_the_bytes_it_carried(stand, tmp_path, mode, reason):
    # Without Content-Length a short or long body ends cleanly; only counting it against the
    # probed size tells it from the whole object.
    origin = _rangeless(stand)
    order = [stand.proxy(), stand.proxy(), stand.proxy(mode)]     # the two clean ones probe
    store, _ = _pool(tmp_path, order)
    out = tmp_path / "f.bin"
    result = _fetch(origin, out, _InOrder(store, order))
    assert result.ok and result.counts == {reason: 1, "ok": 1}
    assert out.read_bytes() == origin.data


def test_a_spent_whole_file_budget_reports_the_file_missing(stand, tmp_path):
    origin = _rangeless(stand)
    _, pool = _pool(tmp_path, [stand.proxy("cut:10000")], fail_ratio=1.0)
    lines = []
    result = _fetch(origin, tmp_path / "f.bin", pool, max_attempts=2, log=lines.append)
    assert not result.ok and result.done == 0 and result.chunks == 1
    assert result.counts == {"cut": 2} and "rerun" in result.note
    assert "whole file, attempts 2: cut 2" in lines
    assert not (tmp_path / "f.bin").exists() and not (tmp_path / "f.bin.part.json").exists()


def test_a_whole_file_pool_that_runs_dry_stops_instead_of_spinning(stand, tmp_path):
    origin = _rangeless(stand)
    _, pool = _pool(tmp_path, [stand.proxy("probe-only")])     # banned on its first download
    lines = []
    began = time.monotonic()
    result = _fetch(origin, tmp_path / "f.bin", pool, log=lines.append)
    assert time.monotonic() - began < 2.0
    assert not result.ok and result.counts == {"wrong-object": 1, "pool-dry": 1}
    assert "whole file, attempts 1: wrong-object 1" in lines
    assert "pool ran dry: the whole file is still missing" in lines


def test_a_ranged_runs_manifest_is_refused_when_the_origin_now_ignores_range(stand, tmp_path):
    origin, manifest = _stopped_run(stand, tmp_path)
    part = tmp_path / "f.bin.part"
    kept = part.read_bytes()
    origin.ignore_range = True
    _, clean = _pool(tmp_path, [stand.proxy(), stand.proxy()], name="store2")
    with pytest.raises(cfetch.ManifestMismatch, match="delete it and the .part file"):
        _fetch(origin, tmp_path / "f.bin", clean)
    # The stream never started: the bytes the manifest records as received are still there.
    assert manifest.exists() and part.read_bytes() == kept
