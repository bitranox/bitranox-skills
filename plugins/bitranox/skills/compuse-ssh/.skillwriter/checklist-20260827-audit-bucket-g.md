# skill-writer checklist - compuse-ssh (2026-08-27, audit bucket G)

The skill was CORRECT and the hook that points at it was wrong.

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
- [x] The filed finding blamed this skill for saying no PowerShell wrapper ships. Ground truth:
      nothing named `runps.sh` ships anywhere in this plugin, so the skill's statement is true.
      The false claim was in `hooks/warn-inline-powershell.py`, which told every user to reach for
      that script, and its test ASSERTED the name, pinning the defect in place.
- [x] Fixing what was filed would have shipped a claim false on every machine but one.

## GREEN
- [x] The hook now names the safe FORM (`-File`) rather than a script. Its test asserts on that,
      plus a negative assertion that the script name cannot return. 16 tests pass.
- [x] The skill now carries the two-step recipe the hook's `Detail:` pointer sends readers to, and
      names the hook, which it previously never mentioned.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
