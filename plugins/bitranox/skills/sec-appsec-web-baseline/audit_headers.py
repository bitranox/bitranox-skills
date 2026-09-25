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
from collections.abc import Callable
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

SEVERITIES = ("SEVERE", "MEDIUM", "MINOR", "OK")

# Elements that LOAD a subresource into the current page (so an http:// URL here is mixed
# content). <a> is deliberately excluded: it navigates away, it is not a subresource.
_SUBRESOURCE_TAGS = frozenset({
    "img", "script", "iframe", "video", "audio", "source", "track", "embed", "object", "link",
})
# The attributes that make those elements fetch. Matched by the WHOLE attribute name, as the
# HTML tokenizer reports it: a lazy-load `data-src` is inert until page JS copies it, and text
# such as `alt="src=http://x"` is a value, not an attribute.
_SUBRESOURCE_ATTRS = frozenset({"src", "data", "srcset", "href", "poster"})

# <link> is the one tag above that does NOT always load: rel decides. `canonical`, `alternate`,
# `dns-prefetch` and friends are metadata or connection hints, so an http:// href there is not
# mixed content, and grading it SEVERE sends the reader chasing a non-existent insecure load.
_NON_LOADING_LINK_RELS = frozenset({
    "canonical", "alternate", "author", "license", "next", "prev", "prefetch-dns",
    "dns-prefetch", "preconnect", "bookmark", "help", "search", "tag", "nofollow",
    "noopener", "noreferrer", "pingback", "profile", "me", "index", "up",
})


def _link_loads_a_subresource(rel: str | None) -> bool:
    """Whether a `<link>` with this `rel` value actually fetches something into the page.

    An absent or unrecognised `rel` counts as loading: a security check fails LOUD, so a rel this
    list has not seen yet is reported rather than silently dropped."""
    rels = {part.lower() for part in (rel or "").split()}
    if not rels:
        return True
    return bool(rels - _NON_LOADING_LINK_RELS)


