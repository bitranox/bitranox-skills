# meta-dream-crosstree: a fact crosses trees untagged

Scope: `SKILL.md` step 2 (a lifted or copied fact arrives untagged) and step 4b (a misfiled
fact that is placed by topic: one candidate, un-bound before `relocate`).

## Step 0b

- [x] `skill_decisions.py show meta-dream-crosstree --kind rejected,removed --full`: one rejected
      entry (d-20261110-8ee5b8fa, an `off` behaviour for a 4b relocate). Kept: the new paragraph
      names `propose` and `auto` only.
- [x] `skill_decisions.py show meta-dream-crosstree`: the live rules `relocate-to-top-by-mode`
      and `relocate-expected-difference` keep their anchors.
- Decisions: d-20261112-b998a8d7, d-20261112-e6a47125

## Commands run on two scratch trees (A with a topic list, B without)

- [x] `reconcile_memory_index.py --check-misplaced <A>` with one fact bound to python, a line at
      two levels, its body citing only B's paths: two `? mis-1 [<level>]` entries, each with its
      own `relocate --from-level <level>` command, and `TOTAL misplaced: 2`.
- [x] `relocate` of it: `! refused: 'feedback-x' is placed by topic: where it is read follows its
      topics and the levels' (set-topics, set-level-topics, then render-topics). To place it by
      hand, un-bind it first: hooks/memory_engine.py set-topics --proj <S>/treeA --slug
      feedback-x --clear (its lines collapse to one at the tree top, where a move or relocate
      takes it)`, exit 2.
- [x] `set-topics --proj <A> --slug <slug> --clear`: `set topics on 1 fact(s); 0 unchanged` and
      `~ note: 1 un-bound fact(s) had a line at several levels; each now has one line, at the tree
      top: mis-1`. The audit then printed one entry, `--from-level <S>/treeA`, `TOTAL misplaced:
      1`.
- [x] `relocate --from-level <A> --to-level <B>/proj`: `relocated feedback-x: <S>/treeA ->
      <S>/treeB/proj (CROSS-TREE: body moved + source archived)`; `--check-tree` on both trees:
      0 problems; the body in B has no `topics:` line.
- [x] A placed fact with ONE line: after `--clear` its line stood where it was, and the relocate
      from that level succeeded.
- [x] A universal fact (`topics: []`): `relocate` printed `~ note: dropped the topics: line of
      ref-plain - topics are tagged against one tree's list; tag it in the target tree with
      set-topics`.
- [x] `add` of a new fact in B whose body file carried `topics: [python]`: `! refused: 'copy-1'
      has no body file yet and the body given carries a frontmatter topics: line; topics change
      only through set-topics. Write the fact without the line, then run set-topics on it`.

## RED (pre-edit steps 2, 4b, 5), opus

- [x] `redcheck --corpus-cascade`: one hit, a stored fact about the name-based misplacement
      signal, on the shared words belongs, confirmed, misfiled, topic. That fact is about the
      audit's detector and says nothing about topics of a relocated fact: a term overlap.
- [x] Commands: the audit's printed `relocate` only. "What to do if relocate is refused: NOT
      STATED." Topics: "What relocate does with the `topics:` line: NOT STATED." Source level:
      "NOT STATED. 4b talks about 'a fact' being relocated as if it had one location."

## GREEN (new text), opus and haiku

- [x] opus: `set-topics --proj <source anchor> --slug feedback-x --clear` requiring its line,
      the audit again, the relocate it prints, from A's top. Tagged in B: "No to both", although
      B's list has the topic. Misfiles reported: "One". Propose mode: "Only the read-only
      audit". A copy whose source body has a `topics:` line: written without it, not tagged.
- [x] haiku (final text): the same order, `relocated feedback-x:` required, one misfile, no
      `set-topics` in B, nothing run in propose mode beyond the audit; a placed fact with one
      line: "the relocate is made from A/svc1".
- [x] Lost results: none.

## Gaps reported, and what was done

- [x] `<source anchor>` undefined; which command prints the `~ note:`; no success line for
      `relocate`; what the proposal shows in propose mode; when the dropped-topics note can
      still print (opus): closed in the paragraph; the haiku run on the final text used each.
- [x] How to word one fact against `TOTAL misplaced: 2` (opus): declined, "judge and report it
      as ONE fact" decides the count; the wording is the reporter's.
- [x] No check after the relocate (opus): declined, step 8's `store_manifest.py verify` and
      integrity checks cover every tree written, and a relocate is listed there as an expected
      difference.
- [x] When the target tree's dream runs (opus, haiku): declined, each tree's own
      consolidation-due nudge decides; this skill never runs a tree dream.
- [x] `relocate` syntax (haiku): declined, the audit prints the command, verified above.

## Final checks

- [x] 2 tiers, 3 cells (opus RED, opus GREEN, haiku GREEN on the final text); the haiku run
      raised no new undecided gap.
- [x] Width and fence check over the added lines: no output. ASCII only.
