# skill-writer checklist - coding-python-uv (memory rules folded in, batch 9)

- [x] Change: SKILL.md routing rows; 05-resolution.md - exempt the own-package closure, keep
      own libraries' third-party floors older than the cooldown, pin a young floor one
      second after its upload instead of lowering it (bmk writes and removes that pin in a
      bmk project), verify resolved versions against the index; 07-tools-and-scripts.md -
      uvx --with . analyses a built copy, not the working tree.
- [x] Verified: the per-package timestamp line reconciled with the removal rule (a later
      release stays excluded until the entry goes).
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
