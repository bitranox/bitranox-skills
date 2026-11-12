# meta-self-improve: document topics as data and the six topic verbs

Scope: `references/memory-backend.md` only (the body-frame bullet, two new paragraphs at the end
of "Store format", six rows in the engine command table after `set-scope`, the exit-code
paragraph), plus the matching six rows and the exit-1 sentence in the repository's
`docs/reference.md`. `SKILL.md` is not changed. The table formatter re-padded every row of both
tables because the new rows widened a column (whitespace only).

## What changed

- Body frame: a `topics:` line lists the topics a fact is bound to; `topics: []` is tagged and
  bound to none, no line is never tagged; only `set-topics` changes a stored line; what "does not
  parse" means for a `topics:` and a `TOPICS:` line.
- "Store format": a descriptor's `TOPICS:` line, which verb sets it where, what `set-scope` keeps
  and refuses, the tree's closed list in `topics.json` with its limits, what a tree without a list
  does, when `topics-stale` reports stale, and that nothing is placed by topic yet.
- Command table: `topics-show`, `topics-set-list`, `set-topics`, `set-level-topics`,
  `set-top-topics`, `topics-stale`, each with its success line and its refusals.
- Exit codes: exit 1 comes from three check verbs (`lint --tree`, `topics-show`, `topics-stale`);
  a refused topic write and a `set-scope` text that changes the `TOPICS:` line are refusals; a
  `topics.json` the two check verbs cannot use is an error.

## Step 0b

- [x] `skill_decisions.py show meta-self-improve --kind rejected,removed --full`: one rejected
      entry (d-20261106-4cb9268c, name-based misplacement signal). Unrelated.
- [x] `skill_decisions.py show meta-self-improve`: five live rules. One touches the body frame
      (d-20261110-7778c924, the `title:` field); its sentence is kept word for word, and
      `skill_decisions.py check` reports 0 findings after the edit.
- [x] `repo-gate.py --mirrors`: `meta-self-improve` is not a mirrored pair.
- Decisions: none - documents data and verbs the engine already has, changes no rule

## Accuracy against the engine (run on a scratch tree, not assumed)

Every command the text names was run against `hooks/memory_engine.py` on a scratch tree of two
levels, with these results:

- [x] No list: `topics-show` printed `no topic list in this tree`, exit 1; `topics-stale` printed
      `fresh`, exit 0; `set-topics`, `set-level-topics` and `set-top-topics` each printed
      `! refused: this tree has no topic list yet (topics-set-list writes one)`, exit 2.
- [x] `topics-set-list`: an empty `topics` object printed `! refused: an empty topic list: a
      tree's list names at least one topic`; a two-topic file printed `topic list updated: 2
      topic(s), tagger opus`, and again `topic list unchanged: 2 topic(s), tagger opus`; a list
      dropping a topic in use printed `! refused: fact <slug> carries uv; level <dir> declares
      uv`. Limits read in `topic_store.py` (`MAX_LIST = 64`, `MAX_MEANING = 200`) and
      `topic_placement.py` (`MAX_TOPICS = 12`, the name pattern of at most 32 characters). In
      `set_topic_list` the dropped set is built from trimmed names, and a level whose line raises
      `InvalidTopic` is skipped.
- [x] `topics-show`: `tagger: opus` then `python - <meaning>` lines; `--json` one object.
- [x] `set-topics`: `would set topics on 1 fact(s); 0 unchanged` with `--dry-run`, then `set
      topics on 1 fact(s); 0 unchanged`; a topic outside the list `! refused: <slug>: rust not in
      the topic list`; an unknown slug `! refused: <slug>: no level points at it`; `--clear`
      removed the line, `--universal` wrote `topics: []`; a one-line `--batch` file applied.
      Pinned fact, body without frontmatter and the 5000-row limit read in `_topic_row_problem`
      and `MAX_TOPIC_BATCH`.
