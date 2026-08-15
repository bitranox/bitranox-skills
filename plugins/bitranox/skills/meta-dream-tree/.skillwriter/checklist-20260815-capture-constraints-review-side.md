# meta-dream-tree: state the two do-not-capture constraints where the reviewer reads them

Scope: one new paragraph inside step 7 "Prune" (an intro sentence plus a two-item numbered list).
The behaviour it documents - the write-time advisory - already shipped in
`hooks/capture_constraints.py` on this branch (a prior, separately-reviewed change); nothing in
`hooks/` changes here. This is prose only.

## What the tests showed

- [x] Pre-edit ABSENT confirmed with the file genuinely read, not assumed: `claim_check.py
      --pattern 'Two questions to ask of every entry reviewed|assert a tool does NOT work'
      --control 'Archive obsolete/superseded/task-state'
      plugins/bitranox/skills/meta-dream-tree/SKILL.md` -> ABSENT, control matched once (the file
      was read).
- [x] Post-edit PRESENT: same tool, same pattern -> PRESENT, 2 hits, both on the new paragraph.
- [x] Behavioural pressure-test not run, for the same reason as the paired `meta-self-improve`
      change: the source text was fixed by a human-reviewed task brief, unmodified from that brief
      for this file (the brief's version-or-date corrections applied only to the
      `meta-self-improve` clause, not to this one - see "Placement" below for why this text needed
      no correction). This is a documentation-conformance change.

## Placement

- [x] Considered step 6 (Voice + firing check) as the anchor first: it already sweeps the whole
      store and applies judgment to hooks/bodies, but its job is STRUCTURAL quality (trigger-first
      phrasing, the 500-char cap, the FIRING check) and its remedy is always a rewrite via a sonnet
      dispatch. A stale negative claim or an unresolved-failure-as-procedure is not a structural
      defect - a perfectly well-formed trigger-first hook can still carry one - so step 6's checks
      would not catch either.
- [x] Placed inside step 7 (Prune) instead: it is the pass literally titled around reviewing
      EXISTING entries for whether their CONTENT is still valid, and its removal policy
      (`references/dream-passes.md`) already lists "content is dead" criteria (references a deleted
      file/flag, a resolved issue, superseded, leaked task-state). A stale, untestable negative
      claim is the same kind of dead content; delegating to "re-test it or delete it" is a natural
      extension of that list. The brief's own framing ("survives longest here") matches: neither the
      lint (step 6, structural) nor the tell-sweep would catch either fact class, only a pass that
      asks whether the CONTENT is still true.
- [x] `dream-passes.md` (which step 7 delegates to for the removal policy's exact wording) is OUT of
      scope per the task's exclusive file list (SKILL.md only for this skill) - the two questions
      live directly in SKILL.md's step 7 rather than in that reference file.
- [x] Did NOT change the "without a version or date" phrasing in question 1 to match the
      `meta-self-improve` correction: that correction addressed a REGEX-based write-time advisory,
      which structurally cannot tell an incidental version from a scoping one. This text is a
      judgment prompt for a REVIEWER reading the whole entry, who can make that distinction; the
      phrasing asks whether the entry, as currently written, is re-testable at all - a genuinely
      different question, not a residual of the deleted exemption mechanism.

## Checks

- [x] Description frontmatter untouched, so the CSO lint and skill-router trigger map are
      unaffected.
- [x] No cross-skill or script references added; no renumbering of the existing 11 (+10b) procedure
      steps - the addition sits inside step 7's own paragraph.
- [x] No session narrative or private provenance in the skill text or this artifact.
- [x] No hostname, IP, credential, or machine-specific path introduced.
- [x] LF endings; ASCII only (scanned the changed file for codepoints above 126: zero hits).
- [x] Version bump and CHANGELOG entry are shared with the companion `meta-self-improve` edit in
      the same commit (5.201.0 to 5.202.0, MINOR); see that skill's checklist for the accounting.
- [x] `repo-gate.py --ci` passes on the full change set: `2432 passed, 8 skipped` (matches this
      branch's stated full-suite baseline exactly - no test files touched by this task), gate prints
      "repo-gate: all checks passed."
