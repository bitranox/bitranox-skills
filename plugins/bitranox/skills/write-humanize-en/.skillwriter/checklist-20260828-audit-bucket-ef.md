# skill-writer checklist - write-humanize-en (2026-08-28, audit bucket E+F)

One unanchored claim: which named chatbots do and do not emit curly quotes.

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
- [x] Stated undated, it is used to attribute authorship to a specific model. If a model's
      behaviour changes in either direction the guidance silently misattributes, with no way for
      the reader to see the claim is old - while comparable behavioural claims in this same file
      are dated.

## GREEN
- [x] The claim is dated to early 2026 and marked a weak signal that changes between releases,
      matching the dated neighbours in the same file. The mechanical advice (curly quotes also
      come from word processors, so they do not prove AI use) is unchanged.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.
