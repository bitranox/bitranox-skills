# skill-writer checklist - compuse-toolbox (memory rules folded in, batch 8 pass 2)

- [x] Change: SKILL.md - with a long workflow_dispatch run on the same sha, ci_wait without
      --event waits for it and times out (exit 2) while push CI is green: pass --event push
      and watch the dispatched run separately.
- [x] Verified: ci_wait.py excludes only schedule by default, passes --event to gh, and exits
      2 on timeout with the last summary.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of each skill (8 rows).
      The rules under test are recorded in this machine's memory store, so a behavioural arm
      would be contaminated; only a verbatim quote counts. RED: 1 NONE, 6 PARTIAL, 1 full.
- [x] GREEN quote-back on haiku and opus: round 1 8/8 on both tiers; round 2 after the review
      fixes, on the 7 questions the fixes touched, 7/7 on both. Every round-2 quote
      substring-checked with quotecheck (14 OK), with a planted false quote as the negative
      control (MISMATCH, exit 1).
- [x] Independent opus review of the full diff: 3 Important, 10 Minor, all fixed. Delta review
      of the fixes: all 13 resolved; 1 Important declined with its reason (the reviewer
      template's severity rule is outside the owner decision; the skill now defers to it
      explicitly), 5 Minor fixed.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), every
      fence closes, added prose wrapped to the surrounding file's width, no code span split.
- [x] Security scan: prose only; no secrets, hostnames, private paths, memory slugs or PII.
