"""find_uncompiled_regex: which call sites are flagged, source decoding, the quadratic-start
shapes, and the CLI contract."""
import functools
import mmap
import os
import re
import sys
import time

import pytest

if sys.platform != "win32":
    import resource

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


# USER CPU time (process-test-design, growth-ratio rule 1). Wall time charges this process for
# time it waited for a core on a loaded machine (measured: 18x for a 64x pattern at a load of 30
# on 16 cores), and process_time adds kernel time, which the large arm's fresh pages inflate.
# getrusage counts every thread of the process, and no other thread runs during a window.
# Windows has no getrusage; there every CPU-time clock steps 15.625 ms, so _min_window() makes
# each window many steps long instead of falling back to the wall clock.
if sys.platform == "win32":
    def _user_cpu():
        return os.times().user
else:
    def _user_cpu():
        return resource.getrusage(resource.RUSAGE_SELF).ru_utime


_STEP_SAMPLES = 3
_BUSY_CHUNK = 2000  # loop iterations between two clock reads: user work, not kernel work


def _clock_step(clock):
    """The smallest advance *clock* reports over a busy loop, best of a few.

    A loop of bare clock reads is mostly kernel time, which a user-time clock barely sees; busy
    arithmetic between reads advances it the way a timed scan does."""
    steps = []
    for _ in range(_STEP_SAMPLES):
        start = now = clock()
        spin = 0
        while now == start:
            for _ in range(_BUSY_CHUNK):
                spin += 1
            now = clock()
        steps.append(now - start)
    return min(steps)


# 10 steps keep one window within 10% of its length; on Windows that is a 156 ms window,
# where a 2 ms arm read 0.0 in 9 of 10 runs (measured on the Windows dev box).
_STEPS_PER_WINDOW = 10
_MIN_WINDOW_FLOOR = 0.02  # seconds, where the clock is fine-grained


@functools.cache
def _min_window():
    """Seconds each timed window must last on this machine's clock."""
    return max(_MIN_WINDOW_FLOOR, _STEPS_PER_WINDOW * _clock_step(_user_cpu))


# A pattern can do constant work on the test text (r"^\s+x" fails at the first character), and
# then both arms finish below the clock's resolution: macOS read 0.0 for the small arm and the
# ratio divided by zero, and on Linux the ratio of two sub-microsecond readings is noise. A large
# arm under this bound cannot be quadratic - a quadratic match over the large arm's 8 * 50000
# units runs for minutes - so such a pattern counts as linear without a ratio.
TOO_FAST_TO_BE_QUADRATIC = 0.005  # seconds per scan

_GROWTH = 8        # the large arm's input is this many times the small arm's
_MAX_REPS = 1 << 16
_ROUNDS = 3


def _finditer(pattern):
    compiled = re.compile(pattern)
    return lambda text: list(compiled.finditer(text))


def _arm_times(pattern, unit, n, tail="", *, scan=None, clock=_user_cpu, min_window=None):
    """Seconds per finditer scan over unit * n + tail and over unit * 8n + tail.

    The two arms get EQUAL windows (growth-ratio rule 2): the small arm is timed as 8 scans back
    to back, so a fast moment of the machine cannot fall wholly inside it, and both windows are
    repeated until they last _min_window(). Each is the best of 3 rounds. *scan* and *clock* are
    the seams a virtual-clock test drives.
    """
    run_scan = scan if scan is not None else _finditer(pattern)
    floor = _min_window() if min_window is None else min_window
    small, big = unit * n + tail, unit * _GROWTH * n + tail

    def window(text, scans):
        start = clock()
        for _ in range(scans):
            run_scan(text)
        return clock() - start

    reps = 1
    while window(small, _GROWTH * reps) < floor and reps < _MAX_REPS:
        reps *= 2
    small_scans = _GROWTH * reps
    small_time = min(window(small, small_scans) for _ in range(_ROUNDS)) / small_scans
    big_time = min(window(big, reps) for _ in range(_ROUNDS)) / reps
    return small_time, big_time


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


