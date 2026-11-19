"""find_uncompiled_regex: which call sites are flagged, source decoding, the quadratic-start
shapes, and the CLI contract."""
import re
import sys
import time

import pytest

import find_uncompiled_regex as fur

SCRIPT = "find_uncompiled_regex.py"
BODY = "import re\n\ndef f(s):\n    return re.match(\"d\", s)\n"


def _lines(tmp_path, code):
    p = tmp_path / "m.py"
    p.write_text(code, encoding="utf-8")
    return sorted(x["line"] for x in fur.find_uncompiled_regex(str(p)))


# --- which calls count ------------------------------------------------------------------

def test_aliases_from_imports_and_pattern_keyword_are_flagged(tmp_path):
    code = (
        "import re as regex\n"                 # 1
        "from re import search\n"              # 2
        "from re import sub as s\n"            # 3
        "import re\n"                          # 4
        "def f(x):\n"                          # 5
        "    regex.match(\"a\", x)\n"          # 6
        "    search(\"b\", x)\n"               # 7
        "    re.match(pattern=\"c\", string=x)\n"  # 8
        "    re.match(\"d\", x)\n"             # 9
        "    s(\"e\", \"\", x)\n"              # 10
        "    other.match(\"f\", x)\n"          # 11: not the re module
        "    match(\"g\", x)\n"                # 12: bare name never imported from re
    )
    assert _lines(tmp_path, code) == [6, 7, 8, 9, 10]


def test_module_level_one_shot_call_is_not_flagged(tmp_path):
    code = (
        "import re\n"
        "X = re.sub(\"a\", \"b\", \"abc\")\n"  # 2: runs once at import
        "class C:\n"
        "    Y = re.match(\"c\", \"c\")\n"     # 4: class body, runs once
        "def f(s):\n"
        "    return re.sub(\"a\", \"b\", s)\n"  # 6: every call
        "async def g(s):\n"
        "    return re.search(\"a\", s)\n"     # 8: every call
        "key = lambda s: re.match(\"a\", s)\n"  # 9: a function body too
    )
    assert _lines(tmp_path, code) == [6, 8, 9]


def test_defaults_decorators_and_annotations_run_where_the_def_runs(tmp_path):
    code = (
        "import re\n"                                              # 1
        "@register(re.sub(\"a\", \"b\", \"abc\"))\n"               # 2: decorator, runs once
        "def f(s, m=re.match(\"a\", \"a\"), *, k=re.search(\"b\", \"b\")"
        ") -> re.split(\"c\", \"c\"):\n"                           # 3: defaults, annotation: once
        "    return re.match(\"d\", s)\n"                          # 4: every call
        "key = lambda s, d=re.findall(\"e\", \"e\"): re.match(\"f\", s)\n"  # 5: body only
        "def outer(s):\n"                                          # 6
        "    def inner(x=re.match(\"g\", s)):\n"                   # 7: default, once per outer call
        "        return x\n"
        "    return inner\n"
    )
    assert _lines(tmp_path, code) == [4, 5, 7]
    p = tmp_path / "m.py"
    calls = sorted((f["line"], f["call"]) for f in fur.find_uncompiled_regex(str(p)))
    assert calls == [(4, "re.match('d', ...)"), (5, "re.match('f', ...)"),
                     (7, "re.match('g', ...)")]


def test_fstring_pattern_is_reported_as_dynamic(tmp_path):
    p = tmp_path / "m.py"
    p.write_text("import re\ndef f(s, n):\n    return re.match(f\"a{n}\", s)\n", encoding="utf-8")
    (finding,) = fur.find_uncompiled_regex(str(p))
    assert finding["call"] == "re.match(<f-string>, ...)"
    assert "Dynamic pattern" in finding["suggestion"]


# --- decoding ---------------------------------------------------------------------------

def test_utf8_bom_file_is_scanned(tmp_path):
    p = tmp_path / "bom.py"
    p.write_bytes(b"\xef\xbb\xbf" + BODY.encode())
    assert len(fur.find_uncompiled_regex(str(p))) == 1


def test_pep263_latin1_file_is_scanned(tmp_path):
    p = tmp_path / "latin.py"
    p.write_bytes(b"# -*- coding: latin-1 -*-\n# caf\xe9\n" + BODY.encode())
    assert len(fur.find_uncompiled_regex(str(p))) == 1


def test_unparseable_file_raises_instead_of_returning_empty(tmp_path):
    p = tmp_path / "bad.py"
    p.write_text("def (oops:\n", encoding="utf-8")
    with pytest.raises(SyntaxError):
        fur.find_uncompiled_regex(str(p))


# --- CLI --------------------------------------------------------------------------------

def test_cli_reports_and_exits_0(tmp_path, run_script):
    p = tmp_path / "good.py"
    p.write_text(BODY, encoding="utf-8")
    r = run_script(SCRIPT, str(p))
    assert r.returncode == 0, r.stderr
    assert b"Found 1 uncompiled regex calls" in r.stdout
    assert b"good.py:4 - re.match('d', ...)" in r.stdout


