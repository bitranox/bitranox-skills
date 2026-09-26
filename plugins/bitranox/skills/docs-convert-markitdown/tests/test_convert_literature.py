"""End-to-end tests for scripts/convert_literature.py.

The script runs as a real subprocess. A "paper" is a text file named *.pdf, which
the offline markitdown stand-in from conftest.py returns verbatim, so these run in
CI. The one test against the REAL markitdown builds a genuine PDF and is skipped
when markitdown (with its PDF extra) is not installed.
"""

import os
import re
import sys

import pytest
import yaml

LINK = re.compile(r"\]\(<?([^)>]+)>?\)")


def _paper(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _lit(runner, tmp_path, fake_dir, *args, encoding="utf-8"):
    return runner(
        "convert_literature", [str(tmp_path / "in"), str(tmp_path / "out"), *args],
        cwd=tmp_path, pythonpath=[fake_dir], encoding=encoding,
    )


def _front_matter(md_file):
    text = md_file.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---\n", 2)[1])


def _index_links(out):
    return LINK.findall((out / "INDEX.md").read_text(encoding="utf-8"))


def test_same_name_in_two_subdirs_keeps_both(script_runner, tmp_path, fake_markitdown_dir):
    _paper(tmp_path / "in" / "a" / "Smith_2023_Deep.pdf", "PAPER A CONTENT")
    _paper(tmp_path / "in" / "b" / "Smith_2023_Deep.pdf", "PAPER B CONTENT")

    run = _lit(script_runner, tmp_path, fake_markitdown_dir, "-r", "--create-index")

    assert run.returncode == 0, run.output
    out = tmp_path / "out"
    assert "PAPER A CONTENT" in (out / "a" / "Smith_2023_Deep.md").read_text(encoding="utf-8")
    assert "PAPER B CONTENT" in (out / "b" / "Smith_2023_Deep.md").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "extra",
    [[], ["--organize-by-year"], ["-r"], ["-r", "--organize-by-year"]],
    ids=["flat", "by-year", "recursive", "recursive-by-year"],
)
def test_every_index_link_resolves(script_runner, tmp_path, fake_markitdown_dir, extra):
    _paper(tmp_path / "in" / "Jones_2022_Wide.pdf", "JONES")
    _paper(tmp_path / "in" / "Smith_2023_Deep.pdf", "SMITH")
    _paper(tmp_path / "in" / "Notes.pdf", "NO YEAR")
    if "-r" in extra:
        _paper(tmp_path / "in" / "sub" / "Lee_2021_Nested.pdf", "LEE")

    run = _lit(script_runner, tmp_path, fake_markitdown_dir, "--create-index", *extra)

    assert run.returncode == 0, run.output
    out = tmp_path / "out"
    links = _index_links(out)
    assert len(links) == (4 if "-r" in extra else 3)
    for link in links:
        assert (out / link).is_file(), link


@pytest.mark.skipif(sys.platform == "win32", reason='" and \\ are not legal in Windows filenames')
def test_front_matter_parses_with_quote_and_backslash(script_runner, tmp_path, fake_markitdown_dir):
    _paper(tmp_path / "in" / 'Doe_2020_The "Best" Paper.pdf', "Q")
    _paper(tmp_path / "in" / "Roe_2019_Back\\slash.pdf", "B")

    run = _lit(script_runner, tmp_path, fake_markitdown_dir)

    assert run.returncode == 0, run.output
    quoted = _front_matter(tmp_path / "out" / 'Doe_2020_The "Best" Paper.md')
    assert quoted["title"] == 'The "Best" Paper'
    assert quoted["source"] == 'Doe_2020_The "Best" Paper.pdf'
    slashed = _front_matter(tmp_path / "out" / "Roe_2019_Back\\slash.md")
    assert slashed["title"] == "Back\\slash"


def test_front_matter_parses_for_a_plain_name(script_runner, tmp_path, fake_markitdown_dir):
    _paper(tmp_path / "in" / "Doe_2020_The_Best_Paper.pdf", "P")

    run = _lit(script_runner, tmp_path, fake_markitdown_dir)

    assert run.returncode == 0, run.output
    meta = _front_matter(tmp_path / "out" / "Doe_2020_The_Best_Paper.md")
    assert (meta["title"], meta["author"], meta["year"]) == ("The Best Paper", "Doe", 2020)


