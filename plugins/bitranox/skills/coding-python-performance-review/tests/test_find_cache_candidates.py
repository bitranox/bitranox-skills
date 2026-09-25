"""find_cache_candidates: source decoding, the purity heuristic, and the CLI contract.

The CLI is driven as a subprocess, the way SKILL.md Step 4a runs it.
"""
import textwrap

import pytest

import find_cache_candidates as fcc

SCRIPT = "find_cache_candidates.py"
PURE_BODY = "def square_sum(n):\n    total = 0\n    for i in range(n):\n        total += i * i\n    return total\n"


def _names(path):
    return {c["function"] for c in fcc.find_cache_candidates(str(path))}


# --- decoding: a file python3 runs must be scannable --------------------------------------

def test_utf8_bom_file_is_scanned(tmp_path):
    p = tmp_path / "bom.py"
    p.write_bytes(b"\xef\xbb\xbf" + PURE_BODY.encode())
    assert _names(p) == {"square_sum"}


def test_pep263_latin1_file_is_scanned(tmp_path):
    p = tmp_path / "latin.py"
    p.write_bytes(b"# -*- coding: latin-1 -*-\n# caf\xe9\n" + PURE_BODY.encode())
    assert _names(p) == {"square_sum"}


def test_unparseable_file_raises_instead_of_returning_empty(tmp_path):
    p = tmp_path / "bad.py"
    p.write_text("def (oops:\n", encoding="utf-8")
    with pytest.raises(SyntaxError):
        fcc.find_cache_candidates(str(p))


# --- purity heuristic ------------------------------------------------------------------

IMPURE = textwrap.dedent('''
    import subprocess
    import time
    import datetime
    import functools
    from functools import lru_cache

    COUNT = 0

    def gen(n):
        for i in range(n):
            yield i * i

    def gen_from(n):
        for _ in range(n):
            pass
        yield from range(n)

    def fill(out, n):
        for i in range(n):
            out[i] = i

    def set_attr(obj, n):
        for i in range(n):
            obj.total = i

    def fetch(cmds):
        for c in cmds:
            subprocess.run(c)

    def stamp(n):
        for _ in range(n):
            pass
        return time.time()

    def clock(n):
        for _ in range(n):
            pass
        return time.perf_counter()

    def when(n):
        for _ in range(n):
            pass
        return datetime.datetime.now()

    def bump(n):
        global COUNT
        for _ in range(n):
            COUNT += 1

    def printer(n):
        for i in range(n):
            print(i)

    @functools.lru_cache(maxsize=None)
    def dotted_cached(n):
        for i in range(n):
            pass
        return n

    @functools.cache
    def dotted_cache(n):
        for i in range(n):
            pass
        return n

    def square_sum(n):
        total = 0
        for i in range(n):
            total += i * i
        return total
''')


def test_impure_functions_are_not_candidates(tmp_path):
    p = tmp_path / "gen.py"
    p.write_text(IMPURE, encoding="utf-8")
    assert _names(p) == {"square_sum"}


def test_open_makes_a_function_impure_and_file_io_is_not_an_indicator(tmp_path):
    p = tmp_path / "io.py"
    p.write_text("def reader(p):\n    for _ in range(3):\n        with open(p) as f:\n            f\n",
                 encoding="utf-8")
    assert _names(p) == set()
    tree = __import__("ast").parse(p.read_text(encoding="utf-8"))
    assert "file_io" not in fcc.is_expensive_computation(tree.body[0])


# --- CLI ---------------------------------------------------------------------------------

def test_cli_reports_a_candidate_and_exits_0(tmp_path, run_script):
    p = tmp_path / "pure.py"
    p.write_text(PURE_BODY, encoding="utf-8")
    r = run_script(SCRIPT, str(p))
    assert r.returncode == 0, r.stderr
    assert b"Found 1 potential candidates" in r.stdout
    assert b"square_sum()" in r.stdout


def test_cli_unparseable_file_exits_2_and_still_prints_the_report(tmp_path, run_script):
    good = tmp_path / "pure.py"
    good.write_text(PURE_BODY, encoding="utf-8")
    bad = tmp_path / "bad.py"
    bad.write_text("def (oops:\n", encoding="utf-8")
    r = run_script(SCRIPT, str(bad), str(good))
    assert r.returncode == 2
    assert b"ERROR" in r.stderr and b"bad.py" in r.stderr
    assert b"Found 1 potential candidates" in r.stdout


def test_cli_directory_argument_exits_2(tmp_path, run_script):
    r = run_script(SCRIPT, str(tmp_path))
    assert r.returncode == 2
    assert b"ERROR" in r.stderr


def test_cli_missing_path_exits_2_and_names_it(tmp_path, run_script):
    missing = tmp_path / "does_not_exist.py"
    r = run_script(SCRIPT, str(missing))
    assert r.returncode == 2
    assert b"not found" in r.stderr and b"does_not_exist.py" in r.stderr


def test_cli_no_arguments_prints_usage_and_exits_2(run_script):
    r = run_script(SCRIPT)
    assert r.returncode == 2
    assert b"usage" in r.stderr.lower()
    assert b"Found" not in r.stdout


def test_cli_help_exits_0_without_scanning(run_script):
    r = run_script(SCRIPT, "--help")
    assert r.returncode == 0
    assert b"usage" in r.stdout.lower()
    assert b"Found" not in r.stdout


def test_cli_non_ansi_path_under_cp1252_stdout_is_written_as_utf8(tmp_path, run_script, clean_env):
    d = tmp_path / "proj_\u7530\u4e2d"
    d.mkdir()
    p = d / "pure.py"
    p.write_text(PURE_BODY, encoding="utf-8")
    r = run_script(SCRIPT, str(p), env=clean_env(PYTHONIOENCODING="cp1252"))
    assert r.returncode == 0, r.stderr
    assert "proj_\u7530\u4e2d" in r.stdout.decode("utf-8")
