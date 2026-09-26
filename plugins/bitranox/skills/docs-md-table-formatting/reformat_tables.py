#!/usr/bin/env python3
"""Reformat all markdown tables in a file with proper column alignment.

Rules applied:
- Cells padded to widest content per column, measured in DISPLAY columns (a CJK character
  counts two, a combining mark none), so the source stays aligned in a terminal or editor
- Separator dashes touch pipes (no spaces)
- Content cells have exactly one space padding
- Consistent column count per table
- Preserves column alignment markers (:---, :---:, ---:)
- Reformats tables inside blockquotes (> | ... |), preserving prefix
- Keeps a table's leading indentation, so a table nested in a list item stays in it
- Leaves a table alone when its indentation makes it an indented code block
- Reformats tables inside ```markdown / ```md fenced code blocks
- Skips tables inside all other fenced code blocks, including one nested in a markdown fence
- Keeps the file's line endings (CRLF stays CRLF) and a leading UTF-8 BOM

Usage:
    python3 reformat_tables.py file.md [file2.md ...]
    python3 reformat_tables.py --check file.md     # dry-run, exit 1 if changes needed
    python3 reformat_tables.py --backup file.md    # creates file.md.bak before writing
    python3 reformat_tables.py -r [dir ...]        # find and reformat all *.md under dir (default: .)
    python3 reformat_tables.py --strict file.md    # exit 1 if any table has a ragged row

Exit codes: 0 = done (nothing needed, or everything was rewritten), 1 = `--check` found a table
to reformat or `--strict` found a ragged row, 2 = usage error or a file that could not be read.

Cells are split the way GFM splits them: at EVERY pipe not escaped with a backslash, including a
pipe inside a code span. GFM does not protect a pipe in backticks, so `a | b` in a cell is two
cells when rendered; write it as `a \\| b`.

A RAGGED ROW - one whose cell count does not match its header - is reported on stderr and named
in the status line, always. It is the one shape this tool cannot repair: GFM splits a row at each
unescaped pipe and DROPS the surplus, so the extra content vanishes when rendered while the table
still looks correct. Since there is nothing to reformat, the file would otherwise be reported as
Unchanged, which reads as a clean bill of health for the exact defect worth catching. `--strict`
turns that report into a non-zero exit for CI; the default stays a warning so existing callers
keep their exit codes.
"""

import re
import shutil
import sys
import unicodedata
from pathlib import Path

USAGE = (
    "Usage: python3 reformat_tables.py [--check] [--backup] [--strict] "
    "(<file.md> [...] | -r [dir ...])"
)

EXIT_OK = 0
EXIT_FINDING = 1
EXIT_ERROR = 2

_FENCE_OPEN_RX = re.compile(r"^(`{3,}|~{3,})")
_FENCE_CLOSE_RX = re.compile(r"^(`{3,}|~{3,})\s*$")
# A list item marker and the whitespace after it; group(0) ends where the item's content starts.
_LIST_ITEM_RX = re.compile(r"^[ \t]*(?:[-*+]|\d{1,9}[.)])(?:[ \t]+|$)")
# CommonMark: four columns of indentation beyond the enclosing block's content make a code block.
_CODE_INDENT = 4
_TAB_WIDTH = 4


def parse_separator_cell(cell):
    """Parse a separator cell, return (left_align, right_align, is_valid).

    Recognizes: ---, :---, ---:, :---:
    """
    s = cell.strip()
    if not s:
        return False, False, False
    left = s.startswith(":")
    right = s.endswith(":")
    inner = s.lstrip(":").rstrip(":")
    if not inner or not all(c == "-" for c in inner):
        return False, False, False
    return left, right, True


def is_separator_row(cells):
    """Check if all cells in a row are valid separator cells."""
    if not cells:
        return False
    return all(parse_separator_cell(c)[2] for c in cells)


