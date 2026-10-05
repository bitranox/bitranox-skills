# skill-writer checklist - git-worktrees (2026-10-05, exit-code unification)

Step 3 warns that a worktree nested in the main checkout inherits tool config above it (measured with pyright) and gives the check and the pin; a Common Mistakes entry repeats it. The wtclean exit codes are restated: 1 plan refusals, 2 bad or forbidden `--cache-dir` and failed removals, `ok` false only on 2.

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
- [x] Question for this skill: pyright reports 0 errors in `.claude/worktrees/x` - what to check first? wtclean with a missing `--cache-dir` - exit code?
- [x] RED (pre-change excerpt): NONE; 1.
- [x] GREEN (new excerpt): the loaded config path via `pyright --verbose`, quoted; 2, quoting "refused by name with exit 2, dry run included".
- [x] The statement matches the code: the pyright behaviour reproduced in a scratch tree (parent `pyrightconfig.json` loaded, 0 errors; control without it, 4; `pyright -p .` restores 4); `wtclean.exit_code` and the `kind` field, pinned in `tests/test_wtclean.py`.
- [x] Both dispatches asked for a `Skill gaps` section. RED listed this question among its
      silent or old answers; GREEN reported none. Diffed in both directions: GREEN lost nothing RED
      produced - every RED answer was the old behaviour or NONE.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
