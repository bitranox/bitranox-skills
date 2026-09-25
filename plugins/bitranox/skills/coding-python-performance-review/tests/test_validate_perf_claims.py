"""validate_perf_claims: what counts as a claim, where it is reported, and the CLI contract."""
import validate_perf_claims as vpc

SCRIPT = "validate_perf_claims.py"


def _claims(tmp_path, text):
    p = tmp_path / "changes.diff"
    p.write_text(text, encoding="utf-8")
    return [c["claim"].lower() for c in vpc.find_performance_claims(str(p))]


# --- false positives -----------------------------------------------------------------------

def test_hex_literals_and_dimensions_are_not_claims(tmp_path):
    assert _claims(tmp_path, '+MASK = 0xFF\n+SIZE = "1920x1080"\n+flags=0x10\n') == []


def test_multiplier_claim_is_still_found(tmp_path):
    assert _claims(tmp_path, "+gives a 3x speedup\n") == ["3x speedup"]


def test_keywords_do_not_match_inside_other_words(tmp_path):
    assert _claims(tmp_path, "+cursor.execute(sql, flags=0x1)\n+    cut_width: 50%\n") == []


def test_keyword_claim_is_still_found(tmp_path):
    assert _claims(tmp_path, "+this cut latency by 50%\n") == ["cut latency by 50%"]


def test_removed_and_context_lines_are_not_scanned(tmp_path):
    diff = ("--- a/m.py\n+++ b/m.py\n@@ -1,3 +1,3 @@\n"
            "-# cache gives 40% faster\n"
            " # unchanged: 25% faster context\n"
            "+# cache removed\n")
    assert _claims(tmp_path, diff) == []


def test_added_claim_is_reported_with_its_new_file_location(tmp_path):
    diff = ("diff --git a/src/m.py b/src/m.py\n--- a/src/m.py\n+++ b/src/m.py\n@@ -10,3 +10,4 @@\n"
            " a = 1\n"
            "-b = 2\n"
            "+# 40% faster now\n"
            "+b = 3\n")
    p = tmp_path / "changes.diff"
    p.write_text(diff, encoding="utf-8")
    assert vpc.find_performance_claims(str(p)) == [{"claim": "40% faster", "where": "src/m.py:11"}]


def test_plus_line_outside_a_hunk_reports_the_diff_line(tmp_path):
    p = tmp_path / "changes.diff"
    p.write_text("preamble\n+This change is 40% faster.\n", encoding="utf-8")
    assert vpc.find_performance_claims(str(p)) == [{"claim": "40% faster", "where": "diff line 2"}]


# --- numberless claims the docstring promises ----------------------------------------------

def test_qualitative_claims_are_found(tmp_path):
    claims = _claims(tmp_path, "+This improves throughput.\n+Twice as fast as before.\n"
                               "+It is 3 times faster.\n+significantly faster\n")
    assert claims == ["improves throughput", "twice as fast", "3 times faster", "significantly faster"]


def test_line_separator_inside_a_line_does_not_split_it(tmp_path):
    # U+2028 is not a line break in a diff: splitlines() would start a new "line" there,
    # which no longer begins with "+" and is silently skipped.
    assert _claims(tmp_path, "+note\u2028 40% faster\n") == ["40% faster"]


# --- CLI -----------------------------------------------------------------------------------

def test_cli_success_lists_claims_and_exits_0(tmp_path, run_script):
    p = tmp_path / "d.diff"
    p.write_text("+This is 40% faster.\n", encoding="utf-8")
    r = run_script(SCRIPT, str(p))
    assert r.returncode == 0, r.stderr
    assert b"Found 1 performance claim(s)" in r.stdout
    assert b"40% faster" in r.stdout and b"diff line 1" in r.stdout


def test_cli_uses_the_default_diff_path(tmp_path, run_script):
    d = tmp_path / "LLM-CONTEXT" / "review-anal" / "scope"
    d.mkdir(parents=True)
    (d / "changes.diff").write_text("+3x speedup\n", encoding="utf-8")
    r = run_script(SCRIPT, cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert b"Found 1 performance claim(s)" in r.stdout


def test_cli_missing_file_exits_2(tmp_path, run_script):
    r = run_script(SCRIPT, str(tmp_path / "nope.diff"))
    assert r.returncode == 2 and b"No diff file found" in r.stderr


def test_cli_extra_arguments_are_rejected(tmp_path, run_script):
    p = tmp_path / "d.diff"
    p.write_text("+40% faster\n", encoding="utf-8")
    r = run_script(SCRIPT, str(p), str(tmp_path / "second.diff"))
    assert r.returncode == 2 and b"usage" in r.stderr.lower()


def test_cli_help_exits_0(run_script):
    r = run_script(SCRIPT, "--help")
    assert r.returncode == 0 and b"usage" in r.stdout.lower()


def test_cli_non_ansi_path_under_cp1252_is_written_as_utf8(tmp_path, run_script, clean_env):
    d = tmp_path / "proj_\u7530\u4e2d"
    d.mkdir()
    p = d / "d.diff"
    p.write_text("+40% faster\n", encoding="utf-8")
    r = run_script(SCRIPT, str(p), env=clean_env(PYTHONIOENCODING="cp1252"))
    assert r.returncode == 0, r.stderr
    assert "proj_\u7530\u4e2d" in r.stdout.decode("utf-8")
