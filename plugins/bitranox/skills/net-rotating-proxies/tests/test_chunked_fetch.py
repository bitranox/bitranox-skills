"""Tests for chunked_fetch: pure helpers, one ranged attempt, the probe, and the whole download.

Everything runs against fetch_standins (an origin and fault-injecting forward proxies bound to
127.0.0.1) and the real ProxyPool, so the pool's ban/record/eviction paths are the ones exercised.
"""
import hashlib
import json
import os

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
    kw.setdefault("chunk_size", CHUNK)
    kw.setdefault("workers", 4)
    kw.setdefault("timeout", 1.0)
    return cfetch.fetch(origin.url, str(out), pool, log=lambda *a: None, warn=lambda *a: None, **kw)


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


def test_a_manifest_for_another_version_is_refused(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, cutting = _pool(tmp_path, [stand.proxy("cut:10000")], fail_ratio=1.0)
    out = tmp_path / "f.bin"
    _fetch(origin, out, cutting, workers=1, max_attempts=1)
    origin.etag = '"v2"'
    _, clean = _pool(tmp_path, [stand.proxy()], name="store2")
    with pytest.raises(cfetch.ManifestMismatch):
        _fetch(origin, out, clean)


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
