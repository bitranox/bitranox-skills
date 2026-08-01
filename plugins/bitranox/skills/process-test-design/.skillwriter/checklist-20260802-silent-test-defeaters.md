# skill-writer checklist - process-test-design (2026-08-02, two more silent test-defeaters)

Change: two mechanics added to the "silently defeat a test that looks right" list - a shared module
BASENAME making pytest exercise the wrong file, and a doctest teardown on the last line that never
runs. Ships with plugin 5.139.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, issued for this batch).
- [x] Both come from measured incidents, not speculation. The basename collision was found IN this
      plugin: `strip_typographic_tells.py` shipped byte-identically under two skills, the German copy
      loaded first, and the English tests exercised it - which is why the previous release's fix read
      as absent in the full run while passing in isolation. The doctest leak cost a CI-red release
      cycle on btx_lib_mail 1.5.0.
- [x] Placed by SYMPTOM, not by topic. Both belong to the existing "silently defeat a test that looks
      right" list because both leave a GREEN suite - that is the reader's entry point, and the list
      header was updated from "Two mechanics" to "Four" rather than left stale.
- [x] Each states the TELL, not just the rule: a fix that reads as absent in the full run while
      passing in isolation; failures that land far away and look unrelated to the doctest. A rule
      without its symptom does not fire when it is needed.
- [x] Verified ABSENT before writing, and PRESENT after, with `claim_check` (control-gated, so an
      "absent" verdict proves the file was actually read).
- [x] Checked against the WHOLE skill tree, not just this file: an earlier per-target check reported
      the single-layer-mutation rule absent when line 229 already carried it, because the pattern
      used hyphenated "defense-in-depth" and the file says "defense in depth". That item was dropped
      from the queue as already shipped rather than duplicated.
- [x] No session narrative, no private paths, no machine-specific detail in the shipped text.
- [x] Suites green and `repo-gate.py --ci` clean with the CI dependency set.
