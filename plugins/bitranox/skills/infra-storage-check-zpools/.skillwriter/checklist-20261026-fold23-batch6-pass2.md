# skill-writer checklist - infra-storage-check-zpools (memory rules folded in)

- [x] Rule: Check whether the issue's severity is in alert_on_severities (or whether
      alert_recipients is empty) before touching mail, since a deliberate skip is also logged as
      'Failed to send alert' and DEBUG logging shows 'Skipping alert'; only the daemon/service
      sends alerts and applies the [daemon] settings, so cron `check` mails nothing; a list env
      override must be JSON such as '["CRITICAL","WARNING"]', not a comma-separated value.
      Where: SKILL.md, ## Use > ### Monitoring (two paragraphs after the daemon paragraph); ## Configure
      (the 'Malformed input degrades' paragraph reconciled)
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. The rules
      under test are recorded in this machine's memory store, so a behavioural arm would be
      contaminated; only a verbatim quote from the snapshot counts.
- [x] GREEN quote-back on haiku and opus against the edited files (5 questions), again after the
      review fixes for every question, and a third time for the 3 questions the fix-delta fixes
      touched: every answer quoted the edited text, no NONE. Quotes were substring-checked against
      the files; the pre-edit snapshots fail the same check.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per question per tier per round.
- [x] Independent review of the full diff, then of the fix delta alone; every finding fixed or
      declined with evidence by the fixer, and the fix delta re-reviewed.
- [x] Each GREEN Skill gaps list triaged: 5 closed in the text, 10 declined with a reason (covered
      elsewhere with file:line, out of scope, owned by another skill, or a judgement the skill
      leaves open).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), added
      prose wrapped like the surrounding text, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; addresses are
      documentation ranges or placeholders.
