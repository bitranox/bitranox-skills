"""Growth tests for the ci_triage and gate regexes. ASCII only.

`search`, `sub`, `split` and `findall` retry a pattern at every position, so a pattern whose start
can sit anywhere inside a run costs N squared (or worse) on a long run that never matches. Each
case times the real compiled pattern on that run at N and at 8N: linear grows about 8x, the old
shapes grew 50x and more. The behaviour cases pin what the callers read from a match, measured on
the old patterns before the rewrite.
"""
import os
import time

import pytest

import ci_triage as T
import gate as G

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


@pytest.mark.parametrize("call, unit", [
    (lambda t: T._PATH_OR_FLAG.sub("", t), "0"),
    (lambda t: T._PATH_OR_FLAG.sub("", t), "a/"),
    (lambda t: G._CARGO_RUNNING.findall(t), "\n"),
], ids=["ci_triage path-or-flag: one name", "ci_triage path-or-flag: components",
        "gate cargo running: blank lines"])
def test_a_long_run_costs_linear_time(call, unit):
    assert _growth(call, unit) < _MAX_GROWTH


@pytest.mark.parametrize("line, scrubbed", [
    ("--foo.bar/x y", "/ y"),                 # a flag running into a path loses both parts
    ("see src/errors/mod.rs: error", "see //: error"),
    ("-Wno-error=foo a/b", " /"),
    ("x\\y.z/w --fail-under=80", "\\/ "),
    ("--a.b.c d.e/f", ".b.c /"),              # no slash after the dotted run: it stays
    ("..\\..\\x", "\\\\"),
])
def test_path_or_flag_removes_what_it_removed_before(line, scrubbed):
    assert T._PATH_OR_FLAG.sub("", line) == scrubbed


def test_cargo_running_counts_a_run_after_blank_lines():
    text = "\n\n  running 3 tests\nrunning 1 test\n  running 0 tests"
    assert G._CARGO_RUNNING.findall(text) == ["3", "1", "0"]
