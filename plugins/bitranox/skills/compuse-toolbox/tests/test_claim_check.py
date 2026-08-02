"""Tests for claim_check.

The tool exists for ONE failure: a check that reports "not found" when it never really looked.
So the control-gate tests are the point, not an extra.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import claim_check as cc  # noqa: E402

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "claim_check.py"


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# --- the control gate: the reason this tool exists -------------------------------------------

def test_control_missing_is_broken_not_absent(tmp_path):
    """A pattern that misses AND a control that misses means the check itself is wrong.

    This is the exact shape of a `grep -ric` whose output was never parsed: it looked like a
    clean 'absent' and was really 'I did not read anything'.
    """
    _write(tmp_path, "a.md", "hello world\n")
    r = cc.check([tmp_path / "a.md"], pattern="nonexistent", control="alsomissing")
    assert r["verdict"] == "BROKEN"
    assert r["control_hits"] == 0


def test_absent_requires_a_passing_control(tmp_path):
    _write(tmp_path, "a.md", "hello world\n")
    r = cc.check([tmp_path / "a.md"], pattern="nonexistent", control="hello")
    assert r["verdict"] == "ABSENT"
    assert r["control_hits"] == 1


def test_no_files_read_is_broken(tmp_path):
    """An empty path list yields zero hits for everything - indistinguishable from a real absent."""
    r = cc.check([], pattern="x", control="y")
    assert r["verdict"] == "BROKEN"
    assert r["files_read"] == 0


def test_unreadable_file_is_broken_not_silently_skipped(tmp_path):
    r = cc.check([tmp_path / "does-not-exist.md"], pattern="x", control="y")
    assert r["verdict"] == "BROKEN"
    assert r["files_read"] == 0


# --- present / reporting ----------------------------------------------------------------------

def test_present_reports_path_line_number_and_text(tmp_path):
    _write(tmp_path, "a.md", "alpha\nbeta LC_ALL=C gamma\ndelta\n")
    r = cc.check([tmp_path / "a.md"], pattern=r"LC_ALL=C", control="alpha")
    assert r["verdict"] == "PRESENT"
    assert len(r["hits"]) == 1
    hit = r["hits"][0]
    assert hit["line"] == 2
    assert "LC_ALL=C" in hit["text"]
    assert hit["path"].endswith("a.md")


def test_case_insensitive_by_default_and_can_be_disabled(tmp_path):
    _write(tmp_path, "a.md", "The LOCALIZED text\n")
    assert cc.check([tmp_path / "a.md"], pattern="localized", control="text")["verdict"] == "PRESENT"
    r = cc.check([tmp_path / "a.md"], pattern="localized", control="text", ignore_case=False)
    assert r["verdict"] == "ABSENT"


def test_scans_every_file_and_attributes_hits(tmp_path):
    _write(tmp_path, "a.md", "control here\n")
    _write(tmp_path, "b.md", "control here\nthe needle\n")
    r = cc.check([tmp_path / "a.md", tmp_path / "b.md"], pattern="needle", control="control")
    assert r["verdict"] == "PRESENT"
    assert r["files_read"] == 2
    assert len(r["hits"]) == 1
    assert r["hits"][0]["path"].endswith("b.md")


def test_invalid_regex_is_broken_not_a_traceback(tmp_path):
    _write(tmp_path, "a.md", "x\n")
    r = cc.check([tmp_path / "a.md"], pattern="unclosed(", control="x")
    assert r["verdict"] == "BROKEN"
    assert "regex" in r["reason"].lower()


# --- CLI contract: exit codes and machine-readable output --------------------------------------

def _run(args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def test_exit_codes_are_format_independent(tmp_path):
    f = _write(tmp_path, "a.md", "alpha needle\n")
    assert _run([str(f), "--pattern", "needle", "--control", "alpha"]).returncode == 0
    assert _run([str(f), "--pattern", "nope", "--control", "alpha"]).returncode == 1
    assert _run([str(f), "--pattern", "nope", "--control", "absent-control"]).returncode == 2


def test_json_envelope_and_still_json_on_failure(tmp_path):
    f = _write(tmp_path, "a.md", "alpha\n")
    r = _run([str(f), "--pattern", "nope", "--control", "missing", "--json"])
    assert r.returncode == 2
    payload = json.loads(r.stdout)
    assert payload["ok"] is False
    assert payload["command"] == "claim_check"
    assert payload["data"]["verdict"] == "BROKEN"


def test_warnings_go_to_stderr_not_the_parsed_stream(tmp_path):
    f = _write(tmp_path, "a.md", "alpha\n")
    r = _run([str(f), "--pattern", "nope", "--control", "missing", "--json"])
    json.loads(r.stdout)  # stdout must parse even though a diagnostic was emitted
    assert r.stderr.strip()
