# skill-writer checklist - process-test-design (memory rules folded in)

- [x] Change: Adversarial inputs at the boundary (the test side of sanitization) - new paragraph
      after the branch-rule paragraph, before 'Scrub a captured artifact' -
      process-test-design/SKILL.md. RED on the pre-edit snapshot: partial. Verified: Cross-reference
      target exists: SKILL.md section '## Damaging the installed package: run a copy, with an intact
      copy as control' (pre-edit line 327), which already says 'Probe each kind of damage in its own
      arm' - so the new text adds only the missing part (the why: each kind surfaces at a different
      place through the library, a catch at the first raise fixes one kind; require the same refusal
      for all; placed at the hardening moment, not only the test-harness moment). Stopping-rule
      conflict the skeptic raised reconciled in the same text: each kind that surfaced differently
      counts as its own branch under the existing stopping rule (pre-edit line 173-179), so no
      contradiction with 'Inputs the code handles identically get one representative case'. The
      per-kind library behaviour is kept only as an unnamed, unversioned single-release measurement,
      as the skeptic required.
- [x] Dropped as stale or unverified: Dropped the library name (lib_layered_config), its version
      (7.x) and the measured exit codes 2/13/78: version-bound and possibly stale (a later release
      wraps an unreadable config's PermissionError in its own error). Dropped the project name, date
      and file name (defaultconfig.toml).
- [x] Change: Run in a clean, project-correct environment - new paragraph after 'A green
      windows-latest cell is WEAKER evidence than a real Windows machine', before 'A permission-wall
      test on Windows' - process-test-design/SKILL.md. RED on the pre-edit snapshot: NONE. Verified:
      pytest writes '<node id> (<phase>)': installed _pytest/runner.py:210-212 (`var_name =
      "PYTEST_CURRENT_TEST"`, `value = f"{item.nodeid} ({when})"`). Guard shape and bound: lsdsk
      tests/conftest.py:81-100 (WINDOWS_ENVIRONMENT_VALUE_LIMIT = 32767, LONGEST_PHASE_SUFFIX = "
      (teardown)", raise pytest.UsageError). Ran the skill's snippet verbatim (extracted from
      SKILL.md with awk) in a scratch dir: a 40000-char unnamed parameter -> rc=4 and 'ERROR: node
      ids too long for Windows ... (40021 chars)'; control with pytest.param(..., id="big") -> rc=0,
      '1 passed'. The 32767 Windows cap and the ValueError text are from the body's dated CI
      measurement and match the guard's own comment; not reproducible on Linux, kept as the search
      string.
- [x] Dropped as stale or unverified: Dropped the project name/version (lsdsk 1.8.0), the nvlist
      decoder cases, the measured node-id lengths (70282, 12200277), the 74 MB log size and the
      date. The skill snippet truncates each named id to 120 chars (as the shipped guard does)
      instead of dumping whole ids into the error.
- [x] Change: Prune low-value tests - new paragraph after 'Fewer, behavior-focused tests beat many
      brittle ones', before 'Never commit a test that asserts behavior the code does not have' -
      process-test-design/SKILL.md. RED on the pre-edit snapshot: NONE. Verified: Skeptic: no rule
      in the Prune section for proving a replacement (confirmed by reading pre-edit SKILL.md lines
      345-359). The cross-referenced 'Single-layer mutation stays green' bullet exists under Common
      mistakes and carries the copy-aside-not-git-checkout restore rule, so it is pointed to rather
      than restated. Text explicitly covers the rewrite/refactor case (the uncovered moment), not
      only a pruning task.
- [x] Dropped as stale or unverified: Nothing stale. Generalised the --traceback example to 'the
      except path an option turns on to print full error details'; dropped the CLI-rewrite incident
      narrative.
- [x] Change: Deterministic and order-independent - new bullet after 'No dependence on test
      execution order'; plus the Quick checklist 'Order-independent' line extended -
      process-test-design/SKILL.md. RED on the pre-edit snapshot: partial. Verified: Restoring
      context manager with main-thread skip: bmk
      src/bmk/adapters/stagerunner/helpers/_bump_version.py:301-316 (`_handlers`: `if
      threading.current_thread() is not threading.main_thread(): yield; return`, `previous = {sig:
      signal.signal(sig, handler) ...}`, restore in `finally`). Nested SIGINT hold-off during undo:
      same file `with _handlers({signal.SIGINT: signal.SIG_IGN}):` in `_undo_bump`. Handler raises
      an exception (`_Terminated(BaseException)`, `_on_signal` raises it). Exit 128 + signum:
      tests/test_bump_version.py:760 (`assert proc.returncode == 128 + signum`). Before/after
      getsignal test: tests/test_bump_version.py:775 and :784. ValueError off the main thread: ran
      signal.signal in a threading.Thread on this host -> 'ValueError: signal only works in main
      thread of the main interpreter'. Existing test-side line 'No shared mutable module/global
      state between tests' kept; the new bullet adds the production-side half, no contradiction.
- [x] Dropped as stale or unverified: Dropped the bmk file name, commit aae6709 (unverified) and
      'the plan for this change' narrative. Dropped the cross-link to the test-side companion memory
      fact (no memory slugs in skill text).
- [x] Review B S1 (PYTEST_CURRENT_TEST room): fixed - the guard subtracts
      len("PYTEST_CURRENT_TEST=") and len(" (teardown)") and counts UTF-16 units (pytest runner
      writes "<nodeid> (<when>)"; CPython's Windows putenv checks the UTF-16 length of NAME=value
      against 32767).
- [x] Nits fixed: one exit code and message shape naming the kind; the 128+signum mapping scoped to
      an entry point that does it; the over-100 pytest paragraph rewrapped.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      every scenario again after the first review's fixes, then the scenarios each later fix
      touched. Every answer was a quote from the new text on both tiers in every round; no NONE.
      Quotes were checked against the files (6-word windows; misses traced to line wraps,
      markup and line-number prefixes).
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps not listed
      here asked for detail the rule does not need (out of scope) or were answered elsewhere in
      the skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history finder clean on the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns except where the file keeps one line per paragraph or list item.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
