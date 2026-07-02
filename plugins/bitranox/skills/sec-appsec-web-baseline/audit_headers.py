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

For a PUBLIC site, run it from OUTSIDE the internal network so it measures the EDGE a visitor
hits (Traefik/CDN TLS + headers), not the internal origin. `--proxy URL` routes the fetch
through an external egress; obtain one via the `net-rotating-proxies` skill (fast, parallel).

The grading functions are pure (header value string -> findings) so they unit-test without a
network; only `fetch` touches the wire. Run: `uv run audit_headers.py https://host`.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import sys
from dataclasses import asdict, dataclass

SEVERITIES = ("SEVERE", "MEDIUM", "MINOR", "OK")

# Elements that LOAD a subresource into the current page (so an http:// URL here is mixed
# content). <a> is deliberately excluded: it navigates away, it is not a subresource.
_SUBRESOURCE_TAG = re.compile(
    r"<(?:img|script|iframe|video|audio|source|track|embed|object|link)\b[^>]*>", re.I
)
_SUBRESOURCE_ATTR = re.compile(r"""(?:src|data|srcset|href)\s*=\s*["']([^"']+)["']""", re.I)


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


def _csp(value: str | None, *, enforced: bool = True) -> Finding:
    """Grade Content-Security-Policy. Missing is SEVERE; report-only is MINOR (not enforced =
    not protection, only a rollout phase); unsafe-inline/eval in scripts is MEDIUM."""
    if not value:
        return Finding("csp", "SEVERE", "no Content-Security-Policy",
                       "add a policy starting from default-src 'self'; object-src 'none'; frame-ancestors 'none'")
    if not enforced:
        return Finding("csp", "MINOR", "CSP is report-only (a rollout phase, not enforced - it protects nothing yet)",
                       "promote to an enforced Content-Security-Policy once violations are clear")
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


def _clickjacking(xfo: str | None, csp_enforced: str | None) -> Finding:
    """Clickjacking is covered by an ENFORCED CSP frame-ancestors OR X-Frame-Options. A
    report-only CSP does not count - it enforces nothing."""
    if csp_enforced and "frame-ancestors" in csp_enforced.lower():
        return Finding("clickjacking", "OK", "CSP frame-ancestors present")
    if xfo and xfo.strip().lower() in ("deny", "sameorigin"):
        return Finding("clickjacking", "OK", f"X-Frame-Options: {xfo.strip()}")
    return Finding("clickjacking", "MEDIUM", "no enforced frame-ancestors and no X-Frame-Options",
                   "add CSP frame-ancestors 'none' (and X-Frame-Options: DENY for old browsers)")


def _referrer_policy(value: str | None) -> Finding:
    # no-referrer-when-downgrade is NOT safe: it sends the full URL (with query) to third-party
    # HTTPS destinations. A baseline wants strict-origin(-when-cross-origin) or stricter.
    safe = {"no-referrer", "strict-origin", "strict-origin-when-cross-origin", "same-origin", "origin"}
    if value and value.strip().lower() in safe:
        return Finding("referrer-policy", "OK", value)
    return Finding("referrer-policy", "MINOR", "missing or weak", 'set Referrer-Policy: strict-origin-when-cross-origin')


def _permissions_policy(value: str | None) -> Finding:
    if value:
        return Finding("permissions-policy", "OK", "present")
    return Finding("permissions-policy", "MINOR", "missing",
                   'set Permissions-Policy revoking unused features, e.g. geolocation=(), camera=(), microphone=()')


def _coop(value: str | None) -> Finding:
    """Cross-Origin-Opener-Policy isolates the browsing context from cross-origin openers."""
    if value and value.strip().lower() in ("same-origin", "same-origin-allow-popups"):
        return Finding("coop", "OK", value)
    return Finding("coop", "MINOR", "no Cross-Origin-Opener-Policy",
                   "set Cross-Origin-Opener-Policy: same-origin-allow-popups (a safe baseline)")


def _xss_auditor(value: str | None) -> Finding:
    """The legacy XSS auditor should be OFF (0) or absent - '1'/'1; mode=block' can introduce bugs."""
    if value and value.strip().startswith("1"):
        return Finding("x-xss-protection", "MEDIUM", "X-XSS-Protection enabled (removed from browsers; can add bugs)",
                       "set X-XSS-Protection: 0 (or remove it); rely on CSP")
    return Finding("x-xss-protection", "OK", "off or absent")


def _server_token(value: str | None) -> Finding:
    # A version looks like 1.2 / 2.4.7 / v3 - a bare product name with a digit (AmazonS3) is not.
    if value and re.search(r"v?\d+\.\d+", value):
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
    """Plain HTTP must redirect to https://. 301/308 is best; 302/307 works but is temporary."""
    if http_status is None:
        return Finding("https-redirect", "MINOR", "plain-HTTP probe failed (could not connect)")
    to_https = bool(location and location.lower().startswith("https://"))
    if http_status in (301, 308) and to_https:
        return Finding("https-redirect", "OK", f"{http_status} -> {location}")
    if http_status in (302, 307) and to_https:
        return Finding("https-redirect", "MEDIUM", f"redirects to HTTPS but with a temporary {http_status}",
                       "use a permanent 301/308 so the redirect is cached")
    return Finding("https-redirect", "SEVERE", f"HTTP did not redirect to HTTPS (got {http_status})",
                   "redirect all :80 to https:// with 301")


