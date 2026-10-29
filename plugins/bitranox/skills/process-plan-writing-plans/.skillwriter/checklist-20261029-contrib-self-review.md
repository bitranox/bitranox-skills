# skill-writer checklist - process-plan-writing-plans (2026-10-29, contributions: two self-review items)

Two queued contributions, both added to the Self-Review checklist: item 5, a real-machine pass
criterion names an observable the build actually produces and where to read it; item 6, every
clause of a quoted user decision maps to a task, and the prescribed tests assert the promised
property rather than an exact value the decision never stated.

- [x] Receipt armed and the skill loaded through the Skill tool before the first edit.
- [x] Route: coverage check against the skill FILE on the pre-edit text.
- [x] RED (`git show HEAD:...process-plan-writing-plans/SKILL.md | grep -ci`): `observable` 0,
      `clause` 0; Self-Review had four items (spec coverage, placeholders, type consistency,
      absence checks), none about pass-criterion observability or quoted decisions.
- [x] GREEN (quoted back): "**5. Observable pass criteria:** Every pass criterion for a run on a
      real machine ... names an observable the build actually produces"; "**6. Quoted user
      decisions:** ... split the chosen option's text into its clauses and point each clause at
      the task that delivers it."
- [x] Paragraph after the insertion read: "If you find issues, fix them inline" applies to all six
      items and still reads correctly.
- [x] Cases decided beyond the reported defects: item 5 offers two remedies (add the logging as a
      task, or reword the criterion to something recorded); neither is a policy the user has to
      rule on.
- [x] Description unchanged. No address, hostname or machine path added. Present tense.
- [x] Subagent arms: none run; 0 tier cells.
