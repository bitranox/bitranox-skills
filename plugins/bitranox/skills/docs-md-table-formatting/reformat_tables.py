#!/usr/bin/env python3
"""Reformat all markdown tables in a file with proper column alignment.

Rules applied:
- Cells padded to widest content per column
- Separator dashes touch pipes (no spaces)
- Content cells have exactly one space padding
- Consistent column count per table
- Preserves column alignment markers (:---, :---:, ---:)
- Reformats tables inside blockquotes (> | ... |), preserving prefix
- Reformats tables inside ```markdown / ```md fenced code blocks
- Skips tables inside all other fenced code blocks

Usage:
    python3 reformat_tables.py file.md [file2.md ...]
    python3 reformat_tables.py --check file.md     # dry-run, exit 1 if changes needed
    python3 reformat_tables.py --backup file.md    # creates file.md.bak before writing
    python3 reformat_tables.py -r [dir]            # find and reformat all *.md under dir (default: .)
    python3 reformat_tables.py --strict file.md    # exit 1 if any table has a ragged row

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
from pathlib import Path


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


def split_table_row(line):
    """Split a markdown table row into cells, respecting backtick spans.

    Pipes inside backtick spans (e.g., `a | b`) are not treated as separators.
    """
    stripped = line.strip()
    # Remove leading and trailing pipe
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]

    cells = []
    current = []
    i = 0
    while i < len(stripped):
        ch = stripped[i]
        if ch == "`":
            # Count opening backticks
            bt_start = i
            while i < len(stripped) and stripped[i] == "`":
                i += 1
            bt_count = i - bt_start
            current.append("`" * bt_count)
            # Find matching closing backticks (same count)
            while i < len(stripped):
                if stripped[i] == "`":
                    close_start = i
                    while i < len(stripped) and stripped[i] == "`":
                        i += 1
                    close_count = i - close_start
                    current.append("`" * close_count)
                    if close_count == bt_count:
                        break  # matched
                else:
                    current.append(stripped[i])
                    i += 1
        elif ch == "\\" and i + 1 < len(stripped) and stripped[i + 1] == "|":
            # Escaped pipe  -  not a separator
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
            col_widths[j] = max(col_widths[j], len(cell))

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
            parts = ["| " + row[j].ljust(col_widths[j]) + " " for j in range(num_cols)]
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


def reformat_file(filepath, *, check_only=False, backup=False, warnings=None):
    """Reformat all tables in a file.

    Tables inside ```markdown / ```md fenced code blocks are reformatted.
    Tables inside all other fenced code blocks are skipped.
    Returns True if the file was (or would be) changed.

    Pass a list as `warnings` to receive one message per ragged table - a row whose cell count
    does not match its header. Those are never reformatted, so without this they leave no trace.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()

    lines = original.split("\n")

    result = []
    table_lines = []
    in_fence = False
    in_markdown_fence = False
    fence_char = None
    fence_len = 0

    table_start = [0]          # 1-based file line of the current table's first row

    def flush_table():
        if table_lines:
            prefixes = [t[0] for t in table_lines]
            contents = [t[1] for t in table_lines]
            if warnings is not None:
                expected = len(split_table_row(contents[0]))
                for offset, count in table_column_mismatches(contents):
                    # The two directions have DIFFERENT consequences, and only one loses content.
                    # A single message claiming loss would be wrong half the time, which is how a
                    # warning trains its reader to ignore it.
                    effect = (
                        "GFM drops the surplus, so this row LOSES CONTENT when rendered"
                        if count > expected else
                        "GFM pads the row, so the missing cell renders EMPTY"
                    )
                    warnings.append(
                        f"{filepath}:{table_start[0] + offset}: ragged table row - "
                        f"{count} cells under a {expected}-column header; {effect}"
                    )
            formatted = reformat_table(contents)
            for prefix, fline in zip(prefixes, formatted):
                result.append(prefix + fline if prefix else fline)
            table_lines.clear()

    for lineno, line in enumerate(lines, 1):
        # Detect fenced code block boundaries (``` or ~~~)
        lstripped = line.lstrip()
        fence_match = re.match(r"^(`{3,}|~{3,})", lstripped)

        if fence_match:
            if not in_fence:
                flush_table()
                in_fence = True
                fence_char = fence_match.group(1)[0]
                fence_len = len(fence_match.group(1))
                # Check if the code block is tagged as markdown
                info_string = lstripped[len(fence_match.group(1)) :].strip()
                lang = info_string.split()[0].lower() if info_string else ""
                in_markdown_fence = lang in ("markdown", "md")
                result.append(line)
                continue
            else:
                # Closing fence: same char, at least same length, nothing else on line
                close_match = re.match(r"^(`{3,}|~{3,})\s*$", lstripped)
                if (
                    close_match
                    and close_match.group(1)[0] == fence_char
                    and len(close_match.group(1)) >= fence_len
                ):
                    if in_markdown_fence:
                        flush_table()
                    in_fence = False
                    in_markdown_fence = False
                result.append(line)
                continue

        if in_fence and not in_markdown_fence:
            result.append(line)
            continue

        # Collect table rows (must start with | and contain at least one more |)
        # Also detect tables inside blockquotes (> | ... |)
        stripped = line.strip()
        bq_prefix, table_content = _strip_blockquote(stripped)
        if table_content.startswith("|") and "|" in table_content[1:]:
            if not table_lines:
                table_start[0] = lineno
            table_lines.append((bq_prefix, table_content))
        else:
            flush_table()
            result.append(line)

    flush_table()

    new_content = "\n".join(result)

    if original == new_content:
        return False

    if check_only:
        return True

    if backup:
        shutil.copy2(filepath, str(filepath) + ".bak")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def main():
    args = sys.argv[1:]
    check_only = False
    backup = False
    recursive = False
    strict = False
    files = []

    for arg in args:
        if arg in ("--check", "-c"):
            check_only = True
        elif arg in ("--backup", "-b"):
            backup = True
        elif arg in ("--recursive", "-r"):
            recursive = True
        elif arg == "--strict":
            strict = True
        elif arg in ("--help", "-h"):
            print(__doc__.strip())
            sys.exit(0)
        elif arg.startswith("-"):
            print(f"Unknown option: {arg}", file=sys.stderr)
            sys.exit(1)
        else:
            files.append(arg)

    if recursive:
        dirs = [Path(f) for f in files] if files else [Path(".")]
        files = []
        for d in dirs:
            if not d.is_dir():
                print(f"Error: not a directory: {d}", file=sys.stderr)
                sys.exit(1)
            files.extend(sorted(d.rglob("*.md")))
        if not files:
            print("No .md files found.", file=sys.stderr)
            sys.exit(0)
    elif not files:
        print(
            "Usage: python3 reformat_tables.py [--check] [--backup] [--recursive] <file.md|dir> [...]",
            file=sys.stderr,
        )
        sys.exit(1)

    any_changed = False

    any_ragged = False
    for path in files:
        path = Path(path)
        if not path.is_file():
            print(f"Error: not a file: {path}", file=sys.stderr)
            sys.exit(1)
        warnings = []
        changed = reformat_file(
            path, check_only=check_only, backup=backup, warnings=warnings)
        for message in warnings:
            print(message, file=sys.stderr)
            any_ragged = True
        # A ragged table is named on stdout too. It cannot be reformatted, so the status line
        # would otherwise read "Unchanged", which is exactly the false all-clear being fixed.
        suffix = f" ({len(warnings)} ragged table row(s))" if warnings else ""
        if changed:
            any_changed = True
            if check_only:
                print(f"Would reformat{suffix}: {path}")
            else:
                print(f"Reformatted{suffix}: {path}")
        else:
            print(f"Unchanged{suffix}: {path}")

    if check_only and any_changed:
        sys.exit(1)
    if strict and any_ragged:
        sys.exit(1)


if __name__ == "__main__":
    main()
