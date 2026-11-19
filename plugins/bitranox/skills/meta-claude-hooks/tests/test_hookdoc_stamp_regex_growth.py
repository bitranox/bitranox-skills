"""Growth tests for the hookdoc_stamp CLI version regex. ASCII only.

`search`, `sub`, `split` and `findall` retry a pattern at every position, so a pattern whose start
can sit anywhere inside a run costs N squared (or worse) on a long run that never matches. Each
case times the real compiled pattern on that run at N and at 8N: linear grows about 8x, the old
shapes grew 50x and more. The behaviour cases pin what the callers read from a match, measured on
the old patterns before the rewrite.
"""
import os
import time

import pytest

import hookdoc_stamp as H

# Linear is about 8x and the quadratic shapes were 50x and more; 24 leaves room for timer noise
# without letting a quadratic pattern through.
_MAX_GROWTH = 24
# process_time ticks coarsely on Windows, so each timed arm runs long enough to dwarf one tick.
_MIN_ARM_SECONDS = 0.06 if os.name == "nt" else 0.015


def _best_of_three(call, text, reps):
    best = float("inf")
    for _ in range(3):
        start = time.process_time()
        for _ in range(reps):
            call(text)
        best = min(best, time.process_time() - start)
    return best


def _growth(call, unit, length=2000):
    """Time `call` on `unit` repeated to about `length` characters and to 8 times that."""
    small = unit * max(1, length // len(unit))
    big = small * 8
    reps = 1
    while _best_of_three(call, small, reps) < _MIN_ARM_SECONDS and reps < 1 << 20:
        reps *= 2
    return _best_of_three(call, big, reps) / max(_best_of_three(call, small, reps), 1e-9)


def test_a_long_digit_run_costs_linear_time():
    assert _growth(lambda t: H.CLI_VERSION_RX.search(t), "0") < _MAX_GROWTH


@pytest.mark.parametrize("text, version", [
    ("Claude Code 2.1.300 (x)", "2.1.300"), ("12.34.56.78", "12.34.56"), ("v1.2", None),
])
def test_cli_version_reads_the_same_version(text, version):
    match = H.CLI_VERSION_RX.search(text)
    assert (match.group(1) if match else None) == version
