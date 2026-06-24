"""Behavioural tests for the python-performance-reviewer scripts.

Each main/public function is exercised with real inputs and asserted on actual output.
"""
import cProfile
import textwrap

import find_cache_candidates as fcc
import find_hotspots as fh
import find_uncompiled_regex as fur
import prioritize_cache_candidates as pcc
import validate_perf_claims as vpc
import compare_performance as cmp
import profile_with_cache_template as pwct


SAMPLE = '''
import re
from functools import lru_cache

def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

def slow_sum(n):
    total = 0
    for i in range(n):
        total += i
    return total

def impure(n):
    print(n)
    return n

def parse(s):
    return re.search(r"\\d+", s)

_RX = re.compile(r"\\d+")
def parse_ok(s):
    return _RX.search(s)

@lru_cache(maxsize=128)
def cached(n):
    total = 0
    for i in range(n):
        total += i
    return total
'''


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return str(p)


# --- find_cache_candidates -------------------------------------------------

def test_cache_candidates_flags_pure_expensive(tmp_path):
    f = _write(tmp_path, "m.py", SAMPLE)
    names = {c["function"] for c in fcc.find_cache_candidates(f)}
    assert "fib" in names           # pure + recursion
    assert "slow_sum" in names      # pure + loop


def test_cache_candidates_skips_cached_and_impure(tmp_path):
    f = _write(tmp_path, "m.py", SAMPLE)
    names = {c["function"] for c in fcc.find_cache_candidates(f)}
    assert "cached" not in names    # already @lru_cache
    assert "impure" not in names    # uses print() -> not pure


def test_cache_candidates_indicators_deduped(tmp_path):
    f = _write(tmp_path, "m.py", SAMPLE)
    fib = next(c for c in fcc.find_cache_candidates(f) if c["function"] == "fib")
    assert fib["indicators"] == sorted(set(fib["indicators"]))  # no "recursion, recursion"


# --- find_uncompiled_regex -------------------------------------------------

def test_uncompiled_regex_flags_literal_and_skips_compiled(tmp_path):
    f = _write(tmp_path, "m.py", SAMPLE)
    findings = fur.find_uncompiled_regex(f)
    calls = " ".join(x["call"] for x in findings)
    assert "re.search" in calls          # parse() uses re.search(literal)
    # parse_ok uses a precompiled _RX.search -> must NOT be flagged
    assert all("compile" not in x["call"] for x in findings)
    assert len(findings) == 1


# --- find_hotspots ---------------------------------------------------------

def _make_profile(tmp_path):
    def helper(n):
        s = 0
        for i in range(n):
            s += i
        return s

    def driver():
        for _ in range(300):
            helper(100)

    prof = str(tmp_path / "t.prof")
    cProfile.runctx("driver()", {"driver": driver, "helper": helper}, {}, prof)
    return prof


def test_hotspots_finds_real_function_and_skips_builtins(tmp_path):
    prof = _make_profile(tmp_path)
    spots = fh.find_hotspots(prof, min_calls=1, min_cumtime=0.0)
    funcs = {s["function"] for s in spots}
    assert "helper" in funcs
    # no built-in / synthesized entries (<built-in ...>, <listcomp>, etc.)
    assert all(not s["function"].startswith("<") for s in spots)
    assert all(s["file"] != "~" for s in spots)


def test_hotspots_thresholds_filter(tmp_path):
    prof = _make_profile(tmp_path)
    # impossibly high thresholds -> nothing qualifies
    assert fh.find_hotspots(prof, min_calls=10**9, min_cumtime=10**9) == []


# --- prioritize_cache_candidates -------------------------------------------

def test_prioritize_matches_by_name_and_basename(tmp_path):
    cand = _write(tmp_path, "cand.txt", """
        # Cache Candidates
        /abs/path/m.py:4 - fib()
        /abs/path/m.py:10 - slow_sum()
    """)
    hot = _write(tmp_path, "hot.txt", """
        # Hot Spots
        m.py:4 - fib()
    """)
    candidates = pcc.parse_candidates(cand)
    hotspots = pcc.parse_hotspots(hot)
    pri = {p["function"] for p in pcc.prioritize(candidates, hotspots)}
    assert pri == {"fib"}           # fib is both; slow_sum is only a candidate


# --- validate_perf_claims --------------------------------------------------

def test_claims_extracts_varied_phrasings(tmp_path):
    diff = _write(tmp_path, "changes.diff", """
        +This change is 40% faster and gives a 3x speedup.
        +It reduced latency by 30%.
        +Improves the cache hit rate noticeably.
    """)
    claims = " | ".join(vpc.find_performance_claims(diff)).lower()
    assert "40% faster" in claims
    assert "3x speedup" in claims
    assert ("latency by 30%" in claims) or ("30%" in claims)
    assert "cache hit rate" in claims


def test_claims_empty_when_none(tmp_path):
    diff = _write(tmp_path, "d.diff", "+just a normal refactor, no numbers here.\n")
    assert vpc.find_performance_claims(diff) == []


def test_validate_main_missing_file_returns_1(tmp_path):
    assert vpc.main([str(tmp_path / "nope.diff")]) == 1


# --- compare_performance ---------------------------------------------------

def test_compare_main_not_a_git_repo(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)        # tmp_path is not a git repo
    rc = cmp.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "git repository" in out.lower()


def test_compare_pytest_argv_includes_tests_dir(tmp_path, monkeypatch):
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)
    argv = cmp._pytest_argv()
    assert argv[:3] == [__import__("sys").executable, "-m", "pytest"]
    assert "tests" in argv
    assert argv[-1] == "-v"


def test_compare_pytest_argv_falls_back_to_test_dir(tmp_path, monkeypatch):
    (tmp_path / "test").mkdir()        # singular form
    monkeypatch.chdir(tmp_path)
    argv = cmp._pytest_argv()
    assert "test" in argv
    assert "tests" not in argv


def test_compare_pytest_argv_omits_path_when_no_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)        # no tests/ or test/ -> let pytest discover
    argv = cmp._pytest_argv()
    assert "tests" not in argv and "test" not in argv
    assert argv[-1] == "-v"            # path omitted, only the flag follows pytest


# --- profile_with_cache_template (import-safe; verdict logic) ---------------

def test_profile_template_import_safe_and_verdict():
    # importing the module must NOT run pytest / do work (it is guarded by __main__)
    assert hasattr(pwct, "main") and hasattr(pwct, "recommend")
    assert pwct.recommend(50.0, 90.0).startswith("RECOMMEND")
    assert "too low" in pwct.recommend(1.0, 90.0)        # improvement below threshold
    assert "hit rate" in pwct.recommend(50.0, 5.0).lower()  # hit rate below threshold


def test_profile_template_pytest_argv_conditional(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)        # no tests dir -> path omitted
    assert "tests" not in pwct._pytest_argv()
    (tmp_path / "tests").mkdir()
    assert "tests" in pwct._pytest_argv()
