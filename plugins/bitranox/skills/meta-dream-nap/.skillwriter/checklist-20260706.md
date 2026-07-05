# skill-writer checklist - meta-dream-nap (2026-07-06, NEW skill)

- [x] Receipt issued (skill_receipt.py, this session)
- [x] RED baseline: without the nap, the agent SKIPPED consolidation at a compaction (tree-wide
      dream too heavy for the budget) and independently wished for a budget-bounded chain-only
      mode with an explicit deferred-list - the nap's spec, articulated by the baseline
- [x] Design: scope delta only; all shared semantics via dream-core.md (single source);
      contract test enforces the family invariants deterministically
- [x] Parity matrix: fixture_asserter --profile nap asserts the same basic functions as the
      dream profiles with inverted reach (siblings byte-untouched is the nap's hard assertion);
      harness unit tests green
- [x] GREEN + pressure: comprehension + sibling-merge/false-done temptations (see run log)
- [x] CSO description: trigger-first (compaction, signals, "nap"); PostCompact nudge rewired here
- [x] Deliverables checklist + rationalization table shipped in the skill
- [x] Security scan: prose-only, clean
- [x] LIVE ACCEPTANCE MET: two consecutive runs on 5.43.0, both 6/6 hard (incl. SIBLINGS
  byte-identity) + 3/3 judgment, at ~6-7 min vs the full dream's ~15 (2.3x faster on the
  small fixture; the gap widens with tree size)
