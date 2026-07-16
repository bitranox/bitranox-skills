# skill-writer checklist - meta-dream-crosstree (2026-07-16, real promotion gate + per-tree tree-wide verify)

Change: two edits carried over from the tree-dream fix (fix-shared-bug-in-all-siblings). (1) The
cross-pollination step named `should_promote` / `note_promotion_candidate` as bare Python functions,
which the model cannot invoke inline - repointed to the real `dream_state.py saw-promotable` /
`should-promote` / `promoted` CLI verbs (the same corroboration gate the tree dream now uses; the
counters are still the out-of-store `self_improve_signals.py` dwell store). (2) Added
`reconcile_memory_index.py --check-tree <anchor>` per affected tree to the final verify, because
promotion to a common ancestor is exactly what can leave a slug pointed at from two levels - which the
chain-only `--check` cannot see.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: notes.md is the observed failure - the `should_promote` gate had no callable path from a dream's flow (function only), and a chain-only verify structurally cannot catch a cross-sibling duplicate that promotion creates
- [x] GREEN (mechanical): `dream_state.py saw-promotable`/`should-promote`/`promoted` verified end-to-end (hold -> promote across two sightings, cleared after promotion); `--check-tree` flags a cross-sibling duplicate and exits 1 - both on a temp fixture
- [x] Scripts/tests: dream_state + reconcile sibling tests green with the CI dep set (part of the 1116-pass run); ruff clean
- [x] Contract test: family literals still single-sourced (test_dream_skill_contracts green) - the new prose references dream-tree/dream-core, does not restate them
- [x] CSO description: unchanged (body edits only)
- [x] Security scan: prose + CLI-invocation references only; no secrets/PII/unsafe code
- [x] Docs describe current state: no legacy narrative
