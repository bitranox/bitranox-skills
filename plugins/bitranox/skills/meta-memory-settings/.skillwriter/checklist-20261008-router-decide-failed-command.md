# skill-writer checklist - meta-memory-settings (2026-10-08, decide decides a failed background command)

One sentence of the `classifier_skill_router` row changed: under `decide`, the notification of a
background command that FAILED is decided like a typed prompt (same request, same 1.5 s wait),
except that a silent Jev nudges nothing there; every other notification kind keeps the earlier
wording (nudged as with `off`, still sent to Jev in the background and logged). The table was
re-aligned by the formatter; `docs/reference.md` carries the same change in its own row.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Retrieval scenario under `decide`: Q1 does Jev choose the nudge on a
      failed background command's notification, Q2 does that turn wait, Q3 does Jev choose the
      nudge on a completed command or a subagent's notification, Q4 what is nudged when Jev is
      silent on the failed command.
- [x] Arms pinned to haiku on the inert `bitranox:baseline-probe` type, the row pasted, answers as
      a direct quote or NONE, each ending with a "Skill gaps" section.
- [x] Inherited context: the arms answer from the pasted row only, and the store holds no fact
      describing this row's notification behaviour, so the RED could fail honestly.
- [x] RED (pre-change row): Q1 and Q3 both quoted "Jev's answer never chooses its nudge", Q2
      "nothing waits for it", Q4 "the keyword match nudge" - Q1, Q2 and Q4 are now false. Gap
      reported: the row does not distinguish a failed from a successful notification.
- [x] GREEN (new row): Q1 quoted "The notification of a background command that FAILED (non-zero
      exit) is decided the same way and waits the same 1.5 s"; Q2 "and waits the same 1.5 s"; Q3
      "Every other background-task notification (a command that completed or was stopped, a
      subagent, a monitor) is nudged exactly as with `off` (Jev's answer never chooses its
      nudge)"; Q4 "when Jev does not answer there NOTHING is nudged". Gaps: none reported.
- [x] RED gap (failed vs successful not distinguished) CLOSED by the Q1 and Q3 quotes. Nothing
      RED answered is missing from GREEN: Q3 keeps its answer, Q1, Q2 and Q4 flip as intended.
- [x] The statement matches the code: `skill-router._decides` is true in decide mode for a typed
      prompt or when `prompt_text.failed_background_command` holds (status `failed` and a summary
      opening `Background command `), `_shadows` excludes exactly that notification, and the
      keyword fallback scores no machine turn. Pinned by
      `test_decide_nudges_the_confident_jev_pick_on_a_failed_background_command`,
      `test_a_silent_jev_nudges_nothing_on_a_failed_background_command` (both fail on the
      pre-change source) and the parametrized
      `test_decide_nudges_any_other_task_notification_exactly_as_off_does` /
      `test_decide_still_shadows_any_other_task_notification_so_its_evidence_keeps_accruing`.
- [x] What is sent is what shadow mode already sent for a notification; no new field leaves the
      machine.
- [x] Table re-pad: line count unchanged; content changed on the edited row only, every other
      changed line is the separator row's dash count.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
