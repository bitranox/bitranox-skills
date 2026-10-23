# skill-writer checklist - meta-memory-settings (2026-10-23, classifier_backlog_ask and classifier_audit_candidate knobs)

Two new knob rows, `classifier_backlog_ask` and `classifier_audit_candidate` (each `off` [default],
`shadow`), for the Jev shadow sites in `hooks/recall-memory.py` (the `asks_for_own_backlog` early
return) and `hooks/self-improve-audit.py`. Both rows are written to the existing column widths; the
table formatter changed no other line. `docs/reference.md` carries the same knobs in its own rows.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - can a reader find each key, what is sent, on
      which turns Jev is asked, whether anything acts on the answer, and that there is no `decide`.
- [x] Inherited coverage checked: `redcheck --corpus-cascade` flagged the tree-top
      `CLAUDE.local.md` and several memory facts on generic shared terms (asks, audit, backlog,
      decide, prompts, typed). No cascade file or fact body contains either knob name (grep), so the
      hits are term overlap, not the lesson. The installed copy of this skill has neither row.
- [x] RED (haiku, `bitranox:baseline-probe`, the classifier rows without the new ones): six
      questions (key, payload and asked-on for each site, and `decide`), each as a direct quote or
      NONE. It answered NONE to all six; its gaps named the missing rows.
- [x] GREEN (haiku, and opus at effort medium; the new rows pasted in full): all six answered by
      direct quotes of the new rows, plus a seventh, whether recall or the note behave differently
      with the sites on ("recall skips or runs exactly as with `off`"; "the note is written first
      and is unchanged").
- [x] Diffed both ways: RED produced no answer to lose; GREEN added all of them.
- [x] GREEN and re-probe gaps, each decided:
      - which turns count as not typed - CLOSED: the row lists the `typed_by_a_person` shapes (task
        notification, slash-command echo or its output, teammate message, interruption notice,
        shell escape).
      - whether a non-English prompt is sent - CLOSED: "in any language".
      - what the 12 limits - CLOSED: "The note shows at most the 12 candidates latest in the
        transcript, and Jev is asked about exactly those" (`render_report` shows
        `candidates[-_MAX_CANDIDATES:]`; `_shadow` sends the same slice).
      - failure cases on the audit row - CLOSED: "(no key, a timeout, an HTTP error, a malformed
        answer)" on both rows, as the other site rows list them.
      - what one audit row holds - CLOSED: "one answer per candidate (empty where Jev did not
        answer or its answer was malformed)" (`run_shadow` records `None` per unanswered request).
      - whether a twice-audited candidate is logged twice - CLOSED: "asked about and logged twice;
        `classifier_eval.py report` counts it once".
      - whether a strict match can be a candidate - CLOSED: "(a strict match is never a
        candidate)" (`find_candidates` skips a strict hit).
      - an audit with no candidates - CLOSED: "sends and logs nothing" (`main` returns before
        `_shadow`).
      - the `classifier_backend = jev` prerequisite, the key file, the log's retention, how a key is
        set - DECLINED: the backend row and the CLI section state them for every site.
      - the candidates beyond the 12 shown - DECLINED: the note's own behaviour, not this knob's;
        the row already says Jev is asked about exactly the ones shown.
- [x] Each closed gap verified by quote-back on the final text: two haiku re-probes answered the
      typed-turn, language, cap, failure, row-content, double-logging, strict-match and
      no-candidate questions by direct quotes; the last raised no new undecided gap.
- [x] Every claim checked against the code: asked on every typed prompt before the early return
      (`_shadow_backlog_ask` runs before `asks_for_own_backlog`), typed only (`typed_by_a_person`),
      fields `{user_prompt, previous_assistant_message}` (`with_previous`, 300-character reply),
      4000-character field cap and redaction (`prepare_state`), excerpt up to 3000 characters
      (`_EXCERPT`, `inert_snippet`), audit shadow after the note is written (`_shadow` after
      `write_text`), off|shadow only (`settings.py`, refusals pinned in `tests/test_settings.py`),
      unchanged recall and note (`test_backlog_ask_shadow_logs_every_typed_prompt_and_recalls_exactly_as_before`,
      `test_audit_shadow_asks_about_each_reported_candidate_and_reports_exactly_as_before`).
- [x] Code review of the whole change (opus, effort medium) found that the excerpt was cut before
      redaction, so a private key whose BEGIN line fell outside the window reached the API
      unredacted, contradicting the row's "secrets replaced by `[REDACTED]`". Fixed in code
      (`shadow_excerpt` redacts, then cuts), pinned by
      `test_the_shadow_excerpt_redacts_a_key_whose_header_falls_outside_the_window`, which fails on
      the cut-then-redact order; the row's claim now holds as written.
- [x] Tiers: RED on haiku; GREEN on haiku and opus (effort medium); re-probes on haiku - 5 cells.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added to the skill.
- [x] Present tense, no session narrative, no private provenance.
