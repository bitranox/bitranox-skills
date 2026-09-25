# skill-writer checklist - meta-skill-audit (2026-09-25, script behaviour sync)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Every changed line states what `audit_skills.py` or
      `script_prepass.py` does, so the RED is a ground-truth check of the old text against the
      code, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft. The artifact checks are immune.
- [x] RED, `--skip-existing`: the old text said a report that "exists and is non-empty" is skipped
      and that without `--reuse-room` "an interrupted run restarts from zero". The code skips only a
      COMPLETE report (a `FINDING:` line or `NO FINDINGS`) and works without `--reuse-room`, because
      `prepare_room` re-copies the plugin dir and leaves `reports/` alone. Reproduced: pre-seeded
      reports, `--scripts --skip-existing` without `--reuse-room` reviewed only the incomplete one.
- [x] RED, launcher: the old text sent three CLIs through `hooks/run-python.sh`, which exits 0 on a
      mistyped script path unless `BITRANOX_RUN_PYTHON_STRICT=1` is set (it then exits 3).
      `tests/test_script_prepass_checks.py::test_skill_md_never_sends_a_cli_through_the_fail_open_launcher_unguarded`
      failed on the old text (3 lines) and passes on the new.
- [x] RED, `--list`: the old text said it "prints the corpus"; it previewed a stale room copy.
      The new text says what it now does, pinned by `tests/test_audit_cli.py` (both directions).
- [x] New documented behaviour, each pinned by a test in `tests/`: reviewers launched with
      `--settings '{"disableAllHooks":true}'`; a `REPORT MISSING:` report names its cause; exit
      codes 0/1/2; `--scripts` refuses `--skills-dir`; `script_prepass.py` exits 2 on a room with
      neither `hooks/` nor `skills/`.
- [x] Hooks-off claim verified against the real CLI (2.1.282), not only a fake: one headless
      `claude -p` ran 16 hooks and SessionStart wrote `CLAUDE.md`, `CLAUDE.local.md` and
      `.remember/` into its cwd; with the setting it ran none and the cwd stayed empty.
- [x] GREEN: a haiku probe given the new text answered all seven retrieval questions (launch
      form, resume without `--reuse-room`, exit 1 meaning, `--scripts --skills-dir`, `--list`
      source, hooks, pre-pass on a skill dir) with a direct quote each; its Skill gaps are
      recorded below and decided.
- [x] Skill gaps from GREEN decided, all three DECLINED: (a) what `--reuse-room` adds - the text
      says the remaining reviewers read the same copy, and `--help` states "keep an existing plugin
      copy"; (b) whether a skill dir lacks `hooks/` and `skills/` - it does by definition, and the
      probe inferred the right answer; (c) whether `--list` honours `--reuse-room` - the quoted
      sentence ("the old room copy only with `--reuse-room`") already says so.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added; ASCII only.
- [x] Present tense, no session narrative, no private provenance.
