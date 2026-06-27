"""Tests for reformat_tables.py.

All inputs are real markdown. Any required non-ASCII char is built via chr(),
never pasted literally (a write hook blocks literal non-ASCII).
"""

import subprocess
import sys
from pathlib import Path

import pytest

import reformat_tables as R

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "reformat_tables.py"


# --------------------------------------------------------------------------
# Helpers for pure-function tests on the table reformatter
# --------------------------------------------------------------------------


def fmt(text):
    """Reformat a multi-line table string, return list of output lines."""
    return R.reformat_table(text.strip("\n").split("\n"))


# --------------------------------------------------------------------------
# split_table_row
# --------------------------------------------------------------------------


def test_split_basic():
    assert R.split_table_row("| a | b | c |") == ["a", "b", "c"]


def test_split_no_outer_pipes():
    assert R.split_table_row("a | b | c") == ["a", "b", "c"]


def test_split_pipe_in_backticks_not_a_separator():
    assert R.split_table_row("| `a | b` | c |") == ["`a | b`", "c"]


def test_split_escaped_pipe_kept():
    assert R.split_table_row(r"| a \| b | c |") == [r"a \| b", "c"]


# --------------------------------------------------------------------------
# separator parsing / alignment
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cell,expected",
    [
        ("---", (False, False, True)),
        (":---", (True, False, True)),
        ("---:", (False, True, True)),
        (":---:", (True, True, True)),
        ("  :-:  ", (True, True, True)),
        ("", (False, False, False)),
        ("abc", (False, False, False)),
        (":::", (False, False, False)),
    ],
)
def test_parse_separator_cell(cell, expected):
    assert R.parse_separator_cell(cell) == expected


def test_is_separator_row():
    assert R.is_separator_row(["---", ":---:", "---:"]) is True
    assert R.is_separator_row(["---", "abc"]) is False
    assert R.is_separator_row([]) is False


# --------------------------------------------------------------------------
# reformat_table - core behaviours
# --------------------------------------------------------------------------


def test_basic_padding():
    src = """
| Name | Age | City |
|---|---|---|
| Alice | 30 | NYC |
| Bob | 5 | Los Angeles |
"""
    expected = [
        "| Name  | Age | City        |",
        "|-------|-----|-------------|",
        "| Alice | 30  | NYC         |",
        "| Bob   | 5   | Los Angeles |",
    ]
    assert fmt(src) == expected


def test_separator_dashes_touch_pipes():
    out = fmt("| a | b |\n|---|---|\n| x | y |")
    sep = out[1]
    # No spaces anywhere in the separator row, and dashes are flush with pipes.
    assert " " not in sep
    assert sep == "|---|---|"


def test_alignment_markers_preserved():
    src = """
| Left | Center | Right |
| :--- | :---: | ---: |
| a | b | c |
"""
    expected = [
        "| Left | Center | Right |",
        "|:-----|:------:|------:|",
        "| a    | b      | c     |",
    ]
    assert fmt(src) == expected


def test_minimum_width_centered_marker():
    # Smallest centered separator must remain valid (":-:"), not collapse to "::".
    out = fmt("| a | b |\n|:-:|:-:|\n| a | b |")
    assert out[1] == "|:-:|:-:|"


def test_inconsistent_column_count_bails():
    src = "| a | b |\n|---|---|\n| x | y | z |"
    lines = src.split("\n")
    # Returned unchanged because row 3 has 3 cols, header has 2.
    assert R.reformat_table(lines) == lines


def test_non_separator_second_row_bails():
    lines = ["| a | b |", "| x | y |", "| 1 | 2 |"]
    assert R.reformat_table(lines) == lines


def test_pipe_in_backtick_span_single_column():
    # The backtick span hides the inner pipe -> two columns, not three.
    out = fmt("| `a | b` | c |\n|---|---|\n| 1 | 2 |")
    assert out == [
        "| `a | b` | c |",
        "|---------|---|",
        "| 1       | 2 |",
    ]


# --------------------------------------------------------------------------
# blockquote tables
# --------------------------------------------------------------------------


def test_blockquote_table(tmp_path):
    src = "> | k | v |\n> |---|---|\n> | aaa | b |\n"
    f = tmp_path / "bq.md"
    f.write_text(src, encoding="utf-8")
    assert R.reformat_file(f) is True
    assert f.read_text(encoding="utf-8") == (
        "> | k   | v |\n"
        "> |-----|---|\n"
        "> | aaa | b |\n"
    )


# --------------------------------------------------------------------------
# fenced code blocks (file level)
# --------------------------------------------------------------------------


def test_python_fence_untouched(tmp_path):
    src = (
        "Text.\n\n"
        "```python\n"
        "| not | a | table |\n"
        "|---|---|---|\n"
        "| x | y | z |\n"
        "```\n"
    )
    f = tmp_path / "py.md"
    f.write_text(src, encoding="utf-8")
    assert R.reformat_file(f) is False
    assert f.read_text(encoding="utf-8") == src


