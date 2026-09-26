"""End-to-end tests for scripts/batch_convert.py.

The script runs as a real subprocess. Conversion goes through the offline
markitdown stand-in from conftest.py (it returns the file's own text), except in
the test marked as using the real library, which is skipped when markitdown is
not installed.
"""

import os
import sys

import pytest


def _put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("<html><body><h1>" + text + "</h1></body></html>", encoding="utf-8")


def _batch(run_script, tmp_path, fake_dir, *args, encoding="utf-8"):
    return run_script(
        "batch_convert", [str(tmp_path / "in"), str(tmp_path / "out"), *args],
        cwd=tmp_path, pythonpath=[fake_dir], encoding=encoding,
    )


def test_same_stem_in_two_subdirs_keeps_both(script_runner, tmp_path, fake_markitdown_dir):
    _put(tmp_path / "in" / "sub1" / "x.html", "SUB1")
    _put(tmp_path / "in" / "sub2" / "x.html", "SUB2")
    _put(tmp_path / "in" / "a.html", "TOP")

    run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", ".html", "-r")

    assert run.returncode == 0, run.output
    out = tmp_path / "out"
    assert "SUB1" in (out / "sub1" / "x.md").read_text(encoding="utf-8")
    assert "SUB2" in (out / "sub2" / "x.md").read_text(encoding="utf-8")
    assert "TOP" in (out / "a.md").read_text(encoding="utf-8")


def test_same_stem_two_extensions_is_a_reported_collision(script_runner, tmp_path, fake_markitdown_dir):
    _put(tmp_path / "in" / "a.html", "ONE")
    _put(tmp_path / "in" / "a.htm", "TWO")

    run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", ".html", ".htm")

    assert run.returncode == 2, run.output
    assert "collision" in run.output.lower()
    assert not (tmp_path / "out" / "a.md").exists()


def test_distinct_stems_do_not_collide(script_runner, tmp_path, fake_markitdown_dir):
    _put(tmp_path / "in" / "sub1" / "x.html", "SUB1")
    _put(tmp_path / "in" / "sub2" / "y.html", "SUB2")

    run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", ".html", "-r")

    assert run.returncode == 0, run.output
    assert "collision" not in run.output.lower()


@pytest.mark.parametrize(
    "name,extensions",
    [("a.html", [".html", ".html"]), ("b.tar.gz", [".gz", ".tar.gz"])],
)
def test_overlapping_extensions_convert_a_file_once(script_runner, tmp_path, fake_markitdown_dir, name, extensions):
    _put(tmp_path / "in" / name, "ONCE")

    run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", *extensions)

    assert run.returncode == 0, run.output
    assert "Found 1 file(s)" in run.output
    assert run.output.count("[OK] Converted") == 1


def test_uppercase_suffix_is_found(script_runner, tmp_path, fake_markitdown_dir):
    _put(tmp_path / "in" / "a.html", "LOWER")
    _put(tmp_path / "in" / "REPORT.HTML", "UPPER")

    run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", ".html")

    assert run.returncode == 0, run.output
    assert "Found 2 file(s)" in run.output
    assert "UPPER" in (tmp_path / "out" / "REPORT.md").read_text(encoding="utf-8")


def test_no_matching_files_exits_1(script_runner, tmp_path, fake_markitdown_dir):
    _put(tmp_path / "in" / "a.html", "X")

    run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", ".pdf")

    assert run.returncode == 1, run.output
    assert "No files found" in run.output


def test_missing_input_dir_exits_2(script_runner, tmp_path, fake_markitdown_dir):
    run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", ".html")

    assert run.returncode == 2, run.output
    assert "does not exist" in run.output


def test_conversion_failure_exits_2_and_is_listed(script_runner, tmp_path, fake_markitdown_dir):
    _put(tmp_path / "in" / "good.html", "GOOD")
    _put(tmp_path / "in" / "bad.html", "FAIL-CONVERSION")

    run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", ".html")

    assert run.returncode == 2, run.output
    assert "Failed:          1" in run.output
    assert "bad.html" in run.output.split("Failed conversions:")[1]
    assert (tmp_path / "out" / "good.md").exists()


def test_cp1252_console_with_non_ascii_name_converts(script_runner, tmp_path, fake_markitdown_dir):
    stem = chr(0x6587) + chr(0x66F8)  # a CJK name cp1252 cannot encode
    _put(tmp_path / "in" / (stem + ".html"), "CJK")

    run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", ".html", "-v", encoding="cp1252")

    assert run.returncode == 0, run.output
    assert "[FAIL]" not in run.output
    assert "CJK" in (tmp_path / "out" / (stem + ".md")).read_text(encoding="utf-8")


