# meta-self-improve: document placement by topic, the block cap and pruned level dirs

Scope: `references/memory-backend.md` (the tree-unique bullet, the end of "Store format", the
`add` semantics paragraph, the engine command table), the conflict-kind list of `ref_map.py` in
`SKILL.md`, and the topic paragraph, command table and consistency-audit paragraph of the
repository's `docs/reference.md`. The table formatter re-padded the command table of
`memory-backend.md` because the new row widened a column (whitespace only).

## What changed

- The sentence "Topics are data for now: no pointer line is placed by them yet." is replaced by
  a section on a fact placed by topic: what makes a fact placed, where `render-topics` puts its
  lines, both scopes, its output, its dry run (no lock, no write) and its refusals.
- The block cap: 1048576 bytes per level's block, what counts, the routes a refusal names, the
  `--check-tree` line, and that `move` and `relocate` hold their target to it.
- What every writer does with a placed fact: the `set-topics` bind refusals with their repairs,
  the un-bind collapse to the tree top and its cap refusal, `add` from a level without a line,
  `add --pin`, `move`/`relocate` refusing, `rename`/`retitle` changing every line, `--archive`
  dropping every line and its failure-midway repairs.
- The tree-unique bullet names the exception for a placed fact's per-level lines.
- `add`, `set-scope`, `move` and `relocate` refuse a level under a pruned directory: the one
  name rule `uuid_store.is_non_level_dirname`.
- Table rows: a new `render-topics` row; `set-topics` refusal list gains the bind refusals and
  the collapse cap; `move`, `relocate`, `rename`, `retitle`, `--check`, `--check-tree` and
  `--archive` rows each say what they do with a placed fact.
- `SKILL.md`: the `ref_map.py --moves` conflict kinds gain `placed-by-topic` and
  `duplicate-pointer`, both printed by `ref_map.py` and missing from the list.

## Step 0b

- [x] `skill_decisions.py show meta-self-improve --kind rejected,removed --full`: one rejected
      entry (d-20261106-4cb9268c, name-based misplacement signal). Unrelated.
- [x] `skill_decisions.py show meta-self-improve`: five live rules; the one in this file
      (d-20261110-7778c924, `title:` field) keeps its anchor sentence word for word.
- [x] `skill_decisions.py check` after the edit: 0 findings.
- Decisions: d-20261112-97039917, d-20261112-6e43d9f0, d-20261112-2b8720d0, d-20261112-3d2d2a0c

## Accuracy against the code (throwaway trees, each command a CLI run from outside the tree)

- [x] `render-topics --scope tree`: per-level `+N added, N refreshed, -N removed` lines and
      `render-topics (tree): 1 managed fact(s); changed 3 level(s)`; again `changed 0 level(s)`;
      `--dry-run` prints `would change` and wrote nothing; `--json` one object.
- [x] `render-topics --scope chain` from a level: dropped the lower copy of a line the top also
      held, left the sibling's line; repaired the `--check` repeated line.
- [x] No topic list: `no topic list in this tree: nothing is placed by topic`, exit 0. A bad
      `--scope`: argparse error, exit 2.
- [x] `BITRANOX_MEMORY_WRITES=off`: dry run exit 0, real run refused exit 2.
- [x] A `TOPICS:` line that does not parse: `! refused: <level>: its TOPICS line does not parse
      (...); set-level-topics replaces it`, exit 2, the dry run too.
- [x] A top with no pointer block: refused naming `ensure-memory-structure`; after running it the
      render passed.
- [x] Cap: 1100 large lines placed at one level refused (dry run too) naming the
      `set-topics --batch` rebind; `--check-tree` printed `! the placement by topic could not be
      checked: ...`, exit 1. `move` onto a full top refused (`would leave its block at ...`). A
      cross-tree `relocate` onto a full top refused with the same text, nothing moved.
      Un-binding 100 facts onto a full top refused (dry run too) with the collapse message.
