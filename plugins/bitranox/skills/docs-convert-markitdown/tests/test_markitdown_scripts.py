"""Tests for the markitdown-dependent scripts' pure helpers.

These modules import ``markitdown`` (and ``openai``) at module top level, so
they are integration-only in an environment without those deps. The ``*``
fixtures in conftest.py use ``pytest.importorskip`` so these tests SKIP rather
than ERROR when the heavy deps are missing, while still providing real coverage
wherever the deps are installed.
"""


def test_extract_metadata_author_year_title(literature):
    md = literature.extract_metadata_from_filename("Smith_2023_Machine_Learning.pdf")
    assert md["year"] == "2023"
    assert md["author"] == "Smith"
    assert md["title"] == "Machine Learning"


def test_extract_metadata_no_year(literature):
    md = literature.extract_metadata_from_filename("Notes_About_Stuff.docx")
    assert "year" not in md
    assert md["author"] == "Notes"
    assert md["title"] == "About Stuff"


def test_extract_metadata_single_token(literature):
    md = literature.extract_metadata_from_filename("readme.pdf")
    assert md["title"] == "readme"
    assert "author" not in md


def test_extract_metadata_dash_separator(literature):
    md = literature.extract_metadata_from_filename("Jones-2022-Climate.pdf")
    assert md["year"] == "2022"
    assert md["author"] == "Jones"
    assert md["title"] == "2022 Climate"  # year is also part of the split parts


def test_extract_metadata_unicode_author(literature):
    # Author name with a Latin-1 accented char, embedded as chr() to keep the
    # test file pure ASCII (a write hook blocks literal non-ASCII).
    muenoz = "M" + chr(0x00FA) + "noz"  # Munoz with u-acute
    md = literature.extract_metadata_from_filename(muenoz + "_2021_Title.pdf")
    assert md["author"] == muenoz
    assert md["year"] == "2021"


def test_prompts_dict_complete(with_ai):
    expected = {"scientific", "presentation", "general", "data_viz", "medical"}
    assert set(with_ai.PROMPTS.keys()) == expected
    for value in with_ai.PROMPTS.values():
        assert value and isinstance(value, str)
        # .strip() applied in source: no surrounding whitespace.
        assert value == value.strip()


def test_batch_default_extensions_logic(batch, tmp_path):
    # batch_convert returns an empty-stats dict when no matching files exist,
    # without ever constructing a MarkItDown instance or doing network I/O.
    out = tmp_path / "out"
    stats = batch.batch_convert(input_dir=tmp_path, output_dir=out, extensions=[".pdf"])
    assert stats == {"total": 0, "success": 0, "failed": 0}
    assert out.is_dir()  # output dir is created eagerly
