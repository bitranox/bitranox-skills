# skill-writer checklist - write-humanize-en (2026-08-27, audit bucket G)

A guarantee that is measurably false today.

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
- [x] The hook and the strip script do not share one definition of code: the hook calls
      `find_tell_lines`, and `transform_outside_code` has exactly one production caller, the strip
      script. They are two independent fence walks, and the function's own docstring calls itself
      the write-side TWIN of the detector.
- [x] They already disagree, shown end to end through the real CLIs: U+2028 inside an inline code
      span passes the sweep and IS rewritten by the script, splitting the span across two lines.
      Root cause is `str.splitlines()`, which breaks on exactly the codepoints that are themselves
      in the tell set. So the claim was not merely a wrong attribution but a false promise.
- [x] The existing guard test cannot reach this: it asserts only over the em dash, which is not a
      line break.

## GREEN
- [x] The passage now names both functions, says they are twins rather than one function, states
      exactly which character class diverges and why, and replaces the false guarantee with the
      accurate protection (keeping examples in backticks).

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
- [x] The German twin repeated the same guarantee and is corrected in the same change.
- [x] The code fix that would make the original guarantee true - one shared line splitter, and a
      test widened past the em dash - is deliberately NOT in this change: it alters shipped
      behaviour of the commit-blocking hook and needs its own RED test, so it is filed separately.
