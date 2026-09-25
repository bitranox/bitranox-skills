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


# --------------------------------------------------------------------------
# Audit fixes: library level
# --------------------------------------------------------------------------

import io  # noqa: E402 - the CLI section below needs these, the library tests above do not
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

SCRIPT = Path(__file__).resolve().parent.parent / "tablekit.py"

FENCED_THEN_REAL = (
    "```markdown\n"
    "| ex | ample |\n"
    "| --- | --- |\n"
    "| 1 | 2 |\n"
    "```\n"
    "\n"
    "```python\n"
    "| not | a table |\n"
    "| --- | --- |\n"
    "```\n"
    "\n"
    "| real | table |\n"
    "| --- | --- |\n"
    "| a | b |\n"
)


def test_a_table_in_a_non_markdown_fence_is_not_a_table():
    tables = TK.parse_tables(FENCED_THEN_REAL)
    assert [t["headers"] for t in tables] == [["ex", "ample"], ["real", "table"]]


def test_numbering_skips_a_code_fenced_example():
    text = "```\n| a | b |\n| --- | --- |\n```\n\n| x | y |\n| --- | --- |\n| 1 | 2 |\n"
    assert TK.parse_tables(text)[0]["headers"] == ["x", "y"]


def test_a_setext_heading_with_a_pipe_is_not_a_table():
    text = "Use a | b\n---\n\n| x | y |\n| --- | --- |\n| 1 | 2 |\n"
    tables = TK.parse_tables(text)
    assert [t["headers"] for t in tables] == [["x", "y"]]


def test_a_header_delimiter_count_mismatch_is_not_a_table():
    text = "| a | b | c |\n| --- | --- |\n| 1 | 2 |\n"
    assert TK.parse_tables(text) == []


def test_surplus_cells_are_recorded_not_silently_dropped():
    text = "| a | b |\n| --- | --- |\n| 1 | 2 | 3 |\n"
    table = TK.parse_tables(text)[0]
    assert table["surplus_lines"] == [3]


def test_render_refuses_a_row_longer_than_the_headers():
    with pytest.raises(ValueError, match="more cells"):
        TK.render_table({"headers": ["a", "b"], "alignments": [], "rows": [["1", "2", "LOST"]]})


def test_render_refuses_an_unknown_alignment():
    with pytest.raises(ValueError, match="centre"):
        TK.render_table({"headers": ["a"], "alignments": ["centre"], "rows": []})


def test_replace_keeps_a_list_nested_tables_indentation():
    text = "- item:\n\n    | a | b |\n    | --- | --- |\n    | 1 | 2 |\n- next\n"
    table = {"headers": ["a", "b"], "alignments": ["none", "none"], "rows": [["x", "y"]]}
    out = TK.replace_table(text, 0, table)
    body = out.split("\n")[2:5]
    assert all(line.startswith("    | ") for line in body), body
    assert out.endswith("- next\n")


def test_replace_keeps_crlf_line_endings():
    text = "intro\r\n\r\n| a | b |\r\n| --- | --- |\r\n| 1 | 2 |\r\n\r\noutro\r\n"
    table = {"headers": ["a", "b"], "alignments": ["none", "none"], "rows": [["x", "y"]]}
    out = TK.replace_table(text, 0, table)
    assert out.count("\r\n") == out.count("\n")
    assert out.startswith("intro\r\n\r\n") and out.endswith("\r\n\r\noutro\r\n")


def test_a_line_separator_in_a_cell_does_not_split_the_row():
    cell = "a" + chr(0x2028) + "b"
    text = "| h | i |\n| --- | --- |\n| " + cell + " | 2 |\n"
    table = TK.parse_tables(text)[0]
    assert table["rows"] == [[cell, "2"]]
    assert table["end_line"] == 3


def test_replace_table_out_of_range_raises_index_error():
    with pytest.raises(IndexError):
        TK.replace_table(BASIC, 5, {"headers": ["a"], "rows": []})


# --------------------------------------------------------------------------
# Audit fixes: the CLI, through main() and a real subprocess
# --------------------------------------------------------------------------


def run_main(monkeypatch, capsys, argv, stdin=""):
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    rc = TK.main(argv)
    out = capsys.readouterr()
    return rc, out.out, out.err


def test_main_read_one_table(tmp_path, monkeypatch, capsys):
    f = tmp_path / "t.md"
    f.write_text(BASIC, encoding="utf-8")
    rc, out, _ = run_main(monkeypatch, capsys, ["read", str(f), "--index", "0"])
    assert rc == 0
    assert json.loads(out)["rows"] == [["Alice", "30"], ["Bob", "5"]]


def test_main_read_lists_all_tables(tmp_path, monkeypatch, capsys):
    f = tmp_path / "t.md"
    f.write_text(FENCED_THEN_REAL, encoding="utf-8")
    rc, out, _ = run_main(monkeypatch, capsys, ["read", str(f)])
    assert rc == 0
    assert [t["index"] for t in json.loads(out)] == [0, 1]


def test_main_read_index_out_of_range_exits_1(tmp_path, monkeypatch, capsys):
    f = tmp_path / "t.md"
    f.write_text(BASIC, encoding="utf-8")
    rc, _, err = run_main(monkeypatch, capsys, ["read", str(f), "--index", "5"])
    assert rc == 1
    assert "out of range" in err


def test_main_read_refuses_a_table_whose_round_trip_would_lose_cells(tmp_path, monkeypatch, capsys):
    f = tmp_path / "t.md"
    f.write_text("| a | b |\n| --- | --- |\n| 1 | 2 | 3 |\n", encoding="utf-8")
    rc, out, err = run_main(monkeypatch, capsys, ["read", str(f), "--index", "0"])
    assert rc == 2
    assert out == ""
    assert "more cells" in err and "3" in err


