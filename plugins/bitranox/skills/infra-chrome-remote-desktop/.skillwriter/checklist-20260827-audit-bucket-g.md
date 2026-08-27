# skill-writer checklist - infra-chrome-remote-desktop (2026-08-27, audit bucket G)

The positive control the skill insists on could not be run.

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
- [x] Executed: the second block alone raises `NameError` on `base64`. Concatenation does not fix
      it either, because the first block ENDS in driver code reading `sys.argv` and opening the
      real config - with no argv it raises `IndexError`, with a fake path it fails on `open`.
- [x] The skill says to run the control BEFORE trusting the real config, which was impossible as
      printed. Its whole anti-false-negative argument rests on that control.

## GREEN
- [x] The driver now sits behind `if __name__ == "__main__"`, the first block is named
      `crdpin.py`, and the control imports from it. Verified by extracting both blocks and running
      the control with no argv and no config: it prints its pass line and exits 0.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
