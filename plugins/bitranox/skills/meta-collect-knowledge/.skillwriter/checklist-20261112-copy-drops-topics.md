# meta-collect-knowledge: a copied body leaves its `topics:` line behind

Scope: one bullet added to Stage 3 of `SKILL.md`, under the three import rules: every COPY made
with engine `add` drops a `topics:` line from the copied body's frontmatter first, and is tagged
afterwards with `set-topics` if this tree's list fits it. Nothing else in the skill changes.

## Step 0b

- [x] `skill_decisions.py show meta-collect-knowledge --kind rejected,removed --full` and
      `skill_decisions.py show meta-collect-knowledge`: the skill has no ledger entries.
- Decisions: none - documents an engine refusal the Stage 3 copy runs into; adds no rule a later
  editor could reverse without the engine changing first

## Accuracy against the engine

- [x] `memory_engine.py` `TopicsOnCreate`: `add` that creates a fact refuses a body whose
      frontmatter carries a `topics:` line, exit 2, nothing written. Pinned by
      `test_add_refuses_a_new_fact_whose_frame_carries_a_topics_line` in the hooks suite.
- [x] Topics are tagged against one tree's closed list (`<anchor>/.claude-memory/topics.json`),
      so a line from another tree names that tree's list; the cross-tree `relocate` drops it for
      the same reason (`relocate_entry`, `_without_topics_line`).
- [x] `set-topics` is the verb that tags a fact; `topics-show` lists the tree's list.

## RED / GREEN

Scenario: a fact imported from ANOTHER tree, body frontmatter `topics: [python, uv]`, about to be
written with `add --body-file`. Q1: what happens to the line before `add`; Q2: how the copy gets
topics in this tree; Q3 (GREEN control): a same-tree copy with a `topics:` line. Each answer with a
direct quote of the governing text or NONE. Text-only probes, the Stage 3 excerpt pasted in.

- [x] RED (`opus` and `haiku`, pre-edit Stage 3, 2 cells): both answered Q1 and Q2 with NONE.
      `haiku` kept the line ("I would leave the `topics: [python, uv]` line alone"); `opus`
      dropped it as its own extension of the no-cross-tree-link rule and could not name the verb
      that tags the copy.
- [x] GREEN (`opus` and `haiku`, new Stage 3, 2 cells): both dropped the line before `add` and
      quoted "**Every COPY:** drop a `topics:` line from the copied body's frontmatter before
      engine `add`"; both quoted "Tag the copy afterwards with `set-topics` if this tree's list
      fits it" for Q2; both gave the same-tree copy the same treatment (Q3).
- [x] GREEN against RED in both directions: nothing the RED answers held is missing from GREEN.

## Skill gaps the probes reported

- How "fits" is judged and the `set-topics` syntax: DECLINED, owned by the storage reference.
  `meta-self-improve/references/memory-backend.md` documents `topics-show` (the tree's list with
  a meaning per topic) and the `set-topics` row with its flags; the bullet names the verb.
- A block-style `topics:` list (a key followed by `- python` lines): DECLINED, the engine writes
  only the inline form: `topic_placement.py` `format_topics` returns `[a, b]`, and `set-topics`
  is the only verb that sets the line.
- A LIFT made with `add`: DECLINED, covered. A lift moves the fact (`move`, the body untouched),
  and an `add` of an existing slug is an update, which keeps the stored line
  (`memory-backend.md`, "Store format": "An `add`, `amend-pinned` or factedit `apply` that
  updates the fact keeps what is stored").
- What "labeled" means for a cross-tree copy: DECLINED, covered elsewhere in the skill, the
  per-tree `TREE:` labels of the candidate list (`SKILL.md` checklist line "Stage-1 candidate
  list with per-tree `TREE:` labels") and the rationalization row "The labels are the
  boundary-crossing audit trail".
- The bullet's two reasons, one of which applies only cross-tree: DECLINED, the `opus` GREEN
  cell read both correctly ("The other reason, that `add` refuses such a body, still does") and
  applied the rule to the same-tree copy.

## Checks a probe cannot see

- [x] Width and fence check over the added lines: nothing reported.
- [x] The paragraph after the insertion point (step 4, the privacy scrub) reads as before.
- [x] Tables canonical: `reformat_tables.py --check SKILL.md` reports it unchanged.
- [x] History finder over the added lines: no version-history wording.
- [x] ASCII only; no host, private path or project name; the example values are `python`, `uv`.
