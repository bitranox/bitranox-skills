# skill-writer checklist - meta-dream-crosstree (promotions in every mode; held candidates; counter key)

- [x] Change: Mode says the mode decides only step 4b relocates, while a promotion to a tree top
      that passed step 4's gate and a step 5 lift below a top are applied in every mode and listed
      as applied with their cost; step 4 counts a user-stated rule as corroborated and says the
      counter keys on the project path made absolute against the cwd; step 8 lists a held
      candidate as held, by slug, with no cost.
- [x] Decisions: d-20261120-a4c9fa36, d-20261120-050309c2, d-20261120-45acb36e
- [x] Step 0b: `skill_decisions.py show meta-dream-crosstree` (all, and `--kind rejected,removed
      --full`) read before the first edit; no rejected or removed entry; the live entries
      promotion-cost-per-fact and promotion-cost-below-top keep their anchors.
- [x] Ground truth: dream-core Boundaries applies a corroborated promotion to the top in every
      mode; `self_improve_signals.should_promote` returns True for source `user`;
      `self_improve_signals.proj_key` normalises the path to an absolute, dot-free form before
      hashing, so "keys on the RAW PROJECT STRING ... no normalisation" was false.
- [x] RED (pre-edit text, text-only probes on opus and haiku): a user-stated rule with `hold`
      printed was proposed (opus) or not moved (haiku), both quoting NONE; a held candidate's
      report line was NONE on both; opus also named the raw-string key claim as contradicting
      dream-core's abspath hash.
- [x] GREEN (edited text, opus and haiku): all four candidates answered as the code and ledger
      decide (gate passed: applied with cost; user-stated: applied; lift below the top: applied
      with level and cost; held: listed as held, no cost), each quoting the new sentences.
- [x] REFACTOR: GREEN opus read step 4's "new + corroborated + nowhere-else" as excluding a
      user-stated rule; step 4 now says user-stated counts. Re-probed on opus and haiku on the
      final text: applied, quoting the step 4 and Mode sentences; no new undecided gap.
- [x] Gaps declined: `promoted` after a lift below the top, proof of user-stated provenance, a
      cost before the line exists, and a held-candidates line in the counts predate this change
      and lie outside it.
- [x] Not a mirrored pair: `repo-gate.py --mirrors` lists neither dream skill.
- [x] Contract tests: hooks/tests/test_dream_skill_contracts.py, 25 passed.
- [x] Width and fence check over the added lines printed nothing; ASCII only; description
      unchanged; the example project name in step 4 is a neutral `alpha`.
