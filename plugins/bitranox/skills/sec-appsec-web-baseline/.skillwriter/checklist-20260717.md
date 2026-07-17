# skill-writer checklist - sec-appsec-web-baseline (2026-07-17, TLS-version claim matches what the scanner actually grades)

Change: SKILL.md listed 'TLS 1.2/1.3 only' under graded Transport checks and references/security-headers.md says
the scanner grades that section - but audit_headers.py has no TLS/ssl-version logic at all, so a clean
'0 SEVERE/0 MEDIUM' re-scan silently certified something never checked.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: grepped the whole skill for tls/ssl_version/PROTOCOL_TLS/minimum_version: the only hit is a prose
      comment; grade() checks headers/cookies/redirects/mixed-content and no TLS version
- [x] GREEN: the TLS-version claim is now marked NOT graded, with the manual check named (testssl.sh /
      openssl s_client)
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
