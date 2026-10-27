# skill-writer checklist - meta-memory-settings (2026-10-27, `classifier_backlog_ask` row removed)

The `backlog_ask` classifier site is removed from the code (classifier.py, recall-memory.py,
self_improve_signals.py defaults, settings.py ENUM_CHOICES), so its settings row is removed. One
row deleted, nothing else in SKILL.md changed.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - which knob a reader sets for a given hook.
- [x] RED by text check against the pre-change file: the row offers `classifier_backlog_ask` =
      `shadow`, a key `settings.py set` now refuses as unknown (exit 2, pinned by
      `test_the_retired_backlog_ask_site_is_an_unknown_key`).
- [x] Claim checked against the code: `git grep -n backlog_ask -- plugins docs` leaves only the
      tests that pin the removal; `settings.py` has no ENUM entry, `DEFAULT_CONFIG` no key.
- [x] Table still canonical after the deletion: `reformat_tables.py --check` reports Unchanged
      (the widest key, `classifier_subagent_signal`, still sets the first column).
- [x] GREEN by quote-back on the classifier rows (opus at effort medium, plus haiku; 3 questions):
      both tiers answer NONE for a knob that shadows recall's backlog skip and refuse to read
      `classifier_recall_rerank` as covering it ("covers ranking, not the decision to skip");
      both list exactly the four `decide` sites and quote "There is no `decide` mode." for
      `classifier_jig_repetition`.
- [x] Gaps, each decided:
      - what `decide` does, the SENT list per site, which steps `classifier_skills` covers -
        DECLINED, covered: the probe was shown abbreviated rows; each full row in SKILL.md
        states its SENT list and its `decide` behaviour.
      - "a backlog-ask site may be folded into recall_rerank" (opus) - DECLINED: both tiers
        rejected that reading from the row text itself; no row names it, which is the truth.
      - `classifier_skills` lacks the "There is no `decide` mode." sentence its siblings carry
        - DECLINED: predates this change; its value column lists only `off` and `shadow`.
- [x] Re-probe: no fix was made, so the GREEN run is the final-text run.
- [x] Tiers: opus + haiku, 2 cells, 3 questions each.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, hostname or machine path added; ASCII only; no version-history phrasing.
