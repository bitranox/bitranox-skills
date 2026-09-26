"""
Template for profiling a specific function with caching.

Usage:
  1. Copy this template to profile_cache_FUNCTION_NAME.py
  2. Update MODULE_NAME and FUNCTION_NAME
  3. Run it FROM THE PROJECT ROOT: python profile_cache_FUNCTION_NAME.py

What it does: one untimed warm-up run of the test suite (imports, collection, first-run
caches), then REPEATS timed runs WITHOUT the cache and REPEATS WITH the function wrapped in
a fresh lru_cache, interleaved (U C, C U, U C, ...) so anything that drifts during the
experiment lands on both arms. It compares the medians, and it recommends the cache only
when the two arms do not overlap at all - every cached run faster than every uncached one.
One run per arm is not a measurement: on a small suite two identical runs differ by 30%.
The copy may live anywhere (SKILL.md puts it in the scratch dir): the current directory goes
on sys.path first, the way ``python -m pytest`` would put it there.

Exit codes: 0 a verdict (RECOMMEND or REJECT) was printed, 2 ABORT - a suite run failed
(with or without the cache), so there is no valid measurement to judge.
"""

import os
import statistics
import sys
import time
from functools import lru_cache


class SuiteFailed(Exception):
    """A test-suite run exited non-zero, so its timing measures nothing useful."""

    def __init__(self, rc, label):
        super().__init__(f"test suite failed {label} (pytest exit code {rc})")
        self.rc = rc


def _pytest_argv():
    """Build the pytest argv, only naming a test dir when one exists.

    If neither ``tests/`` nor ``test/`` is present, omit the path so pytest
    discovers tests itself (honouring any pyproject testpaths). No interpreter
    prefix: both runs call pytest.main() IN THIS PROCESS - see _run_suite."""
    argv = []
    testdir = next((d for d in ('tests', 'test') if os.path.isdir(d)), None)
    if testdir:
        argv.append(testdir)
    argv.append('-q')
    return argv


def _ensure_cwd_importable():
    """Put the project root (the cwd) on sys.path, as ``python -m pytest`` does.

    Run as ``python /elsewhere/profile_cache_x.py``, sys.path[0] is the script's own
    directory, so an uninstalled flat-layout project could not be imported at all."""
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)


def _run_suite(label, clock=time.perf_counter):
    """Run the test suite in THIS process and return the elapsed seconds.

    In-process is not a style choice. The cached run monkey-patches the target
    module, and a subprocess gets a fresh interpreter that never sees the patch:
    the cached function is then never called, cache_info() reports 0 hits and 0
    misses, the hit rate computes as 0, and the verdict is REJECT no matter how
    good the cache would have been.

    Raises SuiteFailed when pytest exits non-zero: a failing suite is not a timing."""
    import pytest
    start = clock()
    rc = int(pytest.main(_pytest_argv()))
    elapsed = clock() - start
    if rc != 0:
        raise SuiteFailed(rc, label)
    return elapsed

# Constants for cache validation
MIN_HIT_RATE_PERCENT = 20  # Minimum cache hit rate percentage to recommend caching
MIN_IMPROVEMENT_PERCENT = 5  # Minimum performance improvement percentage to recommend caching
CACHE_SIZE = 128  # Default LRU cache size
# Timed runs per arm. Under pure noise every cached run beats every uncached one with
# probability 1 / C(2*REPEATS, REPEATS): 1/252 at 5. Raise it for a very noisy suite; each
# repeat costs two suite runs.
REPEATS = 5
MIN_REPEATS = 3

# TODO: Update these
MODULE_NAME = "module.submodule"
FUNCTION_NAME = "function_to_cache"


def _rebind(old, new):
    """Point every module attribute bound to *old* at *new*; return the (module, name) pairs.

    Patching only MODULE_NAME misses every ``from module import function`` done before the
    patch - a test module keeps its own reference to the original, calls it, and the
    cache records 0 hits and 0 misses."""
    changed = []
    for module in list(sys.modules.values()):
        try:
            namespace = vars(module)
        except TypeError:
            continue
        for name, value in list(namespace.items()):
            if value is old:
                setattr(module, name, new)
                changed.append((module, name))
    return changed


def profile_with_cache(clock=time.perf_counter):
    """Profile test suite with caching applied."""
    import importlib
    _ensure_cwd_importable()
    module = importlib.import_module(MODULE_NAME)

    original_func = getattr(module, FUNCTION_NAME)
    cached_func = lru_cache(maxsize=CACHE_SIZE)(original_func)

    patched = _rebind(original_func, cached_func)
    try:
        # Run test suite in-process, so the patch above is the code under test
        elapsed = _run_suite("with the cache", clock)
    finally:
        for owner, name in patched:
            setattr(owner, name, original_func)

    cache_info = cached_func.cache_info()
    hit_rate = (cache_info.hits / (cache_info.hits + cache_info.misses) * 100
                if cache_info.hits + cache_info.misses > 0 else 0)

    return elapsed, cache_info, hit_rate

