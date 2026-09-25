# skill-writer checklist - coding-python-performance-review (2026-09-25, script audit A1)

The bundled scripts changed behaviour (exit codes, the recorded interpreter, the cache
template's warm-up and ABORT, the claim extractor's scope). SKILL.md is corrected to match.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Every SKILL.md change is a FACTUAL statement about what a
      shipped script does, so the test is a ground-truth check against the script, not a
      pressure scenario.
- [x] Scope: correction only. No new capability, no step reordered, description untouched.

## RED
- [x] Behavioural RED deliberately NOT used: the skill is INSTALLED on this machine, so a probe
      answers from the shipped wording, not the draft. Ground truth was checked instead.
- [x] Each old statement was false against the fixed scripts: validate_perf_claims scanned
      removed lines too and printed no location; compare_performance "restore" left HEAD
      detached and exited 0 over a failing suite; setup_env's `python` under `uv run` was uv's
      script env; the cache template compared a cold run against a warm one and never looked at
      pytest's exit code; the AST finders exited 0 on files they could not parse.

## GREEN
- [x] Review-pipeline bullets: claims come from ADDED lines with `path:line`; compare restores
      branch and changes and exit 2 means no valid comparison. Verified by
      tests/test_validate_perf_claims.py and tests/test_compare_performance.py (real git repo,
      real pytest, the script run as a subprocess).
- [x] Step 2: `python` is the project's `.venv`/`venv` interpreter. Verified end to end:
      `uv run setup_env.py` in a project with a real `.venv` printed that venv's python.
- [x] Step 4: the finders' exit 2 plus `ERROR` line. Verified by the CLI tests of all three
      finders (bad file, missing path, directory).
- [x] Step 6: warm-up, warm-against-warm, ABORT exit 2. Verified by
      tests/test_profile_with_cache_template.py, including an end-to-end copy of the template
      run against a real uninstalled project.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/'` over the SKILL.md diff hits
      only two pre-existing context lines.
- [x] Front matter untouched (the diff has no `---` line).
