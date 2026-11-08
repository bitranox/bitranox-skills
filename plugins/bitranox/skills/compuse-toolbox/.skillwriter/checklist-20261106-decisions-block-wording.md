# skill-writer checklist - compuse-toolbox (2026-11-06, the Decisions block's wording matches its form)

Wording fixes in "Building or enhancing a jig", the same two as in meta-claude-hooks'
authoring reference: "that entry's `Rejected:` line" and "the `Rejected:` line" become "a
`- Rejected:` entry", matching the template's separate bullet; "which commit changed it is git's
job" becomes "with no history narrative: a commit is named only as the source of a reason".

Decisions: none - wording fixes that align the prose with the block form already recorded as d-20261106-8590cd34; no rule added, removed or rejected

- [x] Receipt fresh; Step 0b `show compuse-toolbox --kind rejected,removed --full` printed three
      live entries (d-20261106-a18893ae, d-20261106-3a65d299, d-20261106-8ccd6ce2); none touched.
      The anchored sentence "Pin each decision with a test that fails when the decision is
      reverted" is unchanged: `skill_decisions.py check` reports 0 findings.
- [x] Not mirrored (`repo-gate.py --mirrors`).
- [x] Each finding verified against the file first (SKILL.md:449-454).
- [x] Re-probe on the final text, haiku x1 (a jig with no block, reversing a choice only a commit
      records): wrote a `- Rejected:` entry naming the commit as the source of its reason, and
      refused a dated "Switched back" line quoting "with no history narrative". Gaps: sort
      direction, test name and evidence source the scenario did not give; whether a block is
      created on the change (the first paragraph says to record it in the module docstring). No
      new undecided gap.
- [x] No command added. Width and fence check over the added lines printed nothing; ASCII only;
      history-phrase finder: no hit.
