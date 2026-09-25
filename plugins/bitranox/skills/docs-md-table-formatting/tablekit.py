# /// script
# requires-python = ">=3.10"
# ///
"""Round-trip a GitHub-flavored markdown table to JSON, let you edit the JSON, and re-emit it aligned.

Why: hand-editing a markdown table means re-padding every column and fixing the `:--`/`--:` alignment
markers by hand - fiddly and error-prone. Read the table to JSON, change cell values, and render it
back fully aligned; the padding and alignment are recomputed for you. `replace` splices the rendered
table back into the file at its original position, leaving all surrounding prose untouched - its
indentation, its line endings and a leading BOM included.

Stdlib only on purpose: a GFM pipe table is a narrow, well-specified format, and a targeted parser
round-trips alignment and escaped pipes more faithfully than a general markdown library (which
discards formatting) or a re-tabulator.

Tables are numbered the way reformat_tables.py sees them: a table inside a fenced code block is an
example, not a table, unless the fence is tagged `markdown` or `md`.

Run:
  python3 tablekit.py read FILE [--index N]     # FILE (or -) -> JSON (one table, or all)
  python3 tablekit.py render < table.json       # JSON (one table) -> aligned markdown
  python3 tablekit.py replace FILE --index N < table.json   # splice back in place (--stdout to preview)

Exit codes: 0 = done, 1 = no table at that index, 2 = refused or error (a row with more cells than
the headers, which a round trip would delete; an unknown alignment; invalid JSON; an unreadable file).
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
_FENCE_OPEN = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
_FENCE_CLOSE = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*$")
ALIGNMENTS = ("left", "right", "center", "none")


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


def _lines_with_endings(text: str) -> list[str]:
    """Split on newline ONLY. str.splitlines also breaks at a form feed, U+2028 and friends, which
    splits one table row into two and shifts every line number after it."""
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def _strip_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return line[:-2]
    return line[:-1] if line.endswith("\n") else line


def _table_lines(lines: list[str]) -> list[bool]:
    """Per line: may it belong to a table? Fence lines never do, nor anything inside a fence
    whose info string is not markdown. A fence tagged markdown holds a document of its own, so a
    fence nested in it is tracked too and its content is excluded unless it is markdown as well."""
    eligible: list[bool] = []
    stack: list[tuple[str, int, bool]] = []  # (marker char, length, is markdown)
    for line in lines:
        if stack:
            close = _FENCE_CLOSE.match(line)
            char, length, _markdown = stack[-1]
            if close and close.group(1)[0] == char and len(close.group(1)) >= length:
                stack.pop()
                eligible.append(False)
                continue
        opener = _FENCE_OPEN.match(line)
        if opener and (not stack or stack[-1][2]):
            lang = opener.group(2).strip().split()[0].lower() if opener.group(2).strip() else ""
            stack.append((opener.group(1)[0], len(opener.group(1)), lang in ("markdown", "md")))
            eligible.append(False)
            continue
        eligible.append(not stack or stack[-1][2])
    return eligible


def _starts_table(lines: list[str], eligible: list[bool], i: int) -> bool:
    """A header line immediately followed by a delimiter with the SAME cell count. GFM renders no
    table when the counts differ, and a setext heading (`Use a | b` over `---`) must not qualify."""
    if i + 1 >= len(lines) or not (eligible[i] and eligible[i + 1]):
        return False
    if not _looks_like_table_row(lines[i]) or not _is_delimiter(lines[i + 1]):
        return False
    return len(_split_cells(lines[i + 1])) == len(_split_cells(lines[i]))


def parse_tables(text: str) -> list[dict]:
    """Parse every GFM pipe table in `text`.

    Returns a list of tables in document order, each a dict with:
      index         - 0-based position among tables in the document
      start_line    - 1-based line number of the header row
      end_line      - 1-based line number of the last body row (== delimiter line if no body)
      headers       - list[str]
      alignments    - list[str] (left|right|center|none), one per column
      rows          - list[list[str]], each padded/truncated to len(headers)
      surplus_lines - 1-based lines whose row has MORE cells than headers; truncating them to fit
                      is lossy, so `read` and `replace` refuse such a table rather than delete text
    """
    lines = [_strip_ending(line) for line in _lines_with_endings(text)]
    eligible = _table_lines(lines)
    tables: list[dict] = []
    i = 0
    while i < len(lines):
        if not _starts_table(lines, eligible, i):
            i += 1
            continue
        headers = _split_cells(lines[i])
        width = len(headers)
        alignments = [_alignment(c) for c in _split_cells(lines[i + 1])]
        rows: list[list[str]] = []
        surplus: list[int] = []
        end_line = i + 2  # 1-based delimiter line, in case there is no body
        j = i + 2
        while j < len(lines) and eligible[j] and _looks_like_table_row(lines[j]):
            cells = _split_cells(lines[j])
            if len(cells) > width:
                surplus.append(j + 1)
            rows.append((cells + [""] * width)[:width])
            end_line = j + 1
            j += 1
        tables.append(
            {
                "index": len(tables),
                "start_line": i + 1,
                "end_line": end_line,
                "headers": headers,
                "alignments": alignments,
                "rows": rows,
                "surplus_lines": surplus,
            }
        )
        i = j
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


def _validate(table: dict) -> None:
    """Refuse what render would otherwise silently change: an unknown alignment rendered as none,
    and a row longer than the headers truncated - the second deletes content from the file."""
    ncol = len(table["headers"])
    for value in table.get("alignments") or []:
        if value not in ALIGNMENTS:
            raise ValueError(f"unknown alignment {value!r}; use one of {', '.join(ALIGNMENTS)}")
    for number, row in enumerate(table.get("rows") or [], 1):
        if len(row) > ncol:
            raise ValueError(
                f"row {number} has {len(row)} cells, more cells than the {ncol} headers; "
                "rendering would drop the surplus"
            )


def render_table(table: dict) -> str:
    """Render {headers, alignments, rows} as an aligned GFM markdown table (no trailing newline).

    Raises:
        ValueError: an alignment is not left/right/center/none, or a row has more cells than headers.
    """
    _validate(table)
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
    """Return `text` with the table at position `index` replaced by render_table(table).

    The rendered table takes the header line's indentation, so a table nested in a list item stays
    in it, and the header line's line ending, so a CRLF file stays CRLF.

    Raises:
        IndexError: there is no table at `index`.
        ValueError: see render_table.
    """
    tables = parse_tables(text)
    if not (0 <= index < len(tables)):
        raise IndexError(f"table index {index} out of range (found {len(tables)} table(s))")
    target = tables[index]
    lines = _lines_with_endings(text)
    start = target["start_line"] - 1  # to 0-based
    end = target["end_line"]          # exclusive slice end == last body line (1-based)
    header = lines[start]
    indent = header[: len(header) - len(header.lstrip(" \t"))]
    eol = "\r\n" if header.endswith("\r\n") else "\n"
    last = lines[end - 1]
    rendered = eol.join(indent + row for row in render_table(table).split("\n"))
    if last.endswith("\n"):
        rendered += eol
    return "".join(lines[:start]) + rendered + "".join(lines[end:])


def _read_text(path: str) -> tuple[str, bool]:
    """(text without BOM, had_bom). newline="" keeps CRLF so a rewrite can reproduce it."""
    if path == "-":
        text = sys.stdin.read()
    else:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    if text.startswith("﻿"):
        return text[1:], True
    return text, False


def _utf8_stdio() -> None:
    """The documented pipeline is `read | jq | replace`, and jq speaks UTF-8. In a Windows locale
    the default code page crashed `read` on a check mark and made `replace` write mojibake."""
    for stream in (sys.stdin, sys.stdout):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            continue
    try:
        sys.stderr.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError, OSError):
        pass


def _error(message: str, code: int) -> int:
    print(f"tablekit: {message}", file=sys.stderr)
    return code


def _cmd_read(args: argparse.Namespace) -> int:
    text, _bom = _read_text(args.file)
    tables = parse_tables(text)
    if args.index is None:
        for t in tables:
            if t["surplus_lines"]:
                print(f"tablekit: warning: table {t['index']} has rows with more cells than headers "
                      f"at line(s) {t['surplus_lines']}", file=sys.stderr)
        print(json.dumps(tables, indent=2, ensure_ascii=False))
        return 0
    if not (0 <= args.index < len(tables)):
        return _error(f"table index {args.index} out of range ({len(tables)} found)", 1)
    t = tables[args.index]
    if t["surplus_lines"]:
        return _error(
            f"table {args.index} has rows with more cells than headers at line(s) "
            f"{t['surplus_lines']}; a read-edit-replace round trip would delete them. "
            "Fix the row first (escape a literal pipe as \\|).", 2)
    print(json.dumps({"headers": t["headers"], "alignments": t["alignments"], "rows": t["rows"]},
                     indent=2, ensure_ascii=False))
    return 0


def _load_table_json() -> dict:
    table = json.loads(sys.stdin.read())
    if not isinstance(table, dict) or not isinstance(table.get("headers"), list):
        raise ValueError("table JSON must be an object with a 'headers' list")
    return table


def _cmd_replace(args: argparse.Namespace) -> int:
    table = _load_table_json()
    text, bom = _read_text(args.file)
    try:
        new_text = replace_table(text, args.index, table)
    except IndexError as exc:
        return _error(str(exc), 1)
    if bom:
        new_text = "﻿" + new_text
    if args.stdout:
        sys.stdout.write(new_text)
    else:
        with open(args.file, "w", encoding="utf-8", newline="") as f:
            f.write(new_text)
    return 0


def _build_parser() -> argparse.ArgumentParser:
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
    return ap


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    _utf8_stdio()
    try:
        if args.cmd == "read":
            return _cmd_read(args)
        if args.cmd == "render":
            print(render_table(_load_table_json()))
            return 0
        if args.cmd == "replace":
            return _cmd_replace(args)
    except json.JSONDecodeError as exc:
        return _error(f"stdin is not valid JSON: {exc}", 2)
    except (ValueError, TypeError, KeyError) as exc:
        return _error(f"refused: {exc}", 2)
    except (OSError, UnicodeDecodeError) as exc:
        return _error(f"cannot read or write the file: {exc}", 2)
    return 2


if __name__ == "__main__":
    sys.exit(main())
