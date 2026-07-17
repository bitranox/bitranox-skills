---
name: sec-appsec-web-baseline
description: Use when a public web page or site needs its HTTP security baseline hardened or audited - missing or weak security headers (Content-Security-Policy/CSP, Strict-Transport-Security/HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy), cookies without Secure/HttpOnly/SameSite, mixed content, no HTTP-to-HTTPS redirect, a leaked server version, or a low securityheaders/Mozilla-Observatory grade. NOT for deep pentest, auth flows, secret scanning, or GDPR/consent infra (sibling sec-* / privacy skills).
---

# Web Security Baseline Audit

## Overview

Harden + audit a site's HTTP/web-security baseline the same way the responsive skill does layout:
**measure** every dimension with a tool (never hand-read one `curl -I`), fix, and **re-scan** until the
gate is clean (**0 SEVERE / 0 MEDIUM**). Roll changes out in the safe order so a wrong HSTS/CSP never
locks users out.

The skill owns these dimensions and nothing else:

1. **Security response headers** - CSP, HSTS, X-Content-Type-Options, X-Frame-Options/`frame-ancestors`,
   Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy, X-XSS-Protection (must be `0`).
2. **Cookie flags** - `Secure` / `HttpOnly` / `SameSite` on every `Set-Cookie`.
3. **Transport** - HTTP->HTTPS 301/308 redirect, no mixed content. (TLS *version* is NOT graded by
   `audit_headers.py`; a clean scan says nothing about TLS 1.2/1.3-only. Check it by hand with
   `testssl.sh` or `openssl s_client -tls1_1` if it matters.)
4. **Information leakage** - server/framework version tokens.

Use the Read tool to load the reference below before proposing fixes.

## Reference files

| Topic                                                                                                          | File                             |
|----------------------------------------------------------------------------------------------------------------|----------------------------------|
| Per-header recommended values + nginx snippets, CSP build, cookies, TLS/redirects, safe rollout order, gotchas | `references/security-headers.md` |

## Bundled scripts

| Script             | Purpose                                                                                                                                                                                                                                                                                                                                            |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `audit_headers.py` | `uv run audit_headers.py https://host` - one GET + a plain-HTTP HEAD, grades headers/cookies/redirect/mixed-content SEVERE/MEDIUM/MINOR/OK, exits non-zero if not clean. `--json` for machine output. `--proxy URL` egresses through an external proxy (audit a public site from outside - see net-rotating-proxies). No external grading service. |

## Workflow

```
1. Scan      -> uv run audit_headers.py https://host   (save the baseline; scan representative pages, not just /)
2. Diagnose  -> map each finding to references/security-headers.md; sort SEVERE -> MEDIUM -> MINOR
3. Propose   -> concrete config diffs (exact header values); APPLY ONLY AFTER the user confirms
4. Roll out  -> the SAFE ORDER (TLS -> safe headers -> CSP report-only -> CSP enforced -> HSTS short -> HSTS long+preload)
5. Verify    -> re-scan to 0 SEVERE / 0 MEDIUM on every audited page; state the numbers
```

A finding is fixed only when a re-scan shows it gone on every page - never claim "secured" without the
re-run (cross-ref `bitranox:process-review-verification-before-completion`).

## Preferred patterns (opinionated defaults)

Defaults this skill prescribes; deviate only with a reason. Full values + snippets in the reference.

- **Set headers on EVERY response, `always`.** nginx `add_header ... always;` so 4xx/5xx are covered.
- **Stage the dangerous ones.** HSTS: `max-age=300` for a week, THEN `31536000; includeSubDomains;
  preload`. CSP: ship `Content-Security-Policy-Report-Only` for >=48h, fix violations, THEN enforce.
  `preload` is a ~1-year one-way door - only when every subdomain serves HTTPS forever.
- **CSP without `'unsafe-inline'`/`'unsafe-eval'` in scripts** - use a nonce/hash for inline scripts;
  `'unsafe-inline'` is tolerable only in `style-src`. Add `upgrade-insecure-requests`.
- **`X-XSS-Protection: 0`** (or omit). The legacy auditor is removed and buggy; never `1`.
- **Gate on the local scanner**, not an external grader (Observatory/csp-evaluator move and rate-limit) -
  use those only as a bonus cross-check.
- **Audit a PUBLIC site from OUTSIDE the internal network.** Headers/TLS/redirects are usually added at
  the edge (Traefik/CDN); a scan from inside hits the origin (internal DNS -> internal IP, no edge
  headers) and grades the wrong thing. Egress externally: `--proxy http://<proxy>` for one page, or fan a
  multi-page worklist across `net-rotating-proxies` (fast, parallel), ideally in SUBAGENTS (cross-ref
  `bitranox:process-agents-dispatching-parallel`) so each scan's output stays out of the main context.
  Gate proxy-health on a written output file, NOT the scanner's exit code (which is the security verdict,
  not a connection signal).

## Scope boundary (hand off to sibling skills)

| Concern                                                   | Skill                        |
|-----------------------------------------------------------|------------------------------|
| GDPR/privacy: consent, third-party calls, IP leakage      | `sec-privacy-web-gdpr`       |
| Authentication / session / login flows                    | `sec-auth-*`                 |
| Secret scanning / credential hygiene                      | `sec-secrets-*`              |
| Active pentest / exploitation                             | `sec-pentest-*`              |
| Performance / Core Web Vitals (CSP can affect what loads) | `web-frontend-pagespeed`     |
| Responsive layout / touch / viewport                      | `web-frontend-responsive-ux` |
| Deep accessibility beyond the baseline                    | `web-frontend-a11y-audit`    |

## Common mistakes

| Mistake                                           | Reality                                                                                                                                        |
|---------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| Hand-reading one `curl -I` and calling it done    | Scan with the tool, grade every dimension, re-scan after the fix; report 0 SEVERE / 0 MEDIUM                                                   |
| nginx `add_header` in a `location` block          | It DROPS all inherited `add_header`s - a per-location header silently removes your security headers there; re-include them + re-scan each path |
| Forgetting `always`                               | Headers then vanish on 4xx/5xx error pages                                                                                                     |
| `X-XSS-Protection: 1`                             | The auditor is removed + buggy; set `0`. CSP is the real XSS defence                                                                           |
| Enforcing a fresh CSP straight away               | Ship report-only first for >=48h and fix violations, or you break the site                                                                     |
| `'unsafe-inline'`/`'unsafe-eval'` in `script-src` | Defeats CSP's XSS protection; use a nonce/hash                                                                                                 |
| HSTS `preload` on day one                         | Effectively irreversible for a year; stage a short max-age first                                                                               |
| Verifying only an external grade                  | Observatory/csp-evaluator/hstspreload move + rate-limit + go offline; gate on the local scanner                                                |
| Scanning only `/`                                 | The app may inject inline scripts or set cookies on other paths; scan representative pages                                                     |
| Auto-applying fixes                               | Diagnose + propose diffs; apply only after the user confirms                                                                                   |
| Auditing a public site from INSIDE the network    | You grade the internal origin, not the edge visitors hit; egress outside via `--proxy` / `net-rotating-proxies`                                |
| Pulling in GDPR/auth/pentest/perf work            | Out of scope - hand off to the sibling skill above                                                                                             |
