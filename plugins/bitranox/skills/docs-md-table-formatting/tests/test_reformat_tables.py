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


def test_split_pipe_in_backticks_is_a_separator_as_in_gfm():
    """GFM gives a code span no protection: an unescaped pipe inside backticks splits the cell."""
    assert R.split_table_row("| `a | b` | c |") == ["`a", "b`", "c"]


def test_split_escaped_pipe_in_backticks_stays_one_cell():
    assert R.split_table_row(r"| `a \| b` | c |") == [r"`a \| b`", "c"]


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


def test_escaped_pipe_in_backtick_span_single_column():
    # The ESCAPED pipe keeps the span one cell -> two columns, not three.
    out = fmt("| `a \\| b` | c |\n|---|---|\n| 1 | 2 |")
    assert out == [
        "| `a \\| b` | c |",
        "|----------|---|",
        "| 1        | 2 |",
    ]


def test_unescaped_pipe_in_backtick_span_makes_the_table_ragged():
    """The header splits into three cells under a two-cell separator, so it is left alone."""
    lines = ["| `a | b` | c |", "|---|---|", "| 1 | 2 |"]
    assert R.reformat_table(lines) == lines


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


def test_cli_unknown_option_exits_2():
    """A usage error is exit 2, so it cannot be mistaken for --check's 'changes needed' (1)."""
    r = run_cli("--nope")
    assert r.returncode == 2
    assert "Unknown option" in r.stderr


# --------------------------------------------------------------------------
# A ragged row - one whose cell count differs from the header's - is the case
# the formatter cannot fix. It must not be reported as a clean file.
# --------------------------------------------------------------------------


RAGGED = """\
| a | b |
|---|---|
| 1 | 2 |
| 3 | 4 | 5 |
"""


def test_column_mismatches_names_the_row_and_its_count():
    rows = R.table_column_mismatches(RAGGED.rstrip("\n").split("\n"))
    assert rows == [(3, 3)], rows


def test_column_mismatches_is_empty_for_a_well_formed_table():
    good = "| a | b |\n|---|---|\n| 1 | 2 |".split("\n")
    assert R.table_column_mismatches(good) == []


def test_not_a_table_is_not_ragged():
    """No separator row means it is not a table at all, which is not a finding."""
    assert R.table_column_mismatches("| a | b |\n| 1 | 2 |".split("\n")) == []


