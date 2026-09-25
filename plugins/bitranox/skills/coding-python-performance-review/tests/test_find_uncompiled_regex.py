"""find_uncompiled_regex: which call sites are flagged, source decoding, and the CLI contract."""
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
