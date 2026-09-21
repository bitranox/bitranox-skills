# skill-writer checklist - meta-memory-settings (2026-09-21, classifier knobs)

Five new rows in the knobs table: `classifier_backend`, `classifier_model` and the three
first-wave site knobs `classifier_stop_signal`, `classifier_skill_router`, `classifier_recall_rerank`.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The test is a retrieval scenario: can a reader find which knobs to set,
      what leaves the machine, and whether the hook's decision changes.
- [x] Inherited coverage checked with `redcheck --corpus-cascade` from the repo root: it reported two
      CLAUDE.local.md files on shared generic terms (classifier, commands, quote). Neither contains
      `jev`, `typesafe` or a `classifier_` knob name (grep count 0 in both), so the behavioural arm
      was kept.
- [x] Arms pinned to the least inferential tier (haiku) on the inert `bitranox:baseline-probe` type,
      skill text pasted and Skill invocation forbidden, so neither arm could answer from the
      installed copy.
- [x] RED (pre-change text): NONE for all three parts - the table had no classifier knob.
- [x] GREEN (new text): `settings.py set classifier_backend jev` and
      `settings.py set classifier_stop_signal shadow`, each claim backed by a verbatim quote:
      "`jev` does nothing on its own: each site below must ALSO be set to `shadow`", "SENT: the last
      user message and the last assistant reply, each capped at 4000 characters, secrets replaced
      by `[REDACTED]`", "Shadow NEVER changes a hook's decision - the regex still decides".
- [x] Both dispatches asked for a `Skill gaps` section. RED listed the missing knobs; GREEN reported
      none. Nothing the baseline produced is missing from GREEN.
- [x] Coverage: every `DEFAULT_CONFIG` key has a row in this SKILL.md and in `docs/reference.md`
      (scripted comparison, zero missing in both).
- [x] Each row's SENT statement matches the code: `classifier.FIELD_CAP` 4000,
      `recall-memory.SHADOW_SHORTLIST` 30 and `SHADOW_NOTE` 600, redaction in
      `classifier.prepare_state`.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added beyond the documented user-home locations.
- [x] Present tense, no session narrative, no private provenance.