- [x] `set-level-topics`: `topics updated: <dir>`, then `topics unchanged: <dir>`; at the tree
      top `! refused: <dir> is the tree top: its topics are the user's decision`; on a level
      without a descriptor `! refused: <dir> has no descriptor yet (set-scope writes one)`;
      `--topics ''` wrote a `TOPICS:` line with no tag, and `topics-stale` then printed `fresh`.
- [x] `set-top-topics`: below the top `! refused: <dir> is not the tree top (<top>); use
      set-level-topics`; at the top `topics updated: <dir>`.
- [x] `topics-stale`: `stale: no descriptor`, `stale: never tagged`, `fresh`, and after a
      `set-scope` with other text `stale: descriptor changed since its topics were chosen`, each
      stale answer exit 1. The unparsable-line answer read in `level_topics_stale`.
- [x] `set-scope`: a text without the line kept `TOPICS: python, uv` in the block; a text with
      `TOPICS: uv` on a level holding another line, and on a level holding none, printed
      `! refused: a descriptor's TOPICS line changes only through set-level-topics`. The refusal
      for a stored line that does not parse read in `scope_keeping_topics`.
- [x] An `add` that updates a fact, handing in a frame with `topics: [rust]`, left the stored
      `topics: [python, uv]`. `amend-pinned` and factedit's `apply` reach the same
      `add_or_update_entry` branch (`_with_stored_topics`), which also keeps an unparsable line
      and the absence of a line.
- [x] A `topics.json` that is not JSON: `topics-show` and `topics-stale` printed `! error: <file>
      is not valid JSON`, exit 2; `set-topics` printed `! refused:` with the same reason, exit 2.

## RED / GREEN

Text-only probes (no file or shell tools), the reference text pasted in. RED question, kept for
GREEN: "A fact should be read only in directories that use Python. Which engine command records
that on the fact, and which on a directory? Answer with the commands or say the text does not
tell you."

- [x] RED (`opus`, the pre-edit "Store format" section, command table and exit-code paragraph):
      "the text does not tell you. Nothing in the pasted section names a command that marks a
      fact as "read only in directories that use Python", and nothing names a command that marks
      a directory as using Python."
- [x] GREEN (`opus` and `haiku`, new text, 2 cells x 5 questions): both answered `set-topics`
      for the fact and `set-level-topics` for a directory, quoting "To record that a fact is
      read only where a topic is, bind the fact with `set-topics` and give each such directory
      the topic with `set-level-topics`." Both said a dream does not run `set-top-topics`,
      quoting "is run only on the user's decision, never by a nap or dream on its own". Both
      answered the `set-scope` pair (line kept; a different line refused, exit 2), the `add`
      question (stored line kept) and the exit-2 question (the check could not run, not stale)
      with quotes of the governing lines.
- [x] GREEN against RED in both directions: RED produced no command, so nothing it held is
      missing from GREEN.
- [x] Lesson not already in the machine's context: the verbs are new in this release and the
      probes were given the text itself, so the evidence is the text check plus the quotes, each
      of which is in the pasted text.

## Skill gaps and what was done with each

Closed in the text, then re-probed on the final text (`opus` and `haiku`):

- What `--topics ''` writes on a level: the `set-level-topics` row now says it writes the line
  with no topic. Re-probe quote: "`--topics ''` writes the line with no topic: tagged, and the
  directory has none".
- What "does not parse" means, for which line, and whether a name off the list parses: one
  sentence pair in the body-frame bullet. Re-probe quote (`haiku`, final text): "A line with no
  tag parses, and so does one holding a valid name that is missing from the tree's list: the
  list is checked when a topic verb writes, not when a stored line is read."
- An update handing in a `topics:` line when the stored body has none: the bullet now says the
  update keeps "what is stored (the line, a line that does not parse, or no line)". Re-probe
  answer on both tiers: the stored body has no line afterwards, with that quote.

Declined:

