# meta-dream-tree: three cases of the take-back before the render

Scope: `SKILL.md` step 5, the paragraph on a tagged fact landing at the tree top, and the Mode
sentence in `references/dream-core.md`.

## Step 0b

- [x] `skill_decisions.py show meta-dream-tree --kind rejected,removed --full`: one rejected
      entry (d-20261106-7121104c, re-running ref_map after a dropped move). Unrelated.
- [x] `skill_decisions.py show meta-dream-tree`: every live rule keeps its anchor
      (`skill_decisions.py check`: 0 findings).
- Decisions: d-20261112-1d36f463, d-20261112-f93b9384, d-20261112-22ec6ed3

## Commands run on a scratch tree

- [x] Universal fact (`topics: []`), tagged with a topic no level has, then taken back three
      ways, comparing the whole store by sha256 with its state before the tagging: with
      `--universal` byte-identical; with `--clear` the body differs (the `topics:` line is
      gone). A fact that had `python` before: `--topics python` byte-identical. A fact never
      tagged: `--clear` byte-identical. Each printed `set topics on 1 fact(s); 0 unchanged`.
- [x] 25 facts tagged with a topic no level has: the dry run printed `<anchor>: +25 added`,
      `--json` named 20 under `examples` -> `added`; after taking those 20 back it printed
      `+5 added` and named the 5.
- [x] A fact tagged earlier, its only level's `TOPICS:` then changed: the dry run printed
      `<anchor>: +1 added` for it. `set-level-topics --proj <level> --topics <earlier>` printed
      `topics updated: <level>`; the dry run then printed `would change 0 level(s)`, the store
      was byte-identical to before the change, and `topics-stale` printed `fresh`.

## RED (text before this change), opus

- [x] `redcheck --corpus-cascade` on the scenario: clean.
- [x] Universal fact: the probe reached `--universal` only from a background sentence of the
      prompt and marked it "my reading, not a quote". A fact tagged before the run: "NOT
      STATED". More than 20 arrivals: a loop, marked "my construction".

## GREEN (new text), opus and haiku

- [x] opus: `set-topics --proj /t --slug fact-u --universal` ("Do not use `--clear`"); the
      earlier topics again for a fact that had some; `--clear` for a never-tagged one;
      `set-level-topics --proj /t/site --topics web` with "Do not change its binding"; the
      repeat until the top's line counts none of the step's facts; auto keeps every binding and
      the level's new topics and prints the costs.
- [x] haiku (final text), options: B, C, A, B, B, each with the deciding sentence quoted; auto:
      "Nothing is taken back."
- [x] Lost results: none.

## Gaps reported, and what was done

- [x] How a fact tagged before the run is found beyond the first 20 names (opus): closed, "once
      this step's facts are taken back, the names the dry run still lists are such facts"; the
      haiku run on that text answered the level restore.
- [x] The flag that sets explicit topics (opus): declined, step 5's own bind paragraph shows
      `set-topics ... --topics`; the probe saw one paragraph.
- [x] Restoring a level could bring facts tagged for its new topic in this run to the top
      (opus): declined, those are facts this step tagged, so the first rule takes them back and
      the repeat ends only when the top's line counts none of them.
- [x] Order of the level restore and the fact take-backs (haiku): declined, either order ends
      in the same dry-run requirement.
- [x] In auto mode only 20 arrivals are named while each cost is printed (opus, haiku): left
      open and reported; it predates this change and needs an engine answer, not wording.
- [x] How the byte cost is taken, any bound on the repeat (haiku): declined, the cost is
      defined in the paragraph and each round removes at least one arrival.

## Final checks

- [x] 2 tiers, 3 cells. Width and fence check over the added lines: no output. ASCII only.
