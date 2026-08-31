# skill-writer checklist - coding-python-textual (2026-08-31, vendored table repair)

Change: `widgets/progress_bar.md` - the reactive-attributes table wrote the type as
`` `float | None` `` with the pipe unescaped in two rows. Pipes escaped, the two lost Default cells
restored, and the divergence recorded in SKILL.md.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] Found by MEASUREMENT: the ragged-row report added to `reformat_tables.py` in this same
      release flagged both rows on its first sweep of the plugin tree.
- [x] The mechanism is the one this repo already has a fact and a skill row for: GFM processes the
      pipe BEFORE inline parsing, so backticks do not protect it. The cell splits, and here the
      surplus consumed the DEFAULT column - the table rendered a column short while still looking
      well formed.
- [x] The restored values are READ, not inferred: `ProgressBar.percentage` and `.total` both
      default to `None` on the installed textual 8.2.8 - the same version this skill's inverted-
      names section cites - and `progress` defaults to 0.0, matching the one row that was never
      broken. Sourcing them mattered: the file states them nowhere else, so writing them from
      memory would have put an unchecked API claim into a reference doc.
- [x] DIVERGENCE DECIDED AND RECORDED, not silently introduced. Vendored docs are otherwise
      untouched mirrors, so SKILL.md now carries a short section naming this one file, what was
      changed, why, and the instruction to re-apply it if these files are ever re-synced. Without
      that, a future sync silently reverts the fix and nobody knows the table was ever right.
- [x] Verified after the edit: the file reports no ragged rows.
- [x] Scope of the edit is two lines plus the note; no other vendored file touched.
- [x] Security scan: API names and defaults only.
- [x] CSO description: unchanged.