def test_uppercase_pdf_suffix_is_found(script_runner, tmp_path, fake_markitdown_dir):
    _paper(tmp_path / "in" / "Upper_2021_Case.PDF", "UPPER")
    _paper(tmp_path / "in" / "Lower_2021_Case.pdf", "LOWER")

    run = _lit(script_runner, tmp_path, fake_markitdown_dir)

    assert run.returncode == 0, run.output
    assert "Found 2 PDF file(s)" in run.output
    assert "UPPER" in (tmp_path / "out" / "Upper_2021_Case.md").read_text(encoding="utf-8")


def test_same_stem_differing_only_in_case_is_a_collision(script_runner, tmp_path, fake_markitdown_dir):
    _paper(tmp_path / "in" / "Doe_2020_X.pdf", "ONE")
    _paper(tmp_path / "in" / "Doe_2020_X.PDF", "TWO")
    if len(os.listdir(tmp_path / "in")) != 2:
        pytest.skip("case-insensitive file system: the two names are one file")

    run = _lit(script_runner, tmp_path, fake_markitdown_dir)

    assert run.returncode == 2, run.output
    assert "collision" in run.output.lower()


def test_cp1252_console_with_cjk_name_converts_every_paper(script_runner, tmp_path, fake_markitdown_dir):
    cjk = chr(0x674E) + "_2021_" + chr(0x7814) + chr(0x7A76) + ".pdf"
    _paper(tmp_path / "in" / cjk, "CJK PAPER")
    _paper(tmp_path / "in" / "Zed_2020_Later.pdf", "ZED")

    run = _lit(script_runner, tmp_path, fake_markitdown_dir, "--create-index", encoding="cp1252")

    assert run.returncode == 0, run.output
    names = sorted(p.name for p in (tmp_path / "out").glob("*.md"))
    assert names == sorted(["INDEX.md", "Zed_2020_Later.md", cjk[:-4] + ".md"])


def test_failed_paper_exits_2_and_stays_out_of_the_index(script_runner, tmp_path, fake_markitdown_dir):
    _paper(tmp_path / "in" / "Good_2020_Paper.pdf", "GOOD")
    _paper(tmp_path / "in" / "Bad_2021_Paper.pdf", "FAIL-CONVERSION")

    run = _lit(script_runner, tmp_path, fake_markitdown_dir, "--create-index")

    assert run.returncode == 2, run.output
    assert "Failed:          1" in run.output
    index = (tmp_path / "out" / "INDEX.md").read_text(encoding="utf-8")
    assert "Good_2020_Paper.pdf" in index
    assert "Bad_2021_Paper.pdf" not in index


def test_no_pdfs_exits_1(script_runner, tmp_path, fake_markitdown_dir):
    _paper(tmp_path / "in" / "notes.txt", "X")

    run = _lit(script_runner, tmp_path, fake_markitdown_dir)

    assert run.returncode == 1, run.output
    assert "No PDF files found" in run.output


def test_missing_input_dir_exits_2(script_runner, tmp_path, fake_markitdown_dir):
    run = _lit(script_runner, tmp_path, fake_markitdown_dir)

    assert run.returncode == 2, run.output
    assert "does not exist" in run.output


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permission bits enforced (not root, not Windows)",
)
def test_unreadable_subdir_is_reported_not_skipped(script_runner, tmp_path, fake_markitdown_dir):
    _paper(tmp_path / "in" / "Ok_2020_Paper.pdf", "OK")
    locked = tmp_path / "in" / "locked"
    _paper(locked / "Hidden_2020_Paper.pdf", "HIDDEN")
    locked.chmod(0)
    try:
        run = _lit(script_runner, tmp_path, fake_markitdown_dir, "-r")
    finally:
        locked.chmod(0o755)

    assert run.returncode == 2, run.output
    assert "locked" in run.output


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permission bits enforced (not root, not Windows)",
)
def test_unreadable_subdir_is_counted_in_the_total(script_runner, tmp_path, fake_markitdown_dir):
    """The unreadable directory is one of the failures, so it is part of the total too."""
    _paper(tmp_path / "in" / "Ok_2020_Paper.pdf", "OK")
    locked = tmp_path / "in" / "locked"
    _paper(locked / "Hidden_2020_Paper.pdf", "HIDDEN")
    locked.chmod(0)
    try:
        run = _lit(script_runner, tmp_path, fake_markitdown_dir, "-r")
    finally:
        locked.chmod(0o755)

    assert re.search(r"^Total:\s+2\b", run.stdout, re.MULTILINE), run.stdout
    assert "Successful:      1" in run.stdout
    assert "Failed:          1" in run.stdout
    assert "Success rate:    50.0%" in run.stdout


