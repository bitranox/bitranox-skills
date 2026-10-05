# skill-writer checklist - meta-adopting-external-skills (2026-10-05, exit-code unification)

Step 2 names a new gate outcome, LICENSE GATE: CANNOT READ (an unreadable license file, an unlistable dir, a pyproject license table with no tomllib), exit 2, distinct from NO LICENSE FOUND (exit 1), and says to fix the read rather than research the license.

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
- [x] Question for this skill: The source's license file cannot be opened (permission denied) - what does the gate report, what exit code, and should you research the license online?
- [x] RED (pre-change excerpt): NO LICENSE FOUND, exit 1, research online.
- [x] GREEN (new excerpt): CANNOT READ, exit 2, do not research, quoting "fix the read and rerun rather than researching the license".
- [x] The statement matches the code: `adopt_skill.CannotRead` and the `unreadable` status in `find_license`, raised as AdoptError (exit 2) by `_gate`; pinned by the four CANNOT READ tests in `tests/test_adopt_skill.py`, including the reject-wins and absent-wins controls.
- [x] Both dispatches asked for a `Skill gaps` section. RED listed this question among its
      silent or old answers; GREEN reported none. Diffed in both directions: GREEN lost nothing RED
      produced - every RED answer was the old behaviour or NONE.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
