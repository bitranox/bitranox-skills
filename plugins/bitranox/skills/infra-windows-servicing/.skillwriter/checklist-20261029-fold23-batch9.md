# skill-writer checklist - infra-windows-servicing (memory rules folded in, batch 9)

- [x] Change: SKILL.md - Windows Update over ssh fails E_ACCESSDENIED (0x80070005); run it as
      a one-shot SYSTEM scheduled task polling a result file; the 'SYSTEM has less
      access' red flag narrowed to file operations.
- [x] Verified: the recipe is the recorded measurement from the memory fact it folds; not
      re-run on a guest in this change.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: a quote-back against a pre-edit snapshot of each skill (13 rows).
      The rules under test are recorded in this machine's memory store, so a behavioural arm
      would be contaminated; only a verbatim quote counts. RED: 2 NONE, 9 PARTIAL, 2 full
      (the two rows a skill already covered).
- [x] GREEN quote-back on haiku and opus: round 1 13/13 on both tiers; round 2 after the review
      fixes, on the 5 questions the fixes touched, 5/5 on both. Round-2 quotes
      substring-checked with quotecheck (15 OK), with a planted false quote as the negative
      control (MISMATCH, exit 1).
- [x] Independent opus review of the full diff: findings fixed (shellcheck flags, pin
      recognition by value, the own_packages key and default, a uv timestamp contradiction,
      the headSha settle step, coverage-report-file, the twins); 3 declined with reasons
      (the lock timeout is already stated; the Makefile pre-steps run no pipeline; the
      cross-plugin pointer stays removed).
- [x] Two gaps both round-2 readers named, added afterwards as text: own_packages must re-list
      the bitranox libraries the project uses; uv's pin paragraph points at bmk's handling.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical, every fence closes, added prose wrapped to the
      surrounding file's width, no code span split.
- [x] Security scan: prose only; no secrets, hostnames, private paths, memory slugs or PII.
