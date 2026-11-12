# meta-dream-tree: the tree dream tags a stack rule and renders, instead of moving it up

Scope: `SKILL.md` steps 0b (topics of a level), 5 (a rule about a stack or tool is tagged), 8
(render before the manifest diff, `render drift`), 11 (report items);
`references/dream-core.md` (the routing prompt answers `TOPICS`, the verification contract
renders first); `references/dream-passes.md` (the "Belongs wherever a stack is used" bullet).
Every passage opens with its condition (`topics-show` exits 0), so a tree without a topic list
is consolidated by level only.

## Step 0b

- [x] `skill_decisions.py show meta-dream-tree --kind rejected,removed --full`: one rejected entry
      (d-20261106-7121104c, re-running ref_map after a dropped move). Unrelated.
- [x] `skill_decisions.py show meta-dream-tree`: seven live rules; no anchor is removed, and
      `skill_decisions.py check` prints `checked 31 ledger(s), 0 finding(s)` after the edit.
- Decisions: d-20261112-19aaf9ff, d-20261112-0b76f595, d-20261112-c784f540

## Every verb the text cites, run on a scratch tree

A tree with a topic list (`python`, `rust`), levels `a/py` and `b/py` (`python`), `c` (`rust`),
`d` (none). Each line below is the verb's own output.

- [x] `topics-show` without a list: `no topic list in this tree`, exit 1; with one: exit 0.
- [x] `topics-stale` on a level never tagged: `stale: never tagged`, exit 1; after
      `set-level-topics` (also with `--topics ''`): `fresh`, exit 0.
- [x] `set-level-topics --proj <level> --topics python`: `topics updated: <level>`. At the tree
      top: `! refused: <top> is the tree top: its topics are the user's decision (set-top-topics,
      on the user's word)`, exit 2.
- [x] `set-scope` with a text carrying a different `TOPICS:` line: `! refused: a descriptor's
      TOPICS line changes only through set-level-topics ...`, exit 2.
- [x] `set-topics --slug <slug> --topics python --dry-run`: `would set topics on 1 fact(s); 0
      unchanged`; the real run: `set topics on 1 fact(s); 0 unchanged`; a `--batch` file the same.
- [x] `set-topics` refusals: a line differing from its body (`its line at <level> differs from
      what its body renders; run skills/meta-dream-tree/factedit.py apply ...`), a body with no
      `title:` (`... run hooks/memory_engine.py heal --proj <top> --backfill-titles ...`), a
      pinned fact (`is pinned; a pinned fact stays where it is`). All exit 2 and write nothing.
- [x] `render-topics --scope tree --dry-run`: `  <level>: +1 added, 0 refreshed, -0 removed`
      then `render-topics (tree): 1 managed fact(s); would change 1 level(s)`; the real run ends
      `render-topics (tree): 1 managed fact(s); changed 1 level(s)`. The line the fact already
      has at `a/py` stays; `b/py` gains one. When the parent `a` gets `python`, the next render
      adds the line at `a` and removes it at `a/py`.
- [x] `render-topics` with a level whose `TOPICS:` line does not parse: `! refused: <level>: its
      TOPICS line does not parse (...); set-level-topics replaces it`, exit 2.
- [x] Placement lock held by another holder: a dry run answers at once; a real `render-topics`
      prints `! error: render-topics waited 30 s for the placement lock of the tree ...: ... Run
      render-topics again once that one finishes ...`, exit 2.
- [x] `reconcile_memory_index.py --check-tree` between `set-topics` and the render: `! render
      drift: <level> -> 1 line(s) missing, 0 differing from the body, 0 placed elsewhere (...)`
      and `TOTAL tree problems: 1`; after the render `TOTAL tree problems: 0`. `--check` on a
      chain holding the line twice: `! repeated line: <slug> at <level> is also held by <upper>
      above it; ... --scope chain drops the lower copy`.
- [x] `move` on a placed fact: `! refused: '<slug>' is placed by topic: where it is read follows
      its topics and the levels' ...`, exit 2.
- [x] `store_manifest.py verify` after a tag and a render: `added <slug> (<level>)` per level a
      line arrived at, `removed` where it left, `moved` for a fact whose one line changed level,
      and `changed <slug> (body)` for a fact tagged since the backup.
- [x] `topic_tagging.py questions`, `items --levels`, `decide --kind levels`: the decided file
      holds `{"level": "a/py", "topics": ["python"]}` lines and the unsure file the rest with a
      reason; `decide --kind facts` writes the file `set-topics --batch` took.
- [x] Read, not run: a fact with a legacy `uuid:` line is never placed
      (`hooks/memory_engine.py`, `_unplaceable_slugs` and the placement notes at its top).

## RED / GREEN

