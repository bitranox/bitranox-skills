# skill-writer checklist - coding-bash-clean-architecture (2026-08-27, audit bucket G)

Three defects in the canonical example, plus two found while verifying them.

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
- [x] Reproduced by EXECUTION, not review: the six library blocks assembled into the composition
      root and run. Default path exited 0 on `overall=critical`; `$result` held the report twice;
      `total=2` for one service and `total=1` for zero; with a file named `_svcn` present the run
      died `svc[name]: unbound variable` and reported `Config not found` (exit 3) for a config it
      had read. `shellcheck -x` gave SC2313 x3.
- [x] The naive fix for the count is INSUFFICIENT and was measured as such: `${results%$'\n'}`
      still yields one blank record, because a here-string always appends a newline.

## GREEN
- [x] Post-fix matrix, run with `_svcn` and `_svco` present: 1 down -> rc 1 total=1; 2 down ->
      rc 1 total=2; 0 valid -> rc 0 total=0; report printed exactly once in every arm.
- [x] `shellcheck -x` exits 0. The one remaining SC2016 is carved narrowly with its reason on the
      line above, because the single quotes are the injection fix and expanding them is the bug.
- [x] The shipped test block now runs: 7 passed, 0 failed. RED-verified by restoring the guard to
      its old position: rc 127, `domain__validate_service_def: command not found`.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
- [x] Adjacent defects fixed in the same change: the `--source-only` guard sat ABOVE the layer
      sources so the test block defined nothing (this is why the other two shipped undetected),
      and the nameref example in SKILL.md failed the same gate with SC2154.
