# meta-self-improve: document the body title field and heal --backfill-titles

Scope: `references/memory-backend.md` only - the body frame block and the sentence after it, the
verb table's new `heal --proj D --backfill-titles` row, and the `retitle` row. No other row of the
verb table changes in content; the table formatter re-padded every row because the new row widened
its second column (whitespace only).

## What changed

- The frame block gains `title: <the pointer's title>` between `description:` and `metadata:`,
  the position `memory_engine.py` `_with_title` writes it (after `description:`).
- After "The engine writes that frame automatically." a sentence says the `title:` line carries the
  pointer's title as data, that a body-rewriting engine write sets it from the pointer, and that
  `heal --backfill-titles` fills it into older bodies.
- New verb-table row for `heal --proj D --backfill-titles`, with its success line, its skip lines
  and its exit 2.
- The `retitle` row now says the body's `title:` line follows the new title.

## Step 0b

- [x] `skill_decisions.py show meta-self-improve --kind rejected,removed --full`: one rejected
      entry (d-20261106-4cb9268c, name-based misplacement signal). Unrelated; nothing forbids a
      frame key.
- [x] `skill_decisions.py show meta-self-improve`: four live rules (queue and contribution
      handling); none touches the body frame or the verb table.
- [x] `repo-gate.py --mirrors`: `meta-self-improve` is not a mirrored pair, so no twin edit.

## Accuracy against the engine (read, not assumed)

- [x] Output and exit: `memory_engine.py` `_main`, the `heal` + `backfill_titles` branch, prints
      `back-filled %d title(s); %d body(ies) already had one`, then per slug
      `    ~ body has no frontmatter, left as it is: <slug>`,
      `    ~ pointer has no title to copy, body left as it is: <slug>` and
      `    ! missing central body (not fabricated): <slug>`, and returns 0. `backfill_titles` raises
      TreeWalkError on an unreadable level or body, which `main` maps to `! error: cannot read the
      memory store` on stderr and exit 2.
- [x] Scope: `backfill_titles` walks `curated_levels_under(_anchor(proj))`, every level of D's
      tree, and skips a body whose `_body_title` is set (never rewrites one that has a title).
- [x] Sync direction: `add_entry` ends with `e.body = _with_title(e.body, e.title)` (the comment
      names amend-pinned and factedit's apply), `retitle_entry` writes `_with_title(entry.body,
      title)`; the test `test_a_body_handed_back_with_a_stale_title_takes_the_pointer_title` in
      `hooks/tests/test_memory_engine_title_field.py` pins that the pointer wins.

## RED / GREEN (text)

- [x] RED counts on the pre-edit file: `grep -c "title:"` 0, `grep -c "backfill-titles"` 0.
- [x] GREEN counts: `grep -c "title: <the pointer's title>"` 1, `grep -c "backfill-titles"` 2
      (the frame sentence and the new row), as the brief expected.
- [x] Changed passages, quoted from the final text:
  - "The `title:` line carries the pointer's title as data: an engine write that rewrites a body
    (`add`, `amend-pinned`, `retitle`, factedit's `apply`) keeps the two equal by setting it from
    the pointer, so a stale `title:` in a body handed back is overwritten, never copied to the
    pointer, and `heal --backfill-titles` fills it into bodies written before it existed."
  - "`heal --proj D --backfill-titles` (every level of D's tree, a one-off: copies each pointer's
    title into a body that has no `title:`; never rewrites one that has; plain `heal` never opens
    a body. A skipped body prints a `~ ... left as it is: <slug>` or `! missing central body (not
    fabricated): <slug>` line; an unreadable body or level exits 2) | `back-filled N title(s); M
    body(ies) already had one`"
  - "leaving slug, hook and prose untouched; the body's `title:` line follows the new title"
- [x] The brief's prescribed wording was extended in three places, each closing a gap a probe
      reported: the output column's skip lines and exit 2 (from the engine's actual output), the
      sync direction (GREEN could not tell which side wins), and "every level of D's tree" in
      place of "tree-wide" (GREEN could not tell how `--proj D` bounds the walk).

## Probes (bitranox:baseline-probe, passage pasted, no path)

- [x] RED, opus, pre-edit frame block plus the `heal` and `retitle` rows: answered NONE for both
      questions ("Its frame template has exactly these keys: `name: <slug>`, `description: <the
      hook>` and `metadata: type: ...`. There is no `title` field in it."; "The excerpt doesn't
      name one."). It guessed `heal --backfill-titles` from a commit subject in its own context and
      said it could not quote it as the rule.
- [x] GREEN, opus, first edited text: "It carries `New`, the pointer's current title", quoting
      "every engine write keeps the two equal"; command `heal --proj D --backfill-titles`, quoting
      "`heal --backfill-titles` fills it into bodies written before it existed". Gaps reported:
      which side wins the sync (closed), how `--proj D` scopes "tree-wide" (closed), the output for
      an unreadable level, partial writes on exit 2, "level" undefined (declined below).
- [x] Re-probe on the text after those fixes, opus and haiku (2 cells), three questions: both
      answered `New` with the pointer unchanged, `heal --proj D --backfill-titles` over every level
      of D's tree, and plain `heal` does not fill titles, each with a verbatim quote. haiku
      reported that "every engine write keeps the two equal" read as covering the back-fill, which
      leaves a stale `title:` alone; closed by naming the body-rewriting writes.
- [x] Final re-probe, haiku, the two questions that fix touched: body carries `New`, pointer
      unchanged ("an engine write that rewrites a body (`add`, `amend-pinned`, `retitle`,
      factedit's `apply`) keeps the two equal by setting it from the pointer"); the back-fill
      leaves a `title: Old` body as it is and that contradicts nothing ("never rewrites one that
      has"). No new undecided gap.
- [x] Tiers and cells: RED opus 1; GREEN opus 1; re-probe opus 1 + haiku 1; final haiku 1.

## Declined gaps

- Output for an unreadable level: stated in this file's "Engine exit codes" paragraph ("`! error:
  <why>` on stderr when it could not run (... a store it could not read ...)"), and `main` maps
  TreeWalkError to exactly that line and exit 2.
- Partial writes on exit 2, and whether a re-run is safe: each body is written on its own
  (`us.put_body` per slug, no rollback), and the row's "never rewrites one that has" already makes
  a re-run harmless. Not worth a third clause in a table cell.
- "Level" and "D's tree" undefined: defined at the top of this file (altitudes, the knowledge
  tree's anchor); a reader meets the row inside the whole file, not alone.
- No bulk fix for a stale `title:` in a body: no such verb exists. A stale title can only come from
  a write outside the engine, which the edit guard denies, and the next body-rewriting engine write
  corrects it. Documenting a verb that does not exist is out of scope.
- "M body(ies) already had one" does not say the titles match: the success line is quoted verbatim
  from the engine and says what it counts.

## Mechanical checks

- [x] `reformat_tables.py` run on the file: canonical ("Unchanged" after the edit hook re-padded
      the table); `git diff` read: only the four intended passages change content.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the frame
      block and the rows around the new one were read for re-bound references (none).
- [x] ASCII: `git diff -U0 | grep '^+' | grep -P '[^\x00-\x7F]'` printed nothing.
- [x] Ledger anchor "The `title:` line carries the pointer's title as data" occurs once in the
      whitespace-normalised file.

Decisions: d-20261110-7778c924