def _mixed_content(html: str, *, https: bool) -> list[Finding]:
    """http:// subresources on an HTTPS page. Only subresource-LOADING elements count (img,
    script, iframe, link, ...); a plain <a href="http://"> navigates away and is NOT mixed
    content. srcset (space/comma-separated candidates) is split and checked."""
    if not https or not html:
        return []
    seen: list[str] = []
    for tag in _SUBRESOURCE_TAG.findall(html):
        for attr_val in _SUBRESOURCE_ATTR.findall(tag):
            for piece in re.split(r"[,\s]+", attr_val.strip()):
                if piece.lower().startswith("http://") and piece not in seen:
                    seen.append(piece)
    if seen:
        return [Finding("mixed-content", "SEVERE", f"{len(seen)} http:// subresource(s), e.g. {seen[0]}",
                        "serve every subresource over https (and add CSP upgrade-insecure-requests)")]
    return []


def grade(headers: dict[str, str], set_cookies: list[str], *, https: bool,
          http_status: int | None, http_location: str | None, html: str = "") -> list[Finding]:
    """Pure: turn a fetched response into the full graded finding list (no network)."""
    h = {k.lower(): v for k, v in headers.items()}
    csp_enforced = h.get("content-security-policy")
    csp_report_only = h.get("content-security-policy-report-only")
    if csp_enforced:
        csp_finding = _csp(csp_enforced, enforced=True)
    elif csp_report_only:
        csp_finding = _csp(csp_report_only, enforced=False)
    else:
        csp_finding = _csp(None)
    findings = [
        _hsts(h.get("strict-transport-security"), https=https),
        csp_finding,
        _nosniff(h.get("x-content-type-options")),
        _clickjacking(h.get("x-frame-options"), csp_enforced),
        _referrer_policy(h.get("referrer-policy")),
        _permissions_policy(h.get("permissions-policy")),
        _coop(h.get("cross-origin-opener-policy")),
        _xss_auditor(h.get("x-xss-protection")),
        _server_token(h.get("server")),
        _redirect(http_status, http_location),
    ]
    findings += _cookies(set_cookies, https=https)
    findings += _mixed_content(html, https=https)
    return findings


def fetch(url: str, *, proxy: str | None = None) -> list[Finding]:  # pragma: no cover - network boundary
    """I/O boundary: GET the URL (following redirects) + a plain-HTTP HEAD, then grade().

    Pass ``proxy`` (e.g. ``http://host:port``) to egress outside the internal network so a
    PUBLIC site is measured at the edge, not the internal origin. See net-rotating-proxies.
    """
    import httpx2 as httpx

    https = url.lower().startswith("https://")
    ua = {"User-Agent": "sec-appsec-web-baseline/1.0"}
    with httpx.Client(follow_redirects=True, timeout=15.0, proxy=proxy, headers=ua) as c:
        resp = c.get(url)
        html = resp.text if "text/html" in resp.headers.get("content-type", "") else ""
        set_cookies = resp.headers.get_list("set-cookie")
        http_status = http_location = None
        host = re.sub(r"^https?://", "", url)
        try:
            r2 = httpx.head("http://" + host, follow_redirects=False, timeout=10.0, proxy=proxy)
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


def _is_internal_ip(ip: str) -> bool:
    """True if ip is private / loopback / link-local (RFC1918 etc.) - an INTERNAL address, not a
    public edge. Used to detect a same-subnet/internal target."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local


def internal_target_warning(url: str, proxy: str | None) -> str | None:  # pragma: no cover - DNS I/O
    """Warn when a public-site audit is actually hitting an INTERNAL address with no proxy.

    For a site in your own subnet (split-horizon DNS resolving to an RFC1918 IP), a direct scan
    measures the internal origin/edge, not the public path external visitors get. Returns the warning
    text, or None when a proxy is set or the host resolves to a public IP.
    """
    if proxy:
        return None
    host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0]
    try:
        ip = socket.gethostbyname(host)
    except OSError:
        return None
    if _is_internal_ip(ip):
        return (f"{host} resolves to an INTERNAL address ({ip}) and no --proxy was given - this measures the "
                f"internal path (origin / split-horizon edge), NOT what external visitors get. For a public "
                f"site, re-run through an external egress: --proxy http://<proxy> (get a few via the "
                f"net-rotating-proxies skill).")
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a URL's HTTP web-security baseline.")
    parser.add_argument("url")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument("--proxy", help="route the fetch through this proxy URL to egress outside the "
                                        "internal network (public sites; see the net-rotating-proxies skill)")
    args = parser.parse_args(argv)

    warning = internal_target_warning(args.url, args.proxy)
    findings = fetch(args.url, proxy=args.proxy)
    counts = summarize(findings)
    if args.json:
        out: dict[str, object] = {"url": args.url, "counts": counts, "findings": [asdict(f) for f in findings]}
        if warning:
            out["internal_target_warning"] = warning
        print(json.dumps(out, indent=2))
    else:
        if warning:
            sys.stderr.write("WARNING: " + warning + "\n")
        for f in findings:
            if f.severity != "OK":
                print(f"  [{f.severity}] {f.check}: {f.detail}" + (f"  -> {f.fix}" if f.fix else ""))
        print(f"\n{args.url}: " + " ".join(f"{k}={counts[k]}" for k in SEVERITIES))
    # exit non-zero if the gate (0 SEVERE / 0 MEDIUM) is not met
    return 1 if counts["SEVERE"] or counts["MEDIUM"] else 0


if __name__ == "__main__":
    sys.exit(main())
