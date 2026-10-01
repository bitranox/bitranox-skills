# skill-writer checklist - meta-memory-settings (2026-10-01, decide shadows notifications)

One sentence changed in the `classifier_skill_router` row: under `decide`, a background-task
notification is still nudged as with `off`, and is now SENT to Jev in the background as with
`shadow` (status, summary, the reply before it), its answer logged as a comparison row, with
nothing waiting for it. The table was re-aligned by `reformat_tables.py`; no other cell's text
changed. `docs/reference.md` carries the same change in its own row.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Retrieval scenario under `decide`, one failed background command:
      Q1 is anything sent to Jev, Q2 does Jev's answer choose a nudge, Q3 is the answer logged,
      Q4 does anything wait for Jev.
- [x] Arms pinned to haiku on the inert `bitranox:baseline-probe` type, the row pasted, answers as
      a direct quote or NONE, each ending with a "Skill gaps" section.
- [x] RED (pre-change row): Q1, Q2 and Q4 all quoted "A background-task notification is handled
      exactly as with `off`: Jev is not asked." - Q1 is now false. Q3 NONE. Gap reported: the row
      does not say whether a notification is logged under `decide`.
- [x] GREEN (new row): Q1 quoted "it is still SENT to Jev in the background as with `shadow` - its
      status, its summary and the reply before it"; Q2 "Jev's answer never chooses its nudge"; Q3
      "that answer is logged to the shadow log as a comparison row"; Q4 "nothing waits for it".
      Gaps: none reported.
- [x] RED gap (logging under `decide`) CLOSED by the Q3 quote. Nothing RED answered is missing
      from GREEN: Q2 and Q4 keep their answers, Q1 flips as intended.
- [x] The statement matches the code: `skill-router._shadows` returns true in decide mode exactly
      when `prompt_text.notification_fields` is non-empty, `main` sends a notification past
      `_decide` to `_shadow_skill_router`, and the detached child's `get_classifier` accepts any
      site mode but `off`. Pinned by
      `test_decide_still_shadows_a_task_notification_so_its_evidence_keeps_accruing` (fails on the
      pre-change source with no shadow child) and
      `test_decide_nudges_a_task_notification_exactly_as_off_does`.
- [x] What is sent is what shadow mode already sent for a notification (`_turn_fields` plus the
      context `_router_fields` adds); no new field leaves the machine.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
