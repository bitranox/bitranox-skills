#!/usr/bin/env bash
# Before/after performance comparison using git history.
# Stashes current changes, checks out previous commit, benchmarks, returns.

set -euo pipefail

# Portable millisecond clock. GNU `date +%s%N` is not available on macOS/BSD
# (the %N field is dropped), so derive the time from python3, which is already
# required here (it runs pytest).
now_ms() { python3 -c 'import time; print(int(time.time() * 1000))'; }

# Get current commit
current_commit=$(git rev-parse HEAD)

# Stash current changes if any
git stash save "temp_for_perf_comparison" || true

# Go back to previous commit
git checkout HEAD~1

# Run tests and time them
echo "Running tests on BEFORE version..."
time_before=$(now_ms)
pytest tests/ -v >/dev/null 2>&1 || true
time_after=$(now_ms)
duration_before=$((time_after - time_before))

# Return to current commit
git checkout "$current_commit"
git stash pop || true

# Run tests on current version
echo "Running tests on AFTER version..."
time_before=$(now_ms)
pytest tests/ -v >/dev/null 2>&1 || true
time_after=$(now_ms)
duration_after=$((time_after - time_before))

# Calculate improvement
if [ "$duration_before" -gt 0 ]; then
    improvement=$(((duration_before - duration_after) * 100 / duration_before))
    echo "Before: ${duration_before}ms"
    echo "After: ${duration_after}ms"
    echo "Improvement: ${improvement}%"

    if [ "$improvement" -lt 5 ]; then
        echo "WARNING: Performance improvement <5% - may not be significant"
    fi
else
    echo "Could not measure performance"
fi
