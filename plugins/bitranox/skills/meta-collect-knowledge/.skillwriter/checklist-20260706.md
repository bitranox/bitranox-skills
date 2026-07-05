# skill-writer checklist - meta-collect-knowledge (2026-07-06, C4 rewrite)

- [x] Receipt issued (skill_receipt.py, this session)
- [x] RED baseline: no per-tree grouping, cross-tree knob unknown (answered mcp_search), no
      multi-tree concept, legacy store layout in prose
- [x] GREEN: comprehension run correct (TREE labels, cross_tree_search + --cross-tree, copy rule)
- [x] Pressure scenario: blind-seed + cross-tree-reference temptations resisted under time pressure
- [x] Deliverables checklist + rationalization table shipped in the skill
- [x] CSO description: trigger-first, updated for trees
- [x] Scripts/tests: gather_scan legacy strip; 19 tests green incl. the two previously
      environmental discover_claude_md failures (fixtures made hermetic: workspace inside fake HOME)
- [x] Cross-suite: hooks 513 green (trigger map rebuilt - the sync test caught the stale map)
- [x] Security scan: diff clean (prose + test fixtures only)
- [x] Mechanical rename sweep 2026-07-06: bitranox:meta-dream-project/global(-deep) references -> meta-dream-tree/crosstree(-deep); no semantic change
