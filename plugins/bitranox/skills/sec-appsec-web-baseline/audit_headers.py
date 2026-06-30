# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx2>=2.5.0"]
# ///
"""Audit a live URL's HTTP web-security baseline: security headers, cookie flags, the
HTTP->HTTPS redirect, server-version leakage, and mixed content in the returned HTML.

This is the "measure, do not eyeball" tool for the sec-appsec-web-baseline skill - run it
before and after a change instead of hand-reading `curl -I`, and it grades each finding
SEVERE / MEDIUM / MINOR / OK so the same bar (0 SEVERE / 0 MEDIUM) gates the fix. It needs
only `uv` (the deps are fetched on run); it makes ONE GET and one plain-HTTP HEAD, and does
NOT depend on any external grading service (those move and disappear).

The grading functions are pure (header value string -> findings) so they unit-test without a
network; only `fetch` and `audit` touch the wire. Run: `uv run audit_headers.py https://host`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass

SEVERITIES = ("SEVERE", "MEDIUM", "MINOR", "OK")


@dataclass(frozen=True)
class Finding:
    """One graded check: ``check`` is the header/aspect, ``severity`` drives the gate."""

    check: str
    severity: str
    detail: str
    fix: str = ""


def _hsts(value: str | None, *, https: bool) -> Finding:
    """Grade Strict-Transport-Security. Missing on an HTTPS site is SEVERE."""
    if not https:
        return Finding("hsts", "OK", "not applicable on plain HTTP")
    if not value:
        return Finding("hsts", "SEVERE", "no Strict-Transport-Security header",
                       'set "max-age=31536000; includeSubDomains" (stage a short max-age first)')
    age = re.search(r"max-age\s*=\s*(\d+)", value, re.I)
    seconds = int(age.group(1)) if age else 0
    if seconds < 15552000:  # 180 days
        return Finding("hsts", "MEDIUM", f"max-age={seconds} is below 6 months",
                       "raise to max-age=31536000 once stable")
    if "includesubdomains" not in value.lower():
        return Finding("hsts", "MINOR", "no includeSubDomains", "add includeSubDomains if all subdomains are HTTPS")
    return Finding("hsts", "OK", value)


def _csp(value: str | None) -> Finding:
    """Grade Content-Security-Policy. Missing is SEVERE; unsafe-inline/eval in scripts is MEDIUM."""
    if not value:
        return Finding("csp", "SEVERE", "no Content-Security-Policy",
                       "add a policy starting from default-src 'self'; object-src 'none'; frame-ancestors 'none'")
    low = value.lower()
    script = re.search(r"script-src([^;]*)", low)
    script_val = script.group(1) if script else (re.search(r"default-src([^;]*)", low) or [None, ""])[1]
    if script_val and "'unsafe-inline'" in script_val:
        return Finding("csp", "MEDIUM", "script-src allows 'unsafe-inline' (XSS not mitigated)",
                       "drop 'unsafe-inline'; use nonces or hashes for any inline script")
    if script_val and "'unsafe-eval'" in script_val:
        return Finding("csp", "MEDIUM", "script-src allows 'unsafe-eval'", "remove 'unsafe-eval'")
    if "object-src" not in low and "default-src" not in low:
        return Finding("csp", "MINOR", "no object-src/default-src fallback", "add default-src 'self'; object-src 'none'")
    return Finding("csp", "OK", "present, no unsafe-inline/eval in scripts")


def _nosniff(value: str | None) -> Finding:
    if value and value.strip().lower() == "nosniff":
        return Finding("x-content-type-options", "OK", "nosniff")
    return Finding("x-content-type-options", "MEDIUM", "missing or not 'nosniff'", 'set X-Content-Type-Options: nosniff')


def _clickjacking(xfo: str | None, csp: str | None) -> Finding:
    """Clickjacking is covered by CSP frame-ancestors OR X-Frame-Options."""
    if csp and "frame-ancestors" in csp.lower():
        return Finding("clickjacking", "OK", "CSP frame-ancestors present")
    if xfo and xfo.strip().lower() in ("deny", "sameorigin"):
        return Finding("clickjacking", "OK", f"X-Frame-Options: {xfo.strip()}")
    return Finding("clickjacking", "MEDIUM", "no frame-ancestors and no X-Frame-Options",
                   "add CSP frame-ancestors 'none' (and X-Frame-Options: DENY for old browsers)")


def _referrer_policy(value: str | None) -> Finding:
    safe = {"no-referrer", "strict-origin", "strict-origin-when-cross-origin", "same-origin", "no-referrer-when-downgrade"}
    if value and value.strip().lower() in safe:
        return Finding("referrer-policy", "OK", value)
    return Finding("referrer-policy", "MINOR", "missing or weak", 'set Referrer-Policy: strict-origin-when-cross-origin')


def _permissions_policy(value: str | None) -> Finding:
    if value:
        return Finding("permissions-policy", "OK", "present")
    return Finding("permissions-policy", "MINOR", "missing",
                   'set Permissions-Policy revoking unused features, e.g. geolocation=(), camera=(), microphone=()')


def _xss_auditor(value: str | None) -> Finding:
    """The legacy XSS auditor should be OFF (0) or absent - '1'/'1; mode=block' can introduce bugs."""
    if value and value.strip().startswith("1"):
        return Finding("x-xss-protection", "MEDIUM", "X-XSS-Protection enabled (removed from browsers; can add bugs)",
                       "set X-XSS-Protection: 0 (or remove it); rely on CSP")
    return Finding("x-xss-protection", "OK", "off or absent")


def _server_token(value: str | None) -> Finding:
    if value and re.search(r"\d", value):
        return Finding("server-token", "MINOR", f"Server header leaks version: {value}",
                       "nginx: server_tokens off; strip upstream X-Powered-By")
    return Finding("server-token", "OK", value or "absent")


def _cookies(set_cookies: list[str], *, https: bool) -> list[Finding]:
    out: list[Finding] = []
    for raw in set_cookies:
        name = raw.split("=", 1)[0].strip()
        low = raw.lower()
        if https and "secure" not in low:
            out.append(Finding(f"cookie:{name}", "SEVERE", "Set-Cookie without Secure on HTTPS", "add the Secure attribute"))
        if "httponly" not in low:
            out.append(Finding(f"cookie:{name}", "MEDIUM", "Set-Cookie without HttpOnly", "add HttpOnly (unless JS must read it)"))
        if "samesite" not in low:
            out.append(Finding(f"cookie:{name}", "MINOR", "Set-Cookie without SameSite", "add SameSite=Lax (or Strict)"))
    return out


def _redirect(http_status: int | None, location: str | None) -> Finding:
    """Plain HTTP must 301/308 to https://."""
    if http_status is None:
        return Finding("https-redirect", "MINOR", "plain-HTTP probe failed (could not connect)")
    if http_status in (301, 308) and location and location.lower().startswith("https://"):
        return Finding("https-redirect", "OK", f"{http_status} -> {location}")
    return Finding("https-redirect", "SEVERE", f"HTTP did not permanently redirect to HTTPS (got {http_status})",
                   "redirect all :80 to https:// with 301")


