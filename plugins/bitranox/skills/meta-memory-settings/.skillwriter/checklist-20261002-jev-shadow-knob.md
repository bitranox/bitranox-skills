# skill-writer checklist - meta-memory-settings (2026-10-02, classifier_skills knob)

One new row in the knobs table: `classifier_skills` (off / shadow), gating the planned "Jev
shadow" skill-steps pipeline alongside `classifier_backend`.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference, settings-table row. This is NOT a behavioural claim the skill makes
      about its own reasoning - it is a config knob whose contract is enforced in code
      (`ENUM_CHOICES` in `settings.py`, `DEFAULT_CONFIG` in `self_improve_signals.py`). The honest
      verification for this kind of change is the settings test suite, not a RED/GREEN retrieval
      scenario: there is no model behaviour to probe yet, since no skill step reads this knob
      until the Jev-shadow pipeline (a later task) is wired up.
- [x] RED: `test_classifier_skills_defaults_to_off_and_accepts_shadow` and the
      `classifier_skills` case added to `test_classifier_site_refuses_a_mode_it_does_not_have`
      failed before the knob existed (`KeyError: 'classifier_skills'` /
      `unknown key 'classifier_skills'`).
- [x] GREEN: both pass after adding the knob to `ENUM_CHOICES` and `DEFAULT_CONFIG`; the
      existing `test_set_still_accepts_every_documented_enum_value` also covers it generically.
- [x] Scope held: only `off` and `shadow` are valid values. `decide` is explicitly refused
      (parametrized test) - Task 10 (per-site decide mode) decides whether `classifier_skills`
      ever gets one; this task does not add it.
- [x] Coverage: `docs/reference.md` row added (`test_reference_doc_documents_every_config_knob`
      iterates `DEFAULT_CONFIG` and requires every key to appear there) and `SKILL.md` row added
      with the exact Default/effect/who-when text from the task brief.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added beyond the documented user-home locations.
- [x] Present tense, no session narrative, no private provenance.