class _SubresourceUrls(HTMLParser):
    """Collect the URL-bearing attribute values of subresource-loading start tags.

    The stdlib tokenizer gives what a regex over the raw text cannot: quoted values that hold
    `>`, attribute names read whole, comments skipped, and <script> text left unparsed."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _SUBRESOURCE_TAGS:
            return
        named = {name: value or "" for name, value in attrs}
        if tag == "link" and not _link_loads_a_subresource(named.get("rel")):
            return
        self.values.extend(value for name, value in attrs if name in _SUBRESOURCE_ATTRS and value)


def _subresource_urls(html: str) -> list[str]:
    """Every loading attribute value in the page, in document order (srcset still unsplit)."""
    reader = _SubresourceUrls()
    reader.feed(html)
    reader.close()
    return reader.values


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
    age = re.search(r'max-age\s*=\s*"?(\d+)', value, re.I)  # RFC 6797 allows a quoted value
    seconds = int(age.group(1)) if age else 0
    if seconds < 15552000:  # 180 days
        return Finding("hsts", "MEDIUM", f"max-age={seconds} is below 6 months",
                       "raise to max-age=31536000 once stable")
    if "includesubdomains" not in value.lower():
        return Finding("hsts", "MINOR", "no includeSubDomains", "add includeSubDomains if all subdomains are HTTPS")
    return Finding("hsts", "OK", value)


def _csp_directives(value: str) -> dict[str, str]:
    """Split a policy into ``{directive-name: source list}``, both lowercased.

    Directives are matched by NAME: a prefix search for ``script-src`` would find
    ``script-src-elem`` first. A repeated directive keeps its FIRST occurrence, as browsers do.
    """
    directives: dict[str, str] = {}
    for part in value.lower().split(";"):
        tokens = part.split(None, 1)
        if tokens and tokens[0] not in directives:
            directives[tokens[0]] = tokens[1].strip() if len(tokens) > 1 else ""
    return directives


# CSP Level 3 splits inline scripts by where they sit: script-src-elem governs <script> elements,
# script-src-attr inline event handlers, and each falls back to script-src, then default-src.
# script-src itself is graded too, because a CSP 2 browser ignores the two newer directives.
_INLINE_SCRIPT_DIRECTIVES = ("script-src", "script-src-elem", "script-src-attr")
_CSP_FALLBACK = {
    "script-src": ("script-src", "default-src"),
    "script-src-elem": ("script-src-elem", "script-src", "default-src"),
    "script-src-attr": ("script-src-attr", "script-src", "default-src"),
}


def _effective_sources(directives: dict[str, str], name: str) -> str:
    """The source list a browser enforces for ``name``: its own, else the first fallback present."""
    for candidate in _CSP_FALLBACK[name]:
        if candidate in directives:
            return directives[candidate]
    return ""


def _has_nonce_or_hash(sources: str) -> bool:
    """A nonce or hash source makes browsers IGNORE 'unsafe-inline' in the same list."""
    return bool(re.search(r"'(?:nonce-|sha256-|sha384-|sha512-)", sources))


def _csp(value: str | None, *, enforced: bool = True) -> Finding:
    """Grade Content-Security-Policy. Missing is SEVERE; report-only is MINOR (not enforced =
    not protection, only a rollout phase); unsafe-inline/eval in scripts is MEDIUM."""
    if not value:
        return Finding("csp", "SEVERE", "no Content-Security-Policy",
                       "add a policy starting from default-src 'self'; object-src 'none'; frame-ancestors 'none'")
    if not enforced:
        return Finding("csp", "MINOR", "CSP is report-only (a rollout phase, not enforced - it protects nothing yet)",
                       "promote to an enforced Content-Security-Policy once violations are clear")
    directives = _csp_directives(value)
    script_val = _effective_sources(directives, "script-src")
    for name in _INLINE_SCRIPT_DIRECTIVES:
        sources = _effective_sources(directives, name)
        if "'unsafe-inline'" in sources.split() and not _has_nonce_or_hash(sources):
            return Finding("csp", "MEDIUM", f"{name} allows 'unsafe-inline' (XSS not mitigated)",
                           "drop 'unsafe-inline'; use nonces or hashes for any inline script")
    # String compilation (eval) consults script-src only, never script-src-elem/-attr (CSP 3).
    if "'unsafe-eval'" in script_val:
        return Finding("csp", "MEDIUM", "script-src allows 'unsafe-eval'", "remove 'unsafe-eval'")
    if "object-src" not in directives and "default-src" not in directives:
        return Finding("csp", "MINOR", "no object-src/default-src fallback", "add default-src 'self'; object-src 'none'")
    return Finding("csp", "OK", "present, no unsafe-inline/eval in scripts")


def _header_tokens(value: str | None) -> list[str]:
    """A header value split into its comma-separated tokens, trimmed and lowercased.

    A header sent twice (app plus proxy) reaches us joined as ``"a, a"``, so an exact
    comparison against the whole value reads a correct header as missing."""
    if not value:
        return []
    return [token.strip().lower() for token in value.split(",") if token.strip()]


def _nosniff(value: str | None) -> Finding:
    tokens = _header_tokens(value)
    if tokens and tokens[0] == "nosniff":  # Fetch: only the FIRST value is consulted
        return Finding("x-content-type-options", "OK", "nosniff")
    return Finding("x-content-type-options", "MEDIUM", "missing or not 'nosniff'", 'set X-Content-Type-Options: nosniff')


# A frame-ancestors source that lets ANY site (or any site on a scheme) frame the page.
_PERMISSIVE_FRAME_SOURCE = re.compile(r"^(?:\*|[a-z][a-z0-9+.-]*:)$")


def _frame_ancestors_finding(sources: str) -> Finding:
    """Grade an enforced frame-ancestors source list: 'none', 'self' and explicit origins
    restrict framing; ``*`` or a scheme-only source (``https:``) allows any site to frame it."""
    permissive = [s for s in sources.split() if _PERMISSIVE_FRAME_SOURCE.match(s)]
    if permissive:
        return Finding("clickjacking", "MEDIUM",
                       f"CSP frame-ancestors allows any site to frame the page ({' '.join(permissive)})",
                       "restrict frame-ancestors to 'none', 'self' or explicit origins")
    # An empty source list means 'none' in CSP.
    return Finding("clickjacking", "OK", "CSP frame-ancestors " + (sources or "(empty list = 'none')"))


def _clickjacking(xfo: str | None, csp_enforced: str | None) -> Finding:
    """Clickjacking is covered by an ENFORCED CSP frame-ancestors OR X-Frame-Options. A
    report-only CSP does not count - it enforces nothing. When frame-ancestors is present
    browsers ignore X-Frame-Options, so a permissive frame-ancestors is not rescued by it."""
    directives = _csp_directives(csp_enforced) if csp_enforced else {}
    if "frame-ancestors" in directives:
        return _frame_ancestors_finding(directives["frame-ancestors"])
    tokens = _header_tokens(xfo)
    # HTML: a repeated X-Frame-Options applies only when every value agrees.
    if tokens and len(set(tokens)) == 1 and tokens[0] in ("deny", "sameorigin"):
        return Finding("clickjacking", "OK", f"X-Frame-Options: {tokens[0].upper()}")
    return Finding("clickjacking", "MEDIUM", "no enforced frame-ancestors and no X-Frame-Options",
                   "add CSP frame-ancestors 'none' (and X-Frame-Options: DENY for old browsers)")


_REFERRER_POLICIES = frozenset({
    "no-referrer", "no-referrer-when-downgrade", "same-origin", "origin", "strict-origin",
    "origin-when-cross-origin", "strict-origin-when-cross-origin", "unsafe-url",
})


def _referrer_policy(value: str | None) -> Finding:
    # no-referrer-when-downgrade is NOT safe: it sends the full URL (with query) to third-party
    # HTTPS destinations. A baseline wants strict-origin(-when-cross-origin) or stricter.
    safe = {"no-referrer", "strict-origin", "strict-origin-when-cross-origin", "same-origin", "origin"}
    # The header is a comma list and the LAST recognised token wins (Referrer Policy spec).
    known = [t for t in _header_tokens(value) if t in _REFERRER_POLICIES]
    if known and known[-1] in safe:
        return Finding("referrer-policy", "OK", value or "")
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


def _leaks_version(value: str | None) -> bool:
    # A version looks like 1.2 / 2.4.7 / v3 - a bare product name with a digit (AmazonS3) is not.
    return bool(value and re.search(r"v?\d+\.\d+", value))


def _server_token(value: str | None) -> Finding:
    if _leaks_version(value):
        return Finding("server-token", "MINOR", f"Server header leaks version: {value}",
                       "nginx: server_tokens off; strip upstream X-Powered-By")
    return Finding("server-token", "OK", value or "absent")


# Framework headers that name the stack behind the server, graded only when present.
_FRAMEWORK_VERSION_HEADERS = ("x-powered-by", "x-aspnet-version")


def _framework_tokens(h: dict[str, str]) -> list[Finding]:
    """One finding per framework header that is present: MINOR when it carries a version."""
    out: list[Finding] = []
    for header in _FRAMEWORK_VERSION_HEADERS:
        value = h.get(header)
        if value is None:
            continue
        if _leaks_version(value):
            out.append(Finding(f"{header}-token", "MINOR", f"{header} header leaks version: {value}",
                               f"strip or blank the {header} header at the proxy/app"))
        else:
            out.append(Finding(f"{header}-token", "OK", value))
    return out


def _cookie_attribute_names(raw: str) -> set[str]:
    """The attribute NAMES of one Set-Cookie line, lowercased; the name=value pair is skipped.

    A substring test on the whole line would read ``secure_session=...``, ``Path=/secure`` or
    a value of ``httponly`` as the flag itself."""
    parts = raw.split(";")[1:]
    return {part.split("=", 1)[0].strip().lower() for part in parts if part.strip()}


def _cookies(set_cookies: list[str], *, https: bool) -> list[Finding]:
    out: list[Finding] = []
    for raw in set_cookies:
        name = raw.split("=", 1)[0].strip()
        attrs = _cookie_attribute_names(raw)
        if https and "secure" not in attrs:
            out.append(Finding(f"cookie:{name}", "SEVERE", "Set-Cookie without Secure on HTTPS", "add the Secure attribute"))
        if "httponly" not in attrs:
            out.append(Finding(f"cookie:{name}", "MEDIUM", "Set-Cookie without HttpOnly", "add HttpOnly (unless JS must read it)"))
        if "samesite" not in attrs:
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
    for attr_val in _subresource_urls(html):
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
    findings += _framework_tokens(h)
    findings += _cookies(set_cookies, https=https)
    findings += _mixed_content(html, https=https)
    return findings


def plain_http_probe_url(url: str) -> str:
    """The plain-HTTP URL whose redirect is graded.

    An explicit port on an https:// URL belongs to TLS, so the probe goes to the default
    port 80 instead of speaking plain HTTP to the TLS port. An http:// URL keeps its port:
    that is the plain-HTTP endpoint the caller named.
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"
    keep_port = parts.scheme.lower() == "http" and parts.port is not None
    netloc = f"{host}:{parts.port}" if keep_port else host
    return urlunsplit(("http", netloc, parts.path, parts.query, ""))


