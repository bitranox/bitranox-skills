# skill-writer checklist - meta-collect-knowledge (2026-10-05, exit-code unification)

Stage 1 now separates "nothing matched" (exit 0, stop) from `CANDIDATES: 0 (not scanned: <reason>)`, which exits 2 and asks for the reason to be fixed.

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
- [x] Question for this skill: `gather_scan.py` prints `CANDIDATES: 0 (not scanned: no usable keywords from topic)` - exit code, and is it the same as "nothing matched, stop"?
- [x] RED (pre-change excerpt): exit code NONE; yes, the same, quoting "means the same, with the reason".
- [x] GREEN (new excerpt): 2, and no, quoting "`CANDIDATES: 0 (not scanned: <reason>)` exits 2: no scan ran".
- [x] The statement matches the code: `gather_scan._not_scanned` returns 2; pinned by the two not-scanned tests and the control `test_a_scan_that_matches_nothing_still_exits_zero`.
- [x] Both dispatches asked for a `Skill gaps` section. RED listed this question among its
      silent or old answers; GREEN reported none. Diffed in both directions: GREEN lost nothing RED
      produced - every RED answer was the old behaviour or NONE.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
