# skill-writer checklist - infra-chrome-remote-desktop (2026-08-28, audit bucket E+F)

One unanchored claim: a reverse-engineered PIN-hash format stated as fact.

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
- [x] The format is internal and undocumented in a product that updates continuously, and the
      passage named no version. A changed construction would give the reader a false PIN verdict
      rather than a signal to re-check.

## GREEN
- [x] The claim now names chrome-remote-desktop 151.0.7922.13 (read from `dpkg -l` on this box),
      gives that command as the reader's own check, and points at the positive control already in
      the skill as the detector: a changed construction shows up there as a control that fails.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.
