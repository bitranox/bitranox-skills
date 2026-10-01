# skill-writer checklist - devops-bmk (2026-10-01, test-all worker cap)

Change: synced SKILL.md with bmk 3.18.0, which adds a per-project cap on `test-all`'s parallel
version cells (`[tool.scripts.test-all] workers` in `pyproject.toml`, or `BMK_TEST_ALL_WORKERS`
for one run), for a project whose suite binds fixed ports or shares a test database.

- [x] Source: regenerated verbatim from the repo twin, apps/utils/bmk/skills/devops-bmk/SKILL.md,
      at bmk commit 4101a80 (docs(make-targets): test-all is parallel unless the project caps it).
      No by-convention divergence to re-apply for this pair (name/H1/self-install all already match).
- [x] Verified against the merged bmk source: `_matrix.py` reads the workers cap from both the
      pyproject table and the env var, and `tests/test_matrix.py` covers it; `make test` on bmk
      passed before this sync (RC=0).
- [x] `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` reports 0 of 10 pairs drifted after
      this change.
- [x] Scope: shared - bmk ships publicly via uvx, and this is bmk's own target-table/mental-model
      documentation.
- [x] Security scan: no paths, hosts or credentials; only a pyproject table name and an env var name.
- [x] CSO description: unchanged.
- [x] Token budget: reference skill; replaced two paragraphs with their updated twin, no net growth
      beyond the repo side's own wording.
