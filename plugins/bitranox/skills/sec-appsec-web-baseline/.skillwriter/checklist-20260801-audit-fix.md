# skill-writer checklist - sec-appsec-web-baseline (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.129.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] WRONG, in the shipped `audit_headers.py`: the mixed-content detector counted EVERY `<link>`
      as a subresource load, so `<link rel="canonical" href="http://...">` - a common, harmless
      pattern - was graded SEVERE and read identically to a real insecure load. `rel` decides
      whether a `<link>` fetches anything; metadata and connection-hint rels do not.
- [x] Fixed with a non-loading rel set, and deliberately FAIL-LOUD in the other direction: an
      absent or unrecognised `rel` still counts as loading, so a rel this list has not seen yet is
      reported rather than silently dropped. That is the right bias for a security check.
- [x] Five tests written FIRST; the two that pin the defect were observed failing, the rest guard
      the behaviour that must NOT change (loading rels, other tags, `<a>` still excluded). 46 pass.
- [x] The five DANGLING findings against this skill are DECLINED, per the standing decision of
      2026-07-05: `sec-privacy-web-gdpr`, `web-frontend-a11y-audit` and the `sec-auth-*`,
      `sec-secrets-*`, `sec-pentest-*` families are RESERVED ROADMAP NAMES, and a future sibling is
      to be built under exactly the reserved name. An auditor will keep re-reporting these; the
      answer stays no.
- [x] No session narrative or private provenance added; no machine paths added.
