"""
Template for profiling a specific function with caching.

Usage:
  1. Copy this template to profile_cache_FUNCTION_NAME.py
  2. Update MODULE_NAME and FUNCTION_NAME
  3. Run it FROM THE PROJECT ROOT: python profile_cache_FUNCTION_NAME.py

What it does: one untimed warm-up run of the test suite (imports, collection, first-run
caches), then a timed run WITHOUT the cache, then a timed run WITH the function wrapped in
lru_cache - so the comparison is warm against warm. The copy may live anywhere (SKILL.md
puts it in the scratch dir): the current directory goes on sys.path first, the way
``python -m pytest`` would put it there.

Exit codes: 0 a verdict (RECOMMEND or REJECT) was printed, 2 ABORT - a suite run failed
(with or without the cache), so there is no valid measurement to judge.
"""

import os
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

def recommend(improvement, hit_rate):
    """Return the RECOMMEND/REJECT verdict string for a cache experiment."""
    if hit_rate < MIN_HIT_RATE_PERCENT:
        return f"REJECT: Cache hit rate ({hit_rate:.1f}%) too low (minimum {MIN_HIT_RATE_PERCENT}%)"
    if improvement < MIN_IMPROVEMENT_PERCENT:
        return f"REJECT: Performance improvement ({improvement:.1f}%) too low (minimum {MIN_IMPROVEMENT_PERCENT}%)"
    return (f"RECOMMEND: Apply @lru_cache(maxsize={CACHE_SIZE})\n"
            f"  Expected speedup: {improvement:.1f}%\n"
            f"  Cache hit rate: {hit_rate:.1f}%")


def _measure(clock):
    print("\nWarm-up run (imports, collection; not timed)...")
    _run_suite("in the warm-up run", clock)

    print("\nRunning WITHOUT cache...")
    time_uncached = profile_without_cache(clock)
    print(f"Time: {time_uncached:.2f}s")

    print("\nRunning WITH cache...")
    time_cached, cache_info, hit_rate = profile_with_cache(clock)
    print(f"Time: {time_cached:.2f}s")
    return time_uncached, time_cached, cache_info, hit_rate


def main(clock=time.perf_counter):
    """Run the before/after cache experiment and print the verdict; return the exit code.

    Kept under __main__ so the module is import-safe (no work at import time). *clock* is
    the timer seam, so the arithmetic can be tested with exact timings."""
    print(f"Profiling {MODULE_NAME}.{FUNCTION_NAME}")
    print("=" * 80)
    _ensure_cwd_importable()

    try:
        time_uncached, time_cached, cache_info, hit_rate = _measure(clock)
    except SuiteFailed as exc:
        print("\n" + "=" * 80)
        print(f"ABORT: {exc}. No verdict: fix the suite (or the cache) and re-run.")
        return 2

    improvement = ((time_uncached - time_cached) / time_uncached * 100) if time_uncached > 0 else 0

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Uncached: {time_uncached:.2f}s")
    print(f"Cached: {time_cached:.2f}s")
    print(f"Improvement: {improvement:.1f}%")
    print(f"Cache hits: {cache_info.hits}")
    print(f"Cache misses: {cache_info.misses}")
    print(f"Cache hit rate: {hit_rate:.1f}%")
    print(f"Cache size: {cache_info.currsize}/{cache_info.maxsize}")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print(recommend(improvement, hit_rate))
    return 0


if __name__ == "__main__":
    sys.exit(main())
