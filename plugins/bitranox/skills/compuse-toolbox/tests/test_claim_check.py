"""Tests for claim_check.

The tool exists for ONE failure: a check that reports "not found" when it never really looked.
So the control-gate tests are the point, not an extra.
"""

import io
import json
import os
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


# --- a partial read must never be reported as a clean "no" ----------------------------------------

def test_an_unreadable_path_beside_a_readable_one_is_broken_not_absent(tmp_path):
    """The control matched in the file that WAS read, which proves nothing about the one that was
    not: the missing file may be exactly where the pattern lives."""
    good = _write(tmp_path, "a.md", "control line\n")
    r = cc.check([good, tmp_path / "typo.md"], pattern="needle", control="control")
    assert r["verdict"] == "BROKEN"
    assert r["files_read"] == 1
    assert any("typo.md" in u for u in r["unreadable"])
    assert "typo.md" in r["reason"]


def test_an_unreadable_path_does_not_hide_a_hit_that_was_found(tmp_path):
    """A hit in a file that was read is a fact; the unreadable one is still reported."""
    good = _write(tmp_path, "a.md", "control and the needle\n")
    r = cc.check([good, tmp_path / "typo.md"], pattern="needle", control="control")
    assert r["verdict"] == "PRESENT"
    assert any("typo.md" in u for u in r["unreadable"])


def test_cli_partial_read_exits_2_and_names_the_skipped_path(tmp_path):
    good = _write(tmp_path, "a.md", "control line\n")
    r = _run([str(good), str(tmp_path / "typo.md"), "--pattern", "needle", "--control", "control"])
    assert r.returncode == 2, r.stderr
    assert "BROKEN:" in r.stderr and "ABSENT (control matched" not in r.stderr
    assert "skipped:" in r.stderr and "typo.md" in r.stderr


def test_cli_case_sensitive_flag_is_honoured(tmp_path):
    f = _write(tmp_path, "a.md", "The LOCALIZED text\n")
    base = [str(f), "--pattern", "localized", "--control", "text"]
    assert _run(base).returncode == 0
    assert _run(base + ["--case-sensitive"]).returncode == 1


# --- reading the text the way a line-oriented grep would -------------------------------------------

def test_a_utf8_bom_does_not_defeat_an_anchored_match_on_line_one(tmp_path):
    p = tmp_path / "bom.md"
    p.write_bytes(b"\xef\xbb\xbf# Title\nalpha\n")
    r = cc.check([p], pattern="^# Title", control="alpha")
    assert r["verdict"] == "PRESENT"
    assert r["hits"][0]["line"] == 1


def test_a_form_feed_does_not_shift_line_numbers(tmp_path):
    """grep -n counts only newlines; splitlines() also breaks on \\f, U+2028 and friends."""
    p = tmp_path / "ff.md"
    p.write_bytes("a\x0cb\nneedle alpha\nx\u2028y\nneedle again\n".encode("utf-8"))
    r = cc.check([p], pattern="needle", control="alpha")
    assert [h["line"] for h in r["hits"]] == [2, 4]


def test_crlf_lines_report_text_without_the_carriage_return(tmp_path):
    p = tmp_path / "crlf.md"
    p.write_bytes(b"alpha\r\nthe needle\r\n")
    r = cc.check([p], pattern="needle$", control="alpha")
    assert r["verdict"] == "PRESENT"
    assert r["hits"][0] == {"path": str(p), "line": 2, "text": "the needle"}


# --- a file no regex could match must not be folded into ABSENT ---------------------------------

def test_a_utf16_file_with_a_bom_is_decoded_and_searched(tmp_path):
    """PowerShell 5.1 writes UTF-16LE with a BOM; read as UTF-8 it is NUL-interleaved noise."""
    w = tmp_path / "w.log"
    w.write_bytes("the needle\n".encode("utf-16"))
    a = _write(tmp_path, "a.md", "control\n")
    r = cc.check([a, w], pattern="needle", control="control")
    assert r["verdict"] == "PRESENT"
    assert r["hits"][0]["path"] == str(w)


def test_a_nul_bearing_file_is_flagged_unreadable_not_scanned(tmp_path):
    """BOM-less UTF-16 or a binary: neither regex can match it, so it must block ABSENT."""
    w = tmp_path / "w.log"
    w.write_bytes("the needle\n".encode("utf-16-le"))
    a = _write(tmp_path, "a.md", "control\n")
    r = cc.check([a, w], pattern="needle", control="control")
    assert r["verdict"] == "BROKEN"
    assert any("w.log" in u and "NUL" in u for u in r["unreadable"])


def test_files_the_control_never_matched_are_listed(tmp_path):
    a = _write(tmp_path, "a.md", "control\n")
    b = _write(tmp_path, "b.md", "nothing relevant\n")
    r = cc.check([a, b], pattern="needle", control="control")
    assert r["verdict"] == "ABSENT"
    assert r["no_control"] == [str(b)]
    cli = _run([str(a), str(b), "--pattern", "needle", "--control", "control"])
    assert cli.returncode == 1
    assert "no control match: %s" % b in cli.stderr


# --- a crash must never read as ABSENT (exit 1) ------------------------------------------------------

def test_a_regex_that_overflows_is_broken_not_a_crash(tmp_path):
    """re.compile raises OverflowError, not re.error, for a huge repeat count."""
    f = _write(tmp_path, "a.md", "alpha\n")
    r = _run([str(f), "--pattern", "a{4294967296}", "--control", "alpha"])
    assert r.returncode == 2, r.stderr
    assert "Traceback" not in r.stderr


def test_a_hit_the_console_cannot_encode_is_printed_not_a_crash(tmp_path):
    """A Windows console or pipe under cp1252 cannot encode U+2192; the hit must still print."""
    f = _write(tmp_path, "u.md", "alpha\nthe needle \u2192 here\n")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    r = subprocess.run([sys.executable, str(TOOL), str(f), "--pattern", "needle",
                        "--control", "alpha"], capture_output=True, env=env)
    assert r.returncode == 0, r.stderr
    assert b"u.md:2: the needle" in r.stdout
    assert b"Traceback" not in r.stderr


class _FailingStdout(io.StringIO):
    """A stdout whose device fails, the way a redirect to a full disk does."""

    def write(self, s):
        raise OSError(28, "No space left on device")


def test_an_unexpected_error_exits_2_not_the_absent_code(tmp_path, monkeypatch, capsys):
    f = _write(tmp_path, "a.md", "alpha needle\n")
    monkeypatch.setattr(sys, "stdout", _FailingStdout())
    rc = cc.main([str(f), "--pattern", "needle", "--control", "alpha"])
    assert rc == 2
    assert "No space left" in capsys.readouterr().err
