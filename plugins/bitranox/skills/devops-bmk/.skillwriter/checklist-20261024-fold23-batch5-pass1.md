# skill-writer checklist - devops-bmk (memory rules folded in)

- [x] Change: 3. Everyday commands, release/push bullets (new bullet right after the `deps` stage
      bullet) + Troubleshooting table row - devops-bmk/SKILL.md. RED on the pre-edit snapshot: NONE.
      Verified: Own packages exempt from cooldown and take newest release -> bmk
      src/bmk/adapters/stagerunner/helpers/_dependencies.py:910-912 ('An exempt package under an
      active cooldown takes its newest release'; exempt = policy.default is not None and cutoff is
      None) and _supply_chain.py:545-556 own_closure; no cooldown -> no cutoff for anyone
      (_dependencies.py:913). Latest read from JSON API -> _dependencies.py:302 url =
      https://pypi.org/pypi/{normalized}/json. Local failure text -> _dependencies.py:2095
      '<project>: uv lock --upgrade failed after the floor update' and :2104 'uv sync from uv.lock
      failed after the floor update'; existing SKILL.md section 4 says deps_update names its failure
      in JSON mode (so the body's '(no output captured)' shape was NOT carried). CI resolver text
      'Because only <pkg><=<old> is available ... unsatisfiable' -> uv resolver output as recorded
      in the fact body (observed, kept as quoted output). JSON API vs simple index lag -> recorded
      index fact the skeptic cited (kept as 'either can lag the other by minutes'). bmk version
      checked: apps/utils/bmk HEAD 2c27753 (3.25.3).
- [x] Dropped as stale or unverified: Dropped the hint's '[deps_update] (exit code: 1) (no output
      captured)' / 'opaque exit 1' shape (contradicted by SKILL.md section 4: deps_update puts
      failure lines in captured output). Dropped the dated lib_log_rich/finanzonline_uid timing
      instance and the memory slug cross-reference. Did not claim which exact stage of `make push`
      fails first (push's own `deps` check runs before the test pipeline's deps_update,
      registry.py:202-204), only that the gate fails in its [deps_update] block when the floor was
      raised too early.
- [x] Change: 3. 'If the project ships a Claude Code skill' bullet list (new bullet after the 'raise
      plugin.json ... never lower it' bullet) - devops-bmk/SKILL.md. RED on the pre-edit snapshot:
      partial. Verified: Bump writes pyproject, CHANGELOG, __init__conf__, plugin.json and re-locks
      uv.lock -> bmk src/bmk/adapters/stagerunner/helpers/_bump_version.py:17-20 (module docstring)
      and _apply_bump :350-360 (update_pyproject, update_changelog, sync_initconf_version,
      sync_plugin_version; '# uv.lock records the project's own version; left stale it fails `uv
      sync --locked`'; re-lock only when uv.lock is a file). 'when it lags' -> existing SKILL.md
      bullet 'raise plugin.json to the package version whenever it lags, and never lower it' (kept
      consistent; did not carry the body's unconditional-rewrite wording). Existing line 'make
      bump-* ... syncs __init__conf__.py and plugin.json' left unchanged and consistent.
- [x] Dropped as stale or unverified: Dropped the body's claim that plugin.json is rewritten
      unconditionally (superseded by 'raised only when it lags'). Dropped repo-specific names
      (lsdsk, tests/test_metadata_sync.py) and dated versions; generalised to 'a repo's own test
      pins plugin.json to the pyproject.toml version'. Did not list src/<pkg>/makefile/Makefile and
      cooldown.mk (bump syncs those only for a project that ships a bundled Makefile, i.e. bmk
      itself).
- [x] Change: 6. Configuration and custom pipelines (new paragraph after the 'bmk runs pytest in
      this project's own .venv' paragraph) + Troubleshooting table row - devops-bmk/SKILL.md. RED on
      the pre-edit snapshot: NONE. Verified: Upload happens inside the pytest stage ->
      registry.py:159 Stage("pytest", 40, ToolAction(tools.pytest_cov_argv)); tools.py:158-163 runs
      _coverage.py --run without --no-upload; _coverage.py:1079 upload=not args.no_upload. Token env
      first, then .env searched upward -> _coverage.py:542-556 and _find_dotenv_upward :520-527
      (walks parents). codecovcli on PATH required, else skip with exit 0 -> _coverage.py:946-960;
      skip warnings are quiet-suppressed in JSON mode (quiet=quiet). codecov-cli is not a bmk
      dependency -> bmk pyproject.toml:105-111 (commented out). Slug only from origin remote ->
      _coverage.py:836-847 (--slug only if remote.slug) and :862-863 (CODECOV_SLUG). Failed upload
      -> stderr '[codecov] upload failed (exit {exit_code})' :878 and stage returns 1 :963-964; test
      failure returns first :1003-1004. Exact 'ValueError: The provided slug is invalid' text is
      inside codecov-cli and NOT verified in source, kept as 'observed'.
- [x] Dropped as stale or unverified: Dropped the body's dated 'all green on this repo' instance and
      its manual pytest/ruff/pyright command list; dropped the side note about bmk churn (covered
      elsewhere in the skill). Corrected the hint's 'token in .env' to 'environment first, then .env
      in project or any parent' and added the codecovcli-on-PATH precondition.
- [x] Change: 3. Everyday commands, release/push bullets (new bullet after the release-cascade
      bullet) + Troubleshooting table row - devops-bmk/SKILL.md. RED on the pre-edit snapshot: NONE.
      Verified: make test's first stage raises floors -> registry.py:151 Stage("update_deps", 10,
      PipelineAction("deps_update")) and existing SKILL.md text ('a `make test`, whose first stage
      raises floors'). Example behaviour -> [7.1.1]: 'An unreadable config file ... also raises
      `LayerLoadError` instead of a bare `PermissionError`' (generalised in the skill, library name
      not cited).
- [x] Dropped as stale or unverified: Nothing stale; kept the example generic (no library
      name/version) to describe a pattern rather than one release.
- [x] Review B fixed: the release-cascade failure is named per entry point. make push fails first in
      its deps check, with the same output as a stale floor, and the bmk deps --update / make test
      that fixes a stale floor then fails in deps_update ("uv lock --upgrade failed after the floor
      update"); the stale-floor bullet points at the cascade (bmk registry.py _PUSH_PIPELINE /
      _TEST_PIPELINE).
- [x] Delta review fixed: under make push the deps check runs inside the first stage update_deps, so
      JSON mode prints an [update_deps] block with the nested [deps] block, in all three places that
      describe it (engine.py run_pipeline writes report_batch_failures into the parent stage sink).
- [x] GREEN gap fixed: "do not hand-edit plugin.json" after a bump and "bump plugin.json yourself"
      on a release refusal now say which case each covers, and the refusal case includes plugin.json
      already ahead of the new package version.
- [x] Gaps declined: a polling interval for the cascade wait (no measured bound; the text says
      minutes and names the two endpoints to check); an explicit test separating cascade from stale
      floor (the deciding signal, a just-released own library, is stated and checked first).
- [x] Review B: the twin under the bmk repo got the same change by three-way merge (git merge-file
      against the pre-edit text); repo-gate --mirrors reports the pair in sync.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      then the scenarios each review fix touched (6 after the first review, 1 after the second).
      Every answer was a quote from the new text on both tiers in every round; no NONE. Quotes
      were checked against the files; misses traced to line wraps and the arm's own commentary.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff in three slices, then a review of each fix delta alone;
      every finding fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps
      not listed here asked for detail the rule does not need or were answered elsewhere in the
      skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history wording absent from the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
