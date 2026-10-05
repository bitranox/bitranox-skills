# skill-writer checklist - meta-skill-audit (2026-10-05, exit-code unification)

A target with no report now exits 2 (its reviewer could not run) and the run never returns 1; `script_prepass.py --json` is the `{ok, command, data, skipped}` envelope; the shim's mistyped-path exit is stated as 2 (the run-python.sh change lands with group D-8).

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The test is a retrieval scenario: eleven questions over the eight
      SKILL.md files this change touches, each answered with a DIRECT QUOTE of the governing text
      or the single word NONE. The question for this skill is quoted below.
- [x] Arms pinned to the least inferential tier (haiku) on the inert `bitranox:baseline-probe`
      type, the old and the new excerpts (the changed hunks with wide context) pasted, Skill
      invocation forbidden, so neither arm could answer from the installed copy.
- [x] `redcheck --corpus-cascade` over the worktree flagged INHERITED COVERAGE on shared terms
      that are function words of the memory index (coverage, envelope, findings, marketplace),
      not the lesson; the route taken is the text check of the artifact - quote-back of the
      excerpt - which inherited context cannot satisfy, and RED did not answer from it.
- [x] Question for this skill: A reviewer timed out (`REPORT MISSING:`) - exit code of the run? And the shape of `script_prepass.py --json`?
- [x] RED (pre-change excerpt): 1; shape NONE.
- [x] GREEN (new excerpt): 2, quoting "2 at least one has none"; `{ok, command, data, skipped}`.
- [x] The statement matches the code: `audit_skills._sweep` returns 2 on a missing report; `script_prepass._envelope`; pinned in `tests/test_audit_cli.py` and `tests/test_script_prepass_checks.py`.
- [x] Both dispatches asked for a `Skill gaps` section. RED listed this question among its
      silent or old answers; GREEN reported none. Diffed in both directions: GREEN lost nothing RED
      produced - every RED answer was the old behaviour or NONE.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
