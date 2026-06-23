---
name: md-table-formatting
description: Use when creating, editing, or reformatting markdown tables in any document, when table columns look misaligned, or when reviewing markdown files that contain tables
---

# Markdown Table Formatting

## Overview

Rules for consistently formatted, readable markdown tables. Misaligned tables are hard to scan in source view and may trigger linter warnings.

**After editing or creating tables, reformat all `*.md` files under the current working directory** by running `reformat_tables.py -r` from this skill's directory.

## Rules

### 1. Pad all cells to column width

Every cell in a column must be padded with trailing spaces to match the widest content in that column.

```txt
# BAD — unpadded
| Name | Value |
|------|-------|
| Type | Settable |
| Value | String (colon-separated list) |

# GOOD — padded to widest content per column
| Name  | Value                         |
|-------|-------------------------------|
| Type  | Settable                      |
| Value | String (colon-separated list) |
```

### 2. Separator dashes touch the pipes

No spaces between pipes and dashes in the separator row. Dash count = column width + 2 (matching the space-padded content cells).

```txt
# BAD — spaces around dashes
| Name  | Value    |
| ----- | -------- |

# GOOD — dashes touch pipes
| Name  | Value    |
|-------|----------|
```

### 3. Content cells have exactly one space padding

Each content cell has exactly one space after `|` and one space before `|`.

```txt
# BAD — inconsistent spacing
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
# Reformat all *.md files under current directory (recursive)
python3 reformat_tables.py -r

# Reformat all *.md files under a specific directory
python3 reformat_tables.py -r docs/

# Reformat specific files
python3 reformat_tables.py file.md [file2.md ...]

# Dry-run — reports what would change, exits 1 if changes needed
python3 reformat_tables.py --check -r

# Create .bak backup before writing
python3 reformat_tables.py --backup file.md
```

Safe by design: reformats tables inside blockquotes and `` ```markdown ``/`` ```md `` fenced code blocks, skips all other fenced code blocks, preserves alignment markers (`:---`, `:---:`, `---:`), handles pipes inside backtick spans, and bails on tables with inconsistent column counts.
