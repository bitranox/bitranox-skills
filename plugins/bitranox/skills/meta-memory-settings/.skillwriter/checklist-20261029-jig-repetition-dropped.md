# skill-writer checklist - meta-memory-settings (2026-10-29, `classifier_jig_repetition` row removed)

The `jig_repetition` classifier site is removed from the code (classifier.py, jig-repetition-nudge.py,
self_improve_signals.py defaults, settings.py ENUM_CHOICES), so its settings row is removed. One
row deleted, nothing else in SKILL.md changed. The nudge itself is unchanged; only its Jev shadow
is gone.

- [x] Receipt checked fresh (`skill_receipt.py check meta-skill-writer`: fresh, age 0.0h).
- [x] Skill type: reference; the test is retrieval - which knob a reader sets for a given hook.
- [x] RED by text check against the pre-change file: `git show HEAD:.../SKILL.md | grep -c
      '`classifier_jig_repetition`'` = 1, a row offering `shadow` for a key `settings.py set` now
      refuses as unknown (exit 2, pinned by
      `test_a_retired_site_is_an_unknown_key[classifier_jig_repetition]`, which failed on the
      pre-change code with `assert 0 == 2`).
- [x] Claim checked against the code: `git grep -n -i -E 'jig.?repetition|JIG_SAME_JOB|same_job'
      -- plugins docs` leaves only the nudge hook itself, its tests, the tests that pin the
      removal, the `docs/jev-design.md` "Stays deterministic" bullet and older checklists;
      `settings.py` has no ENUM entry, `DEFAULT_CONFIG` no key.
- [x] A stale value is harmless: `load_config` drops keys outside `DEFAULT_CONFIG` and the next
      save rewrites the file without it (pinned by
      `test_a_stale_retired_knob_in_the_config_file_is_ignored_and_dropped_on_the_next_save`), and
      the nudge with a stale `shadow` sends and logs nothing (pinned by
      `test_the_jig_nudge_fires_unchanged_and_asks_jev_nothing_even_with_a_stale_shadow_knob`).
- [x] Table still canonical after the deletion: `reformat_tables.py --check` reports Unchanged
      (the widest key, `classifier_subagent_signal`, still sets the first column).
- [x] GREEN by text check of the final rows (`grep -o '^| `classifier_[a-z_]*` *| [^|]*'`):
      the four sites offering `decide` are listed with it, `classifier_skills` alone with `off`,
      `shadow`; no row names a retired site (`test_no_settings_row_offers_a_retired_site`).
      `classifier_backend`'s "(or `decide`, where its row lists it)" stays true for every
      remaining site row.
- [x] Gaps, each decided:
      - quote-back probes (opus + haiku) - DECLINED for this change: the edit only deletes a row,
        so there is no new text to quote back; the earlier drops of the same shape ran them and
        found no gap from a row deletion. Retrieval is covered by the text check above.
      - no remaining row carries "There is no `decide` mode." (`grep -c` = 0); the jig row was the
        last one with it - DECLINED: `classifier_skills` lists only `off` and `shadow` in its value
        column, which is what the sentence restated.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, hostname or machine path added; ASCII only; no version-history phrasing.
