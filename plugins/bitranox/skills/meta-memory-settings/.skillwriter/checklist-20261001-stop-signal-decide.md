# skill-writer checklist - meta-memory-settings (2026-10-01, stop_signal decide)

The `classifier_stop_signal` row gains `decide` in its allowed values and a description of what
decide does; its SENT list now names the reply the user message answered (300 characters at most),
which the gate sends and the row did not list. The table was re-aligned by `reformat_tables.py`; no
other cell's text changed. `docs/reference.md` carries the same change in its own row.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Retrieval scenario, seven questions: Q1 can the knob be `decide`, Q2 is
      a keyword-flagged turn sent to Jev, Q3 at what score does decide block, Q4 what happens when
      Jev does not answer, Q5 every text sent, Q6 does an approval alone block, Q7 what waits and
      for how long.
- [x] Arms pinned to haiku on the inert `bitranox:baseline-probe` type, the row pasted, answers as a
      direct quote or NONE, each ending with a "Skill gaps" section.
- [x] RED (pre-change row): Q1-Q4, Q6, Q7 NONE. Q5 quoted "SENT: the last user message and the last
      assistant reply, each capped at 4000 characters", which omits the previous reply the gate
      sends - a false answer, not only a missing one.
- [x] GREEN (first new row): Q1, Q3, Q4, Q6, Q7 quoted. Gaps reported: Q2 only implied ("a turn they
      leave quiet is asked"), and Q5 NONE because SENT read as shadow-only.
- [x] REFACTOR: the decide sentence now says "Jev is not asked about a turn they already block" and
      "a turn they leave quiet is sent the same request (the SENT list above)". Quote-back re-run on
      Q2 and Q5 only: Q2 "Jev is not asked about a turn they already block"; Q5 "the last user
      message and the last assistant reply (4000 characters each at most) and the assistant reply
      the user message answered (300 at most)". Gaps: none.
- [x] GREEN against RED in both directions: every RED answer is still answered; Q5 changes from a
      wrong list to the right one, as intended.
- [x] The statement matches the code: `self-improve-gate._decide_stop_signal` logs path `regex`
      without asking when `_regex_verdict` fires, asks via `classifier.ask_in_hook` (deadline
      `DEFAULT_DEADLINE`) otherwise, and blocks on `classifier.stop_signal_firings` at
      `SITE_THRESHOLDS["stop_signal"]` (0.8) with `endorsement` in `NON_FIRING_FAMILIES`; the request
      is `_request`, i.e. `with_previous` (`PREVIOUS_CAP` 300) over the two `FIELD_CAP` 4000 fields.
      Pinned by `tests/test_self_improve_gate_decide.py` (14 tests; the 0.8 threshold and the
      endorsement exclusion each fail under a mutation of their constant).
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