def test_main_render_prints_aligned_markdown(monkeypatch, capsys):
    payload = json.dumps({"headers": ["a", "bb"], "alignments": ["left", "right"], "rows": [["1", "2"]]})
    rc, out, _ = run_main(monkeypatch, capsys, ["render"], stdin=payload)
    assert rc == 0
    assert out.splitlines()[1] == "| :-- | --: |"


def test_main_render_rejects_a_surplus_cell_with_exit_2(monkeypatch, capsys):
    payload = json.dumps({"headers": ["a", "b"], "rows": [["1", "2", "LOST"]]})
    rc, out, err = run_main(monkeypatch, capsys, ["render"], stdin=payload)
    assert rc == 2 and out == ""
    assert "more cells" in err


def test_main_render_rejects_an_unknown_alignment_with_exit_2(monkeypatch, capsys):
    payload = json.dumps({"headers": ["a"], "alignments": ["centre"], "rows": []})
    rc, _, err = run_main(monkeypatch, capsys, ["render"], stdin=payload)
    assert rc == 2
    assert "centre" in err


def test_main_render_rejects_invalid_json_with_exit_2(monkeypatch, capsys):
    rc, _, err = run_main(monkeypatch, capsys, ["render"], stdin="{not json")
    assert rc == 2
    assert "JSON" in err


def test_main_replace_writes_the_file(tmp_path, monkeypatch, capsys):
    f = tmp_path / "t.md"
    f.write_text(BASIC, encoding="utf-8")
    payload = json.dumps({"headers": ["Name", "Age"], "rows": [["Carol", "41"]]})
    rc, out, _ = run_main(monkeypatch, capsys, ["replace", str(f), "--index", "0"], stdin=payload)
    assert rc == 0 and out == ""
    text = f.read_text(encoding="utf-8")
    assert "Carol" in text and "Alice" not in text and text.endswith("outro line\n")


def test_main_replace_stdout_does_not_write(tmp_path, monkeypatch, capsys):
    f = tmp_path / "t.md"
    f.write_text(BASIC, encoding="utf-8")
    payload = json.dumps({"headers": ["Name", "Age"], "rows": [["Carol", "41"]]})
    rc, out, _ = run_main(monkeypatch, capsys, ["replace", str(f), "--index", "0", "--stdout"], stdin=payload)
    assert rc == 0 and "Carol" in out
    assert f.read_text(encoding="utf-8") == BASIC


def test_main_replace_out_of_range_exits_1_without_traceback(tmp_path, monkeypatch, capsys):
    f = tmp_path / "t.md"
    f.write_text(BASIC, encoding="utf-8")
    payload = json.dumps({"headers": ["a"], "rows": []})
    rc, _, err = run_main(monkeypatch, capsys, ["replace", str(f), "--index", "5"], stdin=payload)
    assert rc == 1
    assert "out of range" in err and "Traceback" not in err
    assert f.read_text(encoding="utf-8") == BASIC


def test_main_replace_keeps_a_bom_and_does_not_make_it_a_column(tmp_path, monkeypatch, capsys):
    f = tmp_path / "t.md"
    f.write_bytes(("﻿| a | b |\n| --- | --- |\n| 1 | 2 |\n").encode("utf-8"))
    rc, out, _ = run_main(monkeypatch, capsys, ["read", str(f), "--index", "0"])
    assert rc == 0
    table = json.loads(out)
    assert table["headers"] == ["a", "b"]
    rc, _, _ = run_main(monkeypatch, capsys, ["replace", str(f), "--index", "0"], stdin=out)
    assert rc == 0
    raw = f.read_bytes().decode("utf-8")
    assert raw.startswith("﻿| a ") and raw.count("﻿") == 1


def test_main_replace_keeps_crlf_in_the_file(tmp_path, monkeypatch, capsys):
    f = tmp_path / "t.md"
    f.write_bytes(b"intro\r\n\r\n| a | b |\r\n| --- | --- |\r\n| 1 | 2 |\r\n\r\noutro\r\n")
    payload = json.dumps({"headers": ["a", "b"], "rows": [["x", "y"]]})
    rc, _, _ = run_main(monkeypatch, capsys, ["replace", str(f), "--index", "0"], stdin=payload)
    assert rc == 0
    raw = f.read_bytes()
    assert raw.count(b"\r\n") == raw.count(b"\n")


def test_cli_stdio_is_utf8_whatever_the_locale(tmp_path):
    """A cp1252 locale crashed `read` on a check mark and wrote mojibake through `replace`."""
    f = tmp_path / "u.md"
    check = chr(0x2713)
    cafe = "caf" + chr(0x00E9)
    f.write_text(f"| a | b |\n| --- | --- |\n| {check} | 2 |\n", encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    read = subprocess.run([sys.executable, str(SCRIPT), "read", str(f), "--index", "0"],
                          capture_output=True, env=env)
    assert read.returncode == 0, read.stderr
    assert check in read.stdout.decode("utf-8")
    payload = json.dumps({"headers": ["a", "b"], "rows": [[cafe, "2"]]}, ensure_ascii=False)
    rep = subprocess.run([sys.executable, str(SCRIPT), "replace", str(f), "--index", "0"],
                         input=payload.encode("utf-8"), capture_output=True, env=env)
    assert rep.returncode == 0, rep.stderr
    assert cafe in f.read_text(encoding="utf-8")


def test_cli_replace_missing_file_exits_2(tmp_path):
    proc = subprocess.run([sys.executable, str(SCRIPT), "replace", str(tmp_path / "no.md"), "--index", "0"],
                          input=b'{"headers": ["a"], "rows": []}', capture_output=True)
    assert proc.returncode == 2
    assert b"Traceback" not in proc.stderr
