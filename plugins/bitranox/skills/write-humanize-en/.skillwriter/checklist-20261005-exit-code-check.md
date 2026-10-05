# skill-writer checklist - write-humanize-en (2026-10-05, --check exit 2, D-8/D-11)

One-line amendment: `strip_typographic_tells.py --check FILE` comment now also states exit 2 for
an unreadable file.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - one question answered with a direct quote
      or NONE.
- [x] RED (pre-change text, pasted): "What does `--check` exit when the target file cannot be
      read?" - NONE; the old comment only states exit 1 for tells remaining.
- [x] Verified against the hook source (`hooks/strip_typographic_tells.py`): the `--check` branch
      catches `UnicodeDecodeError`/`OSError` and returns 2, distinct from the `1 if out != data
      else 0` tells-remain branch - matches the added text exactly.
- [x] GREEN (new comment pasted): same question now answers with a direct quote ("2 if a file
      cannot be read").
- [x] GREEN diffed against RED in both directions: nothing removed, one gap closed.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
