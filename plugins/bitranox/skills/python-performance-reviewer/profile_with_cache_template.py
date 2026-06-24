"""
Template for profiling a specific function with caching.

Usage:
  1. Copy this template to profile_cache_FUNCTION_NAME.py
  2. Update MODULE_NAME and FUNCTION_NAME
  3. Run: python profile_cache_FUNCTION_NAME.py
"""

import os
import sys
import time
import subprocess
from functools import lru_cache


def _pytest_argv():
    """Build the pytest argv, only naming a test dir when one exists.

    If neither ``tests/`` nor ``test/`` is present, omit the path so pytest
    discovers tests itself (honouring any pyproject testpaths)."""
    argv = [sys.executable, '-m', 'pytest']
    testdir = next((d for d in ('tests', 'test') if os.path.isdir(d)), None)
    if testdir:
        argv.append(testdir)
    argv.append('-v')
    return argv

# Constants for cache validation
MIN_HIT_RATE_PERCENT = 20  # Minimum cache hit rate percentage to recommend caching
MIN_IMPROVEMENT_PERCENT = 5  # Minimum performance improvement percentage to recommend caching
CACHE_SIZE = 128  # Default LRU cache size

# TODO: Update these
MODULE_NAME = "module.submodule"
FUNCTION_NAME = "function_to_cache"

def profile_with_cache():
    """Profile test suite with caching applied."""
    # Import and patch the function with cache
    import importlib
    module = importlib.import_module(MODULE_NAME)

    # Get original function
    original_func = getattr(module, FUNCTION_NAME)

    # Create cached version
    cached_func = lru_cache(maxsize=CACHE_SIZE)(original_func)

    # Monkey-patch with cached version
    setattr(module, FUNCTION_NAME, cached_func)

    # Run test suite
    start = time.perf_counter()
    result = subprocess.run(_pytest_argv(), capture_output=True)
    elapsed = time.perf_counter() - start

    # Get cache statistics
    cache_info = cached_func.cache_info()
    hit_rate = (cache_info.hits / (cache_info.hits + cache_info.misses) * 100
                if cache_info.hits + cache_info.misses > 0 else 0)

    return elapsed, cache_info, hit_rate

def profile_without_cache():
    """Profile test suite without caching."""
    start = time.perf_counter()
    result = subprocess.run(_pytest_argv(), capture_output=True)
    elapsed = time.perf_counter() - start
    return elapsed

def recommend(improvement, hit_rate):
    """Return the RECOMMEND/REJECT verdict string for a cache experiment."""
    if hit_rate < MIN_HIT_RATE_PERCENT:
        return f"REJECT: Cache hit rate ({hit_rate:.1f}%) too low (minimum {MIN_HIT_RATE_PERCENT}%)"
    if improvement < MIN_IMPROVEMENT_PERCENT:
        return f"REJECT: Performance improvement ({improvement:.1f}%) too low (minimum {MIN_IMPROVEMENT_PERCENT}%)"
    return (f"RECOMMEND: Apply @lru_cache(maxsize={CACHE_SIZE})\n"
            f"  Expected speedup: {improvement:.1f}%\n"
            f"  Cache hit rate: {hit_rate:.1f}%")


def main():
    """Run the before/after cache experiment and print the verdict.

    Kept under __main__ so the module is import-safe (no work at import time)."""
    print(f"Profiling {MODULE_NAME}.{FUNCTION_NAME}")
    print("=" * 80)

    print("\nRunning WITHOUT cache...")
    time_uncached = profile_without_cache()
    print(f"Time: {time_uncached:.2f}s")

    print("\nRunning WITH cache...")
    time_cached, cache_info, hit_rate = profile_with_cache()
    print(f"Time: {time_cached:.2f}s")

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


if __name__ == "__main__":
    main()