def build_separator_cell(width, left_align, right_align):
    """Build a separator cell with proper width and alignment markers.

    Total width between pipes = content_width + 2 (for the spaces in content rows).
    Alignment colons consume one dash each.
    """
    total = width + 2  # must fill same width as "| content |" minus the pipes
    if left_align and right_align:
        return ":" + "-" * (total - 2) + ":"
    elif left_align:
        return ":" + "-" * (total - 1)
    elif right_align:
        return "-" * (total - 1) + ":"
    else:
        return "-" * total


def _strip_edge_pipes(stripped):
    """Drop the row's outer pipes. A trailing `\\|` is an escaped pipe, not the row's edge.

    The splitter below treats every backslash-pipe as escaped, so the edge test must agree with
    it: dropping that pipe would turn cell text into a separator the next pass then pads.
    """
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]
    return stripped


def split_table_row(line):
    """Split a markdown table row into cells the way GFM does.

    Every pipe splits a cell unless a backslash escapes it - INCLUDING a pipe inside a code span.
    GFM gives backticks no protection here, so treating `a | b` as one cell would report a row as
    well formed while the rendered table drops its last cell.
    """
    stripped = _strip_edge_pipes(line.strip())
    cells = []
    current = []
    i = 0
    while i < len(stripped):
        ch = stripped[i]
        if ch == "\\" and i + 1 < len(stripped) and stripped[i + 1] == "|":
            current.append("\\|")
            i += 2
        elif ch == "|":
            cells.append("".join(current).strip())
            current = []
            i += 1
        else:
            current.append(ch)
            i += 1
    cells.append("".join(current).strip())
    return cells


def display_width(text):
    """Columns the text occupies in a monospace view: wide East Asian characters take two,
    combining marks and format characters none. Counting code points instead misaligns every
    row holding CJK text or a decomposed accent, and `--check` then calls it aligned."""
    width = 0
    for ch in text:
        if unicodedata.combining(ch) or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def _pad(cell, width):
    return cell + " " * (width - display_width(cell))


def table_column_mismatches(lines):
    """Rows whose cell count differs from the header's, as (index, count) pairs.

    This is the one shape the reformatter cannot repair, and the reason it needs reporting
    separately: GFM splits a row at each unescaped pipe and DROPS the surplus, so a 4-cell row
    under a 3-column header renders as 3 cells and the extra content disappears. Nothing about
    the rendered table looks wrong, and the formatter - which can only align what parses - is
    right to leave the file alone. Silence is what makes it a defect.

    Empty for anything without a valid separator row: that is not a ragged table, it is not a
    table, and reporting it would bury the real finding in noise.
    """
    if len(lines) < 2:
        return []
    rows = [split_table_row(line) for line in lines]
    if not is_separator_row(rows[1]):
        return []
    expected = len(rows[0])
    return [(i, len(row)) for i, row in enumerate(rows) if len(row) != expected]


def reformat_table(lines):
    """Reformat a markdown table. Returns lines unchanged if structure is invalid."""
    if len(lines) < 2:
        return lines

    rows = [split_table_row(line) for line in lines]

    # Second row must be a valid separator
    if not is_separator_row(rows[1]):
        return lines

    num_cols = len(rows[0])

    # All rows must have the same column count  -  bail if not
    for row in rows:
        if len(row) != num_cols:
            return lines

    # Parse alignment from separator row
    alignments = []
    for cell in rows[1]:
        left, right, _ = parse_separator_cell(cell)
        alignments.append((left, right))

    # Calculate max width per column (skip separator row)
    col_widths = [0] * num_cols
    for i, row in enumerate(rows):
        if i == 1:
            continue
        for j, cell in enumerate(row):
            col_widths[j] = max(col_widths[j], display_width(cell))

    # Minimum width of 1 so separator is at least "---"
    col_widths = [max(w, 1) for w in col_widths]

    result = []
    for i, row in enumerate(rows):
        if i == 1:
            parts = [
                "|" + build_separator_cell(col_widths[j], *alignments[j])
                for j in range(num_cols)
            ]
            result.append("".join(parts) + "|")
        else:
            parts = ["| " + _pad(row[j], col_widths[j]) + " " for j in range(num_cols)]
            result.append("".join(parts) + "|")
    return result


