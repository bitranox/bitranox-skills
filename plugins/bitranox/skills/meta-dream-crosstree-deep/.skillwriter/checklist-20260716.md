# skill-writer checklist - meta-dream-crosstree-deep (2026-07-16, inline reconcile summary names --check-tree)

Change: one consistency edit carried over from the 5.74.0 tree-tooling fix (fix-shared-bug-in-all-siblings).
Step 5 claims to run meta-dream-crosstree "steps 4-8 exactly", but its inline reconcile summary named only
`reconcile_memory_index.py --check`. Since crosstree step 6 now also runs `--check-tree <anchor>` per
affected tree (the cross-sibling duplicate-pointer check the chain-only `--check` cannot make), the deep
summary was stale vs the step it mirrors. Added `--check-tree` to the summary, with the note that the
tree-wide check matters MORE here because deep promotes to common ancestors across many trees - exactly
what leaves a slug pointed at from two levels.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: notes.md is the observed failure - a chain-only reconcile reported clean while two slugs were
      duplicated across sibling chains; deep's heavier cross-tree promotion is the biggest producer of that
      exact duplication, yet its inline hint would lead a reader to run only `--check`
- [x] GREEN (mechanical): `reconcile_memory_index.py --check-tree` verified to flag a cross-sibling
      duplicate and exit 1 in the 5.74.0 work (same binary this skill now points at)
- [x] Scope: deep DELEGATES the rest to meta-dream-crosstree ("steps 4-8 exactly") and dream-core, so
      D (find-not-grep enumeration), K (route-by-fire-site), and F (promotion verbs) are inherited by
      reference; deep's own step-3 gate uses a DIFFERENT valid corroboration basis (>= 2 distinct projects
      in one scan, not >= 2 dreams), so the dwell-counter verbs correctly do not apply there - no edit
- [x] Contract test: family literals still single-sourced (test_dream_skill_contracts green)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose + CLI-reference only; no secrets/PII/unsafe code
- [x] Docs describe current state: no legacy narrative
