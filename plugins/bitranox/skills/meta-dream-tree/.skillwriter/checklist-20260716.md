# skill-writer checklist - meta-dream-tree (2026-07-16, close the silent-tooling-defect gaps from a real dream run)

Change: wired the fixes for the silent-by-construction tooling defects a full dream run surfaced
(notes.md, sections 4-5) into the procedure and its shared reference. Steps touched: 0a (run
`reconcile_memory_index.py --check-tree` after `heal` - heal is chain-scoped and misses cross-sibling
duplicate pointers), 0b (enumerate levels with `find`, never a bare session `grep`; verify the
parallel `set-scope` fan-out from ground truth), 5 (gate tree-top promotion with the real
`dream_state.py saw-promotable`/`should-promote`/`promoted` verbs, backing the docs' ">= 2 dreams"
claim), 6 (`memory_engine.py lint --tree` sweep for the voice/frame backlog), 8 (`--check-tree` in the
verification contract). Shared prose lives in references/dream-core.md (Level enumeration + cross-check,
verify-every-parallel-write-fan-out, route-by-fire-site in the placement prompt, tree-wide verify).

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED baseline: notes.md IS the watched failure - one real dream run silently under-scoped (grep gave 17 of 43 levels), clobbered a sibling descriptor via a mistargeted set-scope, overwrote a richer hook via `move` (direction-decided), reported `--check` clean while two slugs sat duplicated across siblings, cited a `should_promote` gate with no backing counter, had no voice/frame sweep verb, and misfiled facts by topic instead of fire-site
- [x] GREEN (behavioral, opus per the no-lower-model constraint): an opus subagent given the new enumeration + routing prose ran `find /work/tree -name CLAUDE.local.md` (rejecting grep for the gitignore reason) and filed a consumer-triggered bmk fact at the common parent, naming the "about tool X" misfile - both D and K steer correctly
- [x] GREEN (mechanical): every new engine/CLI path exercised end-to-end on a temp two-tree fixture - `--check-tree` flags a cross-sibling duplicate and exits 1; `move` refuses a divergent duplicate and `--force` keeps the LONGER hook regardless of direction; `lint --tree` reports the planted over-cap/trigger-less/unframed offenders; the promote gate goes hold->promote across two sightings; `--archive` drops the pointer and moves the body
- [x] Scripts/tests: sibling tests added/extended and green with the CI dep set (pytest PyYAML lxml defusedxml ruamel.yaml httpx2) - 1116 passed, 7 skipped; ruff clean on all changed .py
- [x] Contract test: family literals still single-sourced in dream-core.md (test_dream_skill_contracts green)
- [x] fix-shared-bug-in-all-siblings: the shared prose (enumeration, fan-out verify, routing, promotion verbs, --check-tree) lives in dream-core.md; the crosstree sibling picked up the promotion verbs + per-tree --check-tree in the same change; nap defers wholly to dream-core (no restatement to fix)
- [x] CSO description: unchanged (procedure/reference edits only, no trigger change) - no re-derivation needed
- [x] Security scan: prose + engine-call references only; no secrets, credentials, hostnames, PII, or unsafe code in the diff
- [x] Docs describe current state: no moved-from/legacy narrative; the defect provenance stays in notes.md, not in the shipped skill
