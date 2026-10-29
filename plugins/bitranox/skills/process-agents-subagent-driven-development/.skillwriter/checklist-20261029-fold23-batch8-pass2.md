# skill-writer checklist - process-agents-subagent-driven-development (memory rules folded in, batch 8 pass 2)

- [x] Change: SKILL.md - a plan-mandated finding is decided by what its fix changes (owner
      decision 2026-10-29, quoted in the coordinator's decision log): a fix that only
      makes the plan's code obey a rule the plan states, or only adds tests, is applied and
      logged in EXECUTION-USER-REVIEW.md with a reopen-if line; any other fix goes to the
      human. Pre-flight plan review, BLOCKED item 4 and the task_brief duplicate-heading
      case route by the same test. Tests written from the plan cannot catch a defect in it:
      the reviewer gets the review package plus the files at HEAD and may contradict the
      plan; a regression test must fail with the defect put back (mutation_arm).
      task-reviewer-prompt.md - the reviewer reports, the controller decides who settles it.
- [x] Verified: review_package.py builds diff -U10 (HEAD context, not whole files);
      mutation_arm --revert FILE REV and --mutate exist; the template still grades a
      rubric defect the plan mandates Important, and the skill defers to it.
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
