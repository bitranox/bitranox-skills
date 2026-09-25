# skill-writer checklist - process-test-driven-development (2026-09-25, skill-script audit P1)

redcheck.py gained a second "unchecked" cause and dedupes documents across flags; the exit-code
table and the paragraph under it follow the code.

## PLAN
- [x] Skill type: technique with a bundled tool. The edits are FACTUAL claims about redcheck.py's
      exit codes, so the test is a ground-truth check against the script, not a pressure scenario.
- [x] Scope: correction only. No procedure reshaped.

## RED
- [x] Behavioural RED deliberately NOT used: the skill is installed here, so a probe answers from
      the shipped wording. Ground truth instead: tests/test_redcheck.py pins exit 3 for an
      --answer with no terms and the single read of a doc named by --corpus and the cascade;
      both fail against the pre-fix script.

## GREEN
- [x] Exit 3 row names the --answer case; the paragraph under the table says a file reached by
      several flags is read once.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, hostname or machine path added.
