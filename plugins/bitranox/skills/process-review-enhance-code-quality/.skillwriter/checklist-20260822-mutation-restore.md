# skill-writer checklist - process-review-enhance-code-quality (restore a mutation from a copy)

Change: extend the "The evidence is a mutation, not a reading" bullet with the restore discipline.
`git checkout -- <file>` discards every uncommitted change in the file, which mid-review is the
work under review.

## PLAN

- [x] Skill type: discipline (a scored review procedure). Test approach: text check of the
      artifact.
- [x] The queue entry nominated `process-test-driven-development`, and that target is WRONG. The
      premise was checked before writing: `grep -n "mutat"` over the TDD skill returns NOTHING. Its
      "Verify RED" step watches a NEW test fail against missing code, which needs no mutation and
      so has no restore hazard.
- [x] Found the real homes by searching every skill for the prescribed action:
      `process-review-enhance-code-quality` ("Break the invariant in the code and require the suite
      to go RED") and `process-test-design` (a defense-in-depth bullet: "Mutate the single layer
      first"). Chose the former as the single home, because there mutation is the step the reader
      executes rather than an aside inside a Common Mistakes bullet.
- [x] Deliberately NOT duplicated into `process-test-design`: a second copy of the rationale is
      what drifts. The underlying git behaviour is stated once more as a `compuse-git` Quick
      reference row, where it stands alone as a git mechanic.

## RED

- [x] Behavioural RED is NOT available on this machine: the lesson is in the always-loaded memory
      store, twice -
      `feedback-restore-an-experiment-from-a-copy-not-from-git-while-the-work-is-uncommitted.md`
      and
      `feedback-reverting-a-mutation-with-git-checkout-discards-the-whole-file-s-uncommitted-work.md`.
      Route taken: TEXT CHECK of the artifact.
- [x] The RED against the FILE failed before this change: the skill instructed the reader to break
      the invariant in the code and said nothing about how to put it back, so the whole loop it
      prescribes ended at an undo it never named.

## GREEN

- [x] Text check: the addition is attached to the mutation instruction itself, states the wrong
      undo by name, says what it takes with it, and gives the correct one (copy aside first,
      restore from the copy).
- [x] Quote-back for the silent-failure property: "The loss is silent in the direction that looks
      like success: the suite goes green because the mutation is gone, and the file drops out of
      `git status`, which reads as clean."

## REFACTOR

- [x] Placed INSIDE the bullet that prescribes the mutation, not as a following paragraph. A rule
      stated after a concrete instruction reads as commentary on it and gets skipped, and the
      restore happens seconds after the mutation.
- [x] States the boundary rather than banning the command: git is a correct restore for work
      already committed, which is the common case and must not read as forbidden.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.

## Deliverables

- [x] One extended bullet in `SKILL.md` Step 3. No script, so no `tests/` change.