def fetch(url: str, *, proxy: str | None = None, transport: object | None = None) -> list[Finding]:
    """I/O boundary: GET the URL (following redirects) + a plain-HTTP HEAD, then grade().

    Pass ``proxy`` (e.g. ``http://host:port``) to egress outside the internal network so a
    PUBLIC site is measured at the edge, not the internal origin. See net-rotating-proxies.
    ``transport`` replaces the network with an httpx transport (tests use a MockTransport).
    """
    import httpx2 as httpx  # noqa: PLC0415 - optional dependency: the pure graders import without it

    ua ={"User-Agent": "sec-appsec-web-baseline/1.0"}
    client_opts: dict[str, object] = {"follow_redirects": True, "timeout": 15.0, "headers": ua}
    if transport is not None:
        client_opts["transport"] = transport
    else:
        client_opts["proxy"] = proxy
    with httpx.Client(**client_opts) as c:
        resp = c.get(url)
        # Grade the page that was actually served: an http:// URL that redirects to https://
        # must get the HTTPS checks (HSTS, Secure cookies, mixed content).
        https = resp.url.scheme == "https"
        html = resp.text if "text/html" in resp.headers.get("content-type", "") else ""
        set_cookies = resp.headers.get_list("set-cookie")
        http_status = http_location = None
        try:
            r2 = c.head(plain_http_probe_url(url), follow_redirects=False, timeout=10.0)
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


