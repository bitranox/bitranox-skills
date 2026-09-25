# skill-writer checklist - net-rotating-proxies (2026-09-25, skill-script audit P1)

The script's exit codes, flaky eviction and --cmd splitting changed; the doc follows the code.

## PLAN
- [x] Skill type: reference/technique. Every edit is a FACTUAL claim about proxy_pool.py, so the
      test is a ground-truth check against the script and its tests, not a pressure scenario.
- [x] Scope: correction only, following the script fixes. No new capability.

## RED
- [x] Behavioural RED deliberately NOT used: the skill is INSTALLED here, so a probe answers from
      the shipped wording. Ground truth instead: each changed claim is pinned by a test in
      tests/test_proxy_pool_cli.py that fails when the matching code change is reverted
      (exit codes, flaky not persisted, Windows split).
- [x] Old text claimed the pool is "re-tested every run" (validate skips live.txt), and that a
      flaky proxy is "evicted and replaced just like a hard-dead one" while the "otherwise" rule
      says "do not ban it"; the script wrote it to bad.txt, contradicting the latter.

## GREEN
- [x] Summary line says the pool is never trusted as-is (rule 1 already explains how).
- [x] Rule 6 and the "otherwise" bullet agree: flaky = out of this run's working set, never bad.txt.
- [x] --cmd paragraph names the per-platform split and the exit codes 0 / 1 / 2.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