def test_ragged_table_is_reported_not_silently_unchanged(tmp_path):
    """The whole point: GFM drops the surplus cell, so 'Unchanged' reads as a false all-clear."""
    f = tmp_path / "ragged.md"
    f.write_text(RAGGED, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(f)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert "ragged" in proc.stdout.lower(), proc.stdout
    assert "4" in proc.stderr, proc.stderr          # the 1-based line of the bad row
    assert proc.returncode == 0                     # a warning by default, not a failure


def test_strict_makes_a_ragged_table_fail(tmp_path):
    f = tmp_path / "ragged.md"
    f.write_text(RAGGED, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--strict", str(f)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)


def test_strict_passes_a_clean_file(tmp_path):
    """The control: --strict must not fail a file whose tables are well formed."""
    f = tmp_path / "clean.md"
    f.write_text("| a | b |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--strict", str(f)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)


SHORT_ROW = """\
| a | b | c |
|---|---|---|
| 1 | 2 |
"""


def test_a_short_row_is_reported_as_padded_not_as_lost_content(tmp_path):
    """The two directions differ: GFM drops a surplus cell but PADS a missing one. A message
    claiming content loss for both is wrong half the time."""
    f = tmp_path / "short.md"
    f.write_text(SHORT_ROW, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(f)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert "EMPTY" in proc.stderr, proc.stderr
    assert "LOSES CONTENT" not in proc.stderr, proc.stderr


def test_a_long_row_is_reported_as_losing_content(tmp_path):
    f = tmp_path / "long.md"
    f.write_text(RAGGED, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(f)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert "LOSES CONTENT" in proc.stderr, proc.stderr


# --------------------------------------------------------------------------
# Audit fixes: each test names the defect it pins.
# --------------------------------------------------------------------------


def run_file(tmp_path, text, *cli_args, name="t.md", env=None):
    """Write `text` as bytes (no newline translation), run the CLI on it, return (proc, bytes)."""
    f = tmp_path / name
    f.write_bytes(text.encode("utf-8"))
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *cli_args, str(f)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    return proc, f.read_bytes().decode("utf-8")


def test_fence_line_after_a_table_in_a_markdown_fence_keeps_its_place(tmp_path):
    """A ``` line inside a ````markdown fence was written ABOVE the table it followed."""
    src = "`````markdown\n| a | b |\n|---|---|\n| long | y |\n```\n`````\n"
    _, out = run_file(tmp_path, src)
    assert out == "`````markdown\n| a    | b |\n|------|---|\n| long | y |\n```\n`````\n"


def test_a_table_in_a_code_fence_nested_in_a_markdown_fence_is_left_alone(tmp_path):
    src = "````markdown\n```python\n| a | b |\n|---|---|\n| long | y |\n```\n````\n"
    proc, out = run_file(tmp_path, src)
    assert out == src
    assert "Unchanged" in proc.stdout


def test_a_table_after_a_nested_fence_in_a_markdown_fence_is_still_formatted(tmp_path):
    """The control: once the nested block closes, the markdown fence's own table is realigned."""
    src = "````markdown\n```python\nx = 1\n```\n| a | b |\n|---|---|\n| long | y |\n````\n"
    _, out = run_file(tmp_path, src)
    assert "| long | y |\n" in out and "|------|---|\n" in out
    assert out.index("```python") < out.index("x = 1") < out.index("| a    | b |")


def test_a_table_nested_in_a_list_item_keeps_its_indentation(tmp_path):
    """Stripping the indent pulled the table out of its list item when rendered."""
    src = "- item\n\n  | a | b |\n  |---|---|\n  | long | y |\n"
    _, out = run_file(tmp_path, src)
    assert out == "- item\n\n  | a    | b |\n  |------|---|\n  | long | y |\n"


def test_an_aligned_list_nested_table_is_not_rewritten(tmp_path):
    src = "- item\n\n  | a    | b |\n  |------|---|\n  | long | y |\n"
    proc, out = run_file(tmp_path, src)
    assert out == src
    assert "Unchanged" in proc.stdout


def test_a_four_space_table_under_a_list_item_is_list_content_not_code(tmp_path):
    src = "- item:\n\n    | a | b |\n    |---|---|\n    | long | y |\n"
    _, out = run_file(tmp_path, src)
    assert out == "- item:\n\n    | a    | b |\n    |------|---|\n    | long | y |\n"


def test_a_pipe_table_in_an_indented_code_block_is_left_alone(tmp_path):
    """Four spaces of indentation outside a list make a code block; rewriting it made it a table."""
    src = "A paragraph.\n\n    | x | y |\n    |---|---|\n    | long | z |\n"
    proc, out = run_file(tmp_path, src)
    assert out == src
    assert "Unchanged" in proc.stdout


def test_a_trailing_escaped_pipe_with_no_closing_pipe_is_kept(tmp_path):
    assert R.split_table_row("| a  | b \\|") == ["a", "b \\|"]
    src = "| h | i |\n|---|---|\n| a  | b \\|\n"
    _, out = run_file(tmp_path, src)
    assert "| a | b \\| |" in out


# ---- fences are matched the CommonMark way ----
# An opener is at most three columns into its block, a backtick fence's info string holds no
# backtick, and a closer is the same character, at least as long, bare, and also at most three
# columns in. Anything looser opens a fence that swallows every later table.
MISALIGNED = "| a | b |\n|---|---|\n| long | y |\n"
ALIGNED = "| a    | b |\n|------|---|\n| long | y |\n"


def test_an_inline_code_span_at_line_start_is_not_a_fence(tmp_path):
    src = "```x``` is inline code, not a fence.\n\n" + MISALIGNED
    _, out = run_file(tmp_path, src)
    assert out.endswith(ALIGNED), out


def test_a_backtick_fence_inside_an_indented_code_block_is_not_a_fence(tmp_path):
    src = "A paragraph.\n\n    ```\n\nMore prose.\n\n" + MISALIGNED
    _, out = run_file(tmp_path, src)
    assert out.endswith(ALIGNED), out


def test_a_closer_indented_four_columns_does_not_close_the_fence(tmp_path):
    src = "```\ncode\n    ```\n" + MISALIGNED + "```\n"
    proc, out = run_file(tmp_path, src)
    assert out == src
    assert "Unchanged" in proc.stdout


def test_a_closer_shorter_than_its_opener_does_not_close_it(tmp_path):
    src = "````\n```\n" + MISALIGNED + "````\n"
    _, out = run_file(tmp_path, src)
    assert out == src


def test_a_tilde_closer_does_not_close_a_backtick_fence(tmp_path):
    src = "```\n~~~\n" + MISALIGNED + "```\n"
    _, out = run_file(tmp_path, src)
    assert out == src


def test_a_tilde_fence_info_string_may_hold_a_backtick(tmp_path):
    """The no-backtick rule is for BACKTICK fences only: ~~~ with `x` still opens a fence."""
    src = "~~~ `x`\n" + MISALIGNED + "~~~\n"
    _, out = run_file(tmp_path, src)
    assert out == src


def test_a_fence_inside_a_nested_list_item_still_hides_its_table(tmp_path):
    """Indentation is judged against the list item's content column, not the page margin."""
    src = "- a\n  - b\n\n    ```\n    | a | b |\n    |---|---|\n    | long | y |\n    ```\n"
    _, out = run_file(tmp_path, src)
    assert out == src


def test_a_ragged_table_after_an_inline_span_line_is_still_reported(tmp_path):
    """The repo gate's ragged check reads through reformat_file, so it went blind here too."""
    f = tmp_path / "r.md"
    f.write_bytes(("```sh``` prose\n\n| a | b |\n|---|---|\n| 1 | 2 | 3 |\n").encode("utf-8"))
    warnings = []
    R.reformat_file(f, check_only=True, warnings=warnings)
    assert len(warnings) == 1 and "LOSES CONTENT" in warnings[0], warnings


def test_strict_fails_a_row_whose_code_span_pipe_drops_a_cell(tmp_path):
    """The HIGH finding: GFM splits at the pipe in backticks, so `z` is dropped when rendered."""
    src = "| a | b |\n|---|---|\n| `x | y` | z |\n"
    proc, _ = run_file(tmp_path, src, "--strict")
    assert proc.returncode == 1, (proc.stdout, proc.stderr)
    assert "LOSES CONTENT" in proc.stderr


def test_an_unmatched_backtick_does_not_swallow_the_row(tmp_path):
    """A lone backtick made the rest of the row one cell: a false ragged report under --strict."""
    src = "| a | b |\n|---|---|\n| x ` y | z |\n"
    proc, out = run_file(tmp_path, src, "--strict")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "ragged" not in proc.stderr
    assert "| x ` y | z |" in out


def test_crlf_line_endings_survive_a_reformat(tmp_path):
    src = "| a | b |\r\n|---|---|\r\n| long | y |\r\n\r\ntext\r\n"
    _, out = run_file(tmp_path, src)
    assert out == "| a    | b |\r\n|------|---|\r\n| long | y |\r\n\r\ntext\r\n"


def test_mixed_line_endings_are_kept_line_by_line(tmp_path):
    src = "intro\n| a | b |\r\n|---|---|\n| long | y |\r\n"
    _, out = run_file(tmp_path, src)
    assert out == "intro\n| a    | b |\r\n|------|---|\n| long | y |\r\n"


def test_a_utf8_bom_before_a_line_one_table_is_kept_and_the_table_formatted(tmp_path):
    src = "\ufeff| a | b |\n|---|---|\n| long | y |\n"
    _, out = run_file(tmp_path, src)
    assert out == "\ufeff| a    | b |\n|------|---|\n| long | y |\n"


def test_recursive_skips_a_directory_named_md_instead_of_aborting(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "notes.md").mkdir()
    for name in ("a.md", "z.md"):
        (tree / name).write_text("| a | b |\n|---|---|\n| long | y |\n", encoding="utf-8")
    proc = run_cli("-r", str(tree))
    assert proc.returncode == 0, proc.stderr
    assert "notes.md" in proc.stderr and "not a regular file" in proc.stderr
    for name in ("a.md", "z.md"):
        assert "| long | y |" in (tree / name).read_text(encoding="utf-8")


def test_recursive_skips_a_dangling_md_symlink(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    try:
        (tree / "a.md").symlink_to(tree / "gone.md")
    except OSError as exc:  # Windows without symlink privilege
        pytest.skip(f"cannot create a symlink here: {exc}")
    (tree / "z.md").write_text("| a | b |\n|---|---|\n| x | y |\n", encoding="utf-8")
    proc = run_cli("--check", "-r", str(tree))
    assert proc.returncode == 0, proc.stderr
    assert "not a regular file" in proc.stderr


def _display(text):
    import unicodedata
    return sum(
        0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in "WF" else 1
        for c in text
    )


def test_wide_and_combining_cells_align_by_display_width(tmp_path):
    cafe = "caf" + chr(0x00E9)
    decomposed = "cafe" + chr(0x0301)
    nihon = chr(0x65E5) + chr(0x672C)
    src = f"| word | n |\n|---|---|\n| {cafe} | 1 |\n| {nihon} | 2 |\n| {decomposed} | 3 |\n| abcde | 4 |\n"
    proc, out = run_file(tmp_path, src)
    rows = [ln for ln in out.split("\n") if ln]
    assert len({_display(r) for r in rows}) == 1, rows
    again = run_cli("--check", str(tmp_path / "t.md"))
    assert again.returncode == 0, again.stdout


def test_a_header_separator_mismatch_is_reported_as_no_table(tmp_path):
    """GFM renders nothing as a table when the delimiter row does not match the header."""
    src = "| a | b | c |\n|---|---|\n| 1 | 2 |\n"
    proc, _ = run_file(tmp_path, src)
    assert "does not render this as a table at all" in proc.stderr
    assert "renders EMPTY" not in proc.stderr
    assert proc.stderr.count("ragged") == 1


def test_cp1252_stdout_with_a_non_ascii_filename_does_not_crash(tmp_path):
    import os
    tree = tmp_path / "uni"
    tree.mkdir()
    name = chr(0x65E5) + chr(0x672C) + ".md"
    (tree / name).write_text("| a | b |\n|---|---|\n| long | y |\n", encoding="utf-8")
    (tree / "zz.md").write_text("| a | b |\n|---|---|\n| long | y |\n", encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "-r", str(tree)],
        capture_output=True, env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert b"Traceback" not in proc.stderr
    assert "| long | y |" in (tree / "zz.md").read_text(encoding="utf-8")


def test_usage_names_strict_and_the_recursive_form_and_exits_2():
    r = run_cli()
    assert r.returncode == 2
    assert "--strict" in r.stderr and "-r [dir" in r.stderr


def test_a_bare_directory_without_r_is_an_error_exit_2(tmp_path):
    r = run_cli(str(tmp_path))
    assert r.returncode == 2
    assert "not a file" in r.stderr


def test_a_missing_file_is_refused_before_any_other_file_is_written(tmp_path):
    good = tmp_path / "good.md"
    src = "| a | b |\n|---|---|\n| long | y |\n"
    good.write_text(src, encoding="utf-8")
    r = run_cli(str(good), str(tmp_path / "missing.md"))
    assert r.returncode == 2
    assert good.read_text(encoding="utf-8") == src


def test_recursive_on_a_file_is_not_a_directory_exit_2(tmp_path):
    f = tmp_path / "x.md"
    f.write_text("x\n", encoding="utf-8")
    r = run_cli("-r", str(f))
    assert r.returncode == 2
    assert "not a directory" in r.stderr


def test_recursive_with_no_md_files_exits_0(tmp_path):
    r = run_cli("-r", str(tmp_path))
    assert r.returncode == 0
    assert "No .md files found" in r.stderr


def test_a_non_utf8_file_is_an_error_exit_2_and_the_rest_still_run(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"| a | b |\n|---|---|\n| \xff | y |\n")
    good = tmp_path / "good.md"
    good.write_text("| a | b |\n|---|---|\n| long | y |\n", encoding="utf-8")
    r = run_cli(str(bad), str(good))
    assert r.returncode == 2
    assert "cannot process" in r.stderr and "Traceback" not in r.stderr
    assert "| long | y |" in good.read_text(encoding="utf-8")


REAL_TABLES = SKILL_DIR / "tests" / "fixtures" / "real_tables.md"


def test_real_canonical_tables_are_byte_identical_after_a_pass(tmp_path):
    """Tables copied verbatim from shipped skill docs (blockquoted, escaped pipes, alignment
    colons, non-ASCII, backticked cells) were canonical before these fixes and must stay so:
    the reformat-md-tables hook and the repo gate both run this code on every doc."""
    copy = tmp_path / "real.md"
    copy.write_bytes(REAL_TABLES.read_bytes())
    warnings = []
    assert R.reformat_file(copy, warnings=warnings) is False
    assert copy.read_bytes() == REAL_TABLES.read_bytes()
    assert warnings == []


@pytest.mark.parametrize("skill", ["docs-md-table-formatting", "meta-claude-hooks", "git-worktrees"])
def test_this_groups_skill_docs_stay_canonical(skill, tmp_path):
    doc = SKILL_DIR.parent / skill / "SKILL.md"
    copy = tmp_path / "SKILL.md"
    copy.write_bytes(doc.read_bytes())
    warnings = []
    assert R.reformat_file(copy, check_only=True, warnings=warnings) is False
    assert warnings == []
