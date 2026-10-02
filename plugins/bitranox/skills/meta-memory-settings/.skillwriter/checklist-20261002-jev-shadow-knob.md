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

## Final-review fixes (2026-10-02)

Scope: the `classifier_skills` row now says what is SENT, as the other classifier rows do: the
hook and body of every fact in the swept tree(s), other projects' note texts, guard commands with
their error output, code lines, CLAUDE.md section bodies, each redacted and capped. It is the
consent text for the knob. `docs/reference.md` carries the same list.

- [x] Text check against the source of truth: each listed kind is the state of a shipped site in
      `meta-self-improve/jev_sites/` (hook/body: dream-*, crosstree-misplaced; candidate:
      collect-relevance; command/error: guard-firing; hit/context/source_line: data-arch-dict,
      quality-*; variants: consolidate-cause), and every one passes `prepare_state` in `run`.
- [x] No behaviour changed: the knob's values, default and effect are as before; this row is
      reference text, so the check is the text against the site files rather than a pressure
      arm.
- [x] Diff reviewed: prose only, ASCII, no secret, address, hostname or real user path.
