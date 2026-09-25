"""Tests for conflict_scan.py - find git merge-conflict markers. ASCII only."""
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

import conflict_scan as C

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "conflict_scan.py"


def _run(*args, cwd=None, env=None):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True,
                          cwd=cwd, env=env)


def test_scan_text_finds_all_three_markers():
    text = (
        "line one\n"
        "<<<<<<< HEAD\n"
        "ours\n"
        "=======\n"
        "theirs\n"
        ">>>>>>> branch\n"
        "line last\n"
    )
    hits = C.scan_text(text)
    assert [ln for ln, _ in hits] == [2, 4, 6]
    assert hits[0][1].startswith("<<<<<<<")


def test_scan_text_clean_is_empty():
    assert C.scan_text("no markers here\njust code\n") == []


def test_marker_must_be_at_line_start():
    # a marker in the middle of a line (e.g. in a string/doc) is NOT a conflict marker. The lone
    # ======= is followed by text, the shape a half-resolved hunk leaves, so it still counts.
    text = 'print("<<<<<<< not a conflict")\n=======\ntheirs\n'
    hits = C.scan_text(text)
    assert [ln for ln, _ in hits] == [2]   # only the real line-start ======= counts


def test_scan_paths_reports_per_file(tmp_path):
    good = tmp_path / "clean.py"; good.write_text("ok\n", encoding="utf-8")
    bad = tmp_path / "conflict.py"; bad.write_text("<<<<<<< HEAD\nx\n=======\ny\n>>>>>>> b\n", encoding="utf-8")
    res = C.scan_paths([str(good), str(bad)])
    assert str(good) not in res
    assert res[str(bad)] == [1, 3, 5]


# --- a lone ======= is a Markdown heading underline far more often than a marker ------------------

def test_a_setext_heading_underline_is_not_a_conflict_marker():
    assert C.scan_text("Summary\n=======\n\nText.\n") == []
    assert C.scan_text("Summary\n=======\n") == []   # heading as the last thing in the file


@pytest.mark.parametrize("text", [
    "=======\nTitle\n=======\n\nBody.\n",              # an RST title opening the file
    "Intro.\n\n=======\nTitle\n=======\n\nBody.\n",    # an RST title mid-document
    "=======\nTitle\n=======\n",                       # an RST title as the whole file
])
def test_an_rst_overline_title_is_not_a_conflict_marker(text):
    # The underline already passed as a heading; its overline has a blank line (or nothing)
    # above and the title below, so it was flagged as a half-resolved hunk's middle marker.
    assert C.scan_text(text) == []


@pytest.mark.parametrize("text, lines", [
    # A real conflict whose ours side is empty has the overline's shape - inside a span it counts.
    ("<<<<<<< HEAD\n\n=======\ntheirs\n>>>>>>> b\n", [1, 3, 5]),
    ("<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> b\n", [1, 3, 5]),
    # Blank above and text below, but no matching underline: not a title, so it still counts.
    ("a\n\n=======\ntheirs\nmore\n", [3]),
    # Overline and underline with text directly under the underline: not a clean title shape.
    ("=======\nTitle\n=======\nBody\n", [1, 3]),
])
def test_a_marker_that_is_not_a_complete_rst_title_still_counts(text, lines):
    assert [ln for ln, _ in C.scan_text(text)] == lines


def test_a_lone_middle_marker_between_text_lines_still_counts():
    """A half-resolved hunk can leave only the middle marker, with code on both sides."""
    assert [ln for ln, _ in C.scan_text("ours\n=======\ntheirs\n")] == [2]


def test_a_middle_marker_inside_a_conflict_span_always_counts():
    text = "<<<<<<< HEAD\nours\n=======\n\ntheirs\n>>>>>>> b\n"
    assert [ln for ln, _ in C.scan_text(text)] == [1, 3, 6]


def test_the_diff3_base_marker_counts():
    text = "<<<<<<< HEAD\nours\n||||||| base\norig\n=======\ntheirs\n>>>>>>> b\n"
    assert [ln for ln, _ in C.scan_text(text)] == [1, 3, 5, 7]


# --- line numbers and decoding match what grep -n reports ----------------------------------------

def test_a_form_feed_does_not_shift_marker_line_numbers():
    assert [ln for ln, _ in C.scan_text("a\n\x0cb\nc\n<<<<<<< HEAD\n")] == [4]
    assert [ln for ln, _ in C.scan_text("a\u2028b\n<<<<<<< HEAD\n")] == [2]


