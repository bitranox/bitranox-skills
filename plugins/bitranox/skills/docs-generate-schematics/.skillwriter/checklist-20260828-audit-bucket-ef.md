# skill-writer checklist - docs-generate-schematics (2026-08-28, audit bucket E+F)

One unanchored claim in the bundled script: two preview-tier model IDs with no verification date.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The defect is a FACTUAL claim carrying no version or date,
      so the test is a ground-truth check against the installed package, the live catalogue or the
      running tool - not a pressure scenario.
- [x] Scope: correction only. No new capability, no procedure reshaped.

## RED
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording rather than the draft and cannot fail honestly. The route
      taken instead is a ground-truth check, whose result is immune to inherited context.
- [x] Preview-tier IDs are renamed and retired without notice. Nothing said when these were last
      known good or how to confirm them, so a retirement surfaces as an opaque HTTP error with no
      documented place to look.

## GREEN
- [x] Both IDs were verified present in the live OpenRouter catalogue on 2026-08-28, and the
      script now records that date beside them plus the one command that lists the current IDs -
      the first thing to run when a request starts failing.
- [x] The file still parses; the change is comments only, so no behaviour and no test moves.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.
- [x] SKILL.md is unchanged: the defect and the fix are both in `scripts/`.