# --- quadratic starts the leading-class rule cannot see -----------------------------------------
# A repeated GROUP before a suffix, and a repeat reached past an optional prefix. The positives
# are real hook patterns that measured 54x to 65x for 8x the input; the negatives are their fixes.

SCRIPT_PATH_OLD = r"(?:[\w.-]+/)+[\w.-]+\.(?:py|sh)\b"
SCRIPT_PATH_FIXED = r"[\w.-]/[\w.-]+\.(?:py|sh)\b"         # one character before the last slash
SCRIPT_PATH_ANCHORED = r"(?<![\w./-])(?:[\w.-]+/)+[\w.-]+\.(?:py|sh)\b"  # the shape's own fix

PUSHCHECK_OLD = (r"(?m)(?:^|[;&|])\s*"
                 r"(?:(?:if|then|elif|else|do|while|until|!)\s+|[({]\s*)*"
                 r"(?:(?:[A-Za-z_]\w*=\S*|env(?:\s+-u\s+\w+)*)\s+)*"
                 r"git(?:\s+-[Cc]\s+(?:[^\s'\"]|'[^']*'|\"[^\"]*\")+)*\s+push\b"
                 r"|\bmake\s+push\b|\bgh\s+pr\s+create\b")
PUSHCHECK_FIXED = (r"(?m)(?:^|[;&|])[^\S\n]*"
                   r"(?:(?:if|then|elif|else|do|while|until|!)[^\S\n]+|[({][^\S\n]*)*"
                   r"(?:(?:[A-Za-z_]\w*=\S*|env(?:\s+-u\s+\w+)*)[^\S\n]+)*"
                   r"git(?:\s+-[Cc]\s+(?:[^\s'\"]|'[^']*'|\"[^\"]*\")+)*\s+push\b"
                   r"|\bmake\s+push\b|\bgh\s+pr\s+create\b")
KEYWORD_PREFIX = r"(?m)^[^\S\n]*(?:then\s+)*git"
KEYWORD_PREFIX_FIXED = r"(?m)^[^\S\n]*(?:then[^\S\n]+)*git"


def test_repeated_group_before_suffix_is_flagged_and_is_quadratic():
    verdict = fur.quadratic_verdict(SCRIPT_PATH_OLD)
    assert verdict is not None and verdict.shape == "group-run-before-suffix"
    assert {"'a/' * N (end of text)", "'a' * N (end of text)"} <= set(verdict.witnesses)
    assert _is_quadratic(SCRIPT_PATH_OLD, "a/", 500)


@pytest.mark.parametrize("pattern", [SCRIPT_PATH_FIXED, SCRIPT_PATH_ANCHORED])
def test_repeated_group_fixes_are_not_flagged_and_are_linear(pattern):
    assert fur.quadratic_verdict(pattern) is None
    assert _is_linear(pattern, "a/", 25000)


def test_repeat_after_optional_prefix_is_flagged_and_is_quadratic():
    verdict = fur.quadratic_verdict(KEYWORD_PREFIX)
    assert verdict is not None and verdict.shape == "repeat-after-optional-prefix"
    assert "'then\\n' * N (end of text)" in verdict.witnesses
    assert _is_quadratic(KEYWORD_PREFIX, "then\n", 400)


def test_repeat_after_optional_prefix_fix_is_not_flagged_and_is_linear():
    assert fur.quadratic_verdict(KEYWORD_PREFIX_FIXED) is None
    assert _is_linear(KEYWORD_PREFIX_FIXED, "then \n", 10000)


def test_old_push_check_names_every_prefix_run():
    verdict = fur.quadratic_verdict(PUSHCHECK_OLD)
    assert verdict is not None and verdict.shape == "newline-start-then-blanks"
    assert {"'\\n' * N (end of text)", "'if\\n' * N (end of text)", "'(\\n' * N (end of text)",
            "'a=\\n' * N (end of text)", "'env\\n' * N (end of text)"} <= set(verdict.witnesses)
    assert _is_quadratic(PUSHCHECK_OLD, "a=\n", 400)


