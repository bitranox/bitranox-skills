# skill-writer checklist - meta-memory-settings (2026-07-06, C5 touch-up)

- [x] Receipt issued (skill_receipt.py, this session)
- [x] Change: discovery_roots row now names its multi-tree consumers (ensure-all-trees,
      cross-tree gather/recall); cross_tree_search row shipped in 5.36.0
- [x] Tests: settings CLI reads knobs from DEFAULT_CONFIG (no code change)
- [x] Security scan: prose-only diff, clean

# skill-writer checklist - meta-memory-settings (2026-07-06, dream-sentinel removal)

- [x] Receipt issued (skill_receipt.py, this session)
- [x] Change: deleted the legacy-sentinel Notes bullet (user-directed removal of the
      `.bitranox-dream-off`/`-auto` mechanism from code and docs; `dream_mode` is the single
      mechanism). Code removed in the same change: `_legacy_dream_mode()` + its `load_config`
      fallback, the dream-due nudge's sentinel wording, dream-core.md + README-acceptance
      references; tests rewritten to set the config file instead of planting sentinels
- [x] RED/GREEN: repo-wide grep is the test - before: 15 references across code/skills/docs;
      after: zero outside the CHANGELOG history
- [x] Tests: hooks suite 527 passed (legacy tests merged into a config test);
      meta-dream-tree 12 passed (contract test confirms dream-core literals intact);
      meta-memory-settings 8 passed
- [x] Security scan: deletions plus one nudge-string rewrite, no secrets/paths/PII

# skill-writer checklist - meta-memory-settings (2026-07-06, skill_placement knob row)

- [x] Receipt issued (skill_receipt.py, this session)
- [x] Change: added the missing `skill_placement` row to the knob table (DEFAULT_CONFIG has 9
      knobs, the table documented 8); ground truth from self_improve_signals.DEFAULT_CONFIG
      ("lowest scope that fits; ask before the public marketplace")
- [x] RED: retrieval scenario (sonnet subagent, current content) - agent listed 8 knobs and
      could not answer which knob controls skill placement
- [x] GREEN: same scenario with the edited content - agent listed 9 knobs, retrieved default,
      set command, and the marketplace ask-first caveat correctly
- [x] REFACTOR: no new failure modes; description/CSO untouched (trigger map + skills.md
      catalog derive from the description, both confirmed in sync by the pytest suite)
- [x] Tests: hooks suite 528 passed; meta-memory-settings sibling tests 8 passed
- [x] Security scan: one prose table row, no secrets/paths/PII
