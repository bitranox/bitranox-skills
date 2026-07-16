# skill-writer checklist - meta-dream-crosstree (2026-07-16b, verify duplicate/merge candidates against bodies)

Change: tightened the deep-scan fan-out instruction (step 3). A subagent now flags a DUPLICATE/MERGE
only from the BODIES (not a title/topic match), and every such finding is a CANDIDATE the main agent
VERIFIES before merging. Single-sources the "verify before merge" rule in dream-core.md "Dedup
semantics" (a summary+detail pair, a valid cross-link, or a cited-across-a-subtree fact is not a
duplicate).

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: observed failure in a real crosstree-deep run - the sonnet fan-out's 3 DUPLICATE/MERGE
      suggestions were ALL complementary on inspection (a summary+detail pair with a valid cross-link,
      a fact cited across the provmm subtree, and a fleet fact whose overlap was one incidental clause);
      merging any of them blindly would have destroyed content
- [x] GREEN: the new clause + dream-core "Dedup semantics" rule makes the main agent read both bodies +
      check refs before merging, and names the three not-a-duplicate shapes; a subagent flags from
      bodies, not topic
- [x] Contract test: family literals still single-sourced (the rule lives in dream-core.md; the skill
      references it) - test_dream_skill_contracts green
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose only; no secrets/PII/unsafe code
- [x] Docs describe current state: no legacy narrative
