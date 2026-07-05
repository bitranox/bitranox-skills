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

# skill-writer checklist - meta-collect-knowledge (2026-07-06, workspace-root guard)

- [x] Change: gather_scan._workspace_root now skips the excluded anchor dirs (HOME, system temp dir, filesystem root) exactly like resolve_anchor - a stray CLAUDE.md at /tmp turned ALL of the temp dir into one workspace and polluted recall with unrelated leftovers (bitten twice on 2026-07-05, once via a Jul-3 stale file and once via debug debris).
- [x] Test: test_stray_claude_md_at_tempdir_does_not_hijack_workspace (monkeypatched gettempdir) + full suites green (hooks 534, collect-knowledge)
- [x] Receipt held; no description change; security scan clean
