# skill-writer checklist - process-test-design (an exemption needs the untouched-direction test)

Change: one paragraph added inside "A gate that only ever passed has not been shown to gate",
extending it from "prove the gate can go red once" to "prove it still goes red after you narrow it".

## PLAN

- [x] Skill type: reference (test-design guidance). Test approach: coverage check across the whole
      shipped catalogue plus the target file's own text. This is a factual-content gap, not a
      discipline an agent can reach several ways, so a pressure scenario would test the wrong thing.
- [x] Scope: one paragraph, placed where the skill already argues that a gate must be shown to have
      teeth. No frontmatter change, no new heading, no script.

## RED

- [x] Coverage checked with `claim_check.py` (home: `skills/compuse-toolbox/scripts/`) rather than a
      bare grep, over all 100 `skills/*/SKILL.md` and `skills/*/references/*.md`. Phrasings tried:
      `exemption`, `scope limit`, `negative test`, `permanent test`, `motivating case`,
      `must NOT apply`, `verdict unchanged`, `silencing the guard`. Every one returned ABSENT with
      its control matching - 910 times across 100 files on the full sweep, 192 across the 9 skills
      most likely to carry it already - so the files were read and the negative is trustworthy.
- [x] The few PRESENT hits on broad terms were read individually and are unrelated: a bash EXIT-trap
      note, a dict-parameter exemption, a memory-pointer exemption, and generic TDD language.
- [x] Read the target file in full. The nearest existing text, "validate it against a KNOWN-BAD
      input once", proves a gate CAN fail; nothing said what happens when a later exemption narrows
      that same gate back down, which is the case that actually occurred.
- [x] Checked the other plausible home: `meta-claude-hooks` owns guards, and its
      "Before you escalate a nudge to a block, price it" section measures a guard's corpus firing
      rate and precision. That answers how often and how right, never whether the exemption you
      just added still leaves the motivating case caught. Different question, so no duplication.

## GREEN

- [x] The paragraph states all three required parts: the test where the trigger is present and the
      exemption must NOT apply with the verdict unchanged, the motivating case kept as a permanent
      test, and the compounding failure where two narrow exemptions each pass alone.
- [x] `old_string` verified unique by exact substring count before applying (count 1), and verified
      disjoint from the other edit landing in this file in the same change (byte ranges compared,
      no overlap).

## REFACTOR

- [x] Placed inside the existing section rather than as a new heading: the addition is one specific
      case of that section's general claim, and a heading would imply a separate discipline.
- [x] Kept to one paragraph with no extra checklist row, because the skill is already long and the
      paragraph is self-sufficient where it stands.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths, no invented addresses.
- [x] Frontmatter untouched, so no CSO or description-length effect.
- [x] No script added or changed, so no sibling-tests obligation.

## Deliverables

- [x] One paragraph in `SKILL.md`, applied.