def test_help_works_without_markitdown(script_runner, block_import, tmp_path):
    run = script_runner(
        "batch_convert", ["--help"], cwd=tmp_path,
        prelude=block_import("markitdown"),
    )

    assert run.returncode == 0, run.output
    assert "usage" in run.stdout.lower()


def test_missing_markitdown_is_a_clear_error(script_runner, block_import, tmp_path):
    _put(tmp_path / "in" / "a.html", "X")

    run = script_runner(
        "batch_convert", [str(tmp_path / "in"), str(tmp_path / "out"), "-e", ".html"],
        cwd=tmp_path, prelude=block_import("markitdown"),
    )

    assert run.returncode == 2, run.output
    assert "markitdown" in run.stderr


def test_pep723_block_declares_markitdown(scripts_dir):
    text = (scripts_dir / "batch_convert.py").read_text(encoding="utf-8")
    block = text.split("# /// script", 1)[1].split("# ///", 1)[0]
    assert "markitdown[all]" in block


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permission bits enforced (not root, not Windows)",
)
def test_unreadable_subdir_is_reported_not_skipped(script_runner, tmp_path, fake_markitdown_dir):
    _put(tmp_path / "in" / "ok.html", "OK")
    locked = tmp_path / "in" / "locked"
    _put(locked / "hidden.html", "HIDDEN")
    locked.chmod(0)
    try:
        run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", ".html", "-r")
    finally:
        locked.chmod(0o755)

    assert run.returncode == 2, run.output
    assert "locked" in run.output


def test_in_process_empty_dir_returns_zero_counts(batch, tmp_path):
    # No matching files: no converter is built, so this runs without markitdown.
    out = tmp_path / "out"
    stats = batch.batch_convert(input_dir=tmp_path, output_dir=out, extensions=[".pdf"])
    assert (stats["total"], stats["success"], stats["failed"]) == (0, 0, 0)
    assert out.is_dir()  # output dir is created eagerly


def test_real_markitdown_html_tree(script_runner, tmp_path):
    pytest.importorskip("markitdown")
    _put(tmp_path / "in" / "sub1" / "x.html", "SUB1")
    _put(tmp_path / "in" / "sub2" / "x.html", "SUB2")

    run = script_runner(
        "batch_convert", [str(tmp_path / "in"), str(tmp_path / "out"), "-e", ".html", "-r"],
        cwd=tmp_path,
    )

    assert run.returncode == 0, run.output
    assert "SUB1" in (tmp_path / "out" / "sub1" / "x.md").read_text(encoding="utf-8")
    assert "SUB2" in (tmp_path / "out" / "sub2" / "x.md").read_text(encoding="utf-8")


def _summary_counts(output):
    """The Total/Successful/Failed numbers of the printed summary."""
    counts = {}
    for line in output.splitlines():
        label, _, rest = line.partition(":")
        if label.startswith("Total") or label in ("Successful", "Failed"):
            counts[label.split()[0]] = int(rest.split()[0])
    return counts


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permission bits enforced (not root, not Windows)",
)
def test_unreadable_subdir_is_counted_in_the_total(script_runner, tmp_path, fake_markitdown_dir):
    """An unreadable directory is a failure, so it is part of the total: the summary must never
    read "Total 1 / Successful 1 / Failed 1 / 100%"."""
    _put(tmp_path / "in" / "ok.html", "OK")
    locked = tmp_path / "in" / "locked"
    _put(locked / "hidden.html", "HIDDEN")
    locked.chmod(0)
    try:
        run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", ".html", "-r")
    finally:
        locked.chmod(0o755)

    counts = _summary_counts(run.stdout)
    assert counts == {"Total": 2, "Successful": 1, "Failed": 1}, run.stdout
    assert "Success rate:    50.0%" in run.stdout
    assert "100.0%" not in run.stdout


def test_case_only_collision_names_every_output_it_would_write(
    script_runner, tmp_path, fake_markitdown_dir
):
    """Two names that differ only in case are one file on Windows and macOS. Each failure line
    must name both outputs, not claim that each input alone "would all write" its own name."""
    _put(tmp_path / "in" / "X.html", "UPPER")
    _put(tmp_path / "in" / "x.html", "LOWER")
    if len(os.listdir(tmp_path / "in")) != 2:
        pytest.skip("case-insensitive file system: the two names are one file")

    run = _batch(script_runner, tmp_path, fake_markitdown_dir, "-e", ".html")

    assert run.returncode == 2, run.output
    lines = [line for line in run.stdout.splitlines() if line.startswith("[FAIL] Output collision")]
    assert len(lines) == 2, run.stdout
    for line in lines:
        assert "X.md" in line and "x.md" in line, line
        assert "case" in line, line
