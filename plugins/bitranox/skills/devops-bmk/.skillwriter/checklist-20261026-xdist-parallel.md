# skill-writer checklist - devops-bmk (2026-10-26, parallel pytest via pytest-xdist, bmk 3.29.0)

Twin sync of bmk's own devops-bmk copy at b787f4e. New text: the `make test` pytest stage runs in
parallel when the project's pytest loads pytest-xdist and pytest-cov (`workers`,
`BMK_TEST_WORKERS`, `xdist_group`, the `coverage report` floor step); `test-all` cells run xdist
only; `shellcheck` and the rest of the order-40 list; pyright's platform runs start together, the
first alone under `PYRIGHT_PYTHON_FORCE_VERSION` / `PYRIGHT_PYTHON_USE_BUNDLED_PYRIGHT`, with a
defined run order deciding the exit code.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - which setting, which plugin, which count,
      which exit code, answered from the text.
- [x] RED by text check against the pre-change file: no line names pytest-xdist,
      `BMK_TEST_WORKERS`, `xdist_group` or `PYRIGHT_PYTHON_FORCE_VERSION`.
- [x] Claims checked against bmk's source at 6b01068 (11 claims, an opus verifier citing file and
      line): 4 true, 7 partly wrong. bmk corrected all 7 in its own copy (de7ddae) and the twin
      re-merged from there; nothing was corrected in the twin alone:
      - test-all cells do not run "as in `make test`": xdist only, no coverage, no floor
        (helpers/_parallel.py); `auto` is CPU count // cells, an explicit count reaches every cell.
      - plugins are judged by what pytest LOADS, not what is installed; the hint names the package
        that is not installed; an installed-but-unloaded plugin gives a serial run and no hint.
      - the floor is checked once by `coverage report` (`--cov-fail-under=0` on the parallel run),
        `fail_under` defaults to 80, and JSON mode shows only the exit line.
      - the order-40 list was missing `ruff_format_check` and `psscriptanalyzer`.
      - the pyright stage takes the exit code of the first failing run by list order, not the
        first to finish (actions.py: "the first failing run in ARGV order decides the code").
- [x] GREEN by quote-back on the corrected text (opus at effort medium, plus haiku; 8 questions
      each): every answer a direct quote, no NONE, no contradiction. All 8 quotes found in
      SKILL.md by quotecheck, one call per quote; a planted invented sentence came back MISMATCH.
- [x] Gaps, each decided:
      - "platform order" was undefined (both tiers) - CLOSED in bmk b787f4e from project.py
        pyright_runs: "each OS in the order `[tool.ci].os` first names it (or the one pinned run),
        then the `pyrightconfig.<platform>.json` arms".
      - the bold lead said "once the project declares pytest-xdist" while the body needs both
        plugins to load (opus) - CLOSED in bmk b787f4e: "loads pytest-xdist and pytest-cov".
      - whether the order-40 list is exhaustive, and how same-order stages run relative to each
        other - DECLINED: the sentence says "ALL order 40"; scheduling within an order is an
        implementation detail the probe-planting advice does not depend on.
      - hint behaviour in text mode - DECLINED: text mode streams every stage, so the hint shows.
      - `auto` when `test-all` runs its cells serially - DECLINED, covered: "CPU count // cells"
        with one cell running at once.
      - whether `BMK_TEST_WORKERS` reaches the cells - DECLINED, covered: it overrides the count,
        and "an explicit count goes to EVERY cell unchanged".
      - the integer exit code of a failing pyright run - DECLINED: pyright's own code, passed on.
- [x] Re-probe on the final text by quote-back (opus at effort medium, plus haiku; 3 questions on
      the two fixes): both tiers answer all 3 correctly with direct quotes (serial run, hint names
      `pytest-cov`; runs Windows, Linux, then the `pyrightconfig.linux.json` arm; the Linux run's
      code although it finishes last). quotecheck: 3 of 3 quotes OK, a planted control MISMATCH.
      Remaining notes are the declines above, details the excerpt omitted on purpose (no
      `[tool.ci].os`, the `<workers>` count, both covered elsewhere in SKILL.md), or pyright's own
      behaviour.
- [x] Tiers: GREEN opus + haiku, re-probe opus + haiku - 4 cells.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added; ASCII only; present tense, no
      version-history phrasing in the added lines. Lines over 100 characters come byte-identical
      from bmk's copy and stay (the twin must match).
