"""Tests for tablekit.py - markdown-table <-> JSON round-trip + reformat. ASCII only."""
import tablekit as TK


BASIC = (
    "intro line\n"
    "\n"
    "| Name | Age |\n"
    "| --- | --- |\n"
    "| Alice | 30 |\n"
    "| Bob | 5 |\n"
    "\n"
    "outro line\n"
)


def test_parse_basic_headers_rows_and_span():
    tables = TK.parse_tables(BASIC)
    assert len(tables) == 1
    t = tables[0]
    assert t["headers"] == ["Name", "Age"]
    assert t["rows"] == [["Alice", "30"], ["Bob", "5"]]
    # header line is line 3 (1-based), last body line is line 6
    assert t["start_line"] == 3
    assert t["end_line"] == 6


def test_parse_alignments():
    text = "| a | b | c | d |\n| :-- | --: | :-: | --- |\n| 1 | 2 | 3 | 4 |\n"
    t = TK.parse_tables(text)[0]
    assert t["alignments"] == ["left", "right", "center", "none"]


def test_parse_handles_tables_without_edge_pipes():
    text = "h1 | h2\n--- | ---\nx | y\n"
    t = TK.parse_tables(text)[0]
    assert t["headers"] == ["h1", "h2"]
    assert t["rows"] == [["x", "y"]]


def test_render_pads_columns_and_writes_alignment_markers():
    table = {
        "headers": ["Name", "Score"],
        "alignments": ["left", "right"],
        "rows": [["Alice", "3"], ["Bob", "10"]],
    }
    out = TK.render_table(table)
    lines = out.splitlines()
    # every rendered row has the same length (columns are padded/aligned)
    assert len({len(ln) for ln in lines}) == 1
    # left column keeps its alignment colon; right column ends with a colon
    assert lines[1].strip().startswith("| :")
    assert lines[1].rstrip().endswith(": |")
    # a right-aligned numeric cell is right-justified within its column
    assert "|    10 |" in out or "| 10 |" in out  # width depends on header 'Score'


def test_render_min_delimiter_width_is_three():
    out = TK.render_table({"headers": ["a"], "alignments": ["none"], "rows": [["x"]]})
    assert "| --- |" in out


def test_round_trip_structure_is_preserved():
    table = {
        "headers": ["Name", "Age"],
        "alignments": ["left", "right"],
        "rows": [["Alice", "30"], ["Bob", "5"]],
    }
    reparsed = TK.parse_tables(TK.render_table(table))[0]
    assert reparsed["headers"] == table["headers"]
    assert reparsed["alignments"] == table["alignments"]
    assert reparsed["rows"] == table["rows"]


def test_round_trip_escaped_pipe_in_cell():
    table = {"headers": ["expr"], "alignments": ["none"], "rows": [["a | b"]]}
    rendered = TK.render_table(table)
    # the literal pipe is escaped in the markdown so it does not split the cell
    assert r"a \| b" in rendered
    reparsed = TK.parse_tables(rendered)[0]
    assert reparsed["rows"] == [["a | b"]]


def test_ragged_row_is_padded_to_column_count():
    table = {"headers": ["a", "b", "c"], "alignments": ["none", "none", "none"], "rows": [["1"]]}
    reparsed = TK.parse_tables(TK.render_table(table))[0]
    assert reparsed["rows"] == [["1", "", ""]]


def test_replace_table_only_touches_that_table():
    text = (
        "# Doc\n"
        "\n"
        "| a | b |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n"
        "\n"
        "middle text\n"
        "\n"
        "| x | y |\n"
        "| --- | --- |\n"
        "| 7 | 8 |\n"
    )
    new_table = {"headers": ["a", "b"], "alignments": ["none", "none"], "rows": [["ONE", "TWO"]]}
    out = TK.replace_table(text, 0, new_table)
    assert "ONE" in out and "TWO" in out
    assert "middle text" in out          # surrounding prose intact
    assert "| 7 | 8 |" in out            # the second table is untouched
    assert "| 1 | 2 |" not in out        # the first table's old body is gone
