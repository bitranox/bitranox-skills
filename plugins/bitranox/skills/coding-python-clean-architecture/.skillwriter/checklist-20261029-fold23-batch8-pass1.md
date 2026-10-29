# skill-writer checklist - coding-python-clean-architecture (memory rules folded in, batch 8 pass 1)

- [x] Change: review-checklists.md - judge a layering by the port signature (does any framework
      or driver type cross it), not by where the class lives.
- [x] Verified: consistent with the existing 'Framework types leaking into ports' row.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of each skill (25 rows).
      The rules under test are recorded in this machine's memory store, so a behavioural arm
      would be contaminated; only a verbatim quote from the snapshot counts. RED: 6 NONE, 11
      PARTIAL, 8 quoted in full (5 rows were already covered and added nothing).
- [x] GREEN quote-back on haiku and opus against the edited files: round 1 opus 24/25 (1 PARTIAL,
      closed by the standing-rule sentence), haiku 24/25 (its NONE a search miss, the text is
      in the compuse-git table); round 2 on the 8 questions the fixes touched, 8/8 on both
      tiers. Every quote substring-checked against the files, misses resolved by grep.
- [x] Independent opus review of the full diff against the code and the fact bodies: fixed the
      ruamel width claim, the merge-tree argument and conflict output, the gate log header,
      the SDK token figure, a clock-resolution clause, the StrEnum raising sentence, a lost
      'skip that fires', and an implied standing-rule sentence. A delta review of the fixes
      found the skip clause misfiled under 'reported as a failure' (fixed and reflowed).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), every
      fence closes, added prose wrapped to the surrounding file's width, no code span split.
- [x] Security scan: prose only; no secrets, hostnames, private paths, memory slugs or PII.
