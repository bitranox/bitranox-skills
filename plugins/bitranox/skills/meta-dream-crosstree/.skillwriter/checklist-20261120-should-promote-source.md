# skill-writer checklist - meta-dream-crosstree (should-promote --source; obey the printed word)

- [x] Change: Mode's gate-passed promotion is "`should-promote` printed `promote`" with no
      separate user-stated clause; step 4 says should-promote prints the verdict the run obeys,
      with `--source user` added for a user-stated concrete rule, and scopes the verify-the-keys
      check to a model-inferred `promote`.
- [x] Decisions: d-20261120-8754ea39, d-20261120-a5ec3244
- [x] Step 0b: `skill_decisions.py show meta-dream-crosstree` read before the edit;
      d-20261120-8754ea39 supersedes d-20261120-a4c9fa36 (same anchor, decision text updated).
- [x] Code: dream_state.py should-promote `--source user` prints `promote` for a slug sighted in
      one project (meta-dream-tree tests/test_dream_state.py, RED on the previous script).
- [x] Probe on the final text (case B), opus and haiku: both ran
      `should-promote <slug> --source user`, read `promote`, quoted "VERIFY a model-inferred
      `promote` before acting on it" to skip the key check, applied the promotion with its cost
      in propose mode, and never acted against the printed word.
- [x] Gaps declined: proof that a rule is user-stated stays a judgement; the move command and
      backup form are covered by step 1 and the core.
- [x] Not a mirrored pair. Contract tests 25 passed. Width and fence check over the added lines
      printed nothing; ASCII only; description unchanged.
