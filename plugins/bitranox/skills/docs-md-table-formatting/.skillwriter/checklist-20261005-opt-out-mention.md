# skill-writer checklist - docs-md-table-formatting (2026-10-05, opt-out mention, D-5/D-11)

One-sentence addition to the overview: the auto-realign hook can be disabled per checkout with
`git config bitranox.reformatMdTables false`.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - one question answered with a direct quote
      or NONE.
- [x] RED (pre-change text, pasted): "Can a checkout turn the auto-realign hook off?" - NONE; the
      old overview states the hook as unconditional.
- [x] Verified against `hooks/reformat-md-tables.py`: `OPT_OUT_KEY = "bitranox.reformatMdTables"`
      and a docstring line "A checkout can opt out as a whole: `git config
      bitranox.reformatMdTables false`" - matches the added text.
- [x] GREEN (new sentence pasted): same question now answers with a direct quote ("unless the
      checkout opted out with `git config bitranox.reformatMdTables false`").
- [x] GREEN diffed against RED in both directions: nothing removed, one gap closed.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
