# Review checklist: meta-skill-writer, Step 0b corrected to the shipped code (2026-11-06)

Change covered: four corrections in "Step 0b" and "Record every decision the edit makes", each
bringing the text in line with what `skill_decisions.py`, `repo-gate.py` and
`skill-edit-guard.py` do in this release. No rule is added, removed or reversed; no anchored
sentence is reworded.

- D1: the edit guard refuses the first edit of a MARKETPLACE SKILL.md only; a tool-repo twin's
  editor runs `show` with the marketplace `--skill-dir`.
- D2: the field list: `add` always assigns `v` and `id` and keeps a supplied `date`; the `topic`
  form; all four `origin` values; `evidence` holds exactly `tier` and `text`; a multi-skill file
  is all or nothing; anchors are counted in git-tracked files.
- D3: where the `Decisions:` line may stand (indented, in a list item, ticked or not).
- D4: void semantics: a void withdraws what its target superseded, and cannot target a void.

Decisions: none - wording corrected to match the shipped code; no rule changed

## Evidence

- [x] Step 0b of the procedure ran: `show meta-skill-writer --kind rejected,removed --full`
      printed one rejected entry (a narrative history file per skill); this change does not
      touch it.
- [x] Each corrected claim checked against the code:
      D1 `skill-edit-guard.py` `_brief_refusal` reads `ledger_path(Path(path).parent)`, the ledger
      beside the edited file, so a twin with no ledger there gets no brief.
      D2 `prepare_entries` sets `v=1` and `date=draft.get("date") or today` and computes `id`;
      `_TOPIC` is `[a-z0-9][a-z0-9-]{0,39}`; `ORIGINS` is `authored, imported, baseline, ab`;
      `_vocabulary_problems` refuses an `evidence` object with other fields; `_cmd_add` prepares
      every skill's batch before writing any; `corpus_from_dir` reads `git ls-files` only.
      D3 `repo-gate.py` `DECISIONS_LINE_RX` accepts leading whitespace, a list marker and a
      ticked box before `Decisions:`, and `_unfenced_lines` skips fenced lines.
      D4 `live_entries` drops a voided entry's `supersedes`; `_entry_problems` refuses a void
      naming a void.
- [x] Commands executed in a scratch git repo holding two skills: `check` with no ledger printed
      "no ledger found under <dir>" on stderr, rc 0; an `add` file naming two skills with the
      second entry's anchor absent printed `refused: entry 2: ...`, rc 1, and wrote no ledger
      for either; the first entry alone with `"date": "2026-10-01"` then wrote
      `d-20261001-...`, rc 0; `show a --kind void` printed the `--all` hint on stderr.
- [x] Each claim is pinned by a test in `hooks/tests/`: `test_voiding_a_superseding_entry_
      withdraws_its_supersede_too`, `test_voiding_a_void_is_refused`,
      `test_cli_add_across_skills_is_all_or_nothing`, `test_an_anchor_only_in_an_untracked_
      markdown_file_is_refused_saying_so`, `test_a_field_of_the_wrong_type_is_refused`,
      `test_a_decisions_line_after_whitespace_a_list_marker_or_a_ticked_box_passes`.
- [x] `python3 plugins/bitranox/hooks/skill_decisions.py check meta-skill-writer`: 0 findings,
      rc 0; each of the five rule anchors occurs exactly once in the skill text (counted with
      `_occurrences` over the normalised corpus).
- [x] No behavioural RED/GREEN probe: the change states what the code does and adds no rule, so
      the evidence is the code reading and the executed commands above, not an agent's choice.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each
      insertion point was read, and no back-reference re-binds.
- [x] No private host, path or session detail added to the skill.
