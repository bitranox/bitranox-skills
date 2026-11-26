# skill-writer checklist - docs-md-table-formatting (2026-11-26, compact form past a 300-column cap)

Decisions: d-20261126-5b3ee8ad

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing; the one live rule
      (re-Read after realign) is untouched.
- [x] RED by text check, pre-edit text (`git show HEAD:`): 0 hits for compact, a width cap or 300
      columns.
- [x] RED probe, haiku, rules 1-3 of the pre-edit text, a 47-row table with one 6,382-character
      cell: padded every column-2 cell to 6,382, rows of about 6,400 characters, about 300 KB;
      its own gaps list: "The rules do not cover an outlier cell".
- [x] GREEN probe, haiku, the new rule 1 and exception: chose compact for the wide table and
      padded for a 20/30/40-column one, quoting the exception and rule 1.
- [x] Gaps closed after GREEN: the compact separator's spacing (it wrote `| :--- | --- |`; the
      text now says the cells touch their pipes and shows `|:---|---:|:---:|---|`), and what is
      measured (now: per table, the widest row padded per rule 1, pipes and spaces counted).
- [x] Quote-back, haiku, after the fix: `|:---|---|` and `| gate | short |`, each with the
      governing sentence quoted verbatim, and the measured quantity quoted.
- [x] Gaps declined: which column a named cell sits in (a detail of the probe's task, not the
      rule); display width of wide characters (rule 1 already says display columns, and the code
      counts a CJK character as two, pinned by test_the_cap_is_measured_in_display_columns);
      leading and trailing pipes (rule 3 and every example show them).
- [x] Code: `reformat_tables.py` (MAX_ALIGNED_WIDTH, too_wide_to_align, render_compact) and
      `tablekit.py` share one predicate and one compact renderer; 9 new tests, including the
      boundary pair (exactly at 300 stays aligned, 301 goes compact), alignment colons, removal
      of existing padding, stability, an empty cell and an escaped pipe, display columns,
      `--check`, and tablekit's output being what the formatter keeps. Suite: 157 passed.
- [x] Width and fence check over the added lines, and the ASCII check, printed nothing; the
      paragraph after the insertion (rule 2) still holds for tables under the cap.
- [x] Tiers: haiku for RED, GREEN and quote-back (3 cells); the rule is mechanical and applied
      by the tool itself, so the weak tier is the one that matters.
