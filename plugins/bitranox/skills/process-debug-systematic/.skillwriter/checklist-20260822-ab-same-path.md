# skill-writer checklist - process-debug-systematic (both A/B arms run from the same path)

Change: one sub-bullet under Phase 3 "Test Minimally". Comparing two versions by copying one to a
scratch directory moves a second variable, so the measured difference is the relocation.

## PLAN

- [x] Skill type: discipline/procedure (the four-phase debugging loop). Test approach: text check
      of the artifact.
- [x] Placement checked against the skill's own structure: Phase 3 item 2 already says "One
      variable at a time", and this is exactly a second variable smuggled in by the setup, so it
      belongs there rather than as a new section.
- [x] Checked against EVERY shipped skill: `grep -rn "A/B\|control arm\|__file__" skills/` over all
      SKILL.md files returns only unrelated hits (a Proxmox storage A/B remark, two textual
      `__file__` code samples). The rule is stated nowhere.

## RED

- [x] Behavioural RED is NOT available on this machine: the lesson is in the always-loaded memory
      store at
      `.claude-memory/facts/feedback-prove-the-independent-variable-moved-before-believing-an-a-b-above-all-a-null-one.md`,
      whose body states that a control copy run from another directory changes every path the
      program derives from `__file__`. Route taken: TEXT CHECK of the artifact.
- [x] `redcheck.py --corpus-cascade .` flagged INHERITED COVERAGE for this scenario but named only
      the aggregate index file on generic terms (compare, comparison, slower, timings, versions),
      which is a weak signal. The specific owning fact was found by reading the store directly, and
      that is what the verdict rests on - not the redcheck hit.

## GREEN

- [x] Text check: the sub-bullet states the mechanism (`__file__` or the working directory), the
      consequence (the difference measured is the relocation), and the remedy (swap in place;
      stash, checkout, or an identically-resolved symlink).
- [x] Quote-back for why this survives review: "The artifact of a relocated arm tends to be the
      more flattering result, which is what makes it survive review."

## REFACTOR

- [x] Written as a constraint on the SETUP rather than a warning about results, because by the time
      there is a number to distrust the run has already happened.
- [x] Kept to one bullet in an existing numbered step. A new Phase-3 section would compete with the
      closed-source-peer escalation already there and dilute both.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.

## Deliverables

- [x] One sub-bullet in `SKILL.md` Phase 3. No script, so no `tests/` change.
