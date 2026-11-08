# Checklist 2026-11-08 - context_mode removed

Change: the `context_mode` row is deleted. Its `CLAUDE_CODE_AUTO_COMPACT_WINDOW` instructions
moved into the `context_handover_cap` row, without the "in compact mode" qualifier. The
`context_window` row now says what it decides: when the context watcher asks for a checkpoint.
User decision 2026-11-08, "Purge it".

- [x] Decisions: d-20261108-b2bb87de
- [x] Step 0b: `skill_decisions.py show meta-memory-settings` printed no entries.
- [x] Skill type: a reference table. The change is checked as text and code, not with a
      behavioural probe. `settings.py set context_mode ...` exits 2 (unknown key). A stored key is
      hidden by `view` and dropped by `set` and `reset`, pinned by
      test_a_stored_context_mode_errors_no_verb and test_context_mode_is_an_unknown_key.

## RED

- [x] Code: a mutation that honours `context_mode=handover` in the watcher's `decide()` failed
      test_a_stored_handover_mode_behaves_exactly_like_compact_mode (mutation_arm, KILLED).
- [x] Text: a repo-wide grep finds no shipped `context_mode` row or handover-mode wording left.
      docs/reference.md was swept too.

## Mechanical checks

- [x] reformat_tables.py reports the table aligned. No non-ASCII added, no history wording.
