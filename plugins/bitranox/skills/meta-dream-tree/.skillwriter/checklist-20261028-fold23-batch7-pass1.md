# skill-writer checklist - meta-dream-tree (memory rules folded in)

- [x] Change: SKILL.md, the manifest verify step - a clean verify says nothing about a fact's kind;
      read it back with factedit.py show (its type line) for every rewritten fact.
- [x] Verified: factedit.py show prints 'type' (factedit.py:565); store_manifest keys hold no type.
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
