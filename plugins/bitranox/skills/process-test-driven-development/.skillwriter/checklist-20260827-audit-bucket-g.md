# skill-writer checklist - process-test-driven-development (2026-08-27, audit bucket G)

An exit code documented as a general guard that only one flag reaches.

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
- [x] `require_corpus` is set from `--corpus-cascade` alone, so `--corpus` can never produce exit
      3. Measured across four arms: an empty `--corpus` directory and a nonexistent one both exit
      0 with verdict `clean`, warning only on stderr, while both cascade arms exit 3. In JSON mode
      the warning does reach the envelope, but the exit code is still 0 and the verdict still
      `clean`, which is what a gate reads.
- [x] The sentence steering readers to `--corpus` is the mistype-prone form and had none of the
      protection the passage promised.

## GREEN
- [x] The exit-code table and the rationale both now scope the guard to `--corpus-cascade` and tell
      the reader to check the printed document count when passing `--corpus`.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
- [x] The same over-broad claim appeared in `redcheck.py`'s own module docstring at two places and
      in the `compuse-toolbox` row for this tool; both are corrected in the same change. The code
      fix that would make the original sentence true is deliberately NOT in this change: it alters
      shipped behaviour and needs its own RED test, so it is filed separately.
