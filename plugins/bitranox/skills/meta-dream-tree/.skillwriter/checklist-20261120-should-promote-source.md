# skill-writer checklist - meta-dream-tree (should-promote --source; obey the printed word)

- [x] Change: dream_state.py should-promote takes `--source inferred|user` (default inferred) and
      passes it to self_improve_signals.should_promote. dream-core.md and step 5 ask it with
      `--source user` for a user-stated concrete rule and obey the printed word everywhere; the
      "whatever that verb prints" override is gone; the key check before acting on a `promote`
      is scoped to a model-inferred fact (a `--source user` verdict rests on no key).
- [x] Decisions: d-20261120-86da333f, d-20261120-b6d93e6c
- [x] Step 0b: `skill_decisions.py show meta-dream-tree` read before the edit; d-20261120-86da333f
      supersedes d-20261120-f5b8a1b5, whose anchor the edit removes; the decision about the
      script is in dream_state.py's module docstring `Decisions:` block.
- [x] Code RED/GREEN: the new tests in tests/test_dream_state.py failed on the previous
      dream_state.py (7 failed: `unknown option(s): --source`, exit 2) and pass now;
      mutation_arm KILLED test_a_user_stated_rule_seen_in_one_project_promotes_with_source_user
      when the call passed "inferred" again, and KILLED
      test_should_promote_without_source_still_judges_a_model_inferred_candidate with
      dream_state.py reverted to origin/master. Default calls answer unchanged.
- [x] Probe on the final text (case B: user-stated rule, one project, propose mode), opus and
      haiku: both ran `should-promote <slug> --source user`, read `promote`, skipped the key
      check quoting "a `--source user` verdict rests on no key", applied the move with its cost,
      and answered that they never act against the printed word.
- [x] REFACTOR: both tiers noted step 5's key exception named no source; it now reads "a
      model-inferred `promote`" with "a verdict asked with `--source user` rests on no key". A
      haiku re-probe of that sentence: the exception does not apply to B, the printed word is
      obeyed.
- [x] Gaps declined: nothing verifies that a rule really is user-stated (a judgement the skill
      leaves to the reader, as before); the move mechanics and the `promoted` key clearing are
      covered elsewhere in the skill and lie outside this change.
- [x] Tests: hooks/tests/test_dream_skill_contracts.py and skills/meta-dream-tree/tests/,
      701 passed; the pinned "corroborated" phrases are unchanged.
- [x] Width and fence check over the added lines printed nothing; ASCII only; description
      unchanged.
