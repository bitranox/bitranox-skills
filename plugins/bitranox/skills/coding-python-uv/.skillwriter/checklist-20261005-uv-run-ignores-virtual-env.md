# skill-writer checklist - coding-python-uv (2026-10-05, uv run ignores foreign VIRTUAL_ENV, D-4/D-11)

New paragraph in the "stray VIRTUAL_ENV" gotcha: inside a uv project, `uv run` ITSELF ignores a
foreign `VIRTUAL_ENV` (only warns, uses `.venv`); it honours the variable only with `--active`/
`--no-project`, or outside a project. The `env -u VIRTUAL_ENV` prefix stays recommended for the
other affected tools (`pip-audit`, `tox`, `nox`, Makefile targets).

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - one question answered with a direct quote
      or NONE.
- [x] RED (pre-change text, pasted): "Inside a uv project, does a foreign `VIRTUAL_ENV` make
      `uv run pytest` use the wrong interpreter?" - NONE; the old text lists `uv` among the tools
      a stray `VIRTUAL_ENV` "leaks into", with no exception stated.
- [x] Reproduced directly on the pinned uv version (0.11.15): `VIRTUAL_ENV=<foreign venv> uv run
      python -c "import sys; print(sys.executable)"` inside a scratch uv project printed a
      warning ("does not match the project environment path `.venv` and will be ignored") and
      resolved to the project's OWN `.venv/bin/python`; the same command with `--active` resolved
      to the FOREIGN venv's interpreter, confirming both halves of the claim.
- [x] GREEN (new paragraph pasted): same question now answers with a direct quote ("it IGNORES a
      foreign `VIRTUAL_ENV`, only warns, and uses the project's own `.venv`").
- [x] GREEN diffed against RED in both directions: nothing removed, one gap closed; the
      `env -u VIRTUAL_ENV` advice for the OTHER tools is kept, not contradicted.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
