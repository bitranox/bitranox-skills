"""prioritize_cache_candidates: path matching (POSIX and Windows shapes) and the CLI contract."""
import pytest

import prioritize_cache_candidates as pcc

SCRIPT = "prioritize_cache_candidates.py"


def _pair(tmp_path, cand_line, hot_line):
    cand = tmp_path / "cand.txt"
    cand.write_text(f"# Cache Candidates Analysis\n\nFound 1 potential candidates\n\n{cand_line}\n"
                    "  Reason: Pure function with: recursion\n", encoding="utf-8")
    hot = tmp_path / "hot.txt"
    hot.write_text(f"--- t.prof ---\n# Hot Spots\n\nFound 1 hot spots\n\n{hot_line}\n"
                   "  Calls: 150, Cumtime: 0.2000s, Per call: 0.001000s\n", encoding="utf-8")
    return str(cand), str(hot)


def _prioritized(tmp_path, cand_line, hot_line):
    cand, hot = _pair(tmp_path, cand_line, hot_line)
    return pcc.prioritize(pcc.parse_candidates(cand), pcc.parse_hotspots(hot))


@pytest.mark.parametrize("cand_line, hot_line, expected", [
    # a longer file name that merely ENDS in the hot file's name is a different file
    ("/proj/src/xm.py:4 - fib()", "/proj/src/m.py:4 - fib()", 0),
    ("/proj/src/other.py:4 - fib()", "/proj/src/m.py:4 - fib()", 0),
    ("/proj/src/m.py:4 - fib()", "/proj/src/m.py:4 - fib()", 1),
    # the relative path find(1) gives against the absolute path cProfile records
    ("src/m.py:4 - fib()", "/proj/src/m.py:4 - fib()", 1),
    ("./src/m.py:4 - fib()", "/proj/src/m.py:4 - fib()", 1),
    # same file name in another package is not the same file
    ("src/a/m.py:4 - fib()", "/proj/src/b/m.py:4 - fib()", 0),
    # Windows: cProfile records native backslash paths with a drive letter
    ("src/m.py:4 - fib()", "C:\\proj\\src\\m.py:4 - fib()", 1),
    ("src/m.py:4 - fib()", "C:/proj/src/m.py:4 - fib()", 1),
    ("src\\m.py:4 - fib()", "C:\\proj\\src\\m.py:4 - fib()", 1),
    ("src/xm.py:4 - fib()", "C:\\proj\\src\\m.py:4 - fib()", 0),
])
def test_candidate_matches_a_hotspot_only_when_it_is_the_same_file(tmp_path, cand_line, hot_line, expected):
    assert len(_prioritized(tmp_path, cand_line, hot_line)) == expected


def test_windows_drive_letter_survives_parsing(tmp_path):
    cand, hot = _pair(tmp_path, "C:\\proj\\src\\m.py:4 - fib()", "D:\\proj\\src\\m.py:9 - fib()")
    assert pcc.parse_candidates(cand) == [{"file": "C:\\proj\\src\\m.py", "line": 4, "function": "fib"}]
    assert pcc.parse_hotspots(hot) == [{"file": "D:\\proj\\src\\m.py", "line": 9, "function": "fib"}]


def test_utf8_bom_does_not_corrupt_the_first_path(tmp_path):
    p = tmp_path / "cand.txt"
    p.write_bytes(b"\xef\xbb\xbfsrc/m.py:4 - fib()\n")
    assert pcc.parse_candidates(str(p))[0]["file"] == "src/m.py"


# --- CLI ---------------------------------------------------------------------------------

def test_cli_prints_the_bold_line_step5_strips(tmp_path, run_script):
    cand, hot = _pair(tmp_path, "src/m.py:4 - fib()", "/proj/src/m.py:4 - fib()")
    r = run_script(SCRIPT, cand, hot)
    assert r.returncode == 0, r.stderr
    assert b"**src/m.py:4 - fib()**" in r.stdout
    assert b"Total high-priority candidates: 1" in r.stdout


def test_cli_usage_error_exits_2(tmp_path, run_script):
    r = run_script(SCRIPT, str(tmp_path / "only_one.txt"))
    assert r.returncode == 2 and b"usage" in r.stderr.lower()


def test_cli_missing_input_exits_2_without_traceback(tmp_path, run_script):
    cand, _hot = _pair(tmp_path, "src/m.py:4 - fib()", "/proj/src/m.py:4 - fib()")
    r = run_script(SCRIPT, cand, str(tmp_path / "missing.txt"))
    assert r.returncode == 2
    assert b"ERROR" in r.stderr and b"missing.txt" in r.stderr and b"Traceback" not in r.stderr
