# skill-writer checklist - web-frontend-pagespeed (2026-08-01, isolated-audit fix)

Source: the clean-room sweep run by `bitranox:meta-skill-audit`. These five skills reported after
four batches had already shipped, so their findings were triaged last. Ships with plugin 5.131.0.

- [x] WRONG: the trap table said `curl -I` never emits `Content-Encoding`, "**for every file**".
      Measured against three servers (gnu.org, example.com, kernel.org): `curl -I --compressed`
      reports it on ALL of them. The claim's likely origin is that a PLAIN `curl -I` sends no
      `Accept-Encoding`, so nothing is negotiated - which is a different statement and the one
      worth making. The row now says a HEAD is unreliable in BOTH directions and to confirm with a
      GET, which is what the surrounding section is actually for.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Every claim re-measured against the real tool or file rather than taken from the report.
- [x] No session narrative or private provenance added; no machine paths added.
