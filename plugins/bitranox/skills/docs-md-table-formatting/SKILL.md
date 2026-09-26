---
name: docs-md-table-formatting
description: Use when creating, editing, or reformatting markdown tables in any document, when table columns look misaligned, or when reviewing markdown files that contain tables
---

# Markdown Table Formatting

## Overview

Rules for consistently formatted, readable markdown tables. Misaligned tables are hard to scan in source view and may trigger linter warnings.

**A `reformat-md-tables` PostToolUse hook auto-realigns tables in every `*.md` file on each Write/Edit**, so tables Claude writes stay aligned with no manual step. To bulk-reformat a tree by hand or in CI, run this skill's `reformat_tables.py -r <dir>` (see Programmatic Reformatting below).

## Rules

### 1. Pad all cells to column width

Every cell in a column must be padded with trailing spaces to match the widest content in that column.

```txt
# BAD  -  unpadded
| Name | Value |
|------|-------|
| Type | Settable |
| Value | String (colon-separated list) |

# GOOD  -  padded to widest content per column
| Name  | Value                         |
|-------|-------------------------------|
| Type  | Settable                      |
| Value | String (colon-separated list) |
```

### 2. Separator dashes touch the pipes

No spaces between pipes and dashes in the separator row. Dash count = column width + 2 (matching the space-padded content cells).

```txt
# BAD  -  spaces around dashes, and columns wider than their content
| Name  | Value    |
| ----- | -------- |

# GOOD  -  dashes touch pipes, width follows the widest cell (rule 1)
| Name | Value |
|------|-------|
```

That GOOD block is exactly what `reformat_tables.py` emits for the BAD input above: it re-sizes
each column to its widest cell, so stale padding does not survive the pass.

### 3. Content cells have exactly one space padding

Each content cell has exactly one space after `|` and one space before `|`.

```txt
# BAD  -  inconsistent spacing
|Name  |Value                         |
| Name  |Value                         |

# GOOD
| Name  | Value                         |
```

### 4. Trailing pipe required

Every row ends with a closing `|`.

### 5. Column count is consistent

Every row (header, separator, data) must have the same number of columns.

### 6. Reformat tables inside blockquotes

Tables inside blockquotes (`> | ... |`) are reformatted using the same rules. The blockquote prefix is preserved.

### 7. Reformat tables inside markdown fenced code blocks

Tables inside fenced code blocks tagged with `markdown` or `md` are reformatted using the same rules as tables in the document body. Tables in other code blocks (e.g., `python`, `json`) are left untouched.

## Quick Reference

```
| header1 | header2 long name |      <- content padded to widest per column
|---------|-------------------|      <- dashes touch pipes, width = content + 2 spaces
| short   | value             |      <- trailing spaces to fill column width
| longer  | x                 |      <- every cell padded
```

## Programmatic Reformatting

For files with many tables, use `reformat_tables.py` in this directory rather than manual edits:

```bash
# Reformat all *.md files under a specific directory (recursive).
# Pass the directory explicitly - a bare -r reformats the CURRENT directory,
# which is this skill's own dir if you cd'd here to run the script.
python3 reformat_tables.py -r docs/

# Reformat specific files
python3 reformat_tables.py file.md [file2.md ...]

# Dry-run  -  reports what would change, exits 1 if changes needed
python3 reformat_tables.py --check -r

# Create .bak backup before writing
python3 reformat_tables.py --backup file.md

# Fail (exit 1) if any table has a ragged row - for CI
python3 reformat_tables.py --strict -r
```

Exit codes: 0 = done, 1 = `--check` found a table to reformat or `--strict` found a ragged row, 2 = usage error or a file that could not be read (not UTF-8, missing, not a regular file). A directory named `*.md` or a dangling link met by `-r` is reported and skipped.

Safe by design: reformats tables inside blockquotes and `` ```markdown ``/`` ```md `` fenced code blocks, skips all other fenced code blocks (including one nested inside a markdown fence) and indented code blocks, recognises fences the CommonMark way (a line that merely opens with an inline span such as ` ```x``` ` is prose, and a fence indented four columns into its block is code, not a fence), keeps a list-nested table's indentation, preserves alignment markers (`:---`, `:---:`, `---:`), measures width in display columns (a CJK character counts two), keeps the file's line endings and a leading BOM, and leaves a table with inconsistent column counts alone.

**A pipe inside backticks still splits the cell.** GFM gives a code span no protection, so `` `a | b` `` in a table cell renders as two cells; write `` `a \| b` ``. The tool splits exactly as GFM does, so such a row is reported as ragged rather than accepted.

**A ragged row is REPORTED, not passed over in silence.** It is the one shape the tool cannot repair, and the two directions differ: a row with MORE cells than the header loses the surplus (GFM splits at each unescaped pipe and DROPS the extras, so a 4-cell row under a 3-column header renders as 3 and the content disappears while the table still looks correct), while a row with FEWER is PADDED, so the missing cell renders empty. The message says which, because a warning that claims content loss for both is wrong half the time. Since there is nothing to reformat, the run would otherwise print `Unchanged`, which reads as a clean bill of health for exactly the defect worth catching. Every ragged row now goes to stderr with its file and line, and the status line carries the count; `--strict` turns that into a non-zero exit for CI, while the default stays a warning so existing callers keep their exit codes. Its first sweep over this plugin found three, one of them a routing table whose third column had gone missing on a single row.

## Editing tables via JSON (tablekit.py)

`reformat_tables.py` re-aligns tables in place; when you need to CHANGE a table's
content (add/remove/reorder rows or columns, retarget alignment) without hand-padding
every cell, use `tablekit.py` in this directory. It round-trips a table through JSON:
read it, edit the JSON, and re-emit it fully aligned. `replace` splices the rendered
table back into the file at its original position, leaving surrounding prose untouched.

```bash
# Read the Nth table (0-based) to JSON: {headers, alignments, rows}
python3 tablekit.py read FILE.md --index 0        # omit --index to list all tables (with line spans)

# Render a table's JSON (from stdin) to aligned markdown
python3 tablekit.py render < table.json

# Edit the JSON in a pipeline, then splice it back into the file (or --stdout to preview)
python3 tablekit.py read FILE.md --index 0 \
  | jq '.rows += [["new", "row"]] | .alignments = ["left","right"]' \
  | python3 tablekit.py replace FILE.md --index 0
```

`alignments` values are `left` / `right` / `center` / `none`; any other value is refused.
`rows` is a list of cell-lists; a SHORT row is padded to the column count on render, a row
with MORE cells than headers is refused (exit 2), because truncating it would delete text
from the file - `read --index` refuses such a table for the same reason. Tables are numbered
as `reformat_tables.py` sees them (it shares that tool's fence scanner): one inside a
non-markdown code fence or an indented code block is not counted, one in a blockquote is. The
one difference is a table written without a leading pipe, which `tablekit.py` counts (GFM
renders it) and `reformat_tables.py` leaves unaligned. `replace` keeps the table's indentation,
its `> ` blockquote prefix, the file's line endings and a leading BOM; `--stdout` prints exactly
the bytes it would have written. Exit
codes: 0 = done, 1 = no table at that index, 2 = refused or error (invalid JSON, unreadable
file). Stdlib only; a literal `|` in a cell round-trips (escaped as `\|` in the markdown,
unescaped in the JSON).
