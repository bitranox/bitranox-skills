# skill-writer checklist - meta-memory-settings (2026-10-06, stop_signal correction length)

The `classifier_stop_signal` row's decide sentence gains one clause: a correction counts only after
a typed user message of at least 40 characters, the other three families after any message. No
other cell's text changed. `docs/reference.md` carries the same change in its own row.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Retrieval scenario, four questions, knob at `decide`, keywords quiet:
      Q1 "release first" with correction 0.95 - block?; Q2 "yes" with a self-admitted miss 0.9 -
      block?; Q3 how long must the prompt be for a correction to count?; Q4 a 67-character
      correction with correction 0.95 - block?
- [x] Arms pinned to haiku on the inert `bitranox:baseline-probe` type, the row pasted, answers as a
      direct quote or NONE, each ending with a "Skill gaps" section.
- [x] RED (pre-change row): Q1 YES, quoting "the gate blocks when Jev scores a correction ... at 0.8
      or more" - a wrong answer under the new behaviour; Q3 NONE; Q2 and Q4 YES. Gap reported: the
      row is silent on any minimum prompt length.
- [x] GREEN (new row): Q1 NO, quoting "a correction counts only when the typed user message is at
      least 40 characters long (surrounding whitespace not counted)"; Q2 YES, quoting "the other
      three count after any message, even a bare 'yes'"; Q3 40 characters; Q4 YES. Gaps: none.
- [x] GREEN against RED in both directions: Q2 and Q4 keep their answers; Q1 changes from the wrong
      answer to the right one and Q3 from NONE to 40, as intended. Nothing lost.
- [x] The statement matches the code: `classifier.stop_signal_firings` drops a family listed in
      `MIN_PROMPT_CHARS` (`{"correction": 40}`) when `len(user_message.strip())` is below it, and
      `self-improve-gate._decide_stop_signal` passes the request's `user_message`. Pinned by
      `tests/test_self_improve_gate_decide.py`: the short-prompt, 39/40 boundary, padding and
      bare-"yes" tests, the first three seen failing before the change.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
