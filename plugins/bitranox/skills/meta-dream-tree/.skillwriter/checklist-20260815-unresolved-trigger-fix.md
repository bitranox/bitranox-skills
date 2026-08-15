# meta-dream-tree: drop the hook-shape clause from the prune-pass question 2

Scope: reword question 2 of the two-item numbered list inside step 7 "Prune" (added in the prior,
separately-reviewed commit). No other section changes. A companion change in
`hooks/capture_constraints.py` (its module docstring item 2 and `_UNRESOLVED_ADVICE`), in
`CHANGELOG.md`, and in the paired `meta-self-improve` bullet reword the same overclaim to match;
the code itself is unchanged.

## The finding this fixes

The prior commit's question 2 read "Does this read as a procedure while describing a session that
never reached a working end state?" - a two-part test (procedure-shaped AND unresolved) that an
entry could fail (answer "no", so skip relabelling) purely by not reading as a step-by-step
procedure, even while its body plainly describes an unresolved failure. The write-time advisory
this question mirrors (`capture_constraints._UNRESOLVED_ADVICE`, fired from
`UNRESOLVED_RX.search(body)`) has no such gate - it does not care whether the hook reads as a
procedure. A reviewer following the old question 2 literally could wave through an unresolved-
failure entry that just does not happen to look like a workflow. Fixed by wording, not by adding a
hook-shape check anywhere.

## What the tests showed

- [x] Pre-edit PRESENT confirmed with the file genuinely read, not assumed: `claim_check.py
      --pattern 'read as a procedure while describing a session' --control 'Archive obsolete'
      plugins/bitranox/skills/meta-dream-tree/SKILL.md`, run against `git show HEAD:...` (this
      branch's tip before this edit) -> PRESENT, 1 hit, control matched (the file was read).
- [x] Post-edit ABSENT: same tool, same pattern, against the working-tree file -> ABSENT, control
      matched (the file was read, the old phrasing is gone).
- [x] Post-edit PRESENT for the new wording: `claim_check.py --pattern 'never reached a working end
      state, without' --control 'Archive obsolete' plugins/bitranox/skills/meta-dream-tree/SKILL.md`
      -> PRESENT, 1 hit on the reworded question.
- [x] Behavioural pressure-test not run: this is a documentation-conformance fix (the wording now
      accurately describes an already-shipped, already-reviewed code trigger), not a new discipline
      rule whose phrasing needs pressure-testing against a subagent's rationalizations.

## Placement / phrasing choice

- [x] Kept the two-question structure and question 1's parallel shape ("Does this assert X, without
      Y? If so, Z.") - question 2 now reads "Does this describe a session that never reached a
      working end state, without labelling it unsolved? If so, relabel it as unsolved." This drops
      the procedure-shape clause entirely rather than softening it, matching the code: any
      unresolved-failure body qualifies, whatever the hook looks like.
- [x] Did not touch question 1 (the stale-negative-claim question) or the surrounding step 7 prose -
      neither carries the procedure-shape overclaim.

## Scope declined

- [x] Did not edit the prior commit's checklist
      (`checklist-20260815-capture-constraints-review-side.md`) even though it records the
      now-superseded wording as reviewed-and-correct - it is a dated receipt of that review, not
      living documentation; this new checklist is the record of what was wrong and how it was fixed.
- [x] No change to `references/dream-passes.md` - the two questions live directly in SKILL.md's
      step 7, unchanged in placement from the prior commit's decision (see that commit's
      review-side checklist for why).

## Checks

- [x] Description frontmatter untouched, so the CSO lint and skill-router trigger map are
      unaffected.
- [x] No cross-skill or script references added; no renumbering of the existing 11 (+10b) procedure
      steps.
- [x] No session narrative or private provenance in the skill text or this artifact.
- [x] No hostname, IP, credential, or machine-specific path introduced.
- [x] LF endings; ASCII only (scanned the changed file for codepoints above 126: zero hits).
- [x] No `plugin.json` version bump in this change (5.202.0 already accounts for the paragraph this
      question lives in; this is a same-version wording correction, not a new capability).
- [x] `repo-gate.py --ci` passes on the full change set (see the paired commit's gate result,
      recorded in this task's own report).
