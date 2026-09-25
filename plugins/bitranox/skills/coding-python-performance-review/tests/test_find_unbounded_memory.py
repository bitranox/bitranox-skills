"""Behavioural tests for find_unbounded_memory.py - flag whole-materialization reads,
leave bounded/streaming ones alone."""

import pytest

import find_unbounded_memory as M


def scan(tmp_path, code):
    p = tmp_path / "sample.py"
    p.write_text(code, encoding="utf-8")
    return M.find_unbounded_memory(str(p))


def kinds(findings):
    return {f["kind"] for f in findings}


def test_flags_whole_file_read(tmp_path):
    f = scan(tmp_path, "def g(fh):\n    return fh.read()\n")
    assert kinds(f) == {"read"} and f[0]["line"] == 2


def test_bounded_read_with_size_is_ok(tmp_path):
    # read(size) streams in chunks -> must NOT be flagged
    assert scan(tmp_path, "def g(fh):\n    return fh.read(8192)\n") == []


def test_flags_readlines(tmp_path):
    assert kinds(scan(tmp_path, "def g(fh):\n    return fh.readlines()\n")) == {"readlines"}


def test_flags_pathlib_read_text_and_bytes(tmp_path):
    code = "from pathlib import Path\n\ndef g(p):\n    a = Path(p).read_text()\n    b = Path(p).read_bytes()\n    return a, b\n"
    assert kinds(scan(tmp_path, code)) == {"read_text", "read_bytes"}


def test_flags_fetchall(tmp_path):
    assert kinds(scan(tmp_path, "def g(cur):\n    return cur.fetchall()\n")) == {"fetchall"}


def test_fetchmany_is_ok(tmp_path):
    assert scan(tmp_path, "def g(cur):\n    return cur.fetchmany(500)\n") == []


def test_flags_pandas_reader_without_chunking(tmp_path):
    f = scan(tmp_path, "import pandas as pd\n\ndef g():\n    return pd.read_csv('big.csv')\n")
    assert kinds(f) == {"pandas"}


def test_pandas_reader_with_chunksize_is_ok(tmp_path):
    assert scan(tmp_path, "import pandas as pd\n\ndef g():\n    return pd.read_csv('big.csv', chunksize=10000)\n") == []


def test_clean_code_has_no_findings(tmp_path):
    code = "def g(fh):\n    total = 0\n    for line in fh:        # streaming, good\n        total += len(line)\n    return total\n"
    assert scan(tmp_path, code) == []


def test_malformed_file_raises_instead_of_returning_empty(tmp_path):
    # [] would be indistinguishable from a clean file; the CLI turns the raise into exit 2.
    with pytest.raises(SyntaxError):
        scan(tmp_path, "def (oops:\n")


def test_finding_shape(tmp_path):
    f = scan(tmp_path, "def g(fh):\n    return fh.read()\n")[0]
    assert set(f) == {"file", "line", "kind", "call", "suggestion"} and f["suggestion"]


# --- literal "no limit" arguments -----------------------------------------------------------

EDGE = (
    "import pandas as pd\n"
    "a = fh.read(-1)\n"                              # 2: unbounded
    "b = fh.read(None)\n"                            # 3: unbounded
    "c = pd.read_csv('big.csv', chunksize=None)\n"   # 4: no chunking
    "d = pd.read_csv('big.csv', iterator=False)\n"   # 5: no chunking
    "e = fh.readlines(4096)\n"                       # 6: bounded by the hint
    "f = fh.read()\n"                                # 7: unbounded
    "g = pd.read_csv('big.csv')\n"                   # 8: no chunking
    "h = fh.read(8192)\n"                            # 9: bounded
    "i = pd.read_csv('big.csv', chunksize=1000)\n"   # 10: chunked
    "j = fh.readlines()\n"                           # 11: unbounded
    "k = fh.readlines(-1)\n"                         # 12: hint <= 0 means no limit
    "l = pd.read_csv('big.csv', nrows=None)\n"       # 13: no limit
)


def test_literal_no_limit_arguments_are_flagged_and_real_bounds_are_not(tmp_path):
    lines = sorted(f["line"] for f in scan(tmp_path, EDGE))
    assert lines == [2, 3, 4, 5, 7, 8, 11, 12, 13]


# --- decoding ------------------------------------------------------------------------------

BODY = "def g(fh):\n    return fh.read()\n"


def test_utf8_bom_file_is_scanned(tmp_path):
    p = tmp_path / "bom.py"
    p.write_bytes(b"\xef\xbb\xbf" + BODY.encode())
    assert kinds(M.find_unbounded_memory(str(p))) == {"read"}


def test_pep263_latin1_file_is_scanned(tmp_path):
    p = tmp_path / "latin.py"
    p.write_bytes(b"# -*- coding: latin-1 -*-\n# caf\xe9\n" + BODY.encode())
    assert kinds(M.find_unbounded_memory(str(p))) == {"read"}


# --- CLI -----------------------------------------------------------------------------------

SCRIPT = "find_unbounded_memory.py"


def test_cli_reports_and_exits_0(tmp_path, run_script):
    p = tmp_path / "good.py"
    p.write_text(BODY, encoding="utf-8")
    r = run_script(SCRIPT, str(p))
    assert r.returncode == 0, r.stderr
    assert b"Found 1 whole-materialization candidate(s)" in r.stdout


def test_cli_unparseable_file_exits_2_and_still_prints_the_report(tmp_path, run_script):
    good = tmp_path / "good.py"
    good.write_text(BODY, encoding="utf-8")
    bad = tmp_path / "bad.py"
    bad.write_text("def (oops:\n", encoding="utf-8")
    r = run_script(SCRIPT, str(bad), str(good))
    assert r.returncode == 2
    assert b"ERROR" in r.stderr and b"bad.py" in r.stderr
    assert b"Found 1 " in r.stdout


def test_cli_directory_argument_exits_2(tmp_path, run_script):
    r = run_script(SCRIPT, str(tmp_path))
    assert r.returncode == 2 and b"ERROR" in r.stderr


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
