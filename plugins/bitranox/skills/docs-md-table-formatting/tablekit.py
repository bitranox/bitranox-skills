# /// script
# requires-python = ">=3.10"
# ///
"""Round-trip a GitHub-flavored markdown table to JSON, let you edit the JSON, and re-emit it aligned.

Why: hand-editing a markdown table means re-padding every column and fixing the `:--`/`--:` alignment
markers by hand - fiddly and error-prone. Read the table to JSON, change cell values, and render it
back fully aligned; the padding and alignment are recomputed for you. `replace` splices the rendered
table back into the file at its original position, leaving all surrounding prose untouched.

Stdlib only on purpose: a GFM pipe table is a narrow, well-specified format, and a targeted parser
round-trips alignment and escaped pipes more faithfully than a general markdown library (which
discards formatting) or a re-tabulator.

Run:
  python3 tablekit.py read FILE [--index N]     # FILE (or -) -> JSON (one table, or all)
  python3 tablekit.py render < table.json       # JSON (one table) -> aligned markdown
  python3 tablekit.py replace FILE --index N < table.json   # splice back in place (--stdout to preview)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# A delimiter cell: optional leading colon, one or more dashes, optional trailing colon.
_DELIM_CELL = re.compile(r"^:?-+:?$")
# Split a row on pipes that are NOT backslash-escaped.
_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def _split_cells(line: str) -> list[str]:
    """Split one table line into stripped, unescaped cells (edge pipes optional)."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in _UNESCAPED_PIPE.split(s)]


def _is_delimiter(line: str) -> bool:
    """True when a line is a table delimiter row (all cells match `:?-+:?`)."""
    cells = _split_cells(line)
    return bool(cells) and all(_DELIM_CELL.match(c) for c in cells)


def _alignment(cell: str) -> str:
    """Map a delimiter cell to left | right | center | none."""
    left, right = cell.startswith(":"), cell.endswith(":")
    if left and right:
        return "center"
    if left:
        return "left"
    if right:
        return "right"
    return "none"


def _looks_like_table_row(line: str) -> bool:
    return "|" in line and line.strip() != ""


def parse_tables(text: str) -> list[dict]:
    """Parse every GFM pipe table in `text`.

    Returns a list of tables in document order, each a dict with:
      index       - 0-based position among tables in the document
      start_line  - 1-based line number of the header row
      end_line    - 1-based line number of the last body row (== delimiter line if no body)
      headers     - list[str]
      alignments  - list[str] (left|right|center|none), one per column
      rows        - list[list[str]], each padded/truncated to len(headers)
    """
    lines = text.splitlines()
    tables: list[dict] = []
    i = 0
    while i < len(lines):
        # A table starts when a header-like line is immediately followed by a delimiter line.
        if _looks_like_table_row(lines[i]) and i + 1 < len(lines) and _is_delimiter(lines[i + 1]):
            headers = _split_cells(lines[i])
            alignments = [_alignment(c) for c in _split_cells(lines[i + 1])]
            width = len(headers)
            alignments = (alignments + ["none"] * width)[:width]
            start_line = i + 1  # 1-based header line
            j = i + 2
            rows: list[list[str]] = []
            end_line = i + 2  # 1-based delimiter line, in case there is no body
            while j < len(lines) and _looks_like_table_row(lines[j]):
                cells = _split_cells(lines[j])
                rows.append((cells + [""] * width)[:width])
                end_line = j + 1
                j += 1
            tables.append(
                {
                    "index": len(tables),
                    "start_line": start_line,
                    "end_line": end_line,
                    "headers": headers,
                    "alignments": alignments,
                    "rows": rows,
                }
            )
            i = j
        else:
            i += 1
    return tables


def _escape(cell: str) -> str:
    return str(cell).replace("|", "\\|")


def _pad(cell: str, width: int, align: str) -> str:
    if align == "right":
        return cell.rjust(width)
    if align == "center":
        return cell.center(width)
    return cell.ljust(width)


def _delim(width: int, align: str) -> str:
    if align == "left":
        return ":" + "-" * (width - 1)
    if align == "right":
        return "-" * (width - 1) + ":"
    if align == "center":
        return ":" + "-" * (width - 2) + ":"
    return "-" * width


def render_table(table: dict) -> str:
    """Render {headers, alignments, rows} as an aligned GFM markdown table (no trailing newline)."""
    headers = [_escape(h) for h in table["headers"]]
    ncol = len(headers)
    aligns = (list(table.get("alignments") or []) + ["none"] * ncol)[:ncol]
    rows = [([_escape(c) for c in row] + [""] * ncol)[:ncol] for row in table.get("rows") or []]
    # Column width is the widest cell/header, floored at 3 so the delimiter always has room.
    widths = []
    for col in range(ncol):
        cells = [headers[col]] + [row[col] for row in rows]
        widths.append(max(3, max(len(c) for c in cells)))

    def line(cells: list[str]) -> str:
        return "| " + " | ".join(_pad(c, widths[k], aligns[k]) for k, c in enumerate(cells)) + " |"

    out = [line(headers), "| " + " | ".join(_delim(widths[k], aligns[k]) for k in range(ncol)) + " |"]
    out.extend(line(row) for row in rows)
    return "\n".join(out)


def replace_table(text: str, index: int, table: dict) -> str:
    """Return `text` with the table at position `index` replaced by render_table(table)."""
    tables = parse_tables(text)
    if not (0 <= index < len(tables)):
        raise IndexError(f"table index {index} out of range (found {len(tables)} table(s))")
    target = tables[index]
    lines = text.splitlines(keepends=True)
    start = target["start_line"] - 1  # to 0-based
    end = target["end_line"]          # exclusive slice end == last body line (1-based)
    trailing_nl = lines[end - 1].endswith("\n") if end - 1 < len(lines) else True
    rendered = render_table(table) + ("\n" if trailing_nl else "")
    return "".join(lines[:start]) + rendered + "".join(lines[end:])


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Round-trip a markdown table through JSON.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_read = sub.add_parser("read", help="parse markdown to JSON (one table with --index, else all)")
    p_read.add_argument("file", help="markdown file, or - for stdin")
    p_read.add_argument("--index", type=int, default=None, help="emit only this table's headers/alignments/rows")

    sub.add_parser("render", help="read one table's JSON from stdin, print aligned markdown")

    p_repl = sub.add_parser("replace", help="splice one table's JSON (stdin) back into a file")
    p_repl.add_argument("file", help="markdown file to modify")
    p_repl.add_argument("--index", type=int, required=True, help="which table to replace (0-based)")
    p_repl.add_argument("--stdout", action="store_true", help="print the result instead of writing the file")

    args = ap.parse_args(argv)

    if args.cmd == "read":
        tables = parse_tables(_read_text(args.file))
        if args.index is not None:
            if not (0 <= args.index < len(tables)):
                print(f"table index {args.index} out of range ({len(tables)} found)", file=sys.stderr)
                return 1
            t = tables[args.index]
            payload = {"headers": t["headers"], "alignments": t["alignments"], "rows": t["rows"]}
        else:
            payload = tables
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "render":
        print(render_table(json.loads(sys.stdin.read())))
        return 0

    if args.cmd == "replace":
        table = json.loads(sys.stdin.read())
        new_text = replace_table(Path(args.file).read_text(encoding="utf-8"), args.index, table)
        if args.stdout:
            sys.stdout.write(new_text)
        else:
            Path(args.file).write_text(new_text, encoding="utf-8")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
