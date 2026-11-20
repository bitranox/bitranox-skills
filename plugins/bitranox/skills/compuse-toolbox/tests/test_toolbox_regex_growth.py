"""Growth tests for the ci_triage and gate regexes. ASCII only.

`search`, `sub`, `split` and `findall` retry a pattern at every position, so a pattern whose start
can sit anywhere inside a run costs N squared (or worse) on a long run that never matches. Each
case times the real compiled pattern on that run at N and at 8N: linear grows about 8x, the old
shapes grew 50x and more. The behaviour cases pin what the callers read from a match, measured on
the old patterns before the rewrite.
"""
import functools
import os
import sys

import pytest

if sys.platform != "win32":
    import resource

import ci_triage as T
import gate as G
import procsig as P
import winpytest as W

# Linear is about 8x and the quadratic shapes were 50x and more; 24 leaves room for timer noise
# without letting a quadratic pattern through.
_MAX_GROWTH = 24
_GROWTH = 8          # the large arm's input is this many times the small arm's
_ROUNDS = 3
_MAX_REPS = 1 << 16


# USER CPU time (process-test-design, growth-ratio rule 1): process_time adds kernel time, which
# the large arm's fresh pages inflate, and wall time charges this process for a busy machine.
# Windows has no getrusage; every CPU-time clock there steps 15.625 ms, so _min_window() makes
# each window many steps long.
if sys.platform == "win32":
    def _user_cpu():
        return os.times().user
else:
    def _user_cpu():
        return resource.getrusage(resource.RUSAGE_SELF).ru_utime


_BUSY_CHUNK = 2000  # loop iterations between two clock reads: user work, not kernel work


def _clock_step(clock):
    """The smallest advance *clock* reports over a busy loop, best of three."""
    steps = []
    for _ in range(3):
        start = now = clock()
        spin = 0
        while now == start:
            for _ in range(_BUSY_CHUNK):
                spin += 1
            now = clock()
        steps.append(now - start)
    return min(steps)


# 10 clock steps keep one window within 10% of its length.
_STEPS_PER_WINDOW = 10
_MIN_WINDOW_FLOOR = 0.02  # seconds, where the clock is fine-grained


@functools.cache
def _min_window():
    """Seconds each timed window must last on this machine's clock."""
    return max(_MIN_WINDOW_FLOOR, _STEPS_PER_WINDOW * _clock_step(_user_cpu))


# A case can do constant work on its run, and then both arms finish below the clock's step and
# their ratio is noise. A quadratic scan of the large arm (16000 characters) runs far longer than
# this, so a large arm under it counts as linear without a ratio.
_TOO_FAST_TO_BE_QUADRATIC = 0.005  # seconds per call


def _arm_times(call, small, big, *, clock=_user_cpu, min_window=None):
    """Seconds per call on `small` and on `big`, each the best of 3 EQUAL windows.

    The small arm is timed as 8 calls back to back (growth-ratio rule 2), so a fast moment of the
    machine cannot fall wholly inside it, and both windows repeat until they last _min_window().
    *clock* and *min_window* are the seams a virtual-clock test drives.
    """
    floor = _min_window() if min_window is None else min_window

    def window(text, calls):
        start = clock()
        for _ in range(calls):
            call(text)
        return clock() - start

    reps = 1
    while window(small, _GROWTH * reps) < floor and reps < _MAX_REPS:
        reps *= 2
    small_calls = _GROWTH * reps
    small_time = min(window(small, small_calls) for _ in range(_ROUNDS)) / small_calls
    big_time = min(window(big, reps) for _ in range(_ROUNDS)) / reps
    return small_time, big_time


def _is_linear(call, unit, length=2000, tail=""):
    """True when `call` on `unit` repeated to 8 times about `length` characters, then `tail`,
    costs under _MAX_GROWTH times what it costs on the `length` run."""
    run = unit * max(1, length // len(unit))
    small, big = _arm_times(call, run + tail, run * _GROWTH + tail)
    return big < _TOO_FAST_TO_BE_QUADRATIC or big < _MAX_GROWTH * small


@pytest.mark.parametrize("call, unit", [
    (lambda t: T._PATH_OR_FLAG.sub("", t), "0"),
    (lambda t: T._PATH_OR_FLAG.sub("", t), "a/"),
    (lambda t: G._CARGO_RUNNING.findall(t), "\n"),
    (lambda t: P._looks_like_a_shell_name(t + "x"), "0"),
    (lambda t: P._looks_like_a_shell_name(t + "x"), "0."),
    (lambda t: W.pytest_summary(t), "\n"),
    (lambda t: W.pytest_summary(t), " \n"),
], ids=["ci_triage path-or-flag: one name", "ci_triage path-or-flag: components",
        "gate cargo running: blank lines", "procsig name suffix: digits",
        "procsig name suffix: dotted digits", "winpytest summary: blank lines",
        "winpytest summary: lines of blanks"])
def test_a_long_run_costs_linear_time(call, unit):
    assert _is_linear(call, unit)


class _VirtualCPU:
    """A user-time clock that advances with work done: 1 us per character a call reads, and ten
    times faster over a stretch of *fast_chars* characters starting *fast_from* characters in."""

    def __init__(self, fast_from, fast_chars):
        self.now = 0.0
        self.work = 0
        self.fast_from = fast_from
        self.fast_to = fast_from + fast_chars

    def clock(self):
        return self.now

    def call(self, text):
        lo, hi = self.work, self.work + len(text)
        fast = max(0, min(hi, self.fast_to) - max(lo, self.fast_from))
        self.now += (len(text) - fast) * 1e-6 + fast * 1e-7
        self.work = hi


@pytest.mark.parametrize("offset", range(120))
def test_a_fast_moment_does_not_make_a_linear_call_read_superlinear(offset):
    # A fast stretch one small call long, placed at small-call boundaries across the whole run:
    # timing the small arm as one short pass let it fall wholly inside that pass.
    n = 2000
    cpu = _VirtualCPU(fast_from=offset * n, fast_chars=n)
    small, big = _arm_times(cpu.call, "a" * n, "a" * n * _GROWTH, clock=cpu.clock, min_window=0.02)
    assert big < _MAX_GROWTH * small


def test_clock_step_reads_a_ticking_clock_as_one_tick():
    tick = 0.015625
    calls = [0]

    def ticking():
        calls[0] += 1
        return (calls[0] // 16) * tick

    assert _clock_step(ticking) == tick


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
