# skill-writer checklist - process-review-receiving-code-review (2026-08-27, audit bucket G)

An inference that does not follow, about a tool's default method.

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
- [x] The text argued that because `gh api` sends GET unless given a method OR a field, the reply
      needs BOTH. From "A or B" that conclusion does not follow. `gh api --help` on 2.92.0 states
      that adding request parameters automatically switches the method to POST, so the field alone
      suffices and `-X POST` is redundant.
- [x] The filed claim said "either alone suffices", which overreaches in the other direction:
      `-X POST` with no body would POST an empty payload and be rejected. The fix does not inherit
      that phrasing.

## GREEN
- [x] The sentence now says the field is what makes it a POST and that the explicit method is for
      readability, not necessity.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
