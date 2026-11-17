# Review checklist - the gate's interpreter, and a CHANGELOG line for raised runtime floors (2026-11-17)

Change: two additions, from two queued contributions. (A) Section "The project venv `.venv`" gains
a paragraph: with a Python minor declared, `UV_PYTHON` does not choose the interpreter a gate runs
on (bmk hands uv the highest declared minor as an explicit `--python` and rebuilds a `.venv` on
another minor); with no classifier uv's default, `UV_PYTHON` included, decides a missing `.venv`;
gate another minor with `make test-all` or CI; name the interpreter a local gate ran on
(`.venv/bin/python -V`). (B) Section 3 gains a bullet after "Gate the bumped tree": a raised
runtime floor needs a CHANGELOG line and bmk writes none; a one-line `tomllib` comparison of
`[project].dependencies` against the last tag prints the changed requirements. Frontmatter
unchanged.

## PLAN
- [x] Skill type: reference. Test: a text coverage check of the pre-edit file (RED) and a
      quote-back on the edited text on two tiers (GREEN).
- [x] Ledger read (`skill_decisions.py show devops-bmk`): no rejected or removed entry is reversed.

## RED
- [x] Coverage check on `git show HEAD:` SKILL.md: no `UV_PYTHON` apart from
      `UV_PYTHON_PREFERENCE`, and no rule tying a runtime floor raise to a CHANGELOG line.

## GREEN
- [x] Mechanism A read in the bmk 3.33.3 source: no `.py` under `src/bmk` names `UV_PYTHON`;
      `desired_python_minor` returns the last of `all_python_minors` (classifiers, numeric order);
      `_create_venv` runs `uv venv --python <minor>`, `_sync_from_lock` runs
      `uv sync --locked --python <minor>`; `discard_venv_on_wrong_python` removes a venv on another
      interpreter; `_matrix.py` provisions `.venv-<minor>` per `test-all` cell.
- [x] uv precedence measured on uv 0.13.0: `UV_PYTHON=3.14 uv venv --python 3.15` built 3.15.0,
      the same without `--python` built 3.14.8.
- [x] Mechanism B read in the source: only `_bump_version.update_changelog` writes `CHANGELOG.md`
      (the heading rename plus a fresh `[Unreleased]`).
- [x] The shipped command, extracted verbatim and run read-only in the bmk checkout: against the
      last tag v3.33.3 no output, rc 0; against v3.30.0 20 lines (a `-` and a `+` per changed
      requirement, the `pydantic >=2.14.1 -> >=2.14.3` example among them); empty stdin (no tag)
      fails with `KeyError: 'project'`, as the text says.
- [x] Quote-back, opus (effort medium) and haiku, 6 questions each, two rounds. Round 1 gaps, all
      closed in the text: the no-classifier case unstated (both tiers), the bold lead over-broad
      (opus), no command for a `test-all` cell's interpreter (haiku), the untagged repo (both).
      Round 2 on the final text: every answer a direct quote, including the dev-extra control
      (the command prints nothing, no line owed).

## REFACTOR
- [x] Premises qualified, not false: "never reads UV_PYTHON" holds for bmk, but with no
      classifier uv honours the variable when bmk creates a missing `.venv` (now stated);
      "every bmk-invoking target" narrowed to "every env-touching `make`".
- [x] Gaps declined: wording for an added, dropped or lowered requirement (judgement left open);
      which targets are env-touching (stated in the same section); an untagged repo (nothing
      released to compare against); `[project].optional-dependencies` floors (declined by the
      integrator: bitranox projects keep their dev tools in an extra there, so covering extras
      would demand a CHANGELOG line for every dev-tool floor the refresh moves).
- [x] Width and fence check over the 27 added lines: nothing reported; ASCII only; no private
      host, path or history wording added.
- [x] Decisions: d-20261117-b5aff024, d-20261117-7e3eb609
