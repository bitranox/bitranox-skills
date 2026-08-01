# skill-writer checklist - coding-rust (2026-08-01, isolated-audit fix)

Source: the clean-room sweep run by `bitranox:meta-skill-audit`. These five skills reported after
four batches had already shipped, so their findings were triaged last. Ships with plugin 5.131.0.

- [x] STALE: a crate-size comparison froze two numbers (`~50 KB` vs `~2 MB`) with no date or
      version. Replaced with the ratio that carries the argument plus how to check the current
      figures, since the point is "prefer the narrow crate", not either number.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Every claim re-measured against the real tool or file rather than taken from the report.
- [x] No session narrative or private provenance added; no machine paths added.
