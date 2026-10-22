# skill-writer checklist - ai-llm-jev-judge (2026-10-22, fold23 batch 3, reach-fails rows)

- [x] Change: Question design (extends the existing 'only to fields every item has' bullet) +
      Workflow step 4 Pilot. Verified against ground truth: Hedging instead of an error, with
      0.66-0.70 against a 0.7 threshold vs 0.89-0.90 when the field is present ->
      plugins/bitranox/hooks/classifier.py:546-553 (the comment states 'answers by HEDGING rather
      than erroring, so there is no failure to notice ... scored 0.66-0.70 there against its own 0.7
      threshold, and 0.89-0.90 (negative 0.05-0.06) with the fields present'). The two remedies
      (send the field with an explicit empty marker, or ask a variant that does not name it) come
      from the fact body's How to apply. Variant selection is what the reference implementation
      does: classifier.py:554 _CONTEXT_FIELDS and :557 _have() name a field only when the caller
      sent it.
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over; the coordinator re-checked in the source: the hedge measurement and the
      variant selection in hooks/classifier.py (_CONTEXT_FIELDS, _have).
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded the skill through the Skill tool before its first edit.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot, opus at effort medium):
      partial for scenario 1. Behavioural RED replaced on purpose: each rule is in the always-loaded
      memory index of the authoring machine (inherited coverage), so the RED is a quote-back against
      the pre-edit file.
- [x] GREEN quote-back on haiku and on opus at effort medium against the edited files; every quote
      checked present by a fragment check, each weak fragment traced to a sentence revised after
      GREEN or to a quote splicing two files.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Pass also run on the weakest tier: haiku arm beside opus for every scenario; tiers haiku and
      opus, one cell per scenario per tier. No later fix touched this skill, so the GREEN run is on
      the final text.
- [x] Gaps closed or declined: declined - which remedy to prefer and what an empty marker looks like
      (the measurement shows the hedge, not which remedy works better, so the skill offers both),
      how to move the sparse item into the first ten lines (step 4 already says to put it among
      them).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, field names, repo file paths or reserved examples (/path/to/scratch).
