# skill-writer checklist - meta-memory-settings (2026-10-08, tmp_prune knob)

One row added to the knobs table: `tmp_prune` (`on` [default], `dry-run`, `off`), the switch for
the new `tmp-prune-hook.py`. `settings.py` accepts exactly those three values, and
`docs/reference.md` carries the same knob in its own row.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Retrieval scenario: Q1 which setting stops the automatic temp-dir
      deletion and with what command, Q2 which value previews without deleting, Q3 which dirs go
      and at what age, Q4 where each run is recorded.
- [x] Arms pinned to haiku on the inert `bitranox:baseline-probe` type, the knobs table pasted
      (cells of unrelated rows shortened, every key kept), answers as a direct quote or NONE, each
      ending with a "Skill gaps" section.
- [x] Inherited context: the knob and its hook are new in this change, so no CLAUDE.md or memory
      fact on the machine describes them, and the arms answer from the pasted table only.
- [x] RED (pre-change table): NONE on all four. Gap reported: the table documents no temp-dir
      cleanup, preview mode or run record.
- [x] GREEN (new row): Q1 quoted "`off`: starts nothing." and built
      `python3 settings.py set tmp_prune off`; Q2 "`dry-run`: decides the same and deletes
      nothing."; Q3 the full "It deletes a session's scratch dir ... once nothing inside changed for
      seven days." sentence; Q4 "Each run appends a line to
      `~/.claude/self-improve-audit/tmp-prune.log.jsonl`". Gaps: none reported.
- [x] RED's one gap is closed by the four GREEN quotes; nothing RED answered is missing from GREEN.
- [x] The row matches the code: `tmp_prune.py` (scratch age 1 day, one-off age 7 days, the
      registry, transcript, holder, socket/FIFO and mount checks, `pytest-of-*` excluded, the log
      name), `tmp-prune-hook.py` (SessionStart and Stop, `claim_slot` at most hourly, `--apply` only
      under `on`), and `settings.py` `ENUM_CHOICES["tmp_prune"]`, pinned by
      `hooks/tests/test_tmp_prune.py` and the three `tmp_prune` tests in `tests/test_settings.py`.
- [x] The route the row names runs: `tmp_prune.py --json` prints a `removed` list of each dir a run
      would delete (`test_the_cli_names_each_dir_it_would_remove`).
- [x] Table re-pad: one line added, no other line changed.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added; paths are `<temp>`, `<plugin>` and `~`.
- [x] Present tense, no session narrative, no private provenance.
