# skill-writer checklist - meta-self-improve (memory rules folded in)

- [x] Change: SKILL.md, step 3 dedup - an update re-sends --slug, --title and --hook (add refuses
      'pass --hook or --hook-file'); a new hook rewrites the pointer and the body's
      description line; omit --type to keep the kind; factedit.py apply re-sends the stored
      title and hook for an unpinned fact; a pinned fact is refused and reported for human
      review (amend-pinned is a human step, factedit switches to it on its own). The dedup
      line no longer claims an upsert keeps the pin; references/memory-backend.md's add
      semantics no longer say it either.
- [x] Verified: hooks/memory_engine.py:1845 (--title required), the 'pass %s or %s' refusal in
      _text_from_flag_or_file, amend-pinned parser at :1870; factedit.py re-sends the stored
      title (factedit.py:505-514).
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
