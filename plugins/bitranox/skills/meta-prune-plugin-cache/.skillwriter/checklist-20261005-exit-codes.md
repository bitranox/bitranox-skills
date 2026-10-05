# skill-writer checklist - meta-prune-plugin-cache (2026-10-05, exit-code unification)

"Use the tool" gains the exit-code paragraph (2 for an I/O-failed removal, 2 wins), the one-entry-per-alias rule and the per-entry `reason_code`; the `--json` comment states `ok` is false only on exit 2.

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
- [x] Question for this skill: `--apply` where one removal fails with Permission denied - exit code? A symlinked marketplace reaching 3 versions - how many REFUSED entries, which field names the kind?
- [x] RED (pre-change excerpt): 1; entries NONE; field NONE.
- [x] GREEN (new excerpt): 2; one entry, as the alias; `reason_code`.
- [x] The statement matches the code: `pluginprune.exit_code`, `_one_entry_per_alias`, `classify_refusal`; pinned by `test_one_symlinked_marketplace_is_reported_once_with_a_reason_code`, `test_a_refusal_alone_exits_1_and_a_failure_wins_with_2` and the apply-failure tests.
- [x] Both dispatches asked for a `Skill gaps` section. RED listed this question among its
      silent or old answers; GREEN reported none. Diffed in both directions: GREEN lost nothing RED
      produced - every RED answer was the old behaviour or NONE.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
