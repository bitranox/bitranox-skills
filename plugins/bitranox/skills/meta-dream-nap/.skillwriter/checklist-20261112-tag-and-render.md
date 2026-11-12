# meta-dream-nap: tag the directory and render the chain

Scope: `SKILL.md` step 4 (a fact the routing answers with TOPICS), the new step 4b (topics of
the cwd's level, `render-topics --scope chain`, a line arriving at the tree top), step 6 (the
chain check's `repeated line`, the deferred list) and one deliverable.

## Step 0b

- [x] `skill_decisions.py show meta-dream-nap --kind rejected,removed --full`: one rejected entry
      (d-20261106-57ee2fca, the reconcile verify step). Unrelated; the step stays.
- [x] `skill_decisions.py show meta-dream-nap`: live rule `move-to-top-by-mode`
      (d-20261110-f1fa0763) keeps its anchor; step 4b applies the same rule to a rendered line.
- Decisions: d-20261112-06ead751, d-20261112-0c1ccf2d, d-20261112-4c390e7a

## Commands run on a scratch tree (levels top, a, a/py, b, b/py, c, c/web; list python, web)

- [x] `topics-show --proj <level>`: exit 0 with the list; in a tree without one,
      `no topic list in this tree`, exit 1.
- [x] `topics-stale` on a level without a descriptor: `stale: no descriptor`, exit 1; on a level
      with a descriptor and no line: `stale: never tagged`, exit 1; after `set-level-topics`:
      `fresh`, exit 0; after a `set-scope` that changed the text:
      `stale: descriptor changed since its topics were chosen`.
- [x] `set-level-topics` on a level without a descriptor:
      `! refused: <level> has no descriptor yet (set-scope writes one)`, exit 2. At the tree top:
      `! refused: <top> is the tree top: its topics are the user's decision (set-top-topics, on
      the user's word)`.
- [x] `set-scope --scope-file`: `scope updated: <level>/CLAUDE.local.md`. `set-level-topics`:
      `topics updated: <level>`.
- [x] `render-topics --proj a/py --scope chain --dry-run`, a fact bound to python with its line
      at b/py only: `<S>/treeA/a/py: +1 added, 0 refreshed, -0 removed` and
      `render-topics (chain): 1 managed fact(s); would change 1 level(s)`; the real run:
      `render-topics (chain): 1 managed fact(s); changed 1 level(s)`. sha256 of every
      `CLAUDE.local.md` before and after: only a/py's changed.
- [x] The level above then given the topic: the chain render printed `a: +1 added` and
      `a/py: +0 added, 0 refreshed, -1 removed`; b/py unchanged.
- [x] `repeated line`: a line left at a/py while `a` holds it made the chain check print
      `! repeated line: feedback-x at <S>/treeA/a/py is also held by <S>/treeA/a above it;
      hooks/memory_engine.py render-topics --proj <S>/treeA/a/py --scope chain drops the lower
      copy`, `TOTAL problems: 1`; after that render, `TOTAL problems: 0`.
- [x] A line arriving at the top: `set-level-topics --proj c/web --topics ''` on a level that
      had `TOPICS: web` made the chain dry run print
      `<S>/treeA: +1 added, 0 refreshed, -0 removed`; setting `web` again made it print
      `would change 0 level(s)`, the store byte-identical to before, `topics-stale` then `fresh`.
- [x] `move` of a placed fact: `! refused: '<slug>' is placed by topic: where it is read follows
      its topics and the levels' ...`, exit 2.

## RED (pre-edit steps 3-6), opus

- [x] `redcheck --corpus-cascade`: `clean - no inherited coverage, no telegraphing found`
      (1919 documents read).
- [x] Coverage check on the pre-edit file: no occurrence of `render-topics`, `set-level-topics`
      or `topics-show`.
- [x] Topics of a/py: "NOT STATED. The excerpt never mentions topics". The bound fact's line:
      "the nap does nothing. No command is stated." A fact that "holds wherever Python is used,
      in more than one branch": moved to the tree top by the mode, quoting the move-to-top
      sentence; "Tagging `ref-q` with the topic `python` instead of moving it: NOT STATED."

## GREEN (new text), opus and haiku

- [x] opus: `topics-stale`, `set-level-topics --proj a/py --topics python` requiring
      `topics updated:`, the chain dry run, then the real render requiring its last line. b/py's
      block, level a's TOPICS and the top's TOPICS: no, each with its sentence. The TOPICS-routed
      fact: "does not move or tag it, in any mode". A stale ancestor: named in the deferred list.
      Tree without a list: "No part of step 4b runs beyond the `topics-show` probe itself."
- [x] haiku (final text, cwd level without a descriptor): `set-scope --scope-file` requiring
      `scope updated:`, then `set-level-topics --proj a/py --topics python`, the dry run, the real
      render. Sibling, ancestor topics, top topics: NO, three quotes. TOPICS-routed fact in auto
      mode: "NEITHER". The level that had `TOPICS: web`, propose mode, top line `+1 added`:
      `set-level-topics --proj c/web --topics web`, propose, dry run again, "the real render does
      NOT run in this pass" while the top line counts one.
- [x] Lost results: none; the pre-edit answers held no action for these questions.

## Gaps reported, and what was done

- [x] No test for "this step's own `set-level-topics` caused it" (opus): closed, the text now
      keys on "replaced a `TOPICS:` line the level already had" and covers a level with no line
      to restore; haiku re-probe on the final text followed it.
- [x] No command to find a stale ancestor (opus): closed, "`topics-stale` (a read)".
- [x] The rule for choosing topics and the descriptor template are not in step 4b (opus,
      haiku): declined, single-sourced in `bitranox:meta-dream-tree` step 0b, "Topics of a
      level" and the template block, which 4b cites; the contract tests forbid a second copy.
- [x] "Cost" not defined in 4b (opus, haiku): declined, step 4 of the same file defines it
      ("the bytes it adds to the top block") and dream-core.md's Mode gives the formula.
- [x] Where `render-topics` puts a line is not explained (opus): declined, 4b states what the
      chain render adds and drops; the full placement rule is in
      `meta-self-improve/references/memory-backend.md`.
- [x] The real render is all or nothing when the top would gain a line (opus): decided, see
      d-20261112-4c390e7a; `render-topics --help` offers `--scope tree|chain` only, no way to
      leave out one level.
- [x] After the restore the level reads `fresh`, so the proposed change lives in the report
      only (opus): declined, measured above; the same holds for the tree dream's restore.
- [x] `--proj <cwd>` beside `--proj <cwd level>` (opus): declined, the file's Scope section
      defines the cwd's level as the first rung of the chain.
- [x] Waiting on the placement lock, and a missing success line (opus, haiku): declined,
      `bitranox:meta-dream-tree` step 5 covers the lock and dream-core.md's verification
      contract a missing success line.

## Final checks

- [x] 2 tiers, 3 cells (opus RED, opus GREEN, haiku GREEN on the final text). The haiku run
      raised no new undecided gap.
- [x] Width and fence check over the added lines: no output. ASCII only.
- [x] `skill_decisions.py check`: 0 findings.
