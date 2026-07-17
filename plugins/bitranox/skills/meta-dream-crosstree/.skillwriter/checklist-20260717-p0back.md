# skill-writer checklist - meta-dream-crosstree (2026-07-17, misplacement audit pass)

Change: added step 4b, the wrong-TREE misplacement audit, with the new
`reconcile_memory_index.py --check-misplaced <anchor>` detector and the engine's new `relocate`
verb. This is the mode's structural privilege: a fact captured while cwd was another repo lands in
the wrong tree's store, and nothing inside that tree can tell it is foreign - meta-dream-tree sees
one tree and cannot notice by construction.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: verified in code - memory_engine.move_entry hard-refuses cross-tree ("cross-tree move
      ... use a lift/copy"), so the ONLY cross-tree path was a duplicating copy that leaves the
      stale original. A misfiled fact was therefore permanent. Failing tests written first.
- [x] GREEN: relocate_entry (copy body to target anchor -> point there -> drop source pointer ->
      archive source body) + find_misplaced detector; 8 engine + 4 reconcile tests green; verified
      end-to-end through the CLI on a real two-tree fixture (--check-tree clean on both after)
- [x] Detector states its own uncertainty: a cited neighbour path is EVIDENCE, not proof, so the
      pass says JUDGE each candidate and expect rejections - it reports, never auto-relocates
- [x] Dogfooded: run over the real tree found exactly 1 candidate, which I judged and REJECTED (a
      universal rule correctly homed at the top that merely cites a hook path). Low false-positive
      rate confirms the "cites only one other tree, and none of its own" heuristic is tight.
- [x] Homed per the plan's decision: cross-tree modes only (tree/nap cannot see a second tree)
- [x] Security scan: prose + stdlib only, no secrets, hostnames, or private paths
- [x] CSO description: unchanged (body edit only)
