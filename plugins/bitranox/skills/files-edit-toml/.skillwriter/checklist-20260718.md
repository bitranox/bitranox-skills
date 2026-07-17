# skill-writer checklist - files-edit-toml (2026-07-18, duplicate-key hard-fail)

Change: added a Common-mistakes row - a duplicated key in any TOML table (e.g. two
[project.scripts] or a repeated key) is invalid TOML that hard-fails every parser (tomllib, uv,
ruff), so nothing builds or tests until it is deduped; editing the parsed object avoids it.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: without the row, an agent hand-editing/sed-ing a pyproject can leave a duplicate key and
      then chase a confusing "nothing builds" state, not realizing the TOML itself is invalid
      (fact reference-toml-duplicate-project-scripts).
- [x] GREEN: row names the symptom (every parser hard-fails), the scope (any table, not just
      project.scripts), and the preventive (edit the parsed object, not sed).
- [x] Scope: universal TOML-authoring fact; not project-specific.
- [x] Security scan: prose only, no secrets/hosts/paths.
- [x] CSO description: unchanged (body edit; "validating a TOML file" / "editing pyproject" cover retrieval).
- [x] Token budget: one table row.