def _mixed_content(html: str, *, https: bool) -> list[Finding]:
    """http:// subresources on an HTTPS page (script/link/img/iframe src/href) are blocked/insecure."""
    if not https or not html:
        return []
    hits = re.findall(r'(?:src|href)\s*=\s*["\'](http://[^"\']+)["\']', html, re.I)
    seen: list[str] = []
    for h in hits:
        if h not in seen:
            seen.append(h)
    if seen:
        return [Finding("mixed-content", "SEVERE", f"{len(seen)} http:// subresource(s), e.g. {seen[0]}",
                        "serve every subresource over https (and add CSP upgrade-insecure-requests)")]
    return []


def grade(headers: dict[str, str], set_cookies: list[str], *, https: bool,
          http_status: int | None, http_location: str | None, html: str = "") -> list[Finding]:
    """Pure: turn a fetched response into the full graded finding list (no network)."""
    h = {k.lower(): v for k, v in headers.items()}
    findings = [
        _hsts(h.get("strict-transport-security"), https=https),
        _csp(h.get("content-security-policy") or h.get("content-security-policy-report-only")),
        _nosniff(h.get("x-content-type-options")),
        _clickjacking(h.get("x-frame-options"), h.get("content-security-policy")),
        _referrer_policy(h.get("referrer-policy")),
        _permissions_policy(h.get("permissions-policy")),
        _xss_auditor(h.get("x-xss-protection")),
        _server_token(h.get("server")),
        _redirect(http_status, http_location),
    ]
    findings += _cookies(set_cookies, https=https)
    findings += _mixed_content(html, https=https)
    return findings


def fetch(url: str) -> list[Finding]:  # pragma: no cover - thin network boundary
    """I/O boundary: GET the URL (following redirects) + a plain-HTTP HEAD, then grade()."""
    import httpx

    https = url.lower().startswith("https://")
    with httpx.Client(follow_redirects=True, timeout=15.0, headers={"User-Agent": "sec-appsec-web-baseline/1.0"}) as c:
        resp = c.get(url)
        html = resp.text if "text/html" in resp.headers.get("content-type", "") else ""
        set_cookies = resp.headers.get_list("set-cookie") if hasattr(resp.headers, "get_list") else (
            [resp.headers["set-cookie"]] if "set-cookie" in resp.headers else [])
        http_status = http_location = None
        host = re.sub(r"^https?://", "", url)
        try:
            r2 = httpx.head("http://" + host, follow_redirects=False, timeout=10.0)
            http_status, http_location = r2.status_code, r2.headers.get("location")
        except httpx.HTTPError:
            pass
    return grade(dict(resp.headers), set_cookies, https=https,
                 http_status=http_status, http_location=http_location, html=html)


def summarize(findings: list[Finding]) -> dict[str, int]:
    counts = {s: 0 for s in SEVERITIES}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a URL's HTTP web-security baseline.")
    parser.add_argument("url")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args(argv)

    findings = fetch(args.url)
    counts = summarize(findings)
    if args.json:
        print(json.dumps({"url": args.url, "counts": counts, "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        for f in findings:
            if f.severity != "OK":
                print(f"  [{f.severity}] {f.check}: {f.detail}" + (f"  -> {f.fix}" if f.fix else ""))
        print(f"\n{args.url}: " + " ".join(f"{k}={counts[k]}" for k in SEVERITIES))
    # exit non-zero if the gate (0 SEVERE / 0 MEDIUM) is not met
    return 1 if counts["SEVERE"] or counts["MEDIUM"] else 0


if __name__ == "__main__":
    sys.exit(main())
