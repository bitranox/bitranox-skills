# skill-writer checklist - meta-memory-settings (2026-10-05, exit-code unification)

The "Use the CLI" bullet for a failed write now says it exits 2 (could not run) rather than 1, and that no verb returns 1. The knob table is unchanged.

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
- [x] Question for this skill: `settings.py set` cannot write its config because `~/.claude` is a plain file - exit code?
- [x] RED (pre-change excerpt): 1, quoting "Exit 1 means the write failed".
- [x] GREEN (new excerpt): 2, quoting "A write that fails ... exits 2 and saves nothing."
- [x] The statement matches the code: `settings._save_and_print` returns 2 on OSError; pinned by `test_set_reports_a_failed_write_and_exits_2` and `test_reset_reports_a_failed_write_and_exits_2`.
- [x] Both dispatches asked for a `Skill gaps` section. RED listed this question among its
      silent or old answers; GREEN reported none. Diffed in both directions: GREEN lost nothing RED
      produced - every RED answer was the old behaviour or NONE.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
