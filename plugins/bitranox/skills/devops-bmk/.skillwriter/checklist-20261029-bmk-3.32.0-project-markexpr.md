# skill-writer checklist - devops-bmk (2026-10-29, a project's own pytest -m is kept, bmk 3.32.0)

Twin sync of bmk's own devops-bmk copy for bmk 3.32.0: the "Test markers" paragraph says how a
project's own `-m` combines with `exclude-markers`. Lines come byte-identical from bmk's copy (the
twin must match).

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - which `-m` `make test` passes for a project
      whose addopts or `PYTEST_ADDOPTS` already carries one, and what `make testintegration` does.
- [x] RED by text check against the pre-change file: no line names `PYTEST_ADDOPTS`, a project's
      own `-m`, or the combined `(<project expr>) and not (<exclude-markers>)` form (grep, no hit).
- [x] Claims checked, each by its own instrument:
      - pytest keeps the last `-m` and ANDs nothing: `_pytest/mark/__init__.py` defines `-m` as a
        `store` option (`dest="markexpr"`); bmk's probe test `env-wins` (addopts `-m slow` plus
        `PYTEST_ADDOPTS="-m 'not slow'"` reads `not slow`) passes against the real pytest.
      - bmk's combine rule: `marker_args` in bmk `src/bmk/adapters/stagerunner/helpers/_parallel.py`,
        used by the coverage stage and every test-all cell; end-to-end tests in
        `tests/test_coverage_parallel.py` (serial and parallel) and `tests/test_matrix.py` run a
        project with addopts `-m 'not slow'` and failing `@slow` and `@integration` tests green, and
        go red with the combine step mutated away.
      - `make testintegration` replaces it: `integration_pytest_argv` in bmk `stagerunner/tools.py`
        appends `-m integration` after the project's addopts.
- [x] GREEN quote-back: rounds 1-3 on haiku and opus, rounds 4-5 on haiku for the clauses those
      fixes touched (one cell per tier per round). Every answer a direct quote: Q1 `(not slow) and
      not (integration)`, Q2 replaced under `make testintegration`, Q3 a `PYTEST_ADDOPTS` `-m` wins
      over the addopts one and its exclusions do not apply. The last round's only NONE (whether
      slow tests run once `PYTEST_ADDOPTS` sets an `-m`) was closed by stating that the addopts
      exclusions do not apply; its re-run derived the answer from that sentence.
- [x] Skill gaps worked: closed - a rendered example, the first sentence pointing at the combine
      rule, single-valued `-m` with its order, who ANDs (bmk, not pytest). Declined - whether a
      shell-exported `PYTEST_ADDOPTS` reaches the run (ordinary environment inheritance), several
      `exclude-markers` (a single marker name, per bmk's `docs/pyproject-reference.md`), the
      fallback when the probe cannot answer (an implementation detail: the plain exclusion), a
      worked example per combination (the rule plus one rendered example covers them), the case
      with no project `-m` (the paragraph's opening sentence).
- [x] Description unchanged - no routing keyword moved.
- [x] Added lines: no address, hostname or machine path; ASCII only; present tense (finder clean on
      the added lines); wrapped at 100 columns.
