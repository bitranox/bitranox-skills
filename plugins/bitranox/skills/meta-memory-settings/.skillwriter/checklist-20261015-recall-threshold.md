# skill-writer checklist - meta-memory-settings (2026-10-15, recall threshold 0.9)

The `classifier_recall_rerank` row's decide sentence changes one number: recall injects the notes
Jev scores at 0.9 or more (was 0.8), following `SITE_THRESHOLDS["recall_rerank"]`, which this change
raises to 0.9. No other cell's text changed; the row keeps its length, so the table stays canonical.
`docs/reference.md` carries the same change in its own row.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the change is one stated value that must equal a code constant.
- [x] Route: a mechanical text check of the artifact against the code, not a behavioural arm. The
      installed copy of this skill states the old value and the inert probe type keeps the Skill
      tool, so a retrieval arm could answer from the installed text in both arms; and a single
      stated number has no judgement for an agent to get wrong.
- [x] RED: `tests/test_settings.py::test_a_decide_row_states_the_threshold_the_site_acts_at`
      (new) asserts each decide row names "at <SITE_THRESHOLDS[site]> or more". Against the
      pre-change row with the constant at 0.9: `[recall_rerank]` FAILED ("at 0.9 or more" not in
      the row), `[stop_signal]` passed - the control that the row lookup reads the right line.
- [x] GREEN: with the row at 0.9, both arms pass; the module's 87 tests pass.
- [x] The statement matches the code: `recall-memory._decide_recall` keeps scores
      `>= classifier.SITE_THRESHOLDS["recall_rerank"]`, now 0.9; pinned by
      `hooks/tests/test_recall_memory_decide.py` (a 0.89 note is not injected, a 0.90 note is) and
      `test_classifier_eval.py` (the constant is 0.9).
- [x] Skill gaps: none raised; no dispatch was made (see Route).
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
