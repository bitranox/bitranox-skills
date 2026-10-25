# skill-writer checklist - process-test-design (memory rules folded in)

- [x] Change: Prune low-value tests > mechanics list ('Six mechanics' changed to 'Eight mechanics
      worth stating because they silently defeat a test that looks right:'), new bullet placed
      before 'A fixture built to make code FAIL' - process-test-design/SKILL.md. RED on the pre-edit
      snapshot: NONE. Verified: Rule is generic test-design reasoning, kept from the current body
      (discovery tested by four exclusion tests while the scan re-walked; assert at the argv seam;
      check -Recurse/rglob). Skeptic: the concrete bmk defect is already fixed
      (_psscriptanalyzer.py:208) and the specific CI venv path is unverified and not universal (CI
      template creates .venv_wheel in the checkout) -> CI claim made conditional ('a job that builds
      its venv outside the checkout'). List count: counted the existing bullets in SKILL.md (6:
      from-import, stdlib wrapper, index, basename, doctest teardown, failing fixture) + 2 new = 8,
      intro updated so it does not contradict the list. Added lines all <=100 cols, ASCII only.
- [x] Dropped as stale or unverified: The concrete CI path ( the
      bmk/PSScriptAnalyzer/find_ps1_files/pyright[nodejs] narrative (defect fixed, private
      provenance), and the unconditional 'CI builds the venv outside the repo' claim.
- [x] Change: Determinism and environment > 'Pin the environment an output premise depends on' (new
      paragraph after the delenv-absent paragraph); routing line in SKILL.md and the reference intro
      extended with '(or one a library reads at import)' -
      process-test-design/references/silent-test-defeaters.md. RED on the pre-edit snapshot:
      partial. Verified: rich-click 1.9.9 (uv run --with rich-click): inspect of
      rich_click/rich_click.py prints 'WIDTH: Optional[int] = terminal_width_default()', 'MAX_WIDTH:
      Optional[int] = terminal_width_default()', 'FORCE_TERMINAL: Optional[bool] =
      force_terminal_default()'; force_terminal_default reads env_vars = ["FORCE_COLOR",
      "PY_COLORS", "GITHUB_ACTIONS"]; terminal_width_default reads TERMINAL_WIDTH; both live in
      rich_click.rich_help_configuration. Probe: launched with GITHUB_ACTIONS=true
      TERMINAL_WIDTH=60, then deleted both from os.environ ->
      RichHelpConfiguration.load_from_globals() gave 'after delenv only: True 60 60'; after the
      three resets via the default functions -> 'after reset: None None None' (confirms
      load_from_globals copies the globals and that the fix works). 'coloured and wrapped' kept as
      the body's observed CI behaviour.
- [x] Dropped as stale or unverified: Project name (a consumer project), the dated CI measurement
      ('five tests failed'), the '1.9.x' version-scoped wording (stated as current behaviour).
      Placement moved from SKILL.md 'Deterministic' (hint) to the reference env-pinning section,
      which the SKILL.md routing line already sends env-variable work to.
- [x] Change: Python patch and import mechanics > new subsection after 'Prove "untested" with branch
      coverage' (beside the existing pytest-cov paragraph); routing line in SKILL.md and reference
      intro gained 'redirects or deletes coverage data from a conftest' -
      process-test-design/references/silent-test-defeaters.md. RED on the pre-edit snapshot: NONE.
      Verified: pytest-cov 7.1.0 source (inspect): '@pytest.hookimpl(tryfirst=True) def
      pytest_load_initial_conftests(early_config, parser, args)' registers CovPlugin(...), whose
      __init__ (start=True) calls self.start(engine.Central); engine start has
      'data_file=os.path.abspath(self.cov.config.data_file)' and 'self.cov.erase()', finish has
      'self.cov.combine()' -> erase-at-start and combine-at-end CONFIRMED (skeptic had them
      UNVERIFIED). Probe in scratch: conftest setting COVERAGE_FILE at import AND in
      pytest_configure -> pytest --cov=mod wrote ./.coverage, redir/ stayed empty; control with
      COVERAGE_FILE in the launching env -> redir/.cov-env written. 'No data to report' after a
      purge kept from the body's reproduction (follows directly from the purge deleting the file).
- [x] Dropped as stale or unverified: Project name (a consumer project), 'a project template', the
      dated measurement, and the bmk/CI-template explanation of why no gate showed it (private
      provenance).
- [x] Change: Prune low-value tests > mechanics list, new bullet directly after the existing
      doctest-teardown bullet (count now 'Eight') - process-test-design/SKILL.md. RED on the
      pre-edit snapshot: NONE. Verified: click 8.5.0 probe in scratch: module with a plain function
      doctest (true) and a @cli.command doctest asserting '1 + 1' -> '3'; 'pytest --doctest-modules
      clim.py' (file named explicitly) -> '1 passed', rc=0 (false example never collected);
      doctest.DocTestFinder().find(clim) -> ['clim.plain'] only;
      DocTestParser().get_doctest(cmd.callback.__doc__, dict(vars(clim)), name, clim.__file__, 0) +
      DocTestRunner over clim.cli.commands -> 'hello 1 TestResults(failed=1, attempted=1)' (the
      introspection runner catches it). Method follows the CURRENT body ('Better: run them',
      enumerate by introspection, fail import-only examples, invoke through the root group with
      obj).
- [x] Dropped as stale or unverified: The hint's 'find them by AST and move the check into a
      CliRunner test' (superseded by the current body: an AST scan misses a command with no
      example), the regex-check snippet, and all private provenance (a consumer project, a project
      template, its test file name, dated counts).
- [x] Gaps declined: a recipe for a CI-side fixture venv planted inside the checkout, and the assert
      shape for an in-process scan (both judgement the rule leaves to the reader; the rule names the
      seam to assert at); whether to keep --doctest-modules for non-Click doctests (unaffected by
      this rule).
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      then the scenarios each review fix touched (9 after the first review, 1 after the second).
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
