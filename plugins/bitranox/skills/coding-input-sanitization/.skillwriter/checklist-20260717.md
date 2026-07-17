# skill-writer checklist - coding-input-sanitization (2026-07-17, quick checklist now covers every sink and the charset decision)

Change: The sink table lists 7 sinks; the Quick checklist enumerated 5, silently dropping Outbound URL (SSRF)
and Log/response-header CRLF stripping - and SSRF is a keyword in the frontmatter description, so the
skill advertises a sink its own checklist skips. The IN-direction charset/normalization rule had no row.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: counted the sink table (7 rows) against the checklist (5 covered): SSRF + CRLF absent; an
      enumeration reads as complete, so a checklist-following agent ships an unguarded sink
- [x] GREEN: added one checklist row per sink plus the explicit-charset row
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
