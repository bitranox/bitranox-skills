# skill-writer checklist - devops-bmk (2026-07-16, document bmk 3.11.0 test-all + clean-all)

- [x] Change: documented two new bmk 3.11.0 make targets - `make test-all` (per-version pytest+pyright matrix) and `make clean-all` (purge every `.venv*`); added the classifier-drives-test-all note and updated the clean/gitignore note to the single `.venv*` glob
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED baseline: sonnet subagent asked how to reproduce CI's per-version matrix locally + purge per-version venvs against the pre-edit skill - found "not documented" for both (searched for `make test-all` explicitly, absent)
- [x] GREEN: same question against the edited skill - subagent named `make test-all` and `make clean-all`, described each correctly, and reported the no-classifier WARNING-once behavior
- [x] Description unchanged (no CSO/trigger-map rebuild needed; frontmatter untouched, so the router map stays in sync)
- [x] Mirror kept byte-identical with the bmk repo copy (skills/devops-bmk/SKILL.md); tell-sweep clean (ASCII only, no typographic tells)
- [x] Security scan: prose/table doc edits only - no secrets, credentials, hostnames, paths, or code changes
