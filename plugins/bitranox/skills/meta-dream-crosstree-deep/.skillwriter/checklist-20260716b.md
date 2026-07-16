# skill-writer checklist - meta-dream-crosstree-deep (2026-07-16b, verify duplicate/merge candidates against bodies)

Change: same tightening as meta-dream-crosstree (fix-shared-bug-in-all-siblings) applied to the deep
skill's mandatory fan-out (step 2): a subagent flags a DUPLICATE/MERGE only from the BODIES (not a
title/topic match), and every such finding is a CANDIDATE the main agent VERIFIES before merging.
References dream-core.md "Dedup semantics" for the not-a-duplicate shapes.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: the deep run whose log motivated this IS the observed failure - this skill's own fan-out
      produced the 3 over-flagged merge candidates
- [x] GREEN: the fan-out instruction now requires body-based dup detection + main-agent verification,
      single-sourced in dream-core.md
- [x] Contract test: family literals still single-sourced (rule in dream-core.md) - test_dream_skill_contracts green
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose only; no secrets/PII/unsafe code
- [x] Docs describe current state: no legacy narrative
