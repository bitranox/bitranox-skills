# skill-writer checklist - coding-python-performance-review (2026-08-27, audit bucket G)

Two claims about shipped scripts that the scripts do not satisfy.

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
- [x] `validate_perf_claims.py` read in full and RUN: it compiles regexes, prints matched claim
      phrases and a static reminder. No profiling, no subprocess, no verdict, `main()` returns 0.
      The skill's own Reference Files table already described it correctly, so the file
      contradicted itself.
- [x] `prioritize_cache_candidates.py` emits the line wrapped in markdown bold plus an `Action:`
      continuation; confirmed with `cat -A` on real-shaped input. All six documented formats were
      checked against their emitters and this was the only wrong one.

## GREEN
- [x] The bullet now says the script EXTRACTS and that the reader validates; the format entry
      carries the `**` and the `Action:` line, with a note to strip the bold before lifting.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
