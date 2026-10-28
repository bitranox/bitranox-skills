# skill-writer checklist - meta-skill-writer (memory rules folded in)

- [x] Change: SKILL.md - a passing review-artifact gate is not evidence the procedure ran for THIS
      change: audit the co-changed checklist for a section on that change, else RED/GREEN it
      now and append; when RED and GREEN tie on the action, read each arm's stated reasons
      against the system as it was for that arm; a description or routing rewrite cannot be
      A/B-tested live where the skill is installed (text check, record routing unverified).
- [x] Verified: the gate checks presence and no open box only (hooks/repo-gate.py check_skill_review);
      the Deployment section the new text points to exists (SKILL.md 'Deployment:').
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of each skill. The rules
      under test are recorded in this machine's memory store, so a behavioural arm would be
      contaminated; only a verbatim quote from the snapshot counts. RED: 2 rows PARTIAL, 5 quoted
      adjacent text; on 2 of those (factedit type, engine add re-supplying the hook) the answerer
      reached the right action by inference from neighbouring lines, so the fold states it.
- [x] GREEN quote-back on haiku and opus against the edited files (7 questions, 14 cells): every
      answer quoted the new text, no NONE; all quotes substring-checked against the files.
- [x] Tiers haiku and opus, one cell per question per tier.
- [x] Independent opus review of the full diff against the code and the fact bodies: no false
      claim; fixed: an upsert said it keeps the pin while add refuses a pinned fact, a
      pinned-fact sentence sent capture to the human-only amend-pinned, two meta-claude-hooks
      paragraphs sat before the replay they extend, a dropped 'fired in every variant'
      qualifier, the backup location, the --slug in the body-only recipe, the exemption
      example's context, the table re-pad case. Round 2: GREEN quote-back on haiku and opus
      (14 cells, all quotes substring-checked) plus a delta review of the fixes alone, which
      found two unreflowed lines, a 'same directory' pointing 45 lines back, and the same
      keeps-the-pin claim in references/memory-backend.md; all four fixed.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical, every fence closes, added prose wrapped at 100
      columns, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
