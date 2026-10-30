# Checklist 2026-10-29 - contribution batch b1 (compuse-toolbox jigs and their rows)

Scope: the SKILL.md rows for `gate`, `ci_wait`, `claim_check`, `mutation_arm`, `conflict_resolve`,
`redaction_scan`, `anchor_edit`; two new rows (`markerwatch`, `winpytest`); the `ci_wait` timeout
default in the release paragraph; the frontmatter description; `references/mutation-arms.md`
and `references/anchored-edits.md`. Each row states behaviour the jig's own tests pin.

- [x] RED: the skill did not say any of it. Before the edit, `grep -c` on SKILL.md returned 0 for
      `INDENTED`, `one command per`, `--workflow`, `fail-on-failed-job`, `jobs done`, `--literal`,
      `mutation_arm[^|]*--cmd`, `re-padded\|padding`, `ABSOLUTE path\|absolute path`,
      `markerwatch`, `winpytest`; the description matched `mutat` 0 times; the release paragraph
      said `--timeout` (default 1500 s), which no longer matches `ci_wait.py`.
- [x] Placement: each rule sits in the row of the jig a reader is about to run (the row is what
      the PreToolUse nudge points at), and the two arm traps sit in `references/mutation-arms.md`,
      which the index tells a reader to load before trusting a verdict.
- [x] GREEN: after the edit `grep -c` returns 1 each for `INDENTED by two spaces`, `ONE command`,
      `--workflow NAME`, `fail-on-failed-job`, `jobs done`, `--literal`, `NON-pytest arm`,
      `FRESH mtime`, `re-padded`, `Every path is ABSOLUTE`, `^| \`markerwatch\``,
      `^| \`winpytest\``, `blank line between them`; `default 3600 s` returns 2 (ci_wait row and
      release paragraph); references/mutation-arms.md matches `FRESH mtime\|NON-pytest suite` 2
      times; references/anchored-edits.md matches `must be ABSOLUTE` once.
- [x] Every claim is the code's: verified against the tests that pin it -
      tests/test_gate.py (TestAShellOperatorInAGateIsRefused, TestAStrayWordBesideAGateIsRefused,
      test_the_help_says_the_verdict_lines_are_indented), tests/test_ci_wait.py (TestAWorkflowFilter,
      TestPerJobProgress, TestAFailedJobInAnUnfinishedRun, TestSuccessNeedsEveryJobFinished,
      TestARepoGivenAsALocalPath, TestTimeoutDefaultAndExpectedDuration,
      TestANoRunsVerdictNamesTheLiveCauses), tests/test_claim_check.py (the literal tests),
      tests/test_mutation_arm.py (cmd arms, fresh mtime, compile-error vs failing-run verdicts),
      tests/test_conflict_resolve.py (markdown blank-line joins), tests/test_redaction_scan.py
      (re-padded rows), tests/test_markerwatch.py, tests/test_winpytest.py; anchor_edit's refusal
      run by hand: `anchor_edit.py reap x.md` -> "refusing a relative path, pass an absolute one:
      x.md", rc=2.
- [x] winpytest run for real against a Windows test host: one run exited 1 with summary
      "1 failed, 1 passed in 0.22s" (the env-dependent test failing without `--env`), the next,
      over the now-existing destination, exited 0 with "2 passed in 0.03s"; the probe dir was
      removed afterwards.
- [x] Description: rewritten, not appended (it stood at 1017 of 1024 characters). Measured with
      `yaml.safe_load` of the frontmatter: 997 characters, YAML-safe, trigger-only. Added: "pytest
      on a Windows host", "waiting for a log marker (tail -F | grep)", "does a test catch a
      mutated line, a mutation battery". Shortened, meaning kept: tracked-vs-ignored, the sweep and
      UTF-16 phrases, the newest-file phrase, the guard-replay and control phrases.
- [x] Generic and public: example hosts are `WINHOST`/`USER`/`KEY`; no private host or repo name.
- [x] ASCII only: `grep -nP '[^\x00-\x7F]'` over SKILL.md, references/*.md and the new scripts and
      tests prints nothing.
- [x] Tables reformatted with docs-md-table-formatting `reformat_tables.py SKILL.md`.
- [x] Not mirrored: `repo-gate.py --mirrors` lists no compuse-toolbox pair.
- [x] Derived artifacts (skill_triggers.json, docs/skills.md) are NOT regenerated here; the batch
      integration regenerates them.
- [x] Subagent retrieval arm (run at integration, 2026-10-30): a text-only probe given ten table
      rows and four scenarios (log marker answered early by a banner, pytest on a Windows host over
      ssh, proving `cargo test` catches a mutated line, is a backticked phrase already in 40 docs)
      picked markerwatch, winpytest, mutation_arm and claim_check, 4 of 4, each quoting the row
      phrase that decided it. The behaviour itself is proven by the jigs' tests.