Text-only probes (no file or shell tools), the passages pasted in. Situation: a tree with a
topic list; `a/py` and `b/py` have `python`, `c` has `rust`, their only common parent is the
tree top; a fact at `a/py` ("When a Python test imports a sibling helper, use the bare module
name.") was sighted in `b/py` too. Q1: which commands for this fact. Q2: level `d` has a
descriptor and no `TOPICS:` line; what about `d` and about the tree top's line.

- [x] RED (`opus`, pre-edit text). Q1: "Command: none. The fact stays at `a/py`, logged as
      `a/py | CONFIDENCE low | UNSURE`", with the alternative a `saw-promotable`,
      `should-promote` and `move` to the tree top; no `set-topics` ("nothing in the pasted text
      turns a topic into a placement target or a command"). Q2: "Command: none for `d`, and
      none for the tree top's `TOPICS:` line"; "No sentence says to write, update or check it".
- [x] GREEN (`opus`, new text). Q1: `set-topics --proj <anchor> --slug <slug> --topics python`
      (dry run first), then `render-topics --proj <anchor> --scope tree`; "there is no `move`
      and no `should-promote`/`promoted`". Q2: `topics-stale --proj d`, then `set-level-topics`;
      for the top "Run nothing", quoting "NEVER run `set-top-topics`, and never
      `topics-set-list`".
- [x] GREEN (`haiku`, new text): the same commands for Q1 ("No `move`") and Q2, same quotes.
- [x] Control, must answer differently (`opus` and `haiku`): the same fact in a tree where
      `topics-show` exits 1, at `py-libs/one`, sighted in `py-libs/two`. Both routed it to
      `py-libs` and ran `move --from-level py-libs/one --to-level py-libs --slug <slug>`, and
      ran none of `set-topics`, `topics-stale`, `render-topics`, quoting the three conditions.
- [x] Second control (`opus`): a fact about one project's release checklist in a tree with a
      topic list gets a level, no `set-topics` ("a fact about a place ... gets a level as
      above").
- Cells: 2 tiers on Q1, Q2 and the no-list control; 1 tier on RED and the place control.

## Gaps the probes reported

- [x] Closed: whether a level without a `TOPICS:` line can read fresh. The text now says it
      prints `stale: never tagged`; quote-back on the final text returned that sentence.
- [x] Closed: what happens to the line a tagged fact already has. The text now says the render
      places a line "at each level that has one of its topics while no level above it does; a
      line it already has at such a level stays as it is"; quote-back returned it.
- [x] Declined, left to the dream's judgment: how much evidence makes a TOPICS answer high
      confidence. The routing prompt's "EVIDENCE, not wording, decides reach" governs it as it
      governs a level answer.
- [x] Declined, not decided by this change: whether a tagged fact's sighting is recorded with
      `saw-promotable`. The gate stays tied to a move to the tree top, which a tagged fact does
      not make; the text says nothing either way.
- [x] Declined, scenario detail: `d`'s topics and the slug and anchor literals were not given
      to the probe; the `--batch` line format is in `set-topics --help`.

## Layout

- [x] Width and fence check over the added lines of the three files prints nothing; no
      non-ASCII byte; the version-history finder has no hit in the added lines.
- [x] The paragraph after each insertion point read: step 0c, step 6, the manifest-diff
      sentence of step 8 and the pinned-fact paragraph under the routing prompt keep their
      referents.
- [x] `tests/` of the skill: 615 passed.

# A landing at the tree top follows the mode; a sibling duplicate is not merged up

Scope: `SKILL.md` step 4 (where a merged sibling duplicate goes), step 5 (the placement lock's
holders; a tagged fact whose line would land at the tree top), step 8 and step 11 (layout, one
report item); `references/dream-core.md` (Mode, the report contract, the paragraph under the
routing prompt reflowed). `topic_tagging.py`: one docstring sentence about the roll-up reworded,
no code.

- [x] `skill_decisions.py show meta-dream-tree --kind rejected,removed --full`: the one rejected
      entry (d-20261106-7121104c) is unrelated. `skill_decisions.py check` prints
      `checked 31 ledger(s), 0 finding(s)` after the edit.
- Decisions: d-20261112-dff1ba7b, d-20261112-0a58e812, d-20261112-422c483a, d-20261112-d4d3e02c
- [x] d-20261110-442234ef and d-20261110-a7f3f64a both reopen when placement is generated from
      topics, which it now is for a tagged fact. Each is superseded by an entry that keeps its
      rule and adds the tagged fact that would land at the top (dff1ba7b, 0a58e812).
      d-20261112-cffc4b77 is superseded by 422c483a, the same rule with the roll-up worded as
      "two or more child levels, EVERY one of which has a topic".

## Verbs run on a scratch tree

Topic list `python`, `rust`, `go`; levels `a/py` and `b/py` (`python`), `c` (`rust`), `a`, `b`,
`d` (none); no level has `go`. Each line is the verb's own output, `<top>` for the tree top.

- [x] A fact at `c`, `set-topics --slug go-rule --topics go`: `set topics on 1 fact(s); 0
      unchanged`. Then `render-topics --scope tree --dry-run`:
      `  <top>: +1 added, 0 refreshed, -0 removed`,
      `  <top>/c: +0 added, 0 refreshed, -1 removed`,
      `render-topics (tree): 1 managed fact(s); would change 2 level(s)`.
- [x] The same dry run with `--json`: `"levels": {"<top>": {"added": 1, "examples": {"added":
      ["go-rule"]}, ...}`. The list holds the first 20 per level (`_RENDER_SHOWN = 20`,
      `hooks/memory_engine.py`).
- [x] `set-topics --slug go-rule --clear`: `set topics on 1 fact(s); 0 unchanged`; the next dry
      run prints no line for `<top>` or `<top>/c`, and the fact's line is still in `c`'s block.
- [x] A fact at `a/py` tagged `python`: the dry run prints
      `  <top>/b/py: +1 added, 0 refreshed, -0 removed` and no line for `<top>`.
- [x] Placement lock held, `retitle` of a fact with no topics in this tree: `! error: retitle
      waited 30 s for the placement lock of the tree <top> (...): another render-topics,
      set-topics, or write to a fact placed by topic holds it. Run retitle again once that one
      finishes; ...`, exit 2. `set-topics --dry-run` under the same held lock answers at once.
- [x] Read, not run: the holders (`hooks/memory_engine.py`, the comment above
      `placement_lock_path`, `_placement_lock_if_bound`, `placement_lock_if_listed`; the archive
      in `skills/meta-self-improve/reconcile_memory_index.py`, which names itself
      `reconcile_memory_index.py --archive` in the lock message).

## RED / GREEN

Text-only probes, the passages pasted in. Tree as above, propose mode. QA: a fact at `c` about
Go, routed `TOPICS go`; which commands, where is its line after step 8, what does the report
say. QB: the same lesson as two facts at `a/py` and `b/py`; what does step 4 do, where does the
merged fact sit. QC: a stack rule at `a/py` sighted in `b/py`.

- [x] RED (`opus`, pre-edit text). QA: binds, renders; "Where the pointer line ends up: NOT
      STATED", "What the report says about it: NOT STATED", "Nothing in propose mode turns it
      into a proposal, so it is applied". QB: "Read literally, 'it merges at their common
      parent' means the tree top"; "step 4 can apply, or propose, a top placement that step 5
      then undoes".
- [x] GREEN (`opus`, new text). QA: bind, dry run, `--json`, then `set-topics --proj
      /path/to/tree --slug go-fmt --clear`, dry run again; "it stays at `c`, unchanged";
      "`go-fmt` is listed as a proposal ... The cost is the UTF-8 byte length of its pointer
      line plus 1 for the newline". In auto mode: "No clear", line at the tree top, cost
      printed. QC: `set-topics --topics python`, render; "Moves to a parent or the top: none";
      "Proposed rather than applied: nothing".
- [x] GREEN (`opus`, new text). QB: "At the end of step 4 the merged fact sits at `a/py` ... It
      does not go to the tree top"; step 5 tags it, the line is read at `a/py` and `b/py`. No
      topic list: "The merged fact goes to `py-libs`, the siblings' common parent". A place
      fact duplicated in a topic-list tree: folded in step 4, then "It then moves to `a` by
      the normal move procedure. `set-topics` is not used."
- [x] GREEN (`haiku`, new text), QA and QB plus two level questions: the same commands and the
      same proposal for QA; QB "It is not moved to a parent". A container with a python and a
      rust child gets `--topics ''`; one with two python children gets `--topics ''` and
      "Python reaches `b` through the engine's roll-up, not through b's line". The tree top's
      empty line: "I do not change it".
- Cells: QA and QB on 2 tiers; QC, the no-list control and the place control on `opus`; RED
  on `opus`.

## Gaps the probes reported

- [x] Closed: whether auto mode repeats the dry run. The repeat now sits in the propose
      sentence; quote-back (`opus`) returned "then run the dry run again and require that the
      top's line no longer counts a fact you took back" for propose and "In auto mode keep the
      binding and print that cost in the report" for auto.
- [x] Closed: "rendered into the other sibling" was narrower than step 8. Now "rendered at
      every level that has its topic"; quote-back returned it.
- [x] Declined, needs an engine change: the binding is written before its landing can be seen
      (`set-topics --dry-run` prints counts only; run: `would set topics on 1 fact(s); 0
      unchanged`), so another session's real render between the bind and the take-back would
      place the line at the top.
- [x] Declined, not decided here: a fact tagged in an earlier run that a level-topic change
      of this run sends to the top; more than 20 arrivals at the top in one run.
- [x] Declined, covered elsewhere: which duplicate to drop and how
      (`references/dream-core.md`, "Dedup semantics": "require a verbatim quote from the entry
      being dropped for every loss it claims"); the cost measure (`references/dream-core.md`,
      Mode: "the UTF-8 length of its pointer line plus the newline").
- [x] Declined, left to step 5: a duplicated fact about a place is folded in step 4 and moved
      by step 5's routing, one move later than a merge at the parent would be.

## Layout

- [x] Width and backtick check over the added lines of `SKILL.md` and
      `references/dream-core.md` prints nothing; no non-ASCII byte.
- [x] The paragraph after each insertion point read: step 6, `## Boundaries`, the report
      contract's promotion sentence, and the `Record each sighting` sentence under the routing
      prompt keep their referents.
