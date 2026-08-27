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
