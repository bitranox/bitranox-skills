# skill-writer checklist - process-test-design (restore a mutation from a copy)

Change: one clause appended to the existing defense-in-depth bullet, naming the correct undo for a
mutation.

## PLAN

- [x] Skill type: reference (test-design guidance). Test approach: text check of the artifact.
- [x] Deliberately minimal. The full rule, with its rationale, ships in
      `process-review-enhance-code-quality`, where mutation is the prescribed evidence step; the
      underlying git behaviour ships as a `compuse-git` Quick reference row. This skill gets the
      actionable core only, because a second copy of the reasoning is what drifts.
- [x] Trigger: this skill's own bullet instructs the reader to "prove it by disabling the whole
      defense stack in ONE mutation", so a reader following only this skill performs the mutation
      and meets the restore hazard with no warning.

## RED

- [x] Behavioural RED is NOT available on this machine: the lesson sits in the always-loaded memory
      store at
      `feedback-restore-an-experiment-from-a-copy-not-from-git-while-the-work-is-uncommitted.md`.
      Route taken: TEXT CHECK of the artifact.
- [x] The RED against the FILE failed before this change: the bullet prescribed a mutation and named
      no way back from it.

## GREEN

- [x] Text check: the clause names the wrong undo, what it discards, and the correct one.
- [x] Quote-back: "Copy the file aside before mutating and restore from that copy, never
      `git checkout -- <file>` - it restores from the index or HEAD and so discards the uncommitted
      work you are testing."

## REFACTOR

- [x] Kept to one clause on the existing bullet rather than a new bullet or section: the reader is
      mid-instruction at exactly the moment the hazard applies, and a separate paragraph after a
      concrete instruction reads as commentary.
- [x] No cross-reference added. A pointer costs a skill invocation at the moment the reader is
      least likely to follow one; the clause is self-sufficient and the rationale is one skill away
      for anyone who wants it.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.

## Deliverables

- [x] One clause in `SKILL.md`. No script, so no `tests/` change.
