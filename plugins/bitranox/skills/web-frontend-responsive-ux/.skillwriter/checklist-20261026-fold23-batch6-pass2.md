# skill-writer checklist - web-frontend-responsive-ux (memory rules folded in)

- [x] Rule: Use white-space:nowrap for identifier columns and overflow-wrap:break-word for free-
      text columns, never word-break:break-word, which shrinks the column to one character so text
      breaks letter by letter. Put a long unbreakable value inside a fixed-width block (with a
      phone media-query override) that alone uses break-all or anywhere. Render with real data and
      screenshot it at desktop and phone width before sending.
      Where: touch-and-gestures.md reconcile), responsive-layout.md '## No horizontal overflow' table
      (row corrected + row added) and new '### Wrapping inside a table (HTML e-mail included)';
      SKILL.md Common Mistakes row after 'Flex/grid child overflowing'; touch-and-gestures.md Text
      expansion bullet
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. The rules
      under test are recorded in this machine's memory store, so a behavioural arm would be
      contaminated; only a verbatim quote from the snapshot counts.
- [x] GREEN quote-back on haiku and opus against the edited files (6 questions), again after the
      review fixes for every question, and a third time for the 1 questions the fix-delta fixes
      touched: every answer quoted the edited text, no NONE. Quotes were substring-checked against
      the files; the pre-edit snapshots fail the same check.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per question per tier per round.
- [x] Independent review of the full diff, then of the fix delta alone; every finding fixed or
      declined with evidence by the fixer, and the fix delta re-reviewed.
- [x] Each GREEN Skill gaps list triaged: 6 closed in the text, 11 declined with a reason (covered
      elsewhere with file:line, out of scope, owned by another skill, or a judgement the skill
      leaves open).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), added
      prose wrapped like the surrounding text, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; addresses are
      documentation ranges or placeholders.
