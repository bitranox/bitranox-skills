# skill-writer checklist - meta-memory-settings (2026-10-20, classifier_subagent_signal knob)

One new knob row, `classifier_subagent_signal` (`off` [default], `shadow`), for the Jev shadow site
in `hooks/subagent-capture.py`. Its key is two characters wider than the first column, so the
table formatter re-padded every row of the table; no other row's cell text changed.
`docs/reference.md` carries the same knob in its own row.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - can a reader find the knob, what it sends, and
      that nothing acts on the answer.
- [x] Inherited coverage checked: `redcheck --corpus-cascade` flagged three CLAUDE.local.md files
      on generic shared terms (classifier, judge, settings, sent). None of them, and no memory fact
      body, contains `subagent_signal`, so the hit is term overlap, not the lesson. The installed
      copy of this skill has no such row either, so the probe's Skill tool could not supply it.
- [x] RED (haiku, `bitranox:baseline-probe`, the knobs section without the new row): asked which
      key enables a Jev shadow of the SubagentStop capture, what is sent, and whether anything acts
      on the answer, each as a direct quote or NONE. It answered NONE to all three, and its gaps
      named the missing site key, payload, log file, buffer behaviour and decide availability.
- [x] GREEN (same model, same fixture plus the new row): all three answered by direct quotes of the
      new row (key and value; the SENT clause; "Nothing acts on Jev's answer: the capture buffers
      exactly what it buffers with `off`"), plus the backend row for `classifier_backend = jev`.
- [x] Diffed both ways: RED produced no answer to lose; GREEN added the three.
- [x] GREEN gaps, each decided:
      - "redacted" undefined for this row - CLOSED: the row now says secrets are replaced by
        `[REDACTED]` (the same `prepare_state` redaction every site uses).
      - behaviour when Jev does not answer - CLOSED: "Nothing acts on Jev's answer, or on its
        absence (no key, a timeout, an HTTP error)".
      - exact question wording - DECLINED: it is `classifier.subagent_signal_questions()`, pinned
        verbatim to the Stop gate's two reply questions by a test; the row names what they ask.
      - sent set differs from buffered set - DECLINED: the probe read it correctly; the row states
        both sets.
      - log pruning for this site - DECLINED: the row names the same classifier shadow log, whose
        retention the `classifier_backend` row states.
      - which process writes the row - DECLINED: an implementation detail no setting depends on.
- [x] Both closed gaps verified by quote-back (haiku): each question answered with the new clause
      verbatim.
- [x] Every claim checked against the code: buffering of broad matches
      (`subagent-capture.find_signals`), the Stop block on a non-empty buffer
      (`self-improve-gate.py`, `sub_hint` sets `fires`), the last-12 cap
      (`SHADOW_MAX_MESSAGES`), the 4000-character cap (`classifier.FIELD_CAP`), off|shadow only
      (`settings.py`, refusal pinned in `tests/test_settings.py`), the unchanged buffer
      (`test_subagent_capture_shadow_logs_every_message_and_buffers_exactly_as_before`).
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
