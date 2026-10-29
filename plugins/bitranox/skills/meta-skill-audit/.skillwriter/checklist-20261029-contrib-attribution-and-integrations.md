# skill-writer checklist - meta-skill-audit (2026-10-29, contributions: attribution pass, external integrations)

Two queued contributions. A new "Audit attribution debt too" section gives the catalogue audit its
own deterministic attribution pass (name-match against each upstream listing with the category
prefix stripped, distinctive-text match for renamed skills, missing `> Adapted from` line), pointing
at meta-adopting-external-skills Step 4 for the fix. A paragraph after the triage table stops a doc
claim about an external service integration from being classed WRONG on a silent tree: check the
integration's PRs, check runs and commit statuses first.

- [x] Receipt armed and the skill loaded through the Skill tool before the first edit.
- [x] Route: coverage check against the skill FILE on the pre-edit text.
- [x] RED (`git show HEAD:...meta-skill-audit/SKILL.md | grep -ci`): `Adapted from`/`attribution`
      0, `check-runs`/`integration` 0. The attribution rule existed only in
      meta-adopting-external-skills Step 4, which a catalogue review does not load.
- [x] GREEN (quoted back): "## Audit attribution debt too"; "Every match with no `> Adapted from`
      line is missing attribution."; "A doc claim about an external service integration is not
      WRONG because the tree is silent."
- [x] Commands run before shipping them: `gh api repos/<o>/<r>/commits/<sha>/check-runs --jq
      '.check_runs[].app.slug'` returned the app slugs on a real commit; the `statuses` form with
      `--jq '.[].context'` ran clean (empty for that commit); `gh api repos/<o>/<r>/contents/<dir>
      --jq '.[].name'` listed a public upstream's skill names.
- [x] Paragraph after each insertion read: "Rank by what a reader DOES" and "## Common mistakes";
      neither refers back to the text before it.
- [x] Width check over the added lines prints nothing.
- [x] Cases decided beyond the reported defects: none; the attribution fix is delegated to the
      adoption skill's Step 4 rather than restated.
- [x] Description unchanged. No address, hostname or machine path added. Present tense.
- [x] Subagent arms: none run; 0 tier cells.
