# skill-writer checklist - process-debug-systematic (2026-09-25, skill-script audit P1)

find_polluter.py gained an exit-code contract; root-cause-tracing.md follows the code.

## PLAN
- [x] Skill type: technique with a bundled tool. The edit is a FACTUAL claim about
      find_polluter.py (what it is, what its exits mean), so the test is a ground-truth check
      against the script, not a pressure scenario.
- [x] Scope: correction only. SKILL.md itself is unchanged.

## RED
- [x] Behavioural RED deliberately NOT used: the skill is installed here. Ground truth instead:
      tests/test_find_polluter.py pins each exit (0 / 1 / 2 / 3), and each guard was reverted in
      a scratch copy to confirm its test fails.
- [x] Old text called it a "bisection script"; the script is a linear scan, and no exit
      contract was documented at all.

## GREEN
- [x] "linear-scan script", and the four exit codes named where the script is introduced.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, hostname or machine path added.
