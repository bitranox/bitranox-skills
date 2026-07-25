# skill-writer checklist - meta-self-improve (2026-07-25)

Change: add the guard-to-chore-ladder CROSSOVER rule in section 6 (5.99.0). Closes the loop blind
spot where a footgun that graduates to a blocking guard is treated as "handled", even though its
SAFE form is still hand-rolled every time - so the jig that would provide the safe action is never
proposed (the exact reason `procsig` had a blocker but no tool for months).

- [x] Skill type: discipline/process - tested with a pressure/application subagent scenario
- [x] RED baseline: sonnet subagent given the PRE-change section 6 + the 8x pkill-self-match-with-guard scenario concluded the only next step was guard PROPAGATION (global vs local); never reached "the safe form is still hand-rolled -> build a jig". Miss reproduced.
- [x] GREEN: sonnet subagent given the POST-change section + same scenario now returns "not handled -> propose a safe-action jig, build it TDD in the toolbox, and add a nudge signature pointing the guard's victims at it". Crossover reached.
- [x] REFACTOR: no new rationalization surfaced; the commit-message false-positive case is covered by the parenthetical (guard that false-fires on legitimate text -> refine/supply jig, do not route around)
- [x] Description unchanged (triggers only) - so skill_triggers.json / docs catalog need no regen
- [x] Body edit only; no @ links; cross-refs (`toolbox`, `meta-skill-writer`) intact
- [x] Receipt held this session (skill_receipt.py start meta-skill-writer)
- [x] Security scan: prose-only edit, no secrets/paths/PII/infra
- [x] repo-gate --ci green
