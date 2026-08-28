# skill-writer checklist - coding-python-network-probe (2026-08-28, audit bucket E+F)

One unanchored claim: the macOS device path is warned as untested, with no version and no way
to tell whether that still holds.

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
- [x] The warning is still TRUE (a GitHub macOS runner is unprivileged and cannot open a BPF
      device), but it named no version, so a reader could not tell whether a later release had
      exercised and fixed the path.

## GREEN
- [x] The warning now names ipscout 1.6.0, the date, and `ipscout --version` as the check, with
      an explicit default: treat it as still true unless a later release says otherwise.
- [x] `ipscout --version` was EXECUTED before shipping and prints `ipscout version 1.6.0`.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.
- [x] Mirrored skill: the twin under `libs/ipscout/` carries the same change.
- [x] The quick-reference table re-padded to the formatter's canonical form (pre-existing drift,
      cell text byte-identical). Re-running the formatter is now a no-op.