def test_fixed_push_check_is_not_flagged_and_is_linear():
    assert fur.quadratic_verdict(PUSHCHECK_FIXED) is None
    assert _is_linear(PUSHCHECK_FIXED, "then\n", 10000)


def test_optional_prefix_before_a_class_run_is_flagged():
    verdict = fur.quadratic_verdict(r"v?\d+\.\d+")
    assert verdict is not None and verdict.shape == "class-run-before-suffix"
    assert "'0' * N (end of text)" in verdict.witnesses
    assert _is_quadratic(r"v?\d+\.\d+", "0", 2000)
    assert fur.quadratic_verdict(r"(?<!\d)v?\d+\.\d+") is None


def test_repeated_body_that_matches_its_whole_run_is_not_flagged():
    # nothing after the repeat, so a match takes the whole run from its first start
    assert fur.quadratic_verdict(r"(?:ab)+") is None
    assert fur.quadratic_verdict(r"(?:\w+)+") is None


# --- how much a scan examined ---------------------------------------------------------------

def test_cli_reports_how_many_call_sites_it_examined(tmp_path, run_script):
    p = tmp_path / "m.py"
    p.write_text(QUADRATIC_MODULE + "def g(s, pat):\n    return re.search(pat, s)\n",
                 encoding="utf-8")
    r = run_script(SCRIPT, str(p))
    assert r.returncode == 0, r.stderr
    # lines 3-7 compile, 10 fullmatch, 11 findall, plus g's search; line 9 is a method call
    assert (b"Examined 8 regex call sites in 1 file: 5 checked for quadratic starts, "
            b"0 in a shape not modelled, 1 built at run time") in r.stdout


UNCHECKED_MODULE = (
    "import re\n"                                  # 1
    "SEP = ','\n"                                  # 2
    "def f(s, name, pat):\n"                       # 3
    "    re.search(f'{name}=(\\\\d+)', s)\n"       # 4
    "    re.findall('a' + re.escape(name), s)\n"   # 5
    "    re.sub(pat, '', s)\n"                     # 6
    "    re.split(SEP + '+', s)\n"                 # 7: folded from a constant, so checked
    "    return re.finditer('%s' % name, s)\n"     # 8
)


def test_cli_lists_each_unchecked_site_under_the_examined_line(tmp_path, run_script):
    p = tmp_path / "m.py"
    p.write_text(UNCHECKED_MODULE, encoding="utf-8")
    r = run_script(SCRIPT, str(p))
    assert r.returncode == 0, r.stderr
    lines = r.stdout.decode("utf-8").splitlines()
    head = next(i for i, line in enumerate(lines) if line.startswith("Examined "))
    assert lines[head] == ("Examined 5 regex call sites in 1 file: 1 checked for quadratic "
                           "starts, 0 in a shape not modelled, 4 built at run time")
    assert lines[head + 1:head + 6] == [
        f"  not checked: {p}:4 - built at run time: an f-string, assembled when the line runs",
        (f"  not checked: {p}:5 - built at run time: joined with + from a part that is not a "
         "string constant: re.escape(name)"),
        (f"  not checked: {p}:6 - built at run time: pat is not a module-level name bound once "
         "to a string"),
        f"  not checked: {p}:8 - built at run time: '%s' % name is evaluated when the line runs",
        "",
    ]


def test_scan_lists_unchecked_sites_in_file_and_line_order(tmp_path):
    a, b = tmp_path / "a.py", tmp_path / "b.py"
    a.write_text(UNCHECKED_MODULE, encoding="utf-8")
    b.write_text("import re\ndef g(s, p):\n    return re.search(p, s)\n", encoding="utf-8")
    total = fur.ScanCounts()
    for path in (a, b):
        total.merge(fur.scan_quadratic_regex(str(path))[1])
    assert [(u["file"], u["line"]) for u in total.unchecked] == [
        (str(a), 4), (str(a), 5), (str(a), 6), (str(a), 8), (str(b), 3)]
    assert len(total.unchecked) == total.unreadable + total.not_modelled


