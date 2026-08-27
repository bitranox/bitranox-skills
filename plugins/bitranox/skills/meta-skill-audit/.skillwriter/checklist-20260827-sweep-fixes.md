# skill-writer checklist - meta-skill-audit (2026-08-27, sweep fixes)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The defect class is a FACTUAL claim, so the RED is a
      ground-truth check against the code or the upstream document, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft, and the arm cannot fail honestly.
      The artifact check is immune to that.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] Step 1 was UNEXECUTABLE: it said to set `cross_tree_search` "via `save_config` in
      `self_improve_signals`", which is a library function - that module has no argparse and no
      `__main__`, so there is nothing to run. Verified the shipped alternative works:
      `settings.py view` prints the config and `settings.py` has `main()` plus a usage line.
      Step 1 now gives two runnable commands, including capturing the old value before the sweep.
- [x] Same gap at step 3 ("restore the setting") is closed by the same front door.
- [x] Added step 4b, from a defect measured in this round's own triage. RED: the skill said nothing
      about re-verifying a findings list against a CHANGED tree, and its step-4 rule ("an unfindable
      quote means the finding is fabricated") inverts into a plausible wrong one on a second pass.
      Evidence both ways: `[2]` and `[119]` had lost their quotes and were still open (incidental
      requoting; a quote normalized at record time), while `[113]` and `[114]` kept theirs and were
      fixed (the repair made the documented command work, so the example correctly persists).
      An 11-of-134 heuristic that is wrong in both directions decides which defects ship.
- [x] REVISED after the decision review: the pre-pass now ABORTS the sweep instead of failing open.
      Fail-open is wrong here specifically because the degraded output is indistinguishable from
      success - an empty map renders as "the pre-pass found no mechanical hits here", so every
      reviewer would re-derive the same hits at full price behind one NOTE in a run that prints
      hundreds. A hook fails open because a wedged turn is worse than a missed check; a sweep is the
      opposite trade, being long, paid per target, and trivial to restart.
- [x] The first RED for this asserted NOTHING and was replaced: a room pointed at a file does not
      raise (rglob over a non-directory returns empty), so the fixture never produced the failure it
      claimed to test. Added a real injection seam (`compute`, the same shape as `runner` here and
      `run` in script_prepass) and a collaborator that genuinely raises.
- [x] RED-verified by mutation: reverting the raise to the old fail-open makes the abort test fail,
      with `__pycache__` cleared first. A negative control asserts the default seam is the REAL
      pre-pass, so `compute` cannot quietly default to something inert.
