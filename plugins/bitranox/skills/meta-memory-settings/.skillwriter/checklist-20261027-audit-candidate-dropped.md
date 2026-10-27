# skill-writer checklist - meta-memory-settings (2026-10-27, `classifier_audit_candidate` row removed)

The `audit_candidate` classifier site is removed from the code (classifier.py, self-improve-audit.py,
self_improve_signals.py defaults, settings.py ENUM_CHOICES), so its settings row is removed. One
row deleted, nothing else in SKILL.md changed.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - which knob a reader sets for a given hook.
- [x] RED by text check against the pre-change file: the row offers `classifier_audit_candidate` =
      `shadow`, a key `settings.py set` now refuses as unknown (exit 2, pinned by
      `test_a_retired_site_is_an_unknown_key[classifier_audit_candidate]`).
- [x] Claim checked against the code: `git grep -n audit_candidate -- plugins docs` leaves only the
      tests that pin the removal and older checklists; `settings.py` has no ENUM entry,
      `DEFAULT_CONFIG` no key.
- [x] Table still canonical after the deletion: `reformat_tables.py --check` reports Unchanged.
- [x] GREEN by quote-back on the classifier rows (opus at effort medium, plus haiku; 3 questions):
      both tiers answer NONE for a knob that has Jev judge the `<SELF-IMPROVE-AUDIT>` candidates
      and name `classifier_stop_signal` / `classifier_subagent_signal` only as rows that could be
      misread, each rejected from its own text; both list exactly the four `decide` sites and
      quote "There is no `decide` mode." for `classifier_jig_repetition` alone.
- [x] Gaps, each decided:
      - opus saw the branch name `jev28/audit-candidate` through its environment and guessed a row
        might exist outside the excerpt - DECLINED: environment contamination, not the text; it
        still answered NONE from the table.
      - `classifier_skills` lacks the "There is no `decide` mode." sentence its sibling carries -
        DECLINED: predates this change; its value column lists only `off` and `shadow`.
- [x] Re-probe: no fix was made, so the GREEN run is the final-text run.
- [x] Tiers: opus + haiku, 2 cells, 3 questions each.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, hostname or machine path added; ASCII only; no version-history phrasing.