def test_a_not_modelled_site_is_listed_with_its_reason():
    # No pattern this checker parses reaches a not-modelled shape today, so the record is
    # exercised directly: a shape added later must still come out with a location.
    counts = fur.ScanCounts()
    counts.record(fur._Site.NOT_MODELLED, file="/opt/m.py", line=9,
                  reason="its parse tree holds GROUPREF")
    counts.record(fur._Site.CHECKED, file="/opt/m.py", line=10)
    assert counts.unchecked == [{"file": "/opt/m.py", "line": 9, "kind": "shape not modelled",
                                 "reason": "its parse tree holds GROUPREF"}]
    assert (counts.sites, counts.not_modelled, counts.checked) == (2, 1, 1)


def test_cli_zero_call_sites_exits_2(tmp_path, run_script):
    p = tmp_path / "plain.py"
    p.write_text("def f(s):\n    return s.strip()\n", encoding="utf-8")
    r = run_script(SCRIPT, str(p))
    assert r.returncode == 2
    assert b"examined 0 regex call sites" in r.stderr
    assert b"Examined 0 regex call sites in 1 file" in r.stdout


# --- the timing helper itself (process-test-design, growth-ratio rules 1 and 2) -----------------

class _VirtualCPU:
    """A user-time clock that advances with work done: 1 us per character a scan reads, and ten
    times faster over a stretch of *fast_chars* characters starting *fast_from* characters in."""

    def __init__(self, fast_from, fast_chars):
        self.now = 0.0
        self.work = 0
        self.fast_from = fast_from
        self.fast_to = fast_from + fast_chars

    def clock(self):
        return self.now

    def scan(self, text):
        lo, hi = self.work, self.work + len(text)
        fast = max(0, min(hi, self.fast_to) - max(lo, self.fast_from))
        self.now += (len(text) - fast) * 1e-6 + fast * 1e-7
        self.work = hi


@pytest.mark.parametrize("offset", range(120))
def test_a_fast_moment_does_not_make_a_linear_scan_read_superlinear(offset):
    # A fast stretch one small scan long, placed at every small-scan boundary of the whole run:
    # timing the small arm as one short pass lets it fall wholly inside that pass (ratio 80x).
    n = 2000
    cpu = _VirtualCPU(fast_from=offset * n, fast_chars=n)
    small, big = _arm_times("", "a", n, scan=cpu.scan, clock=cpu.clock, min_window=0.02)
    assert big < LINEAR_CEILING * small


def test_clock_step_reads_a_ticking_clock_as_one_tick():
    tick = 0.015625
    calls = [0]

    def ticking():
        calls[0] += 1
        return (calls[0] // 16) * tick

    assert _clock_step(ticking) == tick


@pytest.mark.skipif(sys.platform == "win32",
                    reason="Windows user time over page faults measured 0.23 to 0.74 of process_time "
                           "over 512 MiB: no stable split to assert")
def test_user_cpu_leaves_out_the_kernel_time_of_page_faults():
    # Touching fresh anonymous pages is kernel work (page faults); process_time counts it, user
    # time does not (measured on Linux: user time 5% to 23% of process_time).
    size = 128 << 20
    ratios = []
    for _ in range(3):
        region = mmap.mmap(-1, size)
        try:
            user0, process0 = _user_cpu(), time.process_time()
            for offset in range(0, size, mmap.PAGESIZE):
                region[offset] = 1
            ratios.append((_user_cpu() - user0) / max(time.process_time() - process0, 1e-9))
        finally:
            region.close()
    assert min(ratios) < 0.5
