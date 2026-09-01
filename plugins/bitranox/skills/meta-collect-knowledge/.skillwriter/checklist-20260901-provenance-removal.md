# skill-writer checklist - meta-collect-knowledge (the dead gathered: contract is removed)

Change: the `--source gathered:<origin-slug>` and `gathered-cross-tree:<top>` instructions, the
deliverable that required the mark, and the failure-mode line claiming the mark prevents
re-promotion. The flag they use no longer exists and the property they promised was never
implemented. The debounce that does exist is named instead.

## PLAN

- [x] Skill type: technique (a procedure with a marking step and a stated safety property).
- [x] Test approach: coverage check against ground truth, plus the executable check that the flag
      the steps tell the reader to pass is now rejected. Recorded as the chosen route.
- [x] Scope: four passages in this skill. The sibling claim in meta-dream-crosstree has its own
      checklist.

## RED

- [x] The steps instruct passing `--source gathered:<origin-slug>`. That flag is rejected by the
      engine: `error: unrecognized arguments`, exit 2, nothing written. A reader following the old
      text produces a failing command.
- [x] The property it claimed was already absent: 0 facts in the live store carry the mark, and 0
      lines of plugin code read one. The deliverable checklist item required an artifact nothing
      consumed.

## GREEN

- [x] The copy steps now say what to do without naming a removed flag, and the failure-mode line
      names `gather_scan.py`'s `gathered-topics.tsv` as the real debounce, with the reason it is
      kept out of the store.
- [x] `grep -c "gathered:"` over the corrected SKILL.md returns 0.

## REFACTOR

- [x] A documented safety property that does not exist is worse than none, because a later reader
      cites it as settled. The correction states the mechanism instead of asserting the property.
- [x] Undecided gap list is empty.

## Quality

- [x] Present tense, no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added by this change.
- [x] Frontmatter untouched: no `name` or `description` change, so no routing keyword moved.
