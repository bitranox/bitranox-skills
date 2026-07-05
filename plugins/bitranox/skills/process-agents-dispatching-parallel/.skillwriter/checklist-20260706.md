# skill-writer checklist - process-agents-dispatching-parallel (2026-07-06, roster review wave 3)

- [x] Change: description enriched (parallel/dispatch/fan-out keywords were entirely absent); emoji + arrow glyphs swept to ASCII per tell_chars; dated session narrative removed (Real-World Impact section deleted, example genericized); superpowers credit line + THIRD_PARTY_NOTICES entry added (verified upstream roster: obra/superpowers ships the ancestor; MIT notice now travels with the copy)
- [x] Receipt held (skill_receipt.py, this session)
- [x] Review: read-only opus subagent audit, verified against the files by the applier
- [x] Discovery test: fable subagent wave 6/6 (changed descriptions incl. two near-decoy discriminations)
- [x] Security scan: prose/frontmatter edits + file removals, no secrets/paths/PII

# skill-writer checklist - process-agents-dispatching-parallel (2026-07-06, plan-execution model-gate)

- [x] Change: gate reference updated: warning normally, DENY while a plan execution is armed; standalone batches can arm/end the gate themselves.
- [x] Receipt held (skill_receipt.py, this session)
- [x] Enforcement: subagent-model-gate.py (renamed from warn-unpinned-subagent-model.py per telling-naming) + skill_receipt end command; 14 gate/receipt unit tests green incl. deny JSON shape, disarm, fork exemption
- [x] Ground truth verified via claude-code-guide: no per-dispatch effort field exists; PreToolUse deny works for Task
- [x] Security scan: hook emits deny JSON only, no secrets/paths