def _strip_blockquote(line):
    """Strip blockquote prefix (``> ``) from a line.

    Returns (prefix, rest) where *prefix* is the blockquote marker(s)
    including trailing space (e.g. ``"> "``, ``"> > "``) or ``""`` if the
    line is not inside a blockquote.
    """
    prefix = ""
    rest = line
    while rest.startswith(">"):
        rest = rest[1:]
        if rest.startswith(" "):
            prefix += "> "
            rest = rest[1:]
        else:
            prefix += ">"
    return prefix, rest


def _leading_whitespace(line):
    return line[: len(line) - len(line.lstrip(" \t"))]


def _indent_columns(line):
    return len(_leading_whitespace(line).expandtabs(_TAB_WIDTH))


def _is_indented_code(lines, index, floor, base_columns):
    """Whether the line at `index` is indented code rather than a table row.

    Four columns beyond the enclosing block make an indented code block in CommonMark, so a
    pipe table written that way is an example, not a table. Inside a list item the enclosing
    block is the item's content, which starts after its marker, so a table indented to sit in
    the item is not code. The walk goes back to the nearest less-indented line: a list item
    decides by its content column, top-level text means there is no list to belong to.
    """
    columns = _indent_columns(lines[index])
    if columns - base_columns < _CODE_INDENT:
        return False
    for j in range(index - 1, floor, -1):
        prior = lines[j]
        if not prior.strip():
            continue
        prior_columns = _indent_columns(prior)
        if prior_columns >= columns:
            continue
        item = _LIST_ITEM_RX.match(prior)
        if item:
            content_columns = len(item.group(0).expandtabs(_TAB_WIDTH))
            if not item.group(0).endswith((" ", "\t")):
                content_columns += 1
            return columns - content_columns >= _CODE_INDENT
        if prior_columns <= base_columns:
            return True
    return True


class _Fence:
    """An open fenced code block: its marker, and whether its content is markdown."""

    def __init__(self, marker, info, index, columns):
        self.char = marker[0]
        self.length = len(marker)
        lang = info.split()[0].lower() if info else ""
        self.markdown = lang in ("markdown", "md")
        self.index = index
        self.columns = columns

    def closed_by(self, lstripped):
        close = _FENCE_CLOSE_RX.match(lstripped)
        return bool(close) and close.group(1)[0] == self.char and len(close.group(1)) >= self.length


def _fence_opener(lstripped, index, columns):
    match = _FENCE_OPEN_RX.match(lstripped)
    if not match:
        return None
    marker = match.group(1)
    return _Fence(marker, lstripped[len(marker):].strip(), index, columns)


def _ragged_messages(filepath, first_line, contents):
    """One message per ragged row, or one for the whole table when its separator is the problem."""
    expected = len(split_table_row(contents[0]))
    mismatches = table_column_mismatches(contents)
    for offset, count in mismatches:
        if offset == 1:
            # GFM requires the delimiter row to match the header; if it does not, nothing below it
            # is a table at all, so a per-row claim about dropped or padded cells would be false.
            return [
                f"{filepath}:{first_line + 1}: ragged table - the separator row has {count} cells "
                f"under a {expected}-column header; GFM does not render this as a table at all"
            ]
    messages = []
    for offset, count in mismatches:
        # The two directions have DIFFERENT consequences, and only one loses content. A single
        # message claiming loss would be wrong half the time, which is how a warning trains its
        # reader to ignore it.
        effect = (
            "GFM drops the surplus, so this row LOSES CONTENT when rendered"
            if count > expected else
            "GFM pads the row, so the missing cell renders EMPTY"
        )
        messages.append(
            f"{filepath}:{first_line + offset}: ragged table row - "
            f"{count} cells under a {expected}-column header; {effect}"
        )
    return messages


