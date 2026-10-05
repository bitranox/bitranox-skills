# skill-writer checklist - coding-python-new-public-library (table re-pad only)

Change: the "Common mistakes" table is re-padded into the canonical form of
`docs-md-table-formatting/reformat_tables.py`. No word, cell, row, alignment marker or front-matter
line changes. Without it, the reformat-md-tables hook rewrites this file in every fresh worktree
and the commit gate then demands a checklist for a skill nobody edited.

## Proof that this is table padding only

- [x] `reformat_tables.py --check` reported "Would reformat" before the change and exits 0 after it.
- [x] Line count is unchanged; 8 lines differ, every one a table row on both sides.
- [x] Every changed content row has the same cells after stripping whitespace; the separator row
      keeps the same alignment markers (none, left default) in every column. Checked by a script
      that compares the two versions cell by cell, and a control run of that script with one
      cell altered is rejected by it.
- [x] Front matter, description and every non-table line are byte-identical.

## Why no RED/GREEN run

- [x] Nothing a reader or the router sees changes: the rendered table is identical and the
      description is untouched, so a pressure scenario has no behaviour to watch differ. This is
      the whitespace-only table re-padding exception, proven cell by cell above.

## Mirror

- [x] MIRRORED skill: the same re-pad is applied to the twin
      `libs/bitranox_template_py_lib/skills/new-public-python-library/SKILL.md`; the two files
      still differ only on the `name:` line, and the twin's `plugin.json` gets a patch bump.

## Quality

- [x] ASCII only; no address, hostname or machine path added.
- [x] Present tense, no session narrative.
