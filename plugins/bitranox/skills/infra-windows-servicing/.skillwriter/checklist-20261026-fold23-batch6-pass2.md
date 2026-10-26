# skill-writer checklist - infra-windows-servicing (memory rules folded in)

- [x] Rule: Treat the absences as untrustworthy on an unsettled first boot: wait until
      TiWorker/TrustedInstaller are idle, require a plausibility control (the total task count,
      which should be dozens, cross-checked against the files under C:\Windows\System32\Tasks)
      before believing any missing item, read the program's real location from
      Win32_Service.PathName or Get-Command instead of a guessed directory, and read LastResult
      267009 (0x41301) as still running, not failed, so no reinstall, re-register or rollback is
      done.
      Where: SKILL.md, 'The false signals' table (new row) + new subsection '### After the apply reboot:
      inventory only a settled box' at the end of 'Monitoring: what a quiet log means' (after the
      wmic paragraph) + one 'Red flags' line
- [x] Rule: Identify the defect by the failing operation in the Setup event log (the 'Language
      Pack ... Current state is Resolved. Target state is Absent.' line followed by 'failed to be
      changed to the Absent state'), never by one status code, since the same orphaned language
      pack shows 0x800736B3 at Execute and 0x80071A2D at Resolve; DISM RestoreHealth cannot repair
      it, an in-place upgrade does, and after the upgrade an empty Setup log proves nothing until
      the next CU installs.
      Where: SKILL.md, 'The false signals' table (new row) + new subsection '### One defect, several
      codes: an orphaned language pack blocks every cumulative update' under 'A clean health check
      does not mean an update will install' (after 'A cumulative update Windows Update will not
      offer') + one 'Red flags' line
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
