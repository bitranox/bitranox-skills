"""Growth tests for hook regexes that used to rescan one long run from every start.

`search`, `sub`, `split` and `finditer` retry a pattern at every position, so a pattern whose
start can sit anywhere inside a run (`[\\w.-]+` before a suffix, `^\\s*` after every newline)
costs N squared on a long run that never matches. Each case times the real compiled pattern on
the run that used to be quadratic, at N and at 8N: a linear pattern grows about 8x, the old
shapes grew 50x to 65x. The cases where the rewrite changes HOW a pattern matches pin the
behaviour the callers rely on. ASCII only.
"""
import functools
import importlib.util
import os
import pathlib
import sys

import pytest

if sys.platform != "win32":
    import resource

import block_or_echo_verdict as BOEV
import block_write_after_sibling_cd as BW
import compact_resume as CR
import git_footgun_guard as GF
import harness_checks as HC
import jig_repetition_nudge as JR
import open_work as OW
import prompt_text as PT
import repo_gate as RG
import self_improve_signals as SIS
import subagent_model_gate as SM
import toolbox_nudge as TN

_MM_PATH = pathlib.Path(__file__).resolve().parent.parent / "missing-mechanism-nudge.py"
_MM_SPEC = importlib.util.spec_from_file_location("missing_mechanism_nudge_growth", _MM_PATH)
MM = importlib.util.module_from_spec(_MM_SPEC)
_MM_SPEC.loader.exec_module(MM)

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


_CASES = [
    ("toolbox-nudge pushcheck: blank lines", lambda t: TN._PUSHCHECK_RX.search(t), "\n"),
    ("toolbox-nudge pushcheck: subshell lines", lambda t: TN._PUSHCHECK_RX.search(t), "(\n"),
    ("toolbox-nudge pushcheck: keyword lines", lambda t: TN._PUSHCHECK_RX.search(t), "then\n"),
    ("toolbox-nudge pushcheck: assignment lines", lambda t: TN._PUSHCHECK_RX.search(t), "A=1\n"),
    ("toolbox-nudge pushcheck: env lines", lambda t: TN._PUSHCHECK_RX.search(t), "env\n-u\nX\n"),
    ("block-write separator: blanks", lambda t: BW._separator(t), " "),
    # Every `;`, `&`, `|`, `(` and `{` is a start, and a newline after a launcher ends it.
    *[(f"block-or-echo-verdict: {unit!r} run", lambda t: BOEV.refused_shape(t + " || echo clean"),
       unit) for unit in ("&", "(", ";", "{", "|", "sudo\n", "nice\n", "A=(", "/&")],
    # A program word that repeats inside one element is a start at each repeat; with no verdict
    # at the end, each start read the rest of the element (52x to 65x for 8x the input).
    *[(f"block-or-echo-verdict: {unit!r} run, failing",
       lambda t: BOEV.refused_shape(t + " || true"), unit)
      for unit in ("grep (", "grep {", "grep then ", "grep do ", "git grep (", "diff (",
                   "sudo grep (", "(grep ", "grep 2>&", "grep x 2>&1 ")],
    ("compact-resume checkpoint path", lambda t: list(CR._BASH_PATH.finditer(t)), "0"),
    ("git-footgun upstream mark", lambda t: GF._UPSTREAM_MARK.search(t), "0"),
    ("harness_checks non-zero exit", lambda t: HC._NONZERO_EXIT_RX.search(t), "\n"),
    ("harness_checks script name", lambda t: list(HC._SCRIPT_NAME_RX.finditer(t)), "0"),
    ("harness_checks script path: one name", lambda t: HC._SCRIPT_PATH_RX.search(t), "a"),
    ("harness_checks script path: components", lambda t: HC._SCRIPT_PATH_RX.search(t), "a/"),
    ("jig-repetition comment strip", lambda t: JR._COMMENT.sub("", t), "\n"),
    ("jig-repetition trailing digits", lambda t: JR._TRAILING_DIGITS.sub("", t + " "), "0"),
    ("missing-mechanism evidence: digits", lambda t: MM._EVIDENCE.search(t), "0-"),
    ("missing-mechanism evidence: dashes", lambda t: MM._EVIDENCE.search(t), "-a"),
    ("open_work field split", lambda t: OW._FIELD_RX.split(t), " "),
    # One whitespace-free token, so the run reaches the path test whole; `x` ends the suffix.
    *[(f"prompt_text line suffix: {unit!r} run", lambda t: PT.prose(t + "x"), unit)
      for unit in (":0", ":0-0", ":0-1")],
    ("repo-gate H1 parenthetical", lambda t: RG._H1_PAREN_RX.sub(" (<per-repo>)", t), " "),
    ("self_improve run opener: equals", lambda t: SIS._RUN_OPENS.search(t), "="),
    ("self_improve run opener: dashes", lambda t: SIS._RUN_OPENS.search(t), "-"),
    ("subagent-model-gate product name", lambda t: SM._PRODUCT_RE.sub("x", t), "0"),
]


