# skill-writer checklist - compuse-toolbox (description rewritten under the cap)

Change: the frontmatter `description` only. It stood at 1060 characters, over the documented 1024
cap, so its tail was at the mercy of a truncation nothing reports. Rewritten to 999.

## PLAN

- [x] Skill type: reference/index over the bundled tools. The description is a trigger list, one
      clause per tool, which is exactly the shape that grows past a cap by accretion.
- [x] Scope: the description line. No change to the body, the tools, or their tests.
- [x] Method fixed in advance by the rule this change enforces: a bloated description is a REWRITE,
      not a trim. Removing the tail would silently drop whichever tools sit at the end.

## RED

- [x] `test_every_shipped_skill_description_is_within_the_cap` failed naming this skill:
      "descriptions over the 1024 cap: compuse-toolbox (1060)". The test fails without the rewrite
      and passes with it, so it is not vacuous.

## GREEN

- [x] 999 characters, 25 under the cap.
- [x] No trigger lost. Every distinctive keyword in the previous description survives, verified by
      set difference over its extracted terms; the only casualties are filler ("tempted", "with",
      "just", "whether", "wrong", "finished") and the family label "computer-use", which the opening
      sentence already conveys.
- [x] `untracked` is kept as its own word rather than folded into "tracked vs gitignored", because it
      is the query term for that tool.
- [x] `cso_failures_for` returns clean: single-line plain scalar, trigger-first, keyword-rich.
- [x] Derived artifacts regenerated from the new text: `skill_triggers.json` (81 skills) and
      `docs/skills.md`.

## REFACTOR

- [x] Consolidation is by grouping, not by deletion: the three git questions (branch/sync/dirty,
      tracked vs gitignored vs untracked, merge-conflict markers) now share one clause instead of
      three, which is where most of the 61 characters came from.
- [x] The margin is 25 characters, so the next tool added is a rewrite rather than an append. That is
      the intended behaviour for an index description, and the gate now enforces it.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.
- [x] Wording stays symptom-shaped ("did CI finish on the commit I pushed, and pass"), not a summary
      of what the tools do.

## Deliverables

- [x] One line in `SKILL.md`; the two regenerated artifacts above.
