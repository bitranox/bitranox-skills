# skill-writer checklist - coding-python-performance-review (2026-09-25, follow-ups H3)

Two documented behaviours were wrong: the step 4a/4b/4f blocks split every discovered path at
its spaces, and Step 2 described a version gate on the interpreter running `setup_env.py`
instead of the one it records. SKILL.md is corrected to match the fixed blocks and script.

## PLAN
- [x] Skill type: reference/technique. Every SKILL.md change is either a bash block the reader
      executes or a FACTUAL statement about what `setup_env.py` does, so the test is a
      ground-truth run, not a pressure scenario.
- [x] Scope: correction only. No new capability, no step reordered, description untouched.

## RED
- [x] Behavioural RED deliberately NOT used: the skill is INSTALLED on this machine, so a probe
      answers from the shipped wording, not the draft. Ground truth was checked instead.
- [x] The 4a/4b/4f blocks, extracted verbatim from the HEAD SKILL.md and run under bash in a
      project with `src/my pkg/a.py`, wrote `ERROR not found: src/my` and
      `ERROR not found: pkg/a.py` into all three result files and scanned nothing.
- [x] `setup_env.py` in a project whose `.venv` python could not run exited 0: the gate judged
      only the interpreter running the script.

## GREEN
- [x] The blocks collect paths into a bash array (`find -print0` plus `read -d ''`, which bash
      3.2 also has) and pass `"${python_files[@]}"`. `BX_PERF_FILES` is one path per line.
      Verified by tests/test_skill_md_file_discovery.py, which runs the SKILL.md blocks
      verbatim: 6 failed against the HEAD text, 6 pass against this one.
- [x] Step 2: the gate runs the RECORDED interpreter once, requires 3.10+, exits 2 naming its
      path, and creates no scratch dir. Verified by tests/test_setup_env.py and end to end with
      `uv run setup_env.py` in projects holding real 3.9 (exit 2) and 3.10 (exit 0) venvs.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/'` over the SKILL.md diff hits
      nothing.
- [x] Front matter untouched (the diff has no `---` line).
