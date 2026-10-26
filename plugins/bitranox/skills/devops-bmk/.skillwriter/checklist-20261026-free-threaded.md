# skill-writer checklist - devops-bmk (2026-10-26, test-all free-threaded cells)

`make test-all` gains a free-threaded cell per `[tool.ci] free-threaded` entry (bmk 3.28.0). A new
paragraph after the test-all paragraph states where the cells come from, the venv name, the cell
order, that `make test` is unaffected, the three refusals (exit 2, before anything installs) and
the warning-only missing Free Threading classifier, with a TOML example carrying both classifiers.
The targets-table row names the extra cell; its shorter cell re-pads the table to canonical form.
One line of the preceding paragraph over 100 characters is rewrapped (words unchanged).

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - which key, which value, what is refused and
      with what exit code, answered from the text.
- [x] Claims checked against bmk's source at the commit that adds the behaviour, not against the
      request text: the array refusal, the `"X.Y"` and declared-version refusals, exit 2, the
      warning that lets the run go on, and the cell order (`matrix_cells`: "each declared minor,
      its free-threaded build right after it"), plus the `.venv-<request>` naming.
- [x] RED by text check against the pre-change file: no line describes `[tool.ci] free-threaded` or
      a free-threaded test-all cell (its two `free-threaded` hits concern recreating a venv with
      `X.Yt`, a different subject).
- [x] GREEN by quote-back on the edited text (opus at effort medium, plus haiku; 7 questions each):
      every answer a direct quote, no NONE, no contradiction.
- [x] Gaps, each decided:
      - "right after the regular one" read as an execution order while cells run in parallel -
        CLOSED: "next after the regular cell in the cell order".
      - whether the run continues without the Free Threading classifier - CLOSED: "only prints a
        WARNING; the run goes on".
      - whether the `X.Yt` cell runs pyright - CLOSED: "(pytest + pyright, like every cell)".
      - the example omitted the classifier its own refusal rule requires, and gave no `<level>` -
        CLOSED: the TOML example carries the `3.15` classifier and `Free Threading :: 2 - Beta`.
      - how the free-threaded interpreter is obtained - DECLINED, covered elsewhere: SKILL.md
        "Before those commands bmk runs `uv python install <X.Y>` and `uv python upgrade <X.Y>`."
      - the overall exit when a cell fails - DECLINED, covered elsewhere: SKILL.md "Key on the bmk
        line, not on make's exit code."
      - how to turn parallelism off - DECLINED, covered elsewhere (outside the probe excerpt):
        "`[tool.scripts.test-all] workers = 1`".
      - the full list of valid `<level>` values and how the warning matches the classifier -
        DECLINED: the levels are PyPI's trove list, the matching an implementation detail.
- [x] Re-probe on the final text by quote-back (opus at effort medium, plus haiku; 5 questions on
      every fix): every answer a direct quote, no NONE; the remaining notes are the declines above.
- [x] Tiers: GREEN opus + haiku, re-probe opus + haiku - 4 cells.
- [x] Description unchanged - no routing keyword moved. Tables canonical
      (`reformat_tables.py --check --strict`).
- [x] No address, MAC, hostname or machine path added; ASCII only; present tense, no
      version-history phrasing in the added lines.
