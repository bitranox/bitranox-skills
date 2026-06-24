"""Unit tests for the pure / file-backed logic in proxy_pool.py.

Network-hitting code (discover/validate via httpx2) is intentionally NOT
exercised; only the deterministic helpers and _run_item (with a local
subprocess) are tested. All test data is ASCII; any non-ASCII would be
embedded via chr(0xXXXX).
"""
import os
import random
import sys

import proxy_pool as pp


# ----------------------------------------------------------------------------
# _read / _grow
# ----------------------------------------------------------------------------
def test_read_missing_file_returns_empty_set(store):
    assert pp._read(pp._p(store, "nope.txt")) == set()


def test_read_strips_and_drops_blank_lines(store):
    path = pp._p(store, "x.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("  a:1  \n\n b:2\n\n")
    assert pp._read(path) == {"a:1", "b:2"}


def test_grow_creates_sorted_deduped(store):
    path = pp._p(store, "pool.txt")
    pp._grow(path, ["2.2.2.2:80", "1.1.1.1:80", "2.2.2.2:80"])
    with open(path, encoding="utf-8") as f:
        body = f.read()
    assert body == "1.1.1.1:80\n2.2.2.2:80\n"


def test_grow_is_grow_only_never_shrinks(store):
    path = pp._p(store, "pool.txt")
    pp._grow(path, ["a:1", "b:2", "c:3"])
    # second call with a SMALLER (and partly different) set must not remove a/b/c
    pp._grow(path, ["d:4"])
    assert pp._read(path) == {"a:1", "b:2", "c:3", "d:4"}
    # calling with an empty set keeps everything
    pp._grow(path, [])
    assert pp._read(path) == {"a:1", "b:2", "c:3", "d:4"}


def test_grow_result_is_sorted(store):
    path = pp._p(store, "pool.txt")
    pp._grow(path, ["10.0.0.1:80", "9.0.0.1:80", "100.0.0.1:80"])
    lines = [l for l in open(path, encoding="utf-8").read().splitlines() if l]
    assert lines == sorted(lines)


# ----------------------------------------------------------------------------
# _append
# ----------------------------------------------------------------------------
def test_append_adds_lines(store):
    path = pp._p(store, "good.txt")
    pp._append(path, "p:1")
    pp._append(path, "p:2")
    assert open(path, encoding="utf-8").read() == "p:1\np:2\n"


# ----------------------------------------------------------------------------
# _read_speeds / _upsert_speeds
# ----------------------------------------------------------------------------
def test_read_speeds_missing_returns_empty(store):
    assert pp._read_speeds(pp._p(store, "speeds.tsv")) == {}


def test_read_speeds_parses_tab_floats_and_skips_garbage(store):
    path = pp._p(store, "speeds.tsv")
    with open(path, "w", encoding="utf-8") as f:
        f.write("a:1\t0.5\n")
        f.write("b:2\tnotafloat\n")   # bad value -> skipped
        f.write("c:3\t1.25\n")
        f.write("d:4\n")              # only one field -> skipped
    assert pp._read_speeds(path) == {"a:1": 0.5, "c:3": 1.25}


def test_upsert_speeds_roundtrip(store):
    path = pp._p(store, "speeds.tsv")
    pp._upsert_speeds(path, {"a:1": 0.5, "b:2": 2.0})
    assert pp._read_speeds(path) == {"a:1": 0.5, "b:2": 2.0}


def test_upsert_speeds_updates_latest_value(store):
    path = pp._p(store, "speeds.tsv")
    pp._upsert_speeds(path, {"a:1": 0.5})
    pp._upsert_speeds(path, {"a:1": 9.0, "b:2": 1.0})
    d = pp._read_speeds(path)
    assert d["a:1"] == 9.0   # updated to latest
    assert d["b:2"] == 1.0   # new entry kept


def test_upsert_speeds_empty_is_noop(store):
    path = pp._p(store, "speeds.tsv")
    pp._upsert_speeds(path, {"a:1": 0.5})
    pp._upsert_speeds(path, {})
    assert pp._read_speeds(path) == {"a:1": 0.5}
    # file should still exist and be unchanged in content
    assert os.path.exists(path)


# ----------------------------------------------------------------------------
# _median
# ----------------------------------------------------------------------------
def test_median_empty_is_zero():
    assert pp._median([]) == 0.0


def test_median_odd():
    assert pp._median([3, 1, 2]) == 2


def test_median_even():
    assert pp._median([1, 2, 3, 4]) == 2.5


def test_median_ignores_falsy_values():
    # zeros / None are filtered out before computing
    assert pp._median([0, 0, 4, 2]) == 3       # only {2,4} remain -> 3
    assert pp._median([None, 5]) == 5
    assert pp._median([0, 0, 0]) == 0.0


# ----------------------------------------------------------------------------
# _pick
# ----------------------------------------------------------------------------
def _seed_store(store, live=(), good=(), bad=(), speeds=None):
    if live:
        pp._grow(pp._p(store, "live.txt"), list(live))
    for g in good:
        pp._append(pp._p(store, "good.txt"), g)
    for b in bad:
        pp._append(pp._p(store, "bad.txt"), b)
    if speeds:
        pp._upsert_speeds(pp._p(store, "speeds.tsv"), speeds)


def test_pick_empty_store_returns_empty(store):
    assert pp._pick(store, 4) == []


def test_pick_never_returns_bad_listed(store):
    # a bad proxy that is also in live and good must never be returned
    _seed_store(
        store,
        live=["good:1", "banned:1"],
        good=["banned:1"],
        bad=["banned:1"],
        speeds={"good:1": 1.0, "banned:1": 0.01},  # banned is "fast" but excluded
    )
    random.seed(1234)
    for _ in range(200):
        picked = pp._pick(store, 2)
        assert "banned:1" not in picked


def test_pick_favours_fast_proxy_over_slow(store):
    # one fast and one slow proxy, neither proven-good; over many single picks the
    # fast one must dominate by a wide margin.
    _seed_store(
        store,
        live=["fast:1", "slow:1"],
        speeds={"fast:1": 0.1, "slow:1": 5.0},
    )
    random.seed(2024)
    counts = {"fast:1": 0, "slow:1": 0}
    for _ in range(3000):
        picked = pp._pick(store, 1)
        assert len(picked) == 1
        counts[picked[0]] += 1
    # fast should be picked far more often than slow (>5x)
    assert counts["fast:1"] > 5 * max(counts["slow:1"], 1), counts


def test_pick_weights_good_proxies_up(store):
    # same latency for both; the proven-good one (base 3.0) must win much more.
    _seed_store(
        store,
        live=["plain:1", "proven:1"],
        good=["proven:1"],
        speeds={"plain:1": 1.0, "proven:1": 1.0},
    )
    random.seed(99)
    counts = {"plain:1": 0, "proven:1": 0}
    for _ in range(3000):
        picked = pp._pick(store, 1)
        counts[picked[0]] += 1
    assert counts["proven:1"] > counts["plain:1"], counts


def test_pick_returns_at_most_n_and_subset_of_candidates(store):
    _seed_store(
        store,
        live=["a:1", "b:1", "c:1", "d:1"],
        speeds={"a:1": 1.0, "b:1": 1.0, "c:1": 1.0, "d:1": 1.0},
    )
    random.seed(7)
    picked = pp._pick(store, 2)
    assert len(picked) == 2
    assert set(picked) <= {"a:1", "b:1", "c:1", "d:1"}
    assert len(set(picked)) == 2  # sampling WITHOUT replacement


# ----------------------------------------------------------------------------
# _run_item
# ----------------------------------------------------------------------------
def _argv_tpl(code):
    """Build a template argv list that runs Python with the given -c code.
    The code may reference {proxy} and {item}; they are substituted by _run_item.
    """
    return [sys.executable, "-c", code]


def test_run_item_success_records_proxy_and_returns_it(store, tmp_path):
    _seed_store(store, live=["px:1"], speeds={"px:1": 1.0})
    outdir = tmp_path / "out"
    outdir.mkdir()
    # write a file named after {item}; exit 0
    code = (
        "import sys;"
        "open(r'%s/{item}.done','w').write('{proxy}')" % outdir
    )
    success_glob = str(outdir / "{item}.done")
    dead_re = pp.re.compile(pp.DEAD_DEFAULT, pp.re.I)
    item, proxy = pp._run_item(store, "JOB", _argv_tpl(code), 4, 30, success_glob, dead_re)
    assert proxy == "px:1"
    assert item == "JOB"
    # good.txt records the proxy
    assert "px:1" in pp._read(pp._p(store, "good.txt"))
    # the output file actually got the substituted {proxy} content
    assert (outdir / "JOB.done").read_text() == "px:1"
    # not banned
    assert pp._read(pp._p(store, "bad.txt")) == set()


def test_run_item_substitutes_proxy_and_item_in_argv(store, tmp_path):
    _seed_store(store, live=["HOST:9"], speeds={"HOST:9": 1.0})
    marker = tmp_path / "marker.txt"
    # write "<proxy>|<item>" so we can verify BOTH substitutions happened in argv
    code = "open(r'%s','w').write('{proxy}|{item}')" % marker
    success_glob = str(marker)
    dead_re = pp.re.compile(pp.DEAD_DEFAULT, pp.re.I)
    pp._run_item(store, "ITM", _argv_tpl(code), 4, 30, success_glob, dead_re)
    assert marker.read_text() == "HOST:9|ITM"


def test_run_item_success_glob_must_match(store, tmp_path):
    # cmd exits 0 but produces NO matching file -> NOT a success, no good record.
    _seed_store(store, live=["px:1"], speeds={"px:1": 1.0})
    code = "pass"  # exits 0, writes nothing
    success_glob = str(tmp_path / "{item}.never")
    dead_re = pp.re.compile(pp.DEAD_DEFAULT, pp.re.I)
    item, proxy = pp._run_item(store, "JOB", _argv_tpl(code), 3, 30, success_glob, dead_re)
    assert proxy is None
    assert pp._read(pp._p(store, "good.txt")) == set()


def test_run_item_connection_error_bans_proxy(store, tmp_path):
    # cmd exits non-zero and prints a dead-regex phrase -> proxy banned, no success.
    _seed_store(store, live=["dead:1"], speeds={"dead:1": 1.0})
    code = "import sys; sys.stderr.write('connection refused by proxy'); sys.exit(1)"
    dead_re = pp.re.compile(pp.DEAD_DEFAULT, pp.re.I)
    item, proxy = pp._run_item(store, "JOB", _argv_tpl(code), 1, 30, None, dead_re)
    assert proxy is None
    assert "dead:1" in pp._read(pp._p(store, "bad.txt"))
    assert pp._read(pp._p(store, "good.txt")) == set()


def test_run_item_transient_failure_does_not_ban(store):
    # non-zero exit, output does NOT match dead-regex (e.g. HTTP 429) -> rotate, no ban.
    _seed_store(store, live=["px:1"], speeds={"px:1": 1.0})
    code = "import sys; sys.stderr.write('HTTP 429 too many requests'); sys.exit(1)"
    dead_re = pp.re.compile(pp.DEAD_DEFAULT, pp.re.I)
    item, proxy = pp._run_item(store, "JOB", _argv_tpl(code), 1, 30, None, dead_re)
    assert proxy is None
    assert pp._read(pp._p(store, "bad.txt")) == set()
    assert pp._read(pp._p(store, "good.txt")) == set()


def test_run_item_no_candidates_returns_none(store):
    # empty store -> _pick returns [] -> loop body never runs.
    dead_re = pp.re.compile(pp.DEAD_DEFAULT, pp.re.I)
    item, proxy = pp._run_item(store, "JOB", _argv_tpl("pass"), 4, 30, None, dead_re)
    assert (item, proxy) == ("JOB", None)


def test_run_item_cmd_not_found_returns_none(store):
    _seed_store(store, live=["px:1"], speeds={"px:1": 1.0})
    dead_re = pp.re.compile(pp.DEAD_DEFAULT, pp.re.I)
    argv_tpl = ["this-binary-does-not-exist-xyz", "{proxy}", "{item}"]
    item, proxy = pp._run_item(store, "JOB", argv_tpl, 4, 30, None, dead_re)
    assert (item, proxy) == ("JOB", None)
    assert pp._read(pp._p(store, "good.txt")) == set()
