# skill-writer checklist - meta-claude-hooks (2026-11-01, a kept refusal names a passing form)

One paragraph added after the decision-log paragraph in the replay section: when a replay shows a
widened refusing guard's new firings are harmless but the refusal stays for the rare real case,
the refusal text names a command form the guard itself passes, and a test feeds that form back to
the guard. A closing sentence covers the case where the job itself is the harm (printing a
secret): offer the narrowest question that can. Nothing else in SKILL.md changed.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique; the test is application - writing the refusal text for a kept guard.
- [x] RED (opus + haiku, pre-edit section text): both answered NONE for "what must a kept refusal
      contain"; grep of the skill and its references found no coverage.
- [x] GREEN (opus + haiku, edited text): both quoted "put into the refusal text a command that
      does the same job and that the guard itself lets through" and the feed-it-back test.
- [x] Gap from both GREEN probes - what "the same job" means when the job is to print a secret -
      FIXED with the narrowest-question sentence, naming the forms the hook really offers
      (`grep -c NAME .env`, `cut -d= -f1 .env`, read from `Shape.SECRET_FILE` in
      block-env-dump.py). Gaps DECLINED: a numeric threshold for "harmless" (judged per replay, the
      replay rules above already govern it); whether the test goes through the hook entry point
      (the named example test is the model).
- [x] Re-probe on the final text (haiku): quoted the narrowest-question sentence and named
      `grep -c NAME .env` / `cut -d= -f1 .env` plus the feed-it-back test. Remaining gaps
      (no operational definition of "narrowest", `cut` edge cases) DECLINED: judgement per
      guard, and the required test is what catches a leaking offer.
- [x] Claims checked against the code: the `git remote -v | sed` offer is in block-env-dump.py's
      offer table; `test_git_remote_refusal_offers_the_full_listing_redacted_and_the_offer_passes`
      exists in hooks/tests/test_block_env_dump.py.
- [x] Tiers: opus + haiku (RED, GREEN), haiku (final).
- [x] Description unchanged - no routing keyword moved.
- [x] Added lines within width; ASCII only; no address, hostname or machine path; no history
      phrasing.