_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def _is_internal_ip(ip: str) -> bool:
    """True if ip is private / loopback / link-local (RFC1918 etc.) - an INTERNAL address, not a
    public edge. Used to detect a same-subnet/internal target."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    # 100.64.0.0/10 (CGNAT, Tailscale) is not "private" to ipaddress but is not a public edge either.
    in_cgnat = addr.version == 4 and addr in _CGNAT
    return addr.is_private or addr.is_loopback or addr.is_link_local or in_cgnat


def internal_target_warning(url: str, proxy: str | None) -> str | None:
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


def _make_console_safe() -> None:
    """Escape characters the console cannot encode instead of crashing mid-report.

    A cp1252 Windows console (or a redirected stdout) cannot print a URL or IRI holding, say, a
    Greek letter; without this the summary line is lost to a UnicodeEncodeError."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (ValueError, OSError):
            pass  # a detached or non-reconfigurable stream keeps its own error handling


def main(argv: list[str] | None = None, *, fetcher: Callable[..., list[Finding]] | None = None) -> int:
    """CLI entry: exit 0 when the gate (0 SEVERE / 0 MEDIUM) is met, 1 when it is not, 2 when
    the URL could not be fetched at all. ``fetcher`` replaces :func:`fetch` (tests inject a
    network-free one)."""
    _make_console_safe()
    fetcher = fetcher or fetch
    parser = argparse.ArgumentParser(description="Audit a URL's HTTP web-security baseline.")
    parser.add_argument("url")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument("--proxy", help="route the fetch through this proxy URL to egress outside the "
                                        "internal network (public sites; see the net-rotating-proxies skill)")
    args = parser.parse_args(argv)

    warning = internal_target_warning(args.url, args.proxy)
    try:
        findings = fetcher(args.url, proxy=args.proxy)
    except Exception as exc:  # noqa: BLE001 - any fetch failure is "not measured", never a gate verdict
        sys.stderr.write(f"could not fetch {args.url}: {type(exc).__name__}: {exc}\n")
        return 2
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