@pytest.mark.parametrize("call, unit", [c[1:] for c in _CASES], ids=[c[0] for c in _CASES])
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


# ---- behaviour the rewrites must keep ----------------------------------------------------------
@pytest.mark.parametrize("command", [
    "echo hi\n\n\n   git push",          # the line start after the blank lines anchors it
    "(\n(\ngit push",                    # a subshell opener on an earlier line
    "if\ngit push",                      # a keyword on the line before
    "env -u\nX git push",                # env's own option may still wrap
    "cd x &&\n\n  git -C r push",
])
def test_pushcheck_still_finds_a_push_after_line_breaks(command):
    assert TN._PUSHCHECK_RX.search(command)


@pytest.mark.parametrize("command", ["echo if git push", "\n\n\necho git push", "(\n(\n"])
def test_pushcheck_still_ignores_a_push_in_prose(command):
    assert TN._PUSHCHECK_RX.search(command) is None


@pytest.mark.parametrize("gap, expected", [
    (" && ", "&&"), ("&&&", "&&"), (" ||\n", "||"), (";", ";"), (" &", "&"), ("|", "|"),
    ("&|", "|"), ("|&", "&"), (" \n  ", "\n"), ("x \n", "\n"), (";\n", ";"), ("", None),
    ("   ", None), ("x", None), ("&& x", None),
])
def test_separator_names_the_token_a_gap_ends_with(gap, expected):
    assert BW._separator(gap) == expected


@pytest.mark.parametrize("token, ref", [
    ("HEAD...@{u}", "HEAD..."), ("main@{UPSTREAM}", "main"), ("@{u}", ""), ("a/b+c@{u}x", "a/b+c"),
])
def test_upstream_mark_captures_the_whole_ref(token, ref):
    assert GF._UPSTREAM_MARK.search(token).group(1) == ref


@pytest.mark.parametrize("text, names", [
    ("see /usr/lib/x/b.py", True), ("use a/b.sh now", True), ("a//b.py", False), ("b.py", False),
])
def test_script_path_needs_a_component_before_the_name(text, names):
    assert bool(HC._SCRIPT_PATH_RX.search(text)) is names


@pytest.mark.parametrize("text, found", [
    ("-/foo.py", True), ("./x.json", True), ("--.py", False), ("x.pyc", False), ("see line 12", True),
])
def test_evidence_keeps_a_path_after_punctuation(text, found):
    assert bool(MM._EVIDENCE.search(text)) is found


def test_comment_strip_leaves_the_same_tokens_around_blank_lines():
    text = "alpha beta\n\n\n   # gone comment\ngamma\n\n// also gone\ndelta"
    assert JR._TOKEN.findall(JR._COMMENT.sub("", text)) == ["alpha", "beta", "gamma", "delta"]
