# skill-writer checklist - meta-memory-settings (2026-10-23, classifier_jig_repetition knob)

One new knob row, `classifier_jig_repetition` (`off` [default], `shadow`), for the Jev shadow site
in `hooks/jig-repetition-nudge.py`. The row is written to the existing column widths. The table
formatter also re-padded the `classifier_subagent_signal` row, which was over-padded before this
change (1,837 characters against 1,670 for every other row): its cells are equal after stripping,
so that line is whitespace only. `docs/reference.md` carries the same knob in its own row.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - can a reader find the key, what is sent, when
      Jev is asked, and that nothing acts on the answer.
- [x] Inherited coverage checked: `redcheck --corpus-cascade` flagged the tree-top `CLAUDE.local.md` on
      generic shared terms (nudge, sent, settings, solved, warns). Neither it nor any memory fact
      body contains `classifier_jig_repetition`, so the hit is term overlap, not the lesson. The
      installed copy of this skill has no such row, so the probe's Skill tool could not supply it.
- [x] RED (haiku, `bitranox:baseline-probe`, the classifier rows without the new row): asked which
      key enables a Jev shadow of the jig-repetition nudge, what is sent, whether Jev is asked on
      every script write, and whether anything acts on the answer or the site can be set to
      `decide`, each as a direct quote or NONE. It answered NONE to all four; its gaps named the
      missing row and that the table cannot say which sites support `decide`.
- [x] GREEN (same model, same fixture plus the new row): all four answered by direct quotes of the
      new row (key and value; the SENT clause; "Jev is asked only when the nudge FIRES, never on any
      other script write."; "Nothing acts on Jev's answer, or on its absence ..." and "There is no
      `decide` mode.").
- [x] Diffed both ways: RED produced no answer to lose; GREEN added the four.
- [x] GREEN gaps, each decided:
      - log file not named in the row - CLOSED: the row names `classifier-shadow-<UTC date>.jsonl`.
      - whether a row is logged when Jev does not answer - CLOSED: "Each fired nudge logs one row,
        whether or not Jev answers (its reason is recorded when it does not)" (`run_shadow` writes
        `reason` from `last_reason` on every row).
      - the row needs `classifier_backend = jev` as well - DECLINED: the backend row states that
        rule for every site, as the other site rows rely on.
      - API key prerequisite, log directory, day rotation - DECLINED: owned by the backend row.
      - what happens when the tool call fails after the nudge fired - DECLINED: the nudge is a
        PreToolUse hook and asks before the call runs; no setting depends on the call's outcome.
- [x] Both closed gaps verified by quote-back: opus at effort medium and haiku each answered the
      log-file question with the new clause verbatim; a final haiku re-probe on the final text
      answered the log file, the unanswered-row case and `decide` by direct quotes and raised no
      new undecided gap.
- [x] Every claim checked against the code: asked only on a firing nudge (`shadow_request` is built
      only when `should_nudge` fires), after the nudge is written (`_shadow` runs after the stdout
      write), up to 20 earlier scripts (`LEDGER_WINDOW`), purpose as first comment else opening code
      (`purpose`), 80 characters (`_ledger_lines`), the changes-state mark, redaction
      (`prepare_state`), off|shadow only (`settings.py`, refusal pinned in `tests/test_settings.py`),
      the unchanged nudge
      (`test_jig_repetition_shadow_logs_the_nudge_and_nudges_exactly_as_before`).
- [x] Tiers: RED and GREEN on haiku; quote-back on opus (effort medium) and haiku; final re-probe on
      haiku - 5 cells.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added to the skill.
- [x] Present tense, no session narrative, no private provenance.
