# skill-writer checklist - devops-bmk (2026-09-02, proving a gate actually enforces)

Change: one section naming the two readings of a green `make test` that are wrong - `ruff --fix`
running before every checker, and an undeclared tool NOT meaning its stage was skipped.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED route: COVERAGE CHECK AGAINST THE FILE. Pre-change, a grep for `ruff_fix_apply`,
      `stage order` and `prepend_tool_bin` over SKILL.md returned 0 hits.
- [x] VERIFIED against the installed bmk source, not quoted from the report that prompted it:
      `registry.py` has `Stage("ruff_fix_apply", 30, ...)` and `bandit`, `lint_imports`,
      `pip_audit`, `pyright`, `pytest`, `ruff_lint` all at 40.
- [x] The second claim verified the same way: `context._prepend_tool_bin_to_path` puts bmk's own
      venv bin dir first on the child PATH (its docstring states the intent - pin stages to bmk's
      own toolchain), and `lint_imports_argv` returns a bare `["lint-imports"]`.
- [x] This matters because the WRONG reading of (2) produced a defect ticket against a gate that
      was working. The section says so as a directive (do not file against a stage on the theory
      that it was skipped) rather than as a story.
- [x] Scope: shared - bmk ships publicly via uvx, and all of it is bmk's own stage table.
- [x] Security scan: source symbols and integers only; no paths, hosts or credentials.
- [x] CSO description: unchanged.
- [x] Token budget: reference skill; one section, and it cross-references process-test-design
      rather than restating the gate-must-fail rule.
