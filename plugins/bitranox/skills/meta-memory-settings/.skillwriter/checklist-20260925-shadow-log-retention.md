# skill-writer checklist - meta-memory-settings (2026-09-25, shadow log retention)

One cell corrected: the `classifier_backend` row's log location. The shadow child now appends to
one file per UTC day and prunes by age and total size; the cell named a single undated file and
said nothing about retention.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The test is a retrieval scenario: which file holds today's rows,
      whether anything is deleted and when, and whether rows from three months ago are readable.
- [x] Arms pinned to the least inferential tier (haiku) on the inert `bitranox:baseline-probe`
      type, the row pasted and Skill invocation forbidden, so neither arm could answer from the
      installed copy (which still carries the pre-change cell).
- [x] RED (pre-change cell): (1) the undated `classifier-shadow.jsonl`, (2) NONE, (3) NONE.
      (1) is wrong against the code, (2) and (3) are silent.
- [x] GREEN (new cell): all three answered with a direct quote - the dated file for today, deletion
      on every write by age then total size never touching the current day, and "No" for
      three-month-old rows.
- [x] Both dispatches asked for a `Skill gaps` section. RED listed retention, purging and access to
      old rows; GREEN reported none. Nothing RED produced is missing from GREEN.
- [x] The statement matches the code: `classifier.shadow_log_path` (day file name),
      `classifier.prune_shadow_logs` (age first, then oldest-first to `SHADOW_MAX_BYTES`, never
      the current day), `classifier._append_log` (prunes after every append), constants
      `SHADOW_KEEP_DAYS = 30` and `SHADOW_MAX_BYTES = 200 MiB`.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