def _read_document(filepath):
    """(text without BOM, had_bom). newline="" keeps every CR, so line endings survive a rewrite."""
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        original = f.read()
    if original.startswith("\ufeff"):
        return original[1:], True
    return original, False


def _reformat_lines(lines, filepath, warnings):
    """The reformatted lines, one output line per input line and in the same order."""
    result = []
    table_lines = []   # (indent, blockquote prefix, row content)
    table_start = [0]  # 1-based file line of the current table's first row
    fence = None       # the open outer fence
    inner = None       # a fence opened inside a markdown fence
    boundary = [-1]    # index of the last fence line, where the indented-code walk stops

    def flush_table():
        if not table_lines:
            return
        contents = [t[2] for t in table_lines]
        if warnings is not None:
            warnings.extend(_ragged_messages(filepath, table_start[0], contents))
        indent = table_lines[0][0]
        for (_lead, bq_prefix, _row), fline in zip(table_lines, reformat_table(contents)):
            result.append(indent + bq_prefix + fline)
        table_lines.clear()

    for index, line in enumerate(lines):
        lstripped = line.lstrip()
        columns = _indent_columns(line)

        if fence is None:
            opener = _fence_opener(lstripped, index, columns)
            if opener is not None:
                flush_table()
                fence, boundary[0] = opener, index
                result.append(line)
                continue
        elif fence.closed_by(lstripped):
            flush_table()
            fence, inner, boundary[0] = None, None, index
            result.append(line)
            continue
        elif not fence.markdown:
            result.append(line)
            continue
        else:
            # Inside a markdown fence the content is a document of its own, so a fence there opens
            # or closes a nested block. Flushing first keeps the pending table above the fence line.
            if inner is not None and inner.closed_by(lstripped):
                flush_table()
                inner, boundary[0] = None, index
                result.append(line)
                continue
            if inner is None:
                opener = _fence_opener(lstripped, index, columns)
                if opener is not None:
                    flush_table()
                    inner, boundary[0] = opener, index
                    result.append(line)
                    continue
            if inner is not None and not inner.markdown:
                result.append(line)
                continue

        # Collect table rows (must start with | and contain at least one more |)
        # Also detect tables inside blockquotes (> | ... |)
        bq_prefix, table_content = _strip_blockquote(line.strip())
        is_row = table_content.startswith("|") and "|" in table_content[1:]
        if is_row and not table_lines:
            base = fence.columns if fence is not None else 0
            is_row = not _is_indented_code(lines, index, boundary[0], base)
        if is_row:
            if not table_lines:
                table_start[0] = index + 1
            table_lines.append((_leading_whitespace(line), bq_prefix, table_content))
        else:
            flush_table()
            result.append(line)

    flush_table()
    return result


def reformat_file(filepath, *, check_only=False, backup=False, warnings=None):
    """Reformat all tables in a file.

    Tables inside ```markdown / ```md fenced code blocks are reformatted.
    Tables inside all other fenced code blocks are skipped.
    Returns True if the file was (or would be) changed.

    Pass a list as `warnings` to receive one message per ragged table - a row whose cell count
    does not match its header. Those are never reformatted, so without this they leave no trace.

    Raises:
        OSError: the file cannot be read or written.
        UnicodeDecodeError: the file is not UTF-8.
    """
    text, had_bom = _read_document(filepath)
    raw_lines = text.split("\n")
    carriage = [line.endswith("\r") for line in raw_lines]
    lines = [line[:-1] if cr else line for line, cr in zip(raw_lines, carriage)]

    result = _reformat_lines(lines, filepath, warnings)
    body = "\n".join(line + ("\r" if cr else "") for line, cr in zip(result, carriage))

    if body == text:
        return False

    if check_only:
        return True

    if backup:
        shutil.copy2(filepath, str(filepath) + ".bak")

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(("\ufeff" if had_bom else "") + body)
    return True


