# skill-writer checklist - write-humanize-de (2026-10-05, --check Exit 2, D-8/D-11)

One-line amendment (German twin of write-humanize-en's equivalent change):
`strip_typographic_tells.py --check DATEI` comment now also states Exit 2 for an unreadable
file.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - one question answered with a direct quote
      or NONE.
- [x] RED (pre-change text, pasted): "Was passiert bei `--check`, wenn die Datei nicht gelesen
      werden kann?" - NONE; der alte Kommentar nennt nur Exit 1 fuer verbleibende Tells.
- [x] Verified against the same hook source as the English twin
      (`hooks/strip_typographic_tells.py`): the `--check` branch returns 2 on
      `UnicodeDecodeError`/`OSError`, distinct from the tells-remain branch.
- [x] GREEN (new comment pasted): same question now answers with a direct quote ("Exit 2 wenn
      eine Datei nicht lesbar ist").
- [x] GREEN diffed against RED in both directions: nothing removed, one gap closed.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
