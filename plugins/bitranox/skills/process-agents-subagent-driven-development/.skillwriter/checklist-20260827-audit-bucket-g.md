# skill-writer checklist - process-agents-subagent-driven-development (2026-08-27, audit bucket G)

Every documented invocation of both bundled scripts is unrunnable as printed.

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
- [x] Both scripts resolve git AND their output directory from the PROCESS working directory, so
      they must run in the repo under review. The documented path is relative to the skill
      directory, which is the one place those git calls fail. Reproduced in three arms: from the
      skill dir, rc 2 on a bad BASE; from the target repo with the relative path, rc 2 file not
      found; from the target repo with an absolute path, rc 0 and the diff written.
- [x] So changing the directory qualifier alone, as filed, cannot work - the path is wrong too,
      at all 8 sites rather than the one that carried the qualifier.

## GREEN
- [x] All 8 invocations across both files now use `$CLAUDE_PLUGIN_ROOT` and say to run from the
      repo under review. Verified: no bare relative invocation remains.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
