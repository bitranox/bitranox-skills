# skill-writer checklist - compuse-toolbox (2026-09-25, one escaped pipe in a table row)

Change: one table row wrote `` `--after|--before` `` inside a code span. GFM splits a cell at every
unescaped pipe, code spans included, so the row rendered with 4 cells under a 3-column header and
the last cell was dropped. The pipe is now written `\|`; the table is realigned. No wording changed.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session).
- [x] RED: `reformat_tables.py --strict` (now splitting as GFM does) reports this row as
      "4 cells under a 3-column header; GFM drops the surplus". GREEN: the same run reports nothing.
- [x] Text check only: the row's words are unchanged, so no reader-facing behaviour moved.
- [x] Description unchanged; no routing keyword moved.
- [x] Security scan: no hosts, addresses or private paths added.