- Whether anything enforces "read only where": the text says "Topics are data for now: no
  pointer line is placed by them yet", and both tiers quoted it. Placement is a later change.
- Where a dream puts its proposal for the top's topics: out of scope, this file documents the
  data and the verbs; the dream skills own what a dream reports.
- How a topic gets onto the list: covered in the excerpt, the `topics-set-list` row ("replaces
  the whole list").
- How a level gets a descriptor: covered, the `set-scope` row and
  `! refused: ... has no descriptor yet (set-scope writes one)` printed by the engine.
- Whether `heal` touches the line: covered by "Only `set-topics` changes a stored line";
  `backfill_titles` writes through `_with_title` only.
- The literal form of the empty `TOPICS:` line and what `--proj` names for `set-topics`: the
  rows say "writes the line with no topic" and the engine's `--help` says "any dir of the tree";
  the reference points at `--help` for flags.
- The exit-code paragraph naming topic refusals only as "a refused topic write": judged the same
  thing by the probe that raised it; no contradiction reported.

- How a stored line comes to hold a name off the list, and that no verb can write one: the
  sentence states what a reader of a stored line does, which is all a caller needs; the write
  verbs' refusal is in their rows. The identical-line case of `set-scope` follows from "a
  different `TOPICS:` line" and was run (same line, `scope_keeping_topics` returns the text).

Last run on the final text (`opus` and `haiku`, 2 cells x 3 questions): both answered that
`TOPICS: kubernetes` with a valid name off the list parses and does not make `set-scope` refuse
every text, that `--topics ''` writes a line that parses and is not "no `TOPICS:` line", and
`set-topics` / `set-level-topics` for the RED question, each with quotes found in the pasted
text. Every gap either tier listed is one of the declined ones above; no new undecided gap.

## Checks a probe cannot see

- [x] Width and fence check over the added lines: nothing left after two paragraphs were
      reflowed; the file holds the same count of over-width prose lines as before the edit.
- [x] The sentence after each insertion point reads as before (the `**Why:**` labels sentence
      after the frame bullet; "## Two tiers and the capture flow" after the new paragraphs).
- [x] Both tables are canonical: `reformat_tables.py --check` reports both files unchanged.
- [x] History finder over the added lines: no version-history wording.
- [x] ASCII only; no host, private path or project name; the example values are `python`, `uv`.

## Follow-up 2026-11-12: two engine fixes and four corrections

Scope: `references/memory-backend.md` (the body-frame bullet, the exit-code paragraph, the
sentence after it on `set-scope`, the `set-topics` and `topics-set-list` rows) and the
`memory_add` refusal cell in the repository's `docs/reference.md`. `SKILL.md` is not changed.

- [x] `add` that creates a fact now refuses a body whose frontmatter carries a `topics:` line
      (`TopicsOnCreate`, exit 2, no body file, no pointer, no level scaffolded). Pinned by
      `test_add_refuses_a_new_fact_whose_frame_carries_a_topics_line` (RED on the old engine:
      `assert 0 == 2`) and `test_the_library_create_raises_and_a_topics_line_in_the_prose_is_no_frame`.
      The bullet says so and names `set-topics` as the way to tag the new fact.
- [x] A refused `set-scope` on a directory that is not a level yet leaves no `CLAUDE.local.md`:
      the `TOPICS:` check now runs before the level is scaffolded. Pinned by
      `test_a_refused_set_scope_leaves_no_level_scaffolded_behind_it` (RED on the old engine:
      `assert not local.exists()` failed). The sentence after the exit-code paragraph now states
      it for both a missing flag and a `TOPICS:` refusal.
- [x] `set-topics` row: an invalid slug is the first refusal `_topic_row_problem` checks; added.
- [x] `topics-set-list` row: a fact whose `topics:` line does not parse is skipped like a level's
      (`iter_fact_topics` yields only bodies `_body_topics` parses); added.
- [x] Width check over the changed prose lines (none over 100 columns), both tables canonical
      (`reformat_tables.py` reports both files unchanged), ASCII only, no history wording.
- Decisions: none - documents two engine refusals and corrects two refusal lists, changes no rule

## Follow-up 2026-11-12: one TOPICS gate, batch limits, relocate, pinned clear

Scope: `references/memory-backend.md` (the body-frame bullet, the descriptor paragraph split into
a per-verb paragraph and a gate paragraph, a new paragraph on `set-topics --batch`, `--dry-run`,
`--clear` on a pinned fact and the `--topics` usage error, the topic verb rows, the exit-code
paragraph, `add`'s `--scope`, `relocate`), the topic paragraph and `memory_add` refusal cell of
the repository's `docs/reference.md`, and the 11.2.0 `CHANGELOG.md` section. `SKILL.md` is not
changed.

### Accuracy against the engine (each message string grepped in the code)

- [x] Gate message: `memory_engine.py` `scope_keeping_topics` ("a descriptor's TOPICS line changes
      only through set-level-topics (set-top-topics at the tree top); leave the line out of the
      new text"), raised for every descriptor writer: `set-scope` (`_main`, under
      `sig.memory_lock(local)` for the whole read-check-write), `ensure_level` (`scope_default`
      and the legacy harvest, `if not scope and want_scope`), and so `add --scope`.
- [x] Legacy refusal: same function, `stored_in` branch ("the legacy scope block in %s has a
      TOPICS line that does not parse (%s); fix or remove that line there by hand, then run this
      again"); `_current_scope` reads the legacy block without moving it. `scaffold` catches
      `TopicRefusal`/`InvalidTopic` and continues; `heal` skips through its per-level
      `except Exception`. Pinned by
      `test_ensure_memory_structure_skips_a_legacy_level_it_cannot_harvest_without_a_traceback`
      (exit 0, `CLAUDE.md` byte-identical) and the set-scope/add legacy tests.
- [x] `set-level-topics` reads only the pointer block (`set_level_topics`:
      `us.parse_pointer_index(text)`, refusal "has no descriptor yet (set-scope writes one)").
- [x] Symlinked level: `topic_store.level_key` is lexical; a path not below the anchor raises
      `TopicStoreError`, mapped to `! refused` by the topic-verb branch of `_main`.
- [x] Topic-file check before the descriptor write: `topic_store.record_level(..., before=...)`
      runs the descriptor write inside the topic file's lock after the checks; an `OSError` in
      `_write` after it reaches `main`'s `except OSError` (`! error`, stderr, exit 2), and
      `level_topics_stale` then reports "descriptor changed since its topics were chosen".
- [x] Batch: `_read_topic_batch` messages ("line %d is longer than %d bytes", "holds more than %d
      rows", "slug %r is named twice (first on line %d)", "is not UTF-8 (byte at offset %d) -
      re-save it as UTF-8"), `MAX_TOPIC_BATCH_LINE_BYTES = 4096`, `MAX_TOPIC_BATCH = 5000`, BOM
      dropped on line 1, `RecursionError` caught; the whole file is read before
      `set_fact_topics` runs.
- [x] `--topics` usage error: `_topics_arg` ("! error: --topics %r: %s") via `_input_error`
      (stderr, exit 2), used by `set-topics`, `set-level-topics` and `set-top-topics`.
- [x] Pinned: `_topic_row_problem` refuses only `topics is not None` on a pinned fact ("%s is
      pinned; a pinned fact stays where it is (only --clear may change it)"); byte-identity of
      the rest pinned by
      `test_clearing_a_pinned_facts_topics_is_allowed_and_keeps_the_rest_byte_identical`.
- [x] Dry run: `_is_topic_dry_run` lets a topic verb's `--dry-run` past the writes-off gate;
      `set_fact_topics` refuses a real write under the switch.
- [x] Relocate: `relocate_entry` / `_without_topics_line` (leading frontmatter only), note
      "dropped the topics: line of %s - topics are tagged against one tree's list; tag it in the
      target tree with set-topics" printed as `~ note:`; same-tree delegates to `move_entry`.
- [x] `memory_add` refusal: `mod_bridge.REFUSALS` takes `ME.ADD_REFUSALS` (which holds
      `TopicRefusal`), envelope `ok: false` with the kind, rc 1. The bridge passes no scope, so
      only the legacy-block refusal reaches it.

### RED / GREEN

Questions (text-only probes, the paragraphs pasted in, answer plus a direct quote or NONE):
Q1 `add --scope` with an empty `TOPICS:` line on a level with no descriptor; Q2 a legacy block
holding `TOPICS: Not A Tag!` under (a) `ensure-memory-structure`, (b) `set-scope`; Q3
`set-topics --batch --dry-run` under `BITRANOX_MEMORY_WRITES=off`; Q4 a cross-tree `relocate` of
a fact tagged `topics: [python]`; Q5 a batch whose third line is 5000 bytes.

- [x] RED (`opus`, pre-edit paragraphs): Q1, Q2(a), Q3, Q4, Q5 NONE; Q2(b) answered only by
      reading the legacy block as "the stored line", which the old text never said.
- [x] GREEN (`opus` and `haiku`, 2 cells): all five answered with quotes found in the text
      (refusal exit 2 and nothing written for Q1; skip and `CLAUDE.md` untouched, then refusal
      for Q2; exit 0 `would set topics on ...` for Q3; line dropped plus the note for Q4;
      `! error` naming the line for Q5).
- [x] GREEN against RED in both directions: no answer the RED arm held is missing from GREEN.
- [x] Re-probe on the final text after the gap fixes (`opus` and `haiku`, 2 cells): both answered
      that `ensure-memory-structure` exits 0 and leaves `CLAUDE.md` as it is, that `set-scope`
      exits 2 and writes nothing, that `set-level-topics` cannot repair a legacy line, and that a
      batch with a 5000-byte third line changes no fact, each with a quote from the text. No new
      undecided gap.

### Gaps the probes reported, and what was done

- CLOSED: the exit code of `ensure-memory-structure`/`heal` on a skipped legacy level, and that
  the legacy refusal writes nothing - both stated in the gate paragraph.
- CLOSED: whether `set-level-topics` can repair a legacy line - it reads only the pointer block,
  stated.
- CLOSED: whether a batch applies lines before a bad later line - "reads its whole JSONL file
  ... before it changes any fact" and "no fact is changed".
- CLOSED: "the level setup" read as a verb name - reworded to "every other verb that would set
  that level up".
- DECLINED, covered elsewhere in the file: the `TOPICS:` grammar and what "does not parse" means
  ("Store format" bullet: "does not parse when it holds a tag that is no valid topic name or
  more than 12 tags"); the exit code of a successful `relocate` (the exit-code paragraph: "0
  done"); a dry run in a tree with no topic list (the topic list paragraph: "`set-topics`,
  `set-level-topics` and `set-top-topics` refuse there").
- DECLINED, judgement: which verbs set a level up beyond `set-scope` and `add` is not listed;
  every verb that scaffolds a level runs the same gate (`main` maps `TopicRefusal` to a
  refusal wherever it surfaces), so a list would only rot.
- DECLINED, covered elsewhere: the exit code of the gate's own refusals (the exit-code paragraph
  lists "a descriptor text from `set-scope` or `add --scope` that brings or changes a `TOPICS:`
  line" under exit 2).
- DECLINED, judgement: "replace a pointer block's line with `set-level-topics`" read beside the
  legacy sentence as two remedies - the scope "a pointer block's line" and the next sentence
  ("`set-level-topics` reads only the pointer block") separate them, and both tiers answered
  the repair question correctly on the final text.
- DECLINED, out of scope: "Topics are data for now" beside "read only where a topic is" - that
  tension predates this change and is the placement work the paragraph names as not done yet.

### Checks a probe cannot see

- [x] Width and fence check over the added lines of all three files: nothing reported; long
      engine messages are quoted in double quotes, not split code spans.
- [x] Paragraphs after each insertion point read as before (the topic list paragraph after the
      gate paragraph, "## Two tiers" after the batch paragraph, `--skill NAME` after the
      `--scope` sentence, "**`move` is CHAIN-ONLY" after `relocate`).
- [x] Tables canonical: `reformat_tables.py --check` reports `memory-backend.md`,
      `docs/reference.md` and `CHANGELOG.md` unchanged.
- [x] History finder over the added lines: no version-history wording; the CHANGELOG's "still
      keeps" and "behaves as before" are rewritten as current behaviour.
- [x] ASCII only; no host, private path or project name.
- Decisions: none - documents engine behaviour and refusals, adds and removes no rule of the
  skill's text

## Follow-up 2026-11-12: a refused legacy level is named, not skipped

Scope: the gate paragraph of `references/memory-backend.md` (its last two sentences), the topic
paragraph of the repository's `docs/reference.md`, and the 11.2.0 `CHANGELOG.md` entry on the
`TOPICS:` gate. `SKILL.md` is not changed.

- [x] Engine: `heal` reports a level whose legacy `CLAUDE.md` block has a `TOPICS:` line that does
      not parse under `refused`, `scaffold` hands it to an optional `refused` list, and
      `heal`, `ensure-memory-structure` and `ensure-all-trees --apply` print
      "    ! refused level, left untouched: <refusal> [<level>]", exit code unchanged. Pinned by
      `test_ensure_memory_structure_names_the_legacy_level_it_refused`,
      `test_scaffold_hands_a_refused_level_to_the_callers_list`,
      `test_ensure_all_trees_reports_a_member_it_refused`,
      `test_heal_names_the_legacy_level_it_refused_and_heals_the_rest` and
      `test_heal_under_writes_off_carries_an_empty_refused_list`; RED on the previous engine
      (the printed line absent, `TypeError: scaffold() got an unexpected keyword argument
      'refused'`, `KeyError: 'refused'`).
- [x] The documented line was produced by running both commands on a scratch tree, not written
      from the code: both printed it and exited 0.
- [x] RED (text check): the pre-edit paragraph says `ensure-memory-structure` and `heal` "skip such
      a level without a word", which the engine no longer does.
- [x] GREEN quote-back on the new paragraph, `opus` (effort medium) and `haiku`, 4 questions each
      (does heal print, exit code, is CLAUDE.md changed and the parent set up, does `set-scope`
      behave the same): both tiers answered all four with direct quotes and the right reading.
- [x] Gap both tiers reported: the paragraph's first sentence gives "every other verb that would
      set that level up" exit 2 while the next names three commands that do not. CLOSED: the next
      sentence now opens "The three commands that set up a whole chain are the exception to that
      exit 2". Re-probe on the final text (`haiku`): answered with that sentence, no new
      undecided gap.
- DECLINED, covered elsewhere: what "does not parse" means (the "Store format" bullet: "does not
  parse when it holds a tag that is no valid topic name or more than 12 tags").
- DECLINED, judgement: stdout or stderr for the line; no other `! ...` report line of these
  commands states its stream, and the engine prints all of them on stdout.
- DECLINED, judgement: a further explicit statement that the refused level is never set up by
  another route; "leave such a level and its `CLAUDE.md` as they are" says it, and both tiers
  read it that way.
- [x] Width and backtick check over the added lines of all three files: nothing reported. Tables
      canonical (`reformat_tables.py --check` reports all three unchanged). ASCII only; history
      finder over the added lines: no hits.
- Decisions: none - documents the engine's report of a refused level, adds and removes no rule of
  the skill's text