- [x] Bind refusals (`set-topics --topics`): no `title:` names `heal --backfill-titles`; a line
      that differs from the body names `factedit.py apply --hook-file`; both exit 2, dry run
      too. The no-`description:` and legacy-pointer texts read in `_line_problem`.
- [x] Un-bind: `--clear`, `--universal` and a batch row `[]` each left one line at the top with
      the `~ note:` line (`each would keep one line` on the dry run).
- [x] `add` from a level without a line refused naming the levels; `add --pin` refused naming
      `set-topics --clear`; `add` from a level with a line updated it and `--check-tree` was clean.
- [x] `move` and `relocate` of a placed fact refused with the `_PLACED_BY_TOPIC` text.
- [x] `retitle` printed `also retitled at: <level>`; `rename` renamed both lines;
      `--check-tree` clean after each.
- [x] `--archive`: dry run and real run print the other levels; every line gone after it.
- [x] Pruned dirs: `.venv-3.12/lib`, `target/x`, `venv_x` refused with `is no memory level: its
      path crosses '<name>'`; `vendor/y` and `venvnotes` accepted (`vendor` is not a pruned
      name, so the doc names it as an ordinary one).
- [x] `--check-tree` render drift line, `--check` repeated line, `mem_levels` `= placed by topic`
      line and `ref_map` `placed-by-topic` conflict printed as documented.

## RED / GREEN

Text-only probes (`bitranox:baseline-probe`), the reference text pasted in. Question: a fact
bound to `python`, two levels with that topic; which command places its lines, what `move` and
`--archive` do, is there a block limit, can `add` write it from a level without a line.

- [x] RED (`opus`, pre-edit "Store format" and command table): "No command does this, according
      to the text"; `move`: "The text does not say"; block limit: "The text does not say"; `add`:
      "The text does not say"; `--archive` read as dropping only the line at D, and the
      tree-unique bullet read as calling a placed fact a violation.
- [x] GREEN (`opus`, edited text): named `render-topics` with its output and exit codes, `move`
      refuses, `--archive` drops every line, the 1 MiB cap with its routes, `add` refused from a
      level without a line, each with a quote; every quote checked present in the file.
- [x] GREEN against RED: every RED "does not say" is answered in GREEN; nothing RED held is lost.
- [x] Haiku re-run (`haiku`, the cap paragraph and the verbs list): answered `move` refuses and
      un-bind first, `--archive S A` drops the line at B first then A then archives the body,
      `add --pin` refused, each with a verbatim quote. It read the move cap refusal as offering
      the render's four routes; the paragraph now says the move refusal itself names how many
      lines fit and to move the rest to another level with room (the engine text of
      `_move_cap_refusal`), and `add --pin` now carries its exit code.

## Skill gaps and what was done with each

Closed in the text:

- Exit code of the `move`/`relocate`/`add` refusals: now "(exit 2, `! refused:`)" in those
  bullets.
- Whether the cap refusal comes before any level is written: now "refuses before its first write
  (a block that grows while it runs can still stop it at that level, before any line is
  dropped)", as `render_topics`' docstring says.
- When to run which scope: the chain bullet now says the tree scope runs after topics change and
  the chain scope is the repair `--check` names.

Declined:

- Exit code of a successful run: the exit-code paragraph of the engine section states 0 for
  done.
- Field names of `--json`: the reader runs it; the counts are named.
- How to create a placed fact: `add`, then `set-topics`, then `render-topics` follows from the
  definition ("has a line at some level") and the existing `set-topics` paragraph.
- `--archive` when D holds no line: the existing table row covers it (no pointer at D is no
  entry).

## Checks a probe cannot see

- [x] Width check over the added prose lines: none over 100 columns.
- [x] Both tables canonical: `reformat_tables.py` reports both files unchanged.
- [x] History finder over the added lines: only quoted engine output ("each now has one line").
- [x] ASCII only; no host, private path or project name; example values are `python`, `.venv-3.12`.