def test_cli_unparseable_file_exits_2_and_still_prints_the_report(tmp_path, run_script):
    good = tmp_path / "good.py"
    good.write_text(BODY, encoding="utf-8")
    bad = tmp_path / "bad.py"
    bad.write_text("def (oops:\n", encoding="utf-8")
    r = run_script(SCRIPT, str(bad), str(good))
    assert r.returncode == 2
    assert b"ERROR" in r.stderr and b"bad.py" in r.stderr
    assert b"Found 1 uncompiled regex calls" in r.stdout


def test_cli_missing_path_exits_2_and_names_it(tmp_path, run_script):
    r = run_script(SCRIPT, str(tmp_path / "does_not_exist.py"))
    assert r.returncode == 2
    assert b"not found" in r.stderr and b"does_not_exist.py" in r.stderr


def test_cli_no_arguments_prints_usage_and_exits_2(run_script):
    r = run_script(SCRIPT)
    assert r.returncode == 2 and b"usage" in r.stderr.lower()


def test_cli_help_exits_0(run_script):
    r = run_script(SCRIPT, "--help")
    assert r.returncode == 0 and b"usage" in r.stdout.lower() and b"Found" not in r.stdout


def test_cli_non_ansi_path_under_cp1252_stdout_is_written_as_utf8(tmp_path, run_script, clean_env):
    d = tmp_path / "proj_\u7530\u4e2d"
    d.mkdir()
    p = d / "good.py"
    p.write_text(BODY, encoding="utf-8")
    r = run_script(SCRIPT, str(p), env=clean_env(PYTHONIOENCODING="cp1252"))
    assert r.returncode == 0, r.stderr
    assert "proj_\u7530\u4e2d" in r.stdout.decode("utf-8")


# --- quadratic starts: the two shapes Step 4b names ------------------------------------------
# Each positive is proved quadratic by timing and each negative (the anchored fix) linear, so the
# detector's verdict is checked against the behaviour it claims rather than against itself.

QUADRATIC_FLOOR = 24.0  # growth at 8x the input: quadratic is about 64x, linear about 8x
LINEAR_CEILING = 16.0   # between the two, with room for a loaded machine

CLASS_RUN = r"[\w./-]+\.(?:py|sh)\b"
CLASS_RUN_FIXED = r"(?<![\w./-])[\w./-]+\.(?:py|sh)\b"
NEWLINE_START = r"(?<=[;&|\n])\s*grep"
NEWLINE_START_FIXED = r"(?<=[;&|\n])[^\S\n]*grep"

# CPU time, not wall time: on a machine running other suites, wall time charges this process for
# time it spent waiting for a core (measured: ratios of 18x for a 64x pattern at a load of 30 on
# 16 cores). Windows reports process CPU time in 15.6 ms ticks, too coarse for the small arm, so
# it keeps the wall clock; its CI runners are not shared.
_CLOCK = time.perf_counter if sys.platform == "win32" else time.process_time


# A pattern can do constant work on the test text (r"^\s+x" fails at the first character), and
# then both arms finish below the clock's resolution: macOS process_time read 0.0 for the small
# arm and the ratio divided by zero, and on Linux the ratio of two sub-microsecond readings is
# noise. A large arm under this bound cannot be quadratic - a quadratic match over the large
# arm's 8 * 50000 units runs for minutes - so such a pattern counts as linear without a ratio.
TOO_FAST_TO_BE_QUADRATIC = 0.005  # seconds


def _arm_times(pattern, unit, n, tail=""):
    """finditer time over unit * n + tail and over unit * 8n + tail, each the best of 3 runs."""
    compiled = re.compile(pattern)

    def best(text):
        times = []
        for _ in range(3):
            start = _CLOCK()
            list(compiled.finditer(text))
            times.append(_CLOCK() - start)
        return min(times)

    return best(unit * n + tail), best(unit * 8 * n + tail)


def _is_quadratic(pattern, unit, n, tail=""):
    small, big = _arm_times(pattern, unit, n, tail)
    return small > 0 and big / small > QUADRATIC_FLOOR


def _is_linear(pattern, unit, n, tail=""):
    small, big = _arm_times(pattern, unit, n, tail)
    return big < TOO_FAST_TO_BE_QUADRATIC or big < LINEAR_CEILING * small


def test_class_run_before_suffix_is_flagged_and_is_quadratic():
    verdict = fur.quadratic_verdict(CLASS_RUN)
    assert verdict is not None and verdict.shape == "class-run-before-suffix"
    assert "'a' * N (end of text)" in verdict.witnesses
    assert _is_quadratic(CLASS_RUN, "a", 2000)


def test_same_class_lookbehind_is_not_flagged_and_is_linear():
    assert fur.quadratic_verdict(CLASS_RUN_FIXED) is None
    assert _is_linear(CLASS_RUN_FIXED, "a", 50000)