def _reconfigure_stdio():
    """Never let a filename the console code page cannot encode crash a run half way through.

    On Windows a redirected stdout uses the ANSI code page; a CJK filename then raised after that
    file had already been rewritten, and every later file was skipped.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            continue


def _parse_args(args):
    """(options dict, positional paths). Exits 2 on an unknown option."""
    options = {"check": False, "backup": False, "recursive": False, "strict": False}
    paths = []
    for arg in args:
        if arg in ("--check", "-c"):
            options["check"] = True
        elif arg in ("--backup", "-b"):
            options["backup"] = True
        elif arg in ("--recursive", "-r"):
            options["recursive"] = True
        elif arg == "--strict":
            options["strict"] = True
        elif arg in ("--help", "-h"):
            print(__doc__.strip())
            sys.exit(EXIT_OK)
        elif arg.startswith("-"):
            print(f"Unknown option: {arg}", file=sys.stderr)
            print(USAGE, file=sys.stderr)
            sys.exit(EXIT_ERROR)
        else:
            paths.append(arg)
    return options, paths


def _collect_recursive(paths):
    """Every regular *.md file under the named directories. A directory named *.md or a dangling
    link is reported and skipped rather than aborting the run half way through."""
    dirs = [Path(p) for p in paths] if paths else [Path(".")]
    files = []
    for d in dirs:
        if not d.is_dir():
            print(f"Error: not a directory: {d}", file=sys.stderr)
            sys.exit(EXIT_ERROR)
        for candidate in sorted(d.rglob("*.md")):
            if candidate.is_file():
                files.append(candidate)
            else:
                print(f"Skipping (not a regular file): {candidate}", file=sys.stderr)
    return files


def _collect_explicit(paths):
    """The named files, all checked BEFORE any is written, so a typo cannot stop a run half done."""
    files = [Path(p) for p in paths]
    missing = [p for p in files if not p.is_file()]
    for path in missing:
        print(f"Error: not a file: {path}", file=sys.stderr)
    if missing:
        sys.exit(EXIT_ERROR)
    return files


def _process(path, options):
    """(changed, ragged count) for one file; raises OSError / UnicodeDecodeError."""
    warnings = []
    changed = reformat_file(
        path, check_only=options["check"], backup=options["backup"], warnings=warnings)
    for message in warnings:
        print(message, file=sys.stderr)
    # A ragged table is named on stdout too. It cannot be reformatted, so the status line
    # would otherwise read "Unchanged", which is exactly the false all-clear being fixed.
    suffix = f" ({len(warnings)} ragged table row(s))" if warnings else ""
    if not changed:
        print(f"Unchanged{suffix}: {path}")
    elif options["check"]:
        print(f"Would reformat{suffix}: {path}")
    else:
        print(f"Reformatted{suffix}: {path}")
    return changed, len(warnings)


def main():
    _reconfigure_stdio()
    options, paths = _parse_args(sys.argv[1:])

    if options["recursive"]:
        files = _collect_recursive(paths)
        if not files:
            print("No .md files found.", file=sys.stderr)
            sys.exit(EXIT_OK)
    elif not paths:
        print(USAGE, file=sys.stderr)
        sys.exit(EXIT_ERROR)
    else:
        files = _collect_explicit(paths)

    any_changed = any_ragged = any_error = False
    for path in files:
        try:
            changed, ragged = _process(path, options)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"Error: cannot process {path}: {exc}", file=sys.stderr)
            any_error = True
            continue
        any_changed = any_changed or changed
        any_ragged = any_ragged or bool(ragged)

    if any_error:
        sys.exit(EXIT_ERROR)
    if options["check"] and any_changed:
        sys.exit(EXIT_FINDING)
    if options["strict"] and any_ragged:
        sys.exit(EXIT_FINDING)


if __name__ == "__main__":
    main()
