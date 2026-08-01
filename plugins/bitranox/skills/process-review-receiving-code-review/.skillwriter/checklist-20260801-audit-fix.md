# skill-writer checklist - process-review-receiving-code-review (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.129.0.

- [x] WRONG, and it fails silently: the documented way to reply in a GitHub review thread was
      `gh api repos/.../comments/{id}/replies` with no method and no field. `gh api` sends GET
      unless given one, so the command reads the thread instead of replying and exits 0 - the
      reader believes the reply landed. Now shown as `-X POST ... -f body='...'`.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file; behavioural claims checked against the code or the
      tool's own help rather than taken from the report.
- [x] No session narrative or private provenance added; no machine paths added.
