# skill-writer checklist - meta-dream-tree (what "corroborated" means; a held candidate in the report)

- [x] Change: references/dream-core.md's propose-mode bullet defines a corroborated promotion to
      the top as one the gate lets through (`should-promote` printed `promote`, or a user-stated
      concrete rule, whatever that verb prints) and says the report never lists it as a proposal;
      the report contract lists it as applied with its cost in every mode and a held candidate as
      held, by slug, with no cost.
- [x] Decisions: d-20261120-f5b8a1b5, d-20261120-1635ff74
- [x] Step 0b: `skill_decisions.py show meta-dream-tree` (all, and `--kind rejected,removed
      --full`) read before the first edit. No rejected or removed entry concerns promotions; the
      live entries propose-mode-top-carve-out and report-cost-lines keep their anchors, and the
      pinned phrases in hooks/tests/test_dream_skill_contracts.py are unchanged.
- [x] Ground truth: `self_improve_signals.should_promote` returns True for source `user` or the
      `eager` knob, and `dream_state.py should-promote` always passes `inferred`, so it prints
      `hold` for a user-stated rule seen in one project. meta-dream-tree step 5 already says a
      held candidate is reported as held.
- [x] RED (pre-edit text of dream-core.md and meta-dream-crosstree SKILL.md, text-only probes):
      for a user-stated rule with `hold` printed, opus answered PROPOSE and haiku NOT MOVE, both
      with NONE as the governing sentence; for a held inferred candidate both answered NONE for
      the report line.
- [x] GREEN (edited text): opus and haiku applied the user-stated rule and listed it as applied
      with its cost, listed the held candidate as held with no cost, and quoted the new sentences.
- [x] Final re-probe on opus for the touched question, on the final text: applied, quoting the
      new sentence; no new undecided gap.
- [x] Gaps declined: whether `dream_state.py promoted` runs after a lift below the top, how a
      rule is proven user-stated, and a cost before the line is written predate this change and
      sit outside it (both RED and GREEN raised them); the misplacement-or-promotion split is
      decided by the table in the same file.
- [x] Contract tests: hooks/tests/test_dream_skill_contracts.py, 25 passed.
- [x] Width and fence check over the added lines printed nothing; ASCII only; description
      unchanged; no history lines, private hosts or paths.
