# skill-writer checklist - process-agents-subagent-driven-development (2026-11-08, final whole-branch review)

The package bullet points at a new section "Final Whole-Branch Review": the final reviewer reads the
source design, the plan at HEAD with its amendments and the run's ledgers, reports defects (each
with a failing input) apart from plan changes, triages the deferred Minor findings, and a fix
subagent works only the confirmed Critical and Important ones.

Decisions: none - a new section; no ledger entry names the final review, and the A/B result below is the evidence

- [x] Step 0b: `show --kind rejected,removed --full` printed two entries, both about headless plan-text findings; neither touches the final review.
- [x] Evidence, MEASURED: A/B run sdd-final-review-r1 (n = 1 per arm, one blind opus judge on the
      diffs against the source design, not code-checked): the control branch had 13 confirmed
      plan-originated plus cross-task defects, the variant 10 (3 cross-task defects fewer); the
      pre-registered rule (at least 2 fewer, and the idea fired) said ship. Costs were 66.63 and
      67.16 USD.
- [x] The text shipped is the variant's section byte for byte, except the A/B-only line that asked the
      executor to write an idea marker into progress.md; no `[abx]` text remains in the skill.
- [x] Limits recorded, not hidden: one run per arm and one judge, so the effect could be within
      run-to-run variance; the variant's plan-originated count was equal (10 and 10).
- [x] Width and fence check over the added lines printed nothing. ASCII only.
