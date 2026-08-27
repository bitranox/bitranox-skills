# skill-writer checklist - net-rotating-proxies (2026-08-27, audit bucket G)

"The moment one dies" describes a ten-minute poll that is off by default.

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
- [x] The loop waits 600 seconds, hardcoded, exposed by no flag. The wait sits at the TOP of the
      loop, so the first pass is at t+600s, not t+0. The whole loop is opt-in behind
      `--background-discovery`, which defaults to false, while the sentence stated the behaviour
      unconditionally. The bench loop is not a substitute: it only trials proxies already in the
      live set, and discovery is called from the refresh loop alone.
- [x] The genuinely instant path is the ban-and-refill from the over-provisioned pool.

## GREEN
- [x] The sentence now names the warm backup as the only instant replacement, states the cadence
      and the opt-in flag, and tells the reader to size `--need` to survive ten minutes of
      attrition rather than to be rescued from it.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
