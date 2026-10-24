# skill-writer checklist - devops-bmk (memory rules folded in)

- [x] Change: 3. Everyday commands > 'release does not bump; push always commits.' list, new bullet
      directly after the existing 'push stages with git add -A ... empty commit' bullet -
      devops-bmk/SKILL.md. RED on the pre-edit snapshot: partial. Verified: Empty commit on nothing
      staged -> bmk src/bmk/adapters/stagerunner/git_ops.py:101 `commit_flags = ["--allow-empty"] if
      nothing_staged else []`. Subject `<timestamp> - <message>` -> git_ops.py:86
      `f"{timestamp_prefix(datetime.now())} - {message}"`. Message order args -> BMK_COMMIT_MESSAGE
      -> prompt on tty -> 'chores' -> git_ops.py:25-45 resolve_message (args joined first, then env,
      then input() when isatty, else "chores"). MSG= exported as BMK_COMMIT_MESSAGE and is the safe
      channel -> src/bmk/makefile/Makefile:79-101 (`ifdef MSG` / `export BMK_COMMIT_MESSAGE :=
      $(value MSG)`, header comment 'MSG= is the safe channel, ARGS= is not'). Trailing words
      forwarded as args -> Makefile:277-295 (`make push fix login bug`, `override ARGS +=
      $(_EXTRA)`). push runs the test pipeline before commit/push ->
      src/bmk/adapters/stagerunner/registry.py:201-208 (_PUSH_PIPELINE: update_deps 10, build+test
      20, clean 30, commit 40, push 50), so `make test` then `git push` covers the same gate minus
      the commit.
- [x] Dropped as stale or unverified: The body's `python3
      <plugin>/skills/compuse-toolbox/scripts/gate.py --gate ... --then ...` command: a cross-plugin
      bitranox-marketplace tool the bmk-repo twin cannot assume is installed (skeptic). Replaced
      with 'run make test, then a plain git push only if it passed'. Nothing CONTRADICTED.
- [x] Change: 1. Install > 'bmk's env holds bmk alone, and is shared': new bullet after the '[bmk]
      another bmk is using the shared tool environment ...' bullet; reconciled wording in the 'The
      rebuild waits ...' bullet; Troubleshooting table row '`make` keeps using an old bmk right
      after a release' (Cause/fix cell rewritten at the existing column width) -
      devops-bmk/SKILL.md. RED on the pre-edit snapshot: partial. Verified: Skip message text -> bmk
      src/bmk_toollock.py:299-300 ('[bmk] another bmk is using the shared tool environment; waited
      {timeout}s for the lock at {target} and gave up. Nothing was changed.'). Upgrade under
      exclusive lock with 10s timeout and skip -> src/bmk/makefile/Makefile:228 (`--exclusive
      --timeout 10 --on-timeout skip`) and :269-272 (_ensure_bmk runs `$(BMK_LOCK) uv tool upgrade
      bmk`). Every bmk holds the lock shared for its whole run ->
      src/bmk/adapters/cli/main.py:138-143 (`bmk_toollock.hold_shared()` before _run_cli, comment
      'for this whole run') and src/bmk_toollock.py:182-202 (acquire(..., exclusive=False)). A hung
      bmk on the Makefile prompt holds it -> existing SKILL.md section 4 text (unbounded prompt,
      'All that time it holds bmk's shared lock'). Hand-run upgrade takes no bmk lock -> the lock is
      only applied by the Makefile wrapper (Makefile:228/270) and SKILL.md section 1 already states
      a hand-run `uv tool install bmk` is unguarded. 'uv tool upgrade revalidates the index on every
      run' -> already stated in the pre-edit skill section 1; not re-measured (running uv tool
      upgrade would change the system). Tables canonical -> reformat_tables.py --check SKILL.md:
      'Unchanged', rc 0; row length and pipe count asserted equal to the old row.
- [x] Dropped as stale or unverified: The dated measurement (a peer session on 3.19.0 vs 3.20.0, 117
      logs) as internal history; the uv 0.13.0 'Found stale response ... Sending revalidation
      request' log line (UNVERIFIED per skeptic, not re-measurable read-only). Corrected the skill's
      own 'Either way the next `make` upgrades; just re-run it' in the Troubleshooting row and '(the
      next `make` takes it)' in section 1, both wrong while a bmk process stays alive.
- [x] Change: 3. Everyday commands > 'release does not bump; push always commits.' list, new bullet
      after the new 'On an already-committed tree ...' bullet - devops-bmk/SKILL.md. RED on the
      pre-edit snapshot: partial. Verified: make push tests the current (bumped) tree before
      commit/push -> bmk src/bmk/adapters/stagerunner/registry.py:201-208 (_PUSH_PIPELINE test at
      order 20, commit 40, push 50). bump renames [Unreleased] ->
      src/bmk/adapters/stagerunner/helpers/_bump_version.py:2-6 and :133-172 (update_changelog).
      bump syncs __init__conf__.py and plugin.json -> registry.py:176-180 (_bump_pipeline: bump 10,
      sync_initconf 20) and helpers/_sync_initconf.py:1-16 docstring (patches __init__conf__.py,
      bundled Makefile, .claude-plugin/plugin.json, never downward). Nothing in bmk edits SKILL.md
      -> `grep -rn 'SKILL.md\|uvx' src/bmk --include=*.py` hits only run_cmd.py/_run.py (uvx --from
      <project_dir> for `bmk run`), no SKILL.md writer. The general 'pinning test passes pre-bump,
      fails post-bump' is the body's dated measurement, kept only as the generic shape.
- [x] Dropped as stale or unverified: The private sweep script (.plan/sweep_repo.py ship) and the
      dated per-repo measurement (package name, 0.2.5/0.2.6, 18 CI cells); 'sync any mirrored twin
      (bitranox-skills) once PyPI serves the version' (marketplace-specific, not bmk usage).
      Corrected the body's implication that plugin.json/__init__conf__ pins fail often: bmk's bump
      syncs those, so the uvx floors in SKILL.md are the case bmk never fixes.
- [x] Review A fixed: the Troubleshooting row leads with the tool-lock skip and its grep string, uv
      index lag second, "usually" not "almost always"; after make bump-* only the SKILL.md floors of
      the listed pins can fail; commit make test churn before a plain git push; the 124-column line
      rewrapped.
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
