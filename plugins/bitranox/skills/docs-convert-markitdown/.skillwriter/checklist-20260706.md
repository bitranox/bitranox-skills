# skill-writer checklist - docs-convert-markitdown (2026-07-06, roster review wave 1)

- [x] Change: stripped 4 unsupported frontmatter keys; added the verified attribution (credit line + THIRD_PARTY_NOTICES entry: K-Dense-AI/claude-scientific-skills, MIT, verbatim copyright via GitHub API); swept 44 non-ASCII glyphs from scripts/references ([OK]/[FAIL]/[WARN], ASCII tree art) with tests still green (28 passed, 7 skipped); replaced Next Steps with a routing table (links the previously orphaned assets/example_usage.md); rewrote the version-migration section as current-state API notes. Deferred (maintainer decision): dropping the out-of-scope generate_schematic*.py diagram scripts.
- [x] Receipt held (skill_receipt.py, this session)
- [x] Review: read-only opus subagent audit, verified against the files by the applier
- [x] Discovery test: fable subagent, scenario picked this skill from a 12-candidate list (wave 6/6)
- [x] Security scan: prose/frontmatter edits, no secrets/paths/PII

# skill-writer checklist - docs-convert-markitdown (2026-07-06, schematics extraction)

- [x] Change: schematic-generation scripts, their tests, and conftest fixtures extracted to docs-generate-schematics (user decision); the disclaimer note is gone because the out-of-scope code is gone.
- [x] Receipt held (skill_receipt.py, this session)
- [x] Tests: docs-generate-schematics 28 passed; markitdown suite unchanged semantics (importorskip design)
- [x] Catalog + trigger map regenerated (57 skills)
- [x] Security scan: file moves + new SKILL.md, no secrets (API key referenced by env-var name only)
