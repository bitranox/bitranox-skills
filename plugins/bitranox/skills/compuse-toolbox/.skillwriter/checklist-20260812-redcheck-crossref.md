# skill-writer checklist - compuse-toolbox (cross-reference the `redcheck` tool)

Change: index a newly-shipped tool that lives in a DIFFERENT skill (`process-test-driven-development`)
so this skill's tool table stays the one place that answers "is there already a tool for this?".
No script is added here - see `process-test-driven-development`'s own checklist
(`checklist-20260812-redcheck.md`) for the RED/GREEN work on the tool itself.

## PLAN

- [x] Skill type: reference (tool index with a per-tool rationale). This edit adds a table row,
      a rationale bullet, and a description clause - the same three-part shape every other tool in
      this index uses - but no `scripts/`/`tests/` pair, because `redcheck` ships from
      `process-test-driven-development` (it answers "can a RED/baseline SCENARIO fail", which is
      that skill's discipline, not a computer-use chore).
- [x] Checked it is not already indexed: no existing row answers "can this RED/baseline test
      actually fail" - `claim_check` is the nearest neighbor and answers a different question (is
      text already present in a set of files), not whether an agent would already know the answer.
- [x] Scope: one table row, one rationale bullet, one description clause. No script, no test file,
      no new dependency on this skill's own gate.

## RED

- [x] Retrieval baseline (RED) run via `bitranox:baseline-probe` against the PRE-change table (no
      `redcheck` row) with the user's own words describing the "could this RED prompt secretly be
      unfailable" worry - correctly found nothing in the table and did not force-fit a nearby row.
      (Full transcript and question text live in `process-test-driven-development`'s checklist,
      since the row and the retrieval test are one change split across two SKILL.md files.)

## GREEN

- [x] Retrieval run (GREEN) against the updated table: the agent named `redcheck` on the first
      try, quoted the row's own wording back as the match, filled in the exact invocation, and
      correctly read the "(ships in `process-test-driven-development`, not here)" parenthetical
      as meaning the invoke path is relative to that other skill. No rewrite needed.
- [x] Description clause names the SYMPTOM ("whether a RED/baseline test could ever have failed at
      all"), not the implementation (term-overlap, corpus scanning).
- [x] Table row and rationale bullet follow the established shape (a per-tool bullet under "Why a
      jig over a one-liner", a table row with a real, runnable invocation); table realigned
      automatically by the repo's markdown-table hook after each edit.

## REFACTOR

- [x] Cross-check against the two most recent additions to this same table (`diffbehave`,
      `newest`): same three-part shape (row + bullet + description clause), same "ships in `X`, not
      here" parenthetical style already used for `snortblock` in the (separate, personal) toolbox
      index this promotion retires from.

## Quality

- [x] Present tense, no session narrative, in the skill and in this artifact.
- [x] Frontmatter `description` stays a single-line plain YAML scalar, still trigger-first ("Use
      when..."), still yields well over 3 distinctive keywords after the added clause.

## Deliverables

- [x] `SKILL.md` table row + rationale bullet + description clause (no script/tests - those ship
      in `process-test-driven-development`). `plugin.json` bump, `docs/skills.md` and
      `skill_triggers.json` regeneration, and the `CHANGELOG.md` entry are shared with that
      skill's change and recorded once in this same release.
