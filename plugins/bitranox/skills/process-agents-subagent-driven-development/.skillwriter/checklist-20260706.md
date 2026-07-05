# skill-writer checklist - process-agents-subagent-driven-development (2026-07-06)

Change: Concrete tiers gains the fable tier (Mythos-class above opus; premium, paid-API-credits
only; opus stays the universal deep default) + "The session model is fixed" gains the verified
bidirectional /model-switch guidance (a user switch preserves the conversation; UP for capability
below opus-class, DOWN for cost on a fable session facing routine work - user-directed).

- [x] Receipt issued (skill_receipt.py, this session)
- [x] Ground truth: model lineup + fable availability/pricing constraint stated by the user;
      /model context preservation verified against Claude Code behavior
- [x] Cross-refs intact (dream-project and dream-global point here for tiers)
- [x] Security scan: prose-only diff, clean
- [x] Mechanical rename sweep 2026-07-06: bitranox:meta-dream-project/global(-deep) references -> meta-dream-tree/crosstree(-deep); no semantic change

# skill-writer checklist - process-agents-subagent-driven-development (2026-07-06, roster review wave 1)

- [x] Change: fixed 4 broken ../requesting-code-review/ cross-refs; fixed the stale .gitattributes LF pin (pre-rename path, check-attr now reports eol=lf); enriched the thin 85-char description (model-tier reference role + keywords); ported the 3 bash helper scripts to tested Python (task_brief.py/review_package.py/sdd_workspace.py, 16 behavioral tests green, rev-parse existence check hardened with ^{commit}); updated all invocation references. Deferred: rationalization table (needs its own baseline test).
- [x] Receipt held (skill_receipt.py, this session)
- [x] Review: read-only opus subagent audit, verified against the files by the applier
- [x] Discovery test: fable subagent, scenario picked this skill from a 12-candidate list (wave 6/6)
- [x] Security scan: prose/frontmatter edits, no secrets/paths/PII

# skill-writer checklist - process-agents-subagent-driven-development (2026-07-06, roster review wave 3)

- [x] Change: superpowers credit line + THIRD_PARTY_NOTICES entry added (verified upstream roster: obra/superpowers ships the ancestor; MIT notice now travels with the copy)
- [x] Receipt held (skill_receipt.py, this session)
- [x] Review: read-only opus subagent audit, verified against the files by the applier
- [x] Discovery test: fable subagent wave 6/6 (changed descriptions incl. two near-decoy discriminations)
- [x] Security scan: prose/frontmatter edits + file removals, no secrets/paths/PII

# skill-writer checklist - process-agents-subagent-driven-development (2026-07-06, plan-execution model-gate)

- [x] Change: model-pin enforcement wired in: arm the subagent-model-gate (skill_receipt.py start plan-execution) before Task 1, disarm after the final review; while armed the PreToolUse hook DENIES any unpinned dispatch (fork exempt). New Effort paragraph: effort is not a per-dispatch field - it rides the agent-type definition or a Workflow agent() call, so tier + agent type IS the effort decision (verified against current Claude Code docs).
- [x] Receipt held (skill_receipt.py, this session)
- [x] Enforcement: subagent-model-gate.py (renamed from warn-unpinned-subagent-model.py per telling-naming) + skill_receipt end command; 14 gate/receipt unit tests green incl. deny JSON shape, disarm, fork exemption
- [x] Ground truth verified via claude-code-guide: no per-dispatch effort field exists; PreToolUse deny works for Task
- [x] Security scan: hook emits deny JSON only, no secrets/paths

# skill-writer checklist - process-agents-subagent-driven-development (2026-07-06, emoji policy + rationalization tables)

- [x] Change: rationalization table added from a REAL RED baseline (3 pressure scenarios; one subject broke via self-review substitution + zero-risk inline edits - those quotes became rows); red-flag phrases folded in; GREEN re-run of the broken scenario passed quoting the table. Emoji verdict markers swept to ASCII OK/NO/WARN (SKILL.md + task-reviewer-prompt.md).
- [x] Receipt held (skill_receipt.py, this session)
- [x] RED/GREEN evidence per the Iron Law where behavior changed (see Change line)
- [x] Suites green: hooks 532, humanize 54+54, SDD 16
- [x] Security scan: prose/table/marker edits, no secrets/paths/PII

# skill-writer checklist - process-agents-subagent-driven-development (2026-07-06, effort heuristic)

- [x] Change: the Effort paragraph now carries the extremes-only policy + the tier-to-effort mapping table (low for haiku-tier mechanical fan-out, inherit for sonnet default, high-if-set for opus, xhigh/max for adversarial verify/synthesis) and the agents-dir restart caveat. Raw probe numbers stay in the memory fact (no measured numbers in committed docs); the skill says probe-verified.
- [x] Probe basis: Workflow opts.effort A/B-proven this session (wf_9a905b3d-680); Agent tool has no effort field; agent-type frontmatter restart-gated - all reflected accurately.
- [x] GREEN: fable retrieval test 3/3 (Workflow low, sonnet inherit-do-not-set, verifier xhigh/max) incl. correct channel choice.
- [x] Receipt held; description unchanged (generators stay in sync); tests 16 passed; security scan clean.
