# skill-writer checklist - compuse-git (2026-07-25, add-git-state-tool)

Change: ship `scripts/git_state.py` (+ `tests/`) with compuse-git and add a "## Tools" section
referencing it. The skill already teaches the by-hand pre-commit / pre-push state check
(`git branch --show-current`, `git rev-list --left-right --count HEAD...@{upstream}`,
`git status --short`); the tool automates exactly those checks across one or many repos, read-only,
and exits non-zero if any repo is out of sync (doubles as a bulk pre-push guard). Lifted from a
proven machine-local toolbox tool; docstring scrubbed of machine-specific references.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: compuse-git documented the pre-commit state checks only as hand-typed git commands, with
      no runnable tool - so a multi-repo pre-push sweep (fleet work) meant re-typing status/rev-list
      per repo, the recurring chore the local toolbox `git_state` already solved.
- [x] GREEN: ships `scripts/git_state.py` (import-safe: pure `parse_branch_status`/`git_state`/
      `find_repos` + a thin argparse CLI under `__main__`) and `tests/test_git_state.py` +
      `tests/conftest.py`; `uv run --with pytest pytest tests/` = 6 passed. A "## Tools" section
      documents it with `uv run scripts/git_state.py` examples.
- [x] Scope: shared/general - any git user doing a pre-commit/pre-push or multi-repo sync check;
      no bitranox-specific content (docstring scrubbed to a generic "before a risky commit" why).
- [x] Security scan: read-only (`git status --porcelain=v2 --branch`); `subprocess.run` with an
      argv list, never `shell=True`; no secrets/hosts/paths/PII; cross-platform (pathlib-free walk,
      argv list, stdlib only, PEP 723 header, no deps).
- [x] CSO description: unchanged (body + bundled-tool addition, frontmatter untouched, so the
      trigger map needs no rebuild).
- [x] Token budget: one "## Tools" section (~8 lines) added to a reference skill; body stays lean.
- [x] Exec bit: git_state.py is interpreter-run (`uv run`/`python`), not `./`-invoked, so it stays
      100644 - no `git update-index --chmod=+x` needed.