def test_case_only_collision_names_every_output_it_would_write(
    script_runner, tmp_path, fake_markitdown_dir
):
    _paper(tmp_path / "in" / "Doe_2020_X.pdf", "ONE")
    _paper(tmp_path / "in" / "Doe_2020_x.pdf", "TWO")
    if len(os.listdir(tmp_path / "in")) != 2:
        pytest.skip("case-insensitive file system: the two names are one file")

    run = _lit(script_runner, tmp_path, fake_markitdown_dir)

    assert run.returncode == 2, run.output
    lines = [line for line in run.stdout.splitlines() if line.startswith("[FAIL] Output collision")]
    assert len(lines) == 2, run.stdout
    for line in lines:
        assert "Doe_2020_X.md" in line and "Doe_2020_x.md" in line, line
        assert "case" in line, line


# DEL, C1 controls, NEL and the Unicode line/paragraph separators: YAML either refuses them
# outright (not printable) or reads them as line breaks inside a double-quoted scalar.
_YAML_HOSTILE = ["\x7f", "\x80", "\x85", "\x9b", "\x9f", "\u2028", "\u2029"]


@pytest.mark.parametrize("char", _YAML_HOSTILE, ids=[hex(ord(c)) for c in _YAML_HOSTILE])
def test_front_matter_round_trips_a_control_character(literature, char):
    metadata = {
        "title": "A" + char + "B", "author": "Doe" + char, "year": "2020",
        "source_file": "Doe_2020_A" + char + "B.pdf", "converted_date": "2026-01-01T00:00:00",
    }

    text = literature.render_paper(metadata, "BODY")

    front = yaml.safe_load(text.split("---\n", 2)[1])
    assert front["title"] == metadata["title"]
    assert front["author"] == metadata["author"]
    assert front["source"] == metadata["source_file"]


def test_front_matter_parses_for_a_filename_holding_del(script_runner, tmp_path, fake_markitdown_dir):
    name = "Doe_2020_A\x7fB.pdf"
    try:
        _paper(tmp_path / "in" / name, "DEL")
    except OSError:
        pytest.skip("this file system refuses DEL in a filename")

    run = _lit(script_runner, tmp_path, fake_markitdown_dir)

    assert run.returncode == 0, run.output
    meta = _front_matter(tmp_path / "out" / "Doe_2020_A\x7fB.md")
    assert meta["source"] == name


def test_help_works_without_markitdown(script_runner, block_import, tmp_path):
    run = script_runner("convert_literature", ["--help"], cwd=tmp_path, prelude=block_import("markitdown"))

    assert run.returncode == 0, run.output
    assert "usage" in run.stdout.lower()


def test_pep723_block_declares_markitdown_pdf(scripts_dir):
    text = (scripts_dir / "convert_literature.py").read_text(encoding="utf-8")
    block = text.split("# /// script", 1)[1].split("# ///", 1)[0]
    assert "markitdown[pdf]" in block


def test_title_always_comes_from_the_filename(literature):
    # There is no content-title fallback: every name yields a title, so none is needed.
    for name in ["2301.01234.pdf", "readme.pdf", "Smith_2023_X.pdf", "_.pdf", "2020.pdf"]:
        assert literature.extract_metadata_from_filename(name)["title"], name


def _minimal_pdf(text):
    """A one-page PDF showing `text` (ASCII only), with a correct xref table."""
    stream = ("BT /F1 12 Tf 72 720 Td (" + text + ") Tj ET").encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    data = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(number).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n0000000000 65535 f \n"
    data += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    data += b"trailer\n<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\n"
    data += b"startxref\n" + str(xref).encode() + b"\n%%EOF\n"
    return data


def test_real_markitdown_same_name_pdfs(script_runner, tmp_path):
    pytest.importorskip("markitdown")
    pytest.importorskip("pdfminer")
    for sub, text in (("a", "PAPER A CONTENT"), ("b", "PAPER B CONTENT")):
        target = tmp_path / "in" / sub / "Smith_2023_Deep.pdf"
        target.parent.mkdir(parents=True)
        target.write_bytes(_minimal_pdf(text))

    run = script_runner(
        "convert_literature", [str(tmp_path / "in"), str(tmp_path / "out"), "-r", "--create-index"],
        cwd=tmp_path,
    )

    assert run.returncode == 0, run.output
    out = tmp_path / "out"
    assert "PAPER A CONTENT" in (out / "a" / "Smith_2023_Deep.md").read_text(encoding="utf-8")
    assert "PAPER B CONTENT" in (out / "b" / "Smith_2023_Deep.md").read_text(encoding="utf-8")
