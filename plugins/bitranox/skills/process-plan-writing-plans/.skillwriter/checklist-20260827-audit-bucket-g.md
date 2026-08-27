# skill-writer checklist - process-plan-writing-plans (2026-08-27, audit bucket G)

The self-announcement names a slug that exists nowhere else in the repo.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Every defect here is a FACTUAL claim, so the test is a
      ground-truth check against the real file, the installed package or live tool output, not a
      pressure scenario.
- [x] Scope: correction only. No new capability, no procedure reshaped.

## RED
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than the draft and cannot fail honestly. The route
      taken instead is the one the skill names - a ground-truth check whose result is immune to
      inherited context.
- [x] Four skills carry an announcement line. On raw counts, two match their frontmatter name and
      two do not, so counting settles nothing. The third channel does: the bare short forms occur
      NOWHERE in the repo except inside those two announcement lines, while every cross-reference
      uses the prefixed name. The H1-derived theory also fails, since a sibling whose H1 differs
      from its name announces the name. Both short forms are pre-rename upstream slugs.

## GREEN
- [x] The announcement now names the skill as its frontmatter does.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
- [x] The sibling `process-ship-finishing-development-branch` had the identical defect and was not
      filed; it is fixed in the same change.