def test_markdown_fence_reformatted(tmp_path):
    src = (
        "Text.\n\n"
        "```markdown\n"
        "| a | bb | ccc |\n"
        "|---|---|---|\n"
        "| 1 | 2 | 3 |\n"
        "```\n"
    )
    f = tmp_path / "md.md"
    f.write_text(src, encoding="utf-8")
    assert R.reformat_file(f) is True
    assert f.read_text(encoding="utf-8") == (
        "Text.\n\n"
        "```markdown\n"
        "| a | bb | ccc |\n"
        "|---|----|-----|\n"
        "| 1 | 2  | 3   |\n"
        "```\n"
    )


def test_md_alias_fence_reformatted(tmp_path):
    src = "```md\n| a | bb |\n|---|---|\n| 1 | 2 |\n```\n"
    f = tmp_path / "alias.md"
    f.write_text(src, encoding="utf-8")
    assert R.reformat_file(f) is True
    assert "|---|----|" in f.read_text(encoding="utf-8")


def test_tilde_python_fence_untouched(tmp_path):
    src = "~~~python\n| a | b |\n|---|---|\n| longcell | y |\n~~~\n"
    f = tmp_path / "tilde.md"
    f.write_text(src, encoding="utf-8")
    assert R.reformat_file(f) is False


# --------------------------------------------------------------------------
# whole-file behaviour & non-ASCII content
# --------------------------------------------------------------------------


def test_non_ascii_cell_content_padded(tmp_path):
    # Build a non-ASCII word without pasting a literal glyph: "caf" + e-acute.
    cafe = "caf" + chr(0x00E9)  # 'cafe' with acute accent, 4 code points
    src = "| a | place |\n|---|---|\n| 1 | " + cafe + " |\n"
    f = tmp_path / "u.md"
    f.write_text(src, encoding="utf-8")
    R.reformat_file(f)
    out = f.read_text(encoding="utf-8")
    # 'place' (5) vs cafe (4) -> column width 5: cafe ljust to 5 (one pad space),
    # then the cell wrapper adds a leading and trailing space.
    assert "| " + cafe + "  |" in out


def test_no_change_returns_false(tmp_path):
    src = (
        "| Name  | Age |\n"
        "|-------|-----|\n"
        "| Alice | 30  |\n"
    )
    f = tmp_path / "ok.md"
    f.write_text(src, encoding="utf-8")
    assert R.reformat_file(f) is False
    assert f.read_text(encoding="utf-8") == src


def test_check_only_does_not_write(tmp_path):
    src = "| a | b |\n|---|---|\n| longvalue | y |\n"
    f = tmp_path / "c.md"
    f.write_text(src, encoding="utf-8")
    assert R.reformat_file(f, check_only=True) is True
    assert f.read_text(encoding="utf-8") == src  # unchanged on disk


def test_backup_created(tmp_path):
    src = "| a | b |\n|---|---|\n| longvalue | y |\n"
    f = tmp_path / "b.md"
    f.write_text(src, encoding="utf-8")
    R.reformat_file(f, backup=True)
    bak = tmp_path / "b.md.bak"
    assert bak.exists()
    assert bak.read_text(encoding="utf-8") == src


def test_idempotency(tmp_path):
    src = """
| Name | Age | City |
|---|---|---|
| Alice | 30 | NYC |
| Bob | 5 | Los Angeles |
"""
    f = tmp_path / "idem.md"
    f.write_text(src.strip("\n") + "\n", encoding="utf-8")
    assert R.reformat_file(f) is True
    once = f.read_text(encoding="utf-8")
    assert R.reformat_file(f) is False  # second pass is a no-op
    assert f.read_text(encoding="utf-8") == once


# --------------------------------------------------------------------------
# CLI / exit codes
# --------------------------------------------------------------------------


def run_cli(*cli_args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *cli_args],
        capture_output=True,
        text=True,
    )


def test_cli_check_misaligned_exits_1(tmp_path):
    f = tmp_path / "m.md"
    f.write_text("| a | b |\n|---|---|\n| longvalue | y |\n", encoding="utf-8")
    r = run_cli("--check", str(f))
    assert r.returncode == 1
    assert "Would reformat" in r.stdout


def test_cli_check_aligned_exits_0(tmp_path):
    f = tmp_path / "a.md"
    f.write_text(
        "| a         | b |\n|-----------|---|\n| longvalue | y |\n",
        encoding="utf-8",
    )
    r = run_cli("--check", str(f))
    assert r.returncode == 0
    assert "Unchanged" in r.stdout


def test_cli_reformat_writes(tmp_path):
    f = tmp_path / "w.md"
    f.write_text("| a | b |\n|---|---|\n| longvalue | y |\n", encoding="utf-8")
    r = run_cli(str(f))
    assert r.returncode == 0
    assert "Reformatted" in r.stdout
    assert "| longvalue | y |" in f.read_text(encoding="utf-8")


def test_cli_recursive(tmp_path):
    (tmp_path / "sub").mkdir()
    f = tmp_path / "sub" / "r.md"
    f.write_text("| a | b |\n|---|---|\n| longvalue | y |\n", encoding="utf-8")
    r = run_cli("-r", str(tmp_path))
    assert r.returncode == 0
    assert "| longvalue | y |" in f.read_text(encoding="utf-8")


def test_cli_unknown_option_exits_1():
    r = run_cli("--nope")
    assert r.returncode == 1
    assert "Unknown option" in r.stderr
