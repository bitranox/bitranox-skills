# checklist - point at the decision review from a verified completion claim

One cross-reference line to `bitranox:process-review-uncertain-decisions`. No doctrine is added
here: the question, its suppression clause and its output rule live in that skill alone, so the
two cannot drift.

## RED

- [x] No separate RED was run for this line, and that is a decision, not an omission. The
      behaviour it points at was baseline-tested on the OWNER (see that skill's artifact: the
      question passed clean-room on `haiku` and `sonnet`, so it ships verbatim). A RED here could
      only re-measure the owner's text through one more indirection.
- [x] What this edit CAN get wrong is a dangling pointer, so that is what was checked: the named
      skill exists at `skills/process-review-uncertain-decisions/SKILL.md` and its frontmatter
      `name:` matches the invocation string used here.

## GREEN

- [x] The line states WHY this moment is the right one to ask - a verified claim is true, which is a different property from being the right call - rather than only naming
      the skill, so a reader who does not follow the link still learns something.
- [x] It is one sentence plus its reason. This file is already long; a copy of the question here
      would be a second source of truth to keep in sync.

## REFACTOR

- [x] Checked against the other two pointers for duplicated prose: each states the reason its own
      moment matters, and none repeats the question, the suppression clause, or the output rule.
- [x] The guard in the Stop hook is what keeps three entry points from producing three asks in one
      session; without it this pointer would be a nagging source rather than a routing one.
- [x] No session narrative, no scratch paths, no machine-derived values.
