# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-08-27, audit bucket G)

One self-consistency defect: a count that disagrees with the list under it.

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
- [x] The header says "do all four" and five numbered items follow. The authoritative definition
      earlier in the same file lists exactly four INITIALIZATION steps and opens STEP A with the
      launch action, so item 5 was a lossy copy of STEP A missing its first two actions.

## GREEN
- [x] Item 5 removed and replaced by a sentence pointing at the MAIN LOOP, restoring the
      INITIALIZATION/STEP-A boundary the rest of the file uses.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
