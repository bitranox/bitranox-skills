# Security headers, cookies, TLS, redirects - values, snippets, rollout, gotchas

The scanner (`audit_headers.py`) grades these; this file is the fix detail. Apply on EVERY response
(nginx `add_header ... always;`) so error pages are covered too.

## Headers - recommended values

| Header                      | Recommended value                                                                                                          | Missing =                        | Why                                                     |
|-----------------------------|----------------------------------------------------------------------------------------------------------------------------|----------------------------------|---------------------------------------------------------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (add `preload` only when sure)                                                       | SEVERE                           | force HTTPS; stops SSL-strip                            |
| `Content-Security-Policy`   | start `default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'` then tighten per resource inventory | SEVERE                           | the real XSS defence                                    |
| `X-Content-Type-Options`    | `nosniff`                                                                                                                  | MEDIUM                           | stop MIME-sniffing to script                            |
| `X-Frame-Options`           | `DENY` (legacy twin of CSP `frame-ancestors`)                                                                              | MEDIUM (if no `frame-ancestors`) | clickjacking                                            |
| `Referrer-Policy`           | `strict-origin-when-cross-origin`                                                                                          | MINOR                            | leak less URL on cross-origin                           |
| `Permissions-Policy`        | revoke unused, e.g. `geolocation=(), camera=(), microphone=(), payment=()`                                                 | MINOR                            | drop unused powerful features                           |
| `X-XSS-Protection`          | `0` (or omit)                                                                                                              | -                                | the legacy auditor is removed and BUGGY; do NOT set `1` |
| `Server`                    | no version (`server_tokens off;`, strip upstream `X-Powered-By`)                                                           | MINOR                            | info leak                                               |

## CSP, the site-specific one
- Inventory every external origin the page loads (fonts, analytics, CDN, the form's API) and allow each
  explicitly per directive (`script-src`, `style-src`, `img-src`, `font-src`, `connect-src`, `form-action`).
- NO `'unsafe-inline'` / `'unsafe-eval'` in `script-src` - use a per-response **nonce** or a **hash** for
  any inline script. `'unsafe-inline'` in `style-src` is a common, lesser concession.
- Add `upgrade-insecure-requests` to auto-upgrade stray `http://` subresources.
- Reporting: `report-uri` is deprecated - prefer `Reporting-Endpoints: csp="https://.../report"` +
  `report-to csp` in the policy (keep `report-uri` too for old browsers).

## Cookies
Every `Set-Cookie`: `Secure` (SEVERE if missing on HTTPS), `HttpOnly` (unless JS must read it),
`SameSite=Lax` (or `Strict`; `None` requires `Secure`).

## TLS + redirects
- `ssl_protocols TLSv1.2 TLSv1.3;` only. Modern cipher suite, OCSP stapling on.
- All `:80` -> `301`/`308` to `https://`; pick one canonical host (apex or `www`) and redirect the other.
- No mixed content: zero `http://` subresources on an HTTPS page (the scanner greps the returned HTML).

## Safe rollout order (each step is a config reload = ~1-minute rollback via git)
1. Audit baseline (`audit_headers.py`, save the report).
2. TLS hardening (handshake only, cannot break page content).
3. Safe headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`,
   `X-XSS-Protection: 0`, `server_tokens off`.
4. **CSP in `Content-Security-Policy-Report-Only` for >=48h**, watch the report endpoint, fix violations.
5. Promote CSP to enforced (`Content-Security-Policy`), keep reporting.
6. HSTS at `max-age=300` for a week (fast rollback if a subdomain's TLS breaks).
7. HSTS to `max-age=31536000; includeSubDomains; preload` - **preload is effectively irreversible for a
   year for browsers that have seen it; only when every subdomain will serve HTTPS forever.**

## Gotchas (these bite even careful work)
- **nginx `add_header` does NOT inherit when a block adds its OWN header.** Any `location` (or `server`)
  that has even one `add_header` DROPS all `add_header`s from the parent. So a per-location header silently
  removes your security headers there. Fix: put the security headers in an `include security_headers.conf;`
  and re-`include` it in every block that adds anything, or set them at `server` level with nothing
  overriding. Always re-audit each path, not just `/`.
- **The `always` flag** is required or the headers are absent on 4xx/5xx (error pages).
- **`X-XSS-Protection: 1`** is worse than nothing - set `0`.
- **HSTS `preload`** is a one-way door (see step 7).
- **Verifying only via an external grader** (Mozilla Observatory, csp-evaluator, hstspreload): they move,
  rate-limit, and go offline. Gate on the local `audit_headers.py` run; use external graders as a bonus.
- **CSP that "passes" on `/` but the app injects inline scripts elsewhere** - scan representative pages
  and run report-only first.
