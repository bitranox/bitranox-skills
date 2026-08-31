# skill-writer checklist - coding-python-rpyc (2026-08-31, missing routing cell)

Change: one cell. The `Per-module API` row of the upstream-docs routing table had two cells under a
three-column header, so its third column - the upstream path - was absent. Restored as `api/`.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] Found by MEASUREMENT, not review: the ragged-row report added to
      `docs-md-table-formatting/reformat_tables.py` in this same change flagged it on its first
      sweep of the plugin tree.
- [x] Direction checked before calling it content loss: a SHORT row is padded by GFM, so the cell
      rendered EMPTY rather than dropping text. The consequence is a tier-2 routing row that names
      no file, which is a dead entry in a table whose whole job is routing a reader to one.
- [x] The restored value is the path the row's own prose already names (`api/*.md`), so it is
      recovered from the row rather than invented.
- [x] Verified after the edit: the file reports no ragged rows.
- [x] No other change to this skill; content, triggers and structure untouched.
- [x] Scope / security: one relative path in a routing table; nothing sensitive.
- [x] CSO description: unchanged.
