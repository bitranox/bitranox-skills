# skill-writer checklist - meta-claude-hooks (2026-10-05, exit-code unification)

"Maintaining this skill" states `hookdoc_stamp.py`'s exit codes, including 2 for a refused stamp and for BROKEN whatever `--expect` said; the reference baseline line is refreshed with the re-stamp. `references/events.md` SubagentStart notes that the event carries no prompt and that `agent_type` can hold a named dispatch's NAME.

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
- [x] Question for this skill: `stamp --write` refuses because coverage has gaps - exit code?
- [x] RED (pre-change excerpt): NONE.
- [x] GREEN (new excerpt): 2, quoting "refuses (exit 2) while coverage has gaps".
- [x] The statement matches the code: `hookdoc_stamp._check_exit`, the stamp and baseline refusals returning 2, and `_broken`; pinned in `tests/test_hookdoc_stamp.py`. The SubagentStart note rests on two transcripts on CLI 2.1.289: a named Explore dispatch recorded `SubagentStart:<name>`, a named general-purpose dispatch recorded `SubagentStart:general-purpose`.
- [x] Both dispatches asked for a `Skill gaps` section. RED listed this question among its
      silent or old answers; GREEN reported none. Diffed in both directions: GREEN lost nothing RED
      produced - every RED answer was the old behaviour or NONE.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
