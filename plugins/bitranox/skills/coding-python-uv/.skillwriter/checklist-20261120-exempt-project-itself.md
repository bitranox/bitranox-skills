# checklist - exempt the project itself from a cooldown

One queued contribution: a bullet in "Exempting your own packages from a cooldown" saying
`uv pip install <project>` run inside the project's directory obeys that project's `[tool.uv]`,
so the project's own name belongs in `exclude-newer-package` too; the intro now counts three
silent traps and names `uv pip install` beside `uv lock`.

Decisions: d-20261120-d5674bb7

## RED

- [x] Skill decisions read first: none rejected or removed for this section.
- [x] Text check of the pre-edit file: "project ITSELF" 0 hits; the section exempted only the
      transitive closure of own dependencies.

## GREEN

- [x] Quote-back probe (opus, haiku): C1 answered with the new bullet's lines; no NONE.

## REFACTOR

- [x] Declined (haiku): entry syntax - the bullet above shows
      `exclude-newer-package = { <own-pkg> = false }`.
- [x] Evidence is INHERITED from the reporting session's 2026-11-19 measurement; not re-run here
      (uv 0.13.0 installed).
- [x] Width, fence and ASCII checks on the added lines clean.