def profile_without_cache(clock=time.perf_counter):
    """Profile test suite without caching."""
    return _run_suite("without the cache", clock)

def assess(uncached, cached):
    """Compare the repeated timings of both arms; return (improvement %, separated).

    *improvement* compares the medians. *separated* is True only when the slowest cached run
    is still faster than the fastest uncached one: a median gap smaller than the spread of
    the runs is noise, whatever its size."""
    median_uncached = statistics.median(uncached)
    median_cached = statistics.median(cached)
    improvement = ((median_uncached - median_cached) / median_uncached * 100
                   if median_uncached > 0 else 0)
    return improvement, max(cached) < min(uncached)


def recommend(improvement, hit_rate, *, separated):
    """Return the RECOMMEND/REJECT verdict string for a cache experiment.

    *separated* is required: a verdict that forgot to ask whether the difference exceeds the
    run-to-run spread would recommend on noise again."""
    if hit_rate < MIN_HIT_RATE_PERCENT:
        return f"REJECT: Cache hit rate ({hit_rate:.1f}%) too low (minimum {MIN_HIT_RATE_PERCENT}%)"
    if improvement < MIN_IMPROVEMENT_PERCENT:
        return f"REJECT: Performance improvement ({improvement:.1f}%) too low (minimum {MIN_IMPROVEMENT_PERCENT}%)"
    if not separated:
        return (f"REJECT: Performance improvement ({improvement:.1f}%) is within run-to-run noise: "
                f"the cached and uncached runs overlap (raise REPEATS to measure more precisely)")
    return (f"RECOMMEND: Apply @lru_cache(maxsize={CACHE_SIZE})\n"
            f"  Expected speedup: {improvement:.1f}%\n"
            f"  Cache hit rate: {hit_rate:.1f}%")


def _timed_uncached(clock):
    elapsed = profile_without_cache(clock)
    print(f"  without cache: {elapsed:.3f}s")
    return elapsed


def _timed_cached(clock):
    elapsed, cache_info, hit_rate = profile_with_cache(clock)
    print(f"  with cache:    {elapsed:.3f}s")
    return elapsed, cache_info, hit_rate


def _measure(clock):
    """Warm up, then REPEATS rounds of both arms, alternating which arm goes first."""
    print("\nWarm-up run (imports, collection; not timed)...")
    _run_suite("in the warm-up run", clock)

    uncached, cached = [], []
    cache_info = hit_rate = None
    for round_no in range(REPEATS):
        print(f"\nRound {round_no + 1}/{REPEATS}")
        if round_no % 2 == 0:
            uncached.append(_timed_uncached(clock))
        # every cached run starts from an empty cache, as a fresh process would
        elapsed, cache_info, hit_rate = _timed_cached(clock)
        cached.append(elapsed)
        if round_no % 2 == 1:
            uncached.append(_timed_uncached(clock))
    return uncached, cached, cache_info, hit_rate


def _spread(times):
    return f"median {statistics.median(times):.3f}s, range {min(times):.3f}-{max(times):.3f}s"


def main(clock=time.perf_counter):
    """Run the before/after cache experiment and print the verdict; return the exit code.

    Kept under __main__ so the module is import-safe (no work at import time). *clock* is
    the timer seam, so the arithmetic can be tested with exact timings."""
    print(f"Profiling {MODULE_NAME}.{FUNCTION_NAME}")
    print("=" * 80)
    if REPEATS < MIN_REPEATS:
        print(f"ABORT: REPEATS is {REPEATS}; at least {MIN_REPEATS} runs per arm are needed to "
              "tell a difference from noise.")
        return 2
    _ensure_cwd_importable()

    try:
        uncached, cached, cache_info, hit_rate = _measure(clock)
    except SuiteFailed as exc:
        print("\n" + "=" * 80)
        print(f"ABORT: {exc}. No verdict: fix the suite (or the cache) and re-run.")
        return 2

    improvement, separated = assess(uncached, cached)

    print("\n" + "=" * 80)
    print(f"RESULTS ({REPEATS} interleaved runs per arm)")
    print("=" * 80)
    print(f"Uncached: {_spread(uncached)}")
    print(f"Cached: {_spread(cached)}")
    print(f"Improvement: {improvement:.1f}% (of the medians)")
    print(f"Arms separated: {'yes' if separated else 'no - the runs overlap'}")
    print("Cache statistics (one cached run; each starts with an empty cache):")
    print(f"Cache hits: {cache_info.hits}")
    print(f"Cache misses: {cache_info.misses}")
    print(f"Cache hit rate: {hit_rate:.1f}%")
    print(f"Cache size: {cache_info.currsize}/{cache_info.maxsize}")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print(recommend(improvement, hit_rate, separated=separated))
    return 0


if __name__ == "__main__":
    sys.exit(main())
