"""Behaviour tests for the pure graders in audit_headers (no network)."""

import audit_headers as a


def sev(finding):
    return finding.severity


# ---- HSTS ----
def test_hsts_missing_on_https_is_severe():
    assert sev(a._hsts(None, https=True)) == "SEVERE"


def test_hsts_not_applicable_on_http():
    assert sev(a._hsts(None, https=False)) == "OK"


def test_hsts_short_max_age_is_medium():
    assert sev(a._hsts("max-age=300; includeSubDomains", https=True)) == "MEDIUM"


def test_hsts_strong_is_ok():
    assert sev(a._hsts("max-age=31536000; includeSubDomains", https=True)) == "OK"


def test_hsts_long_but_no_subdomains_is_minor():
    assert sev(a._hsts("max-age=31536000", https=True)) == "MINOR"


# ---- CSP ----
def test_csp_missing_is_severe():
    assert sev(a._csp(None)) == "SEVERE"


def test_csp_unsafe_inline_script_is_medium():
    assert sev(a._csp("default-src 'self'; script-src 'self' 'unsafe-inline'")) == "MEDIUM"


def test_csp_unsafe_eval_is_medium():
    assert sev(a._csp("default-src 'self'; script-src 'self' 'unsafe-eval'")) == "MEDIUM"


def test_csp_unsafe_inline_only_in_style_is_ok():
    # unsafe-inline in style-src must NOT trip the script check
    assert sev(a._csp("default-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'")) == "OK"


def test_csp_reasonable_is_ok():
    assert sev(a._csp("default-src 'self'; object-src 'none'; frame-ancestors 'none'")) == "OK"


# ---- nosniff / clickjacking / referrer / permissions / xss / server ----
def test_nosniff_present_ok_missing_medium():
    assert sev(a._nosniff("nosniff")) == "OK"
    assert sev(a._nosniff(None)) == "MEDIUM"


def test_clickjacking_csp_frame_ancestors_ok():
    assert sev(a._clickjacking(None, "default-src 'self'; frame-ancestors 'none'")) == "OK"


def test_clickjacking_xfo_ok():
    assert sev(a._clickjacking("DENY", None)) == "OK"


def test_clickjacking_neither_is_medium():
    assert sev(a._clickjacking(None, "default-src 'self'")) == "MEDIUM"


def test_referrer_policy_safe_ok_missing_minor():
    assert sev(a._referrer_policy("strict-origin-when-cross-origin")) == "OK"
    assert sev(a._referrer_policy(None)) == "MINOR"


def test_permissions_policy_present_ok_missing_minor():
    assert sev(a._permissions_policy("geolocation=()")) == "OK"
    assert sev(a._permissions_policy(None)) == "MINOR"


def test_xss_auditor_enabled_is_medium_off_is_ok():
    assert sev(a._xss_auditor("1; mode=block")) == "MEDIUM"
    assert sev(a._xss_auditor("0")) == "OK"
    assert sev(a._xss_auditor(None)) == "OK"


def test_server_token_version_leak_is_minor():
    assert sev(a._server_token("nginx/1.24.0")) == "MINOR"
    assert sev(a._server_token("nginx")) == "OK"


# ---- cookies ----
def test_cookie_without_secure_on_https_is_severe():
    findings = a._cookies(["sid=abc; Path=/"], https=True)
    assert any(f.severity == "SEVERE" for f in findings)


def test_cookie_secure_httponly_samesite_is_clean():
    findings = a._cookies(["sid=abc; Secure; HttpOnly; SameSite=Lax"], https=True)
    assert findings == []


def test_cookie_missing_httponly_and_samesite():
    findings = a._cookies(["sid=abc; Secure"], https=True)
    sevs = sorted(f.severity for f in findings)
    assert sevs == ["MEDIUM", "MINOR"]


# ---- redirect ----
def test_redirect_301_to_https_ok():
    assert sev(a._redirect(301, "https://x/")) == "OK"


def test_redirect_missing_is_severe():
    assert sev(a._redirect(200, None)) == "SEVERE"


def test_redirect_probe_failed_is_minor():
    assert sev(a._redirect(None, None)) == "MINOR"


# ---- mixed content ----
def test_mixed_content_flags_http_subresource():
    html = '<img src="http://cdn/x.png"><script src="https://ok/y.js"></script>'
    findings = a._mixed_content(html, https=True)
    assert findings and findings[0].severity == "SEVERE"


def test_mixed_content_clean_https_only():
    assert a._mixed_content('<img src="https://cdn/x.png">', https=True) == []


def test_mixed_content_skipped_on_http_page():
    assert a._mixed_content('<img src="http://cdn/x.png">', https=False) == []


# ---- grade() + summarize() integration ----
def test_grade_clean_site_has_no_severe_or_medium():
    headers = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; object-src 'none'; frame-ancestors 'none'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=()",
        "Server": "nginx",
    }
    findings = a.grade(headers, [], https=True, http_status=301, http_location="https://x/", html="")
    counts = a.summarize(findings)
    assert counts["SEVERE"] == 0 and counts["MEDIUM"] == 0


def test_grade_bare_site_flags_severe():
    findings = a.grade({}, [], https=True, http_status=200, http_location=None, html="")
    counts = a.summarize(findings)
    # missing HSTS, missing CSP, no https redirect -> at least 3 SEVERE
    assert counts["SEVERE"] >= 3


def test_summarize_counts_all_levels():
    findings = [a.Finding("a", "SEVERE", ""), a.Finding("b", "MEDIUM", ""), a.Finding("c", "OK", "")]
    counts = a.summarize(findings)
    assert counts["SEVERE"] == 1 and counts["MEDIUM"] == 1 and counts["OK"] == 1 and counts["MINOR"] == 0
