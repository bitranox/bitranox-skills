# checklist - restate an example's general rule; review the draft before section approval

Two bullets added: under "Understanding the idea", restate and confirm the general rule a user's
concrete example stands for before measuring anything; under "Presenting the design", run the
elephants-in-the-room review (pointed at in process-plan-writing-plans, not restated) over the
whole draft before asking for the first section's approval.

Decisions: d-20261115-c671d984, d-20261115-811816f4

## RED

- [x] Skill decisions read first (`show --kind rejected,removed --full`): one rejected entry about
      the memory-bound rule's home; neither bullet touches it.
- [x] `redcheck --corpus-cascade` on both scenarios: clean (weak evidence, so the text check below
      is the evidence).
- [x] Coverage check on the pre-edit text, inert text-only probe, opus and haiku. Q1 (user explains
      a placement rule with `/a/python` and `/b/python`): no line governs it; opus reached for the
      counter-idea bullet (turn the idea into a concrete scheme), haiku for "Ask WHETHER". Q2 (run
      an independent review before section approval): NONE on both tiers.

## GREEN

- [x] Same questions on the edited text, opus and haiku, plus a control (a fully specified one-line
      change). Both tiers quoted the new example bullet for Q1 and the new review bullet for Q2,
      and listed the five review questions from the pointed-to step. Control: both skip the
      review (no design section to approve; the skill's "When NOT to use" excludes it).
- [x] Quote-back: each quote is verbatim from the edited text.
- [x] GREEN diffed against RED: no baseline result lost; the WHETHER rule still applies before any
      HOW question.

## REFACTOR

- [x] Every dispatch asked for a `Skill gaps` section; all lists recorded and decided.
- [x] Declined: "the body has no scope exclusion" - covered at SKILL.md line 14, "**When NOT to
      use:** trivial, mechanical, or fully-specified tasks" (the probe saw an excerpt).
- [x] Declined: "what counts as an equivalent independent pass" and "how to act on findings" -
      judgement left to the reader; one question at a time already governs any finding that needs
      a user decision.
- [x] Declined: "the pointed-to step says before planning" - the bullet points at the step's
      questions, not its timing, and states its own timing.
- [x] Declined: "an example that fits several general rules" - "Prefer multiple choice questions"
      already covers offering candidates.
- [x] Width and fence check over the added lines printed nothing; the bullet after each insertion
      point read, no re-bound reference.
- [x] Both decisions recorded with `skill_decisions.py add` (rule entries with anchors).
