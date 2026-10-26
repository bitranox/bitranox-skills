# skill-writer checklist - coding-python-pwshpy (memory rules folded in)

- [x] Rule: Write the diagnostic through pwshpy from Python, even as a one-off, instead of hand-
      rolling a .ps1; if a .ps1 is unavoidable, know that `$name:` inside a double-quoted string
      is parsed as a scope/drive-qualified variable, a parse error that rejects the whole script
      (so a scheduled task exits with no output), and write `${name}:` or `$($name):` and parse-
      check the file before shipping it.
      Where: SKILL.md, ## Still writing a `.ps1`? Nine traps (heading count Eight -> Nine, new ninth
      table row, new paragraph after 'Test a forwarding wrapper ...')
- [x] Rule: Register the task with no trigger (on demand, TaskPrincipal.system()) and start it
      explicitly, because a run-once trigger stays armed and fires unattended if the launcher
      dies; know that unregistering or disabling a task does not stop a running instance, while
      stopping it ends the whole process tree, so unregister once the job has started and stop-
      then-unregister on every failure path; read identity from the process token
      (get_current_identity), since USERNAME under SYSTEM names the computer account.
      Where: SKILL.md, Scheduled-task inputs block (new paragraph after '... `pwshpy
      register_scheduled_task --help` lists them.')
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
