# skill-writer checklist - compuse-ssh (2026-10-19, merged-read sentinels and Alpine account setup)

Change: the "Reading a remote FILE into a variable" row gains the `json.loads` symptom, the
sentinel wrapper for a helper that cannot be un-merged, and the `od -c` check; the "Key auth
refused on a FRESH Alpine account" row gains the confirming log line, the exact unlock command,
the busybox edit-lock fix, the sudo setup with its sudoers line, and the `sudo id` verification.

- [x] Skill type: reference - tested by quote-back (answer only with a verbatim quote, or NONE).
- [x] RED (rows as they stood, opus): Q3, Q5 NONE; Q1, Q2, Q4 PARTIAL (no technique for a helper
      that cannot be un-merged, no exact unlock command, no log location).
- [x] GREEN (new rows, opus and haiku): all five questions answered by a direct quote.
- [x] REFACTOR: the GREEN gap "sudoers file named but not its content" closed with the NOPASSWD
      line (a key-only account has no password for sudo to ask); re-test on haiku quoted it.
- [x] Lost-result diff: every RED quote survives in GREEN; nothing missing.
- [x] Skill gaps, declined: the client-side split between markers ("keep only what lies between
      them" is the rule); "key-only" wording is the row's own framing.
- [x] Both rows written within the table's existing column width; `reformat_tables.py --check`
      reports the file unchanged and the diff touches those two lines only.
- [x] Description unchanged, so skill_triggers.json and the docs catalogue need no regeneration.
- [x] Security: placeholders only (`<u>`, `<host>`, `<f>`); no hosts, keys or private paths.
