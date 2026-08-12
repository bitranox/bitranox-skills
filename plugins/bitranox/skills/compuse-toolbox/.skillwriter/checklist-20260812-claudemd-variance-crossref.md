# skill-writer checklist - compuse-toolbox (cross-reference the `claudemd_variance` tool)

Change: index a newly-shipped tool that lives in a DIFFERENT skill (`meta-consolidate-claude-md`)
so this skill's tool table stays the one place that answers "is there already a tool for this?".
No script is added here - see `meta-consolidate-claude-md`'s own checklist
(`checklist-20260812-claudemd-variance.md`) for the RED/GREEN work on the tool itself.

## PLAN

- [x] Skill type: reference (tool index with a per-tool rationale). This edit adds a table row, a
      rationale bullet, and a description clause - the same three-part shape every other
      cross-referenced tool in this index uses (`redcheck`, `wtclean`) - but no `scripts/`/
      `tests/` pair, because `claudemd_variance` ships from `meta-consolidate-claude-md` (it
      closes that skill's own Step 1, which prescribes the measurement but shipped no tool).
- [x] Checked it is not already indexed: no existing row splits/hashes/groups CLAUDE.md sections
      or computes a common ancestor. `grep_all` answers a text-search completeness question, not
      this section-level measurement; `git_state --files` classifies tracked/ignored status of
      files you already name, not which sections repeat and where they belong.
- [x] Scope: one table row, one rationale bullet, one description clause. No script, no test
      file, no new dependency on this skill's own gate.

## RED

- [x] No separate PRE-change retrieval dispatch was run: the task brief calls for one required
      retrieval test against the finished row, not a paired RED/GREEN pair of dispatches, so
      "not already indexed" (PLAN, above) is established by reading the existing table rather
      than by a probe transcript. The single dispatch made is recorded under GREEN.

## GREEN

- [x] Retrieval run via `bitranox:baseline-probe` (foreground, `sonnet`, whole current table
      shown verbatim, no tool name given, none of the other skills allowed) with the question:
      "I've got CLAUDE.md files scattered across dozens of repos in my tree, and a bunch of them
      repeat the same sections... Before I go writing a script to split each file into sections,
      hash the bodies, group the duplicates, and figure out which directory the shared version
      should actually live in (the common ancestor of wherever it's duplicated) - is there
      already something in this list that does that? Or should I just write it myself?"
      The agent answered: "Yes - the last row in the table is exactly this: `claudemd_variance`.
      Its 'hand-roll' column reads almost verbatim as your question... It's not installed with
      the base `compuse-toolbox` skill, though - the table notes it 'ships in
      `meta-consolidate-claude-md`, not here'... Given that this does section-splitting, hashing,
      grouping, and common-ancestor computation - the exact three things you described wanting to
      hand-roll - I'd use it as-is rather than writing your own." It quoted the row's own wording
      back as the match, correctly read the "ships in X, not here" parenthetical as meaning the
      script is invoked relative to that other skill, and named the owning skill
      (`bitranox:meta-consolidate-claude-md`) to pull in. No rewrite needed.
- [x] Row is written in the USER'S NOUN, not the mechanism: it opens on "which sections are
      duplicated across my CLAUDE.md files, and where should they live?" rather than on hashes,
      variants, or ancestor arithmetic - confirmed by the probe echoing that exact phrasing back
      as its reason for the match.
- [x] The Invoke column carries a REAL runnable value (`--root ~/src`), not a placeholder
      metavariable, matching the convention the other rows follow.
- [x] Description clause names the SYMPTOM (hand-splitting, hashing and grouping sections, then
      guessing the common ancestor), not the implementation.

## REFACTOR

- [x] Cross-checked against the two most recent additions to this same table (`redcheck`,
      `wtclean`): same three-part shape (row + bullet + description clause) and the same
      "ships in `X`, not here" parenthetical style.
- [x] Did not inflate any "N tools ship in compuse-toolbox" count sentence - none exists in this
      skill's SKILL.md or the generated docs today; nothing needed removing or updating.

## Quality

- [x] Present tense, no session narrative, in the skill and in this artifact.
- [x] Frontmatter `description` stays a single-line plain YAML scalar, still trigger-first ("Use
      when..."), still yields well over 3 distinctive keywords after the added clause.
- [x] Table realigned by the repo's markdown-table hook after the edit; ASCII only.

## Deliverables

- [x] `SKILL.md` table row + rationale bullet + description clause (no script/tests - those ship
      in `meta-consolidate-claude-md`). `plugin.json` bump, `docs/skills.md` regeneration, and the
      `CHANGELOG.md` entry are shared with that skill's change and recorded once in this same
      release. `skill_triggers.json` checked - already in sync.