def test_a_crlf_file_is_scanned(tmp_path):
    f = tmp_path / "crlf.txt"
    f.write_bytes(b"<<<<<<< HEAD\r\nx\r\n=======\r\ny\r\n>>>>>>> b\r\n")
    assert C.scan_paths([f]) == {str(f): [1, 3, 5]}


def test_a_utf8_bom_does_not_hide_a_marker_on_line_one(tmp_path):
    f = tmp_path / "bom.txt"
    f.write_bytes(b"\xef\xbb\xbf<<<<<<< HEAD\nx\n")
    assert C.scan_paths([f]) == {str(f): [1]}


# --- CLI: exit codes 0 clean / 1 markers / 2 error, and one path:line: text row per hit -----------

def test_cli_clean_tree_exits_0(tmp_path):
    (tmp_path / "ok.txt").write_text("fine\n", encoding="utf-8")
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout == b""


def test_cli_reports_one_path_line_text_row_per_marker(tmp_path):
    f = tmp_path / "multi.txt"
    f.write_text("<<<<<<< HEAD\nx\n=======\ny\n>>>>>>> b\n", encoding="utf-8")
    r = _run(f)
    assert r.returncode == 1
    rows = r.stdout.decode().splitlines()
    assert rows[:3] == ["%s:1: <<<<<<< HEAD" % f, "%s:3: =======" % f, "%s:5: >>>>>>> b" % f]
    assert rows[3] == "CONFLICT MARKERS in 1 file(s)"


def test_cli_skips_the_git_directory(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "MERGE_MSG").write_text("<<<<<<< HEAD\n", encoding="utf-8")
    assert _run(tmp_path).returncode == 0


def test_cli_default_path_is_the_cwd(tmp_path):
    (tmp_path / "c.txt").write_text(">>>>>>> b\n", encoding="utf-8")
    r = _run(cwd=tmp_path)
    assert r.returncode == 1
    assert b"c.txt:1: >>>>>>> b" in r.stdout


def test_cli_missing_path_is_an_error_not_a_clean_tree(tmp_path):
    r = _run(tmp_path / "does_not_exist.txt")
    assert r.returncode == 2
    assert b"does_not_exist.txt" in r.stderr


def test_cli_missing_path_beside_a_marker_still_exits_2_and_lists_the_marker(tmp_path):
    f = tmp_path / "c.txt"
    f.write_text("<<<<<<< HEAD\n", encoding="utf-8")
    r = _run(f, tmp_path / "typo.txt")
    assert r.returncode == 2
    assert b"c.txt:1:" in r.stdout
    assert b"typo.txt" in r.stderr


@pytest.mark.skipif(sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="needs POSIX permissions that bind the running user (root reads anyway)")
def test_cli_unreadable_subdir_is_an_error_not_a_silent_skip(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "x.txt").write_text("<<<<<<< HEAD\n", encoding="utf-8")
    sub.chmod(0)
    try:
        r = _run(tmp_path)
    finally:
        sub.chmod(0o755)
    assert r.returncode == 2
    assert b"sub" in r.stderr


@pytest.mark.skipif(sys.platform != "linux",
                    reason="only Linux filesystems accept a filename that is not valid UTF-8")
def test_cli_a_non_utf8_filename_does_not_truncate_the_listing(tmp_path):
    bad = os.path.join(os.fsencode(tmp_path), b"a\xff")
    with open(bad, "wb") as fh:
        fh.write(b"<<<<<<< HEAD\n")
    (tmp_path / "b.txt").write_text("<<<<<<< HEAD\n", encoding="utf-8")
    r = _run(tmp_path)
    assert r.returncode == 1, r.stderr
    assert b"b.txt:1:" in r.stdout
    assert b"CONFLICT MARKERS in 2 file(s)" in r.stdout


def test_cli_a_marker_line_the_console_cannot_encode_is_printed(tmp_path):
    f = tmp_path / "u.txt"
    f.write_text("<<<<<<< HEAD \u2192 feature\n", encoding="utf-8")
    r = _run(f, env=dict(os.environ, PYTHONIOENCODING="cp1252"))
    assert r.returncode == 1, r.stderr
    assert b"CONFLICT MARKERS in 1 file(s)" in r.stdout


class _FailingStdout(io.StringIO):
    """A stdout whose device fails, the way a redirect to a full disk does."""

    def write(self, s):
        raise OSError(28, "No space left on device")


def test_an_unexpected_error_exits_2_not_the_markers_code(tmp_path, monkeypatch, capsys):
    f = tmp_path / "c.txt"
    f.write_text("<<<<<<< HEAD\n", encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", _FailingStdout())
    assert C.main([str(f)]) == 2
    assert "No space left" in capsys.readouterr().err
