"""Behavioural tests for find_unbounded_memory.py - flag whole-materialization reads,
leave bounded/streaming ones alone."""

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


def test_malformed_file_returns_empty(tmp_path):
    assert scan(tmp_path, "def (oops:\n") == []


def test_finding_shape(tmp_path):
    f = scan(tmp_path, "def g(fh):\n    return fh.read()\n")[0]
    assert set(f) == {"file", "line", "kind", "call", "suggestion"} and f["suggestion"]
