# skill-writer checklist - devops-bmk (memory rules folded in, batch 8 pass 2)

- [x] Change: SKILL.md section 4 - a stage missing from a failed run never ran: list every
      (exit code: N) marker, place each silent stage by its order; the order-40 checks;
      make push nests the test pipeline's markers under [test].
- [x] Verified: bmk engine.py (fail-fast per order batch, report_batch_failures in both output
      modes), output.py marker format, registry.py order-40 list and _PUSH_PIPELINE
      orders. Mirrored to the bmk repo's twin; repo-gate --mirror-of reports in sync.
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
