# skill-writer checklist - infra-chrome-remote-desktop (memory rules folded in)

- [x] Rule: Read the host's journal before touching the PIN: 'Local login check for <user> failed'
      means the per-connection PAM account check failed, typically because /etc/shadow is not
      root:shadow 0640 so setgid unix_chkpwd cannot read it; fix with chgrp shadow and chmod 0640
      on the shadow files, and prove it with pamtester run as the unprivileged user (positive and
      a nosuchuser negative), since a root test passes either way.
      Where: no text change (already covered)
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. The rules
      under test are recorded in this machine's memory store, so a behavioural arm would be
      contaminated; only a verbatim quote from the snapshot counts.
- [x] GREEN quote-back on haiku and opus against the edited files (5 questions), again after the
      review fixes for every question, and a third time for the 1 questions the fix-delta fixes
      touched: every answer quoted the edited text, no NONE. Quotes were substring-checked against
      the files; the pre-edit snapshots fail the same check.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per question per tier per round.
- [x] Independent review of the full diff, then of the fix delta alone; every finding fixed or
      declined with evidence by the fixer, and the fix delta re-reviewed.
- [x] Each GREEN Skill gaps list triaged: 5 closed in the text, 7 declined with a reason (covered
      elsewhere with file:line, out of scope, owned by another skill, or a judgement the skill
      leaves open).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), added
      prose wrapped like the surrounding text, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; addresses are
      documentation ranges or placeholders.
