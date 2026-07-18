# skill-writer checklist - meta-self-improve (2026-07-18, fourth endpoint: recurring chore -> tool)

Change: added the fourth self-improvement endpoint - a recurring manual CHORE ends in a TOOL, the
craftsman analogue of "a recurring rule violation ends in a guard". Step 6 gains the endpoint
(2nd-occurrence threshold, propose-first, LOCAL-by-default in the personal `toolbox` skill, TDD,
enhance-don't-work-around, contribute-upstream only when broadly useful). Step 2 classification
table gains the routing row.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session).
- [x] RED: the loop had homes for knowledge (memory), procedure (skill), and enforcement (guard) but
      NONE for a reusable TOOL - so a recurring manual chore (parse/scan/extract re-hand-rolled) was
      re-derived every session with nothing to capture the capability. The craftsman case fell through.
- [x] GREEN: step 6 adds the 4th endpoint on the SAME escalation ladder (first time do it by hand;
      2nd time propose a tool; on OK build it TDD in the LOCAL toolbox); step 2 adds the routing row.
      Enhance (RED-regression, not work-around) and the local-stays-local / share-when-broad split
      are both spelled out, referencing the existing contrib_queue + upstream loop.
- [x] Propose-first / no auto-author: explicit. NO new hook or fuzzy chore-detector (that would
      re-create the realization/subagent gate false-positive class fixed in 5.87.1/5.87.2) - it is a
      model judgement in the reflection that already runs.
- [x] Local vs marketplace: mirrors the existing skill-contribution model (personal ~/.claude/skills/
      vs the plugin); the LOCAL `toolbox` skill is referenced by its bare personal-skill name, not a
      `bitranox:` marketplace prefix.
- [x] Meta-loop note: this edits the self-improve SKILL (allowed meta-loop exception). The change is
      ADDITIVE prose (a new endpoint) and does NOT touch the gate code or detection patterns
      (`self_improve_signals.py` / `self-improve-gate.py` unchanged), so gate behavior is unchanged and
      a baseline gate re-test is not implicated. Verified: full hook suite + repo-gate --ci green.
- [x] Security scan: prose only; no secrets/hosts/paths.
- [x] CSO description: unchanged (body edit only; existing triggers "a reusable discovery ... a
      procedure, a gotcha, a flag combination, a path" already cover the tool-capture case).
- [x] Token budget: one table row + one short ladder subsection; skill stays within budget.