def test_narrower_lookbehind_is_flagged_on_the_characters_it_omits():
    pattern = r"(?<![\w.])[\w./-]+\.py"
    verdict = fur.quadratic_verdict(pattern)
    assert verdict is not None
    assert set(verdict.witnesses) == {"'-' * N (end of text)", "'/' * N (end of text)"}
    assert _is_quadratic(pattern, "/", 2000)


def test_newline_start_then_blanks_is_flagged_and_is_quadratic():
    verdict = fur.quadratic_verdict(NEWLINE_START)
    assert verdict is not None and verdict.shape == "newline-start-then-blanks"
    assert verdict.witnesses == ("'\\n' * N (end of text)",)
    assert _is_quadratic(NEWLINE_START, "\n", 2000)


def test_blanks_that_stop_at_a_newline_are_not_flagged_and_are_linear():
    assert fur.quadratic_verdict(NEWLINE_START_FIXED) is None
    assert _is_linear(NEWLINE_START_FIXED, " \n", 50000)


def test_multiline_caret_is_a_newline_start():
    verdict = fur.quadratic_verdict(r"^\s*grep", re.MULTILINE)
    assert verdict is not None and verdict.shape == "newline-start-then-blanks"
    assert fur.quadratic_verdict(r"^\s*grep") is None  # no MULTILINE: one start only


@pytest.mark.parametrize("pattern", [
    r"\w+",              # nothing after the repeat: a match takes the whole run
    r"\d{4}-\d{2}",      # bounded repeats
    r"\bfoo\w*",         # leading literal, not a class repeat
    r"^\s+x",            # anchored to the start of the text
    r"\w+\w",            # the suffix matches inside the run
])
def test_ordinary_regexes_are_not_flagged(pattern):
    assert fur.quadratic_verdict(pattern) is None
    assert _is_linear(pattern, "a", 50000)


def test_word_boundary_does_not_hold_back_a_mixed_run():
    verdict = fur.quadratic_verdict(r"\b[\w.]+\.py")
    assert verdict is not None and verdict.witnesses == ("'0.' * N (end of text)",)
    assert fur.quadratic_verdict(r"\b\w+\.py") is None  # a pure word run has no inner boundary


def test_trailing_blanks_fail_only_before_a_terminator():
    # A run of blanks at the end of the text matches \s+$ from its first start; the run is
    # rescanned only when something other than a blank follows it.
    verdict = fur.quadratic_verdict(r"\s+$")
    assert verdict is not None and "' ' * N + 'x'" in verdict.witnesses
    assert "' ' * N (end of text)" not in verdict.witnesses
    assert _is_quadratic(r"\s+$", " ", 2000, tail="x")
    assert _is_linear(r"\s+$", " ", 50000)


def test_bytes_and_inline_flags_are_read():
    assert fur.quadratic_verdict(rb"[a-z]+\.py") is not None
    verdict = fur.quadratic_verdict(r"(?i)[A-Z]+:")
    assert verdict is not None and "'a' * N (end of text)" in verdict.witnesses


QUADRATIC_MODULE = (
    "import re\n"                                                     # 1
    "_START = r'(?:^|(?<=[;&|\\n]))'\n"                               # 2
    "_PATTERN = re.compile(_START + r'\\s*' + r'grep')\n"             # 3: built from constants
    "_FIXED = re.compile(_START + r'[^\\S\\n]*grep')\n"              # 4: the fix
    "_TOKEN = re.compile(r'[\\w./-]+\\.py')\n"                        # 5
    "_ONE_START = re.compile(r'[\\w./-]+\\.py')\n"                    # 6: only ever .match()ed
    "_LINES = re.compile(r'^\\s*x', re.M)\n"                          # 7: flags argument
    "def f(s):\n"                                                     # 8
    "    _ONE_START.match(s)\n"                                       # 9
    "    re.fullmatch(r'[\\w./-]+\\.py', s)\n"                        # 10: one start
    "    return re.findall(r'\\d+-\\d+', s)\n"                        # 11
)


def test_file_scan_reports_each_quadratic_call_site(tmp_path):
    p = tmp_path / "m.py"
    p.write_text(QUADRATIC_MODULE, encoding="utf-8")
    found = {(f["line"], f["shape"]) for f in fur.find_quadratic_regex(str(p))}
    assert found == {(3, "newline-start-then-blanks"), (5, "class-run-before-suffix"),
                     (7, "newline-start-then-blanks"), (11, "class-run-before-suffix")}


def test_cli_prints_the_quadratic_section(tmp_path, run_script):
    p = tmp_path / "m.py"
    p.write_text(QUADRATIC_MODULE, encoding="utf-8")
    r = run_script(SCRIPT, str(p))
    assert r.returncode == 0, r.stderr
    assert b"Found 4 patterns whose search can rescan one run from every start" in r.stdout
    assert b"m.py:5 - re.compile('[\\\\w./-]+\\\\.py', ...) [class-run-before-suffix]" in r.stdout
