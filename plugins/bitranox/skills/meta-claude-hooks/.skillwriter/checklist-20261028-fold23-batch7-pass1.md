# skill-writer checklist - meta-claude-hooks (memory rules folded in)

- [x] Change: SKILL.md, 'Before you escalate a nudge to a block, price it' - the replay also comes
      before a NEW warn-only nudge, with a firing budget set first (about 1% needs a stated
      justification, several percent is a dead nudge); a prompt-keyed rule is replayed over the
      prompt corpus with corpus_prompts.py; a fifth trustworthiness bullet splits the firings
      by trigger arm (guard_replay.py --firings, per-arm shares, one measured case); two rates
      are quoted; a hook firing on its motivating incident is not
      evidence a signal exists, and a decision-log guard is replaced by a comment at the code site.
- [x] Verified: guard_replay.py --firings (scripts/guard_replay.py:573) and its second-argument
      dispatch (:226); corpus_prompts.py dedupe and default skips (:154-211); the per-arm
      figure is hooks/unbuffered-python-nudge.py:52-56. The file is not named in the skill: it
      has no back-pointer test like gated-prep-nudge's, so a rename would rot it silently.
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
