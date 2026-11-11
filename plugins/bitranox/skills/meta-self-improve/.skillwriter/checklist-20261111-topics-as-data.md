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
