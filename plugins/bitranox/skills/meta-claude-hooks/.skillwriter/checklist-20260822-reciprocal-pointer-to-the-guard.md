# skill-writer checklist - meta-claude-hooks (bind the section to its worked example)

Change: the "price it" section now names `hooks/gated-prep-nudge.py` as its worked example and
states that the two move together; the guard's docstring names the skill and the section back; a
test asserts both pointers resolve.

## PLAN

- [x] Skill type: reference/hub for hook authoring. Test approach: an executable check of the
      invariant, not prose - the invariant is "these two artifacts reference each other", which is
      mechanically testable.
- [x] Trigger is a real condition, verified before writing: `grep` showed the skill did NOT name the
      guard and the guard did NOT name the skill. The split (method here, figures there) was a
      deliberate choice to stop a number existing twice, but nothing recorded the coupling, so it
      lived only in one session's working memory.
- [x] Considered and rejected converging the two: no number appears in both places today, which is
      the property worth keeping. The risk is not disagreement, it is a rename or deletion turning
      the other side's pointer into a lie.
- [x] Scope: one paragraph here, one in the guard's docstring, three tests in the guard's existing
      suite. No frontmatter change.

## RED

- [x] The RED against the FILES failed before this change, in both directions: neither artifact
      named the other, so a reader of either had no way to reach the half it does not carry, and a
      rename on either side would have gone unnoticed.
- [x] Both new pointer tests RED-verified by mutation, each file copied aside first and restored
      from the copy:
      - guard's `bitranox:meta-claude-hooks` replaced -> exactly
        `test_the_guard_points_at_the_skill_that_carries_the_method` fails (1 failed, 39 passed)
      - skill's `gated-prep-nudge.py` replaced -> exactly
        `test_the_skill_points_back_at_this_guard_as_its_worked_example` fails (1 failed, 39 passed)
      - restored: 40 passed
- [x] A CONTROL test guards against the checks being vacuous: it asserts both files are found at the
      paths the test computes AND that each really is the intended document (the guard contains
      `gated-verb`, the skill contains the section heading), so a moved or renamed file fails loudly
      instead of leaving the pointer assertions checking nothing.

## GREEN

- [x] Text check: the section names the guard, states which half lives where, says why the split
      exists (no number in both, so they cannot disagree), and names the test that enforces it.
- [x] Quote-back for the coupling: "If you revisit that guard, update its docstring AND this
      section, and if you retire either, the reciprocal pointer in the other becomes a lie."
- [x] 40 tests pass; whole-repo suite green via `repo-gate.py --ci`.

## REFACTOR

- [x] The rule is enforced, not merely stated. A note saying "these must move together" is the
      thing that rots; a test that fails on a rename is the thing that does not.
- [x] Tests assert on STABLE tokens (the skill's section heading, the guard's filename, the skill
      name) rather than on sentences, so ordinary rewording of either document does not false-fail.
- [x] The tests live in the guard's existing suite rather than a new file, because that suite
      already runs in CI and the invariant belongs to the pair, not to a third place.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths (paths are computed relative
      to the test file, so the suite is checkout-location independent).

## Deliverables

- [x] One paragraph in `SKILL.md`, one in `hooks/gated-prep-nudge.py`'s docstring, and three tests
      in `hooks/tests/test_gated_prep_nudge.py` (40 total, up from 37).
