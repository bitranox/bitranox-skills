"""Growth tests for hook regexes that used to rescan one long run from every start.

`search`, `sub`, `split` and `finditer` retry a pattern at every position, so a pattern whose
start can sit anywhere inside a run (`[\\w.-]+` before a suffix, `^\\s*` after every newline)
costs N squared on a long run that never matches. Each case times the real compiled pattern on
the run that used to be quadratic, at N and at 8N: a linear pattern grows about 8x, the old
shapes grew 50x to 65x. The cases where the rewrite changes HOW a pattern matches pin the
behaviour the callers rely on. ASCII only.
"""
import importlib.util
import os
import pathlib
import time

import pytest

import block_write_after_sibling_cd as BW
import compact_resume as CR
import git_footgun_guard as GF
import harness_checks as HC
import jig_repetition_nudge as JR
import open_work as OW
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


_CASES = [
    ("toolbox-nudge pushcheck: blank lines", lambda t: TN._PUSHCHECK_RX.search(t), "\n"),
    ("toolbox-nudge pushcheck: subshell lines", lambda t: TN._PUSHCHECK_RX.search(t), "(\n"),
    ("toolbox-nudge pushcheck: keyword lines", lambda t: TN._PUSHCHECK_RX.search(t), "then\n"),
    ("toolbox-nudge pushcheck: assignment lines", lambda t: TN._PUSHCHECK_RX.search(t), "A=1\n"),
    ("toolbox-nudge pushcheck: env lines", lambda t: TN._PUSHCHECK_RX.search(t), "env\n-u\nX\n"),
    ("block-write separator: blanks", lambda t: BW._separator(t), " "),
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
    ("repo-gate H1 parenthetical", lambda t: RG._H1_PAREN_RX.sub(" (<per-repo>)", t), " "),
    ("self_improve run opener: equals", lambda t: SIS._RUN_OPENS.search(t), "="),
    ("self_improve run opener: dashes", lambda t: SIS._RUN_OPENS.search(t), "-"),
    ("subagent-model-gate product name", lambda t: SM._PRODUCT_RE.sub("x", t), "0"),
]


@pytest.mark.parametrize("call, unit", [c[1:] for c in _CASES], ids=[c[0] for c in _CASES])
def test_a_long_run_costs_linear_time(call, unit):
    assert _growth(call, unit) < _MAX_GROWTH


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
