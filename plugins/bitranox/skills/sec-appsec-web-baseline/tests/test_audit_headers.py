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


# ---- regression: review fixes ----
def test_mixed_content_ignores_anchor_href():
    # a plain <a href="http://"> navigates away - it is NOT a mixed-content subresource
    assert a._mixed_content('<a href="http://wikipedia.org/x">link</a>', https=True) == []


def test_mixed_content_flags_srcset():
    findings = a._mixed_content('<img srcset="http://cdn/x.png 1x, https://cdn/x2.png 2x">', https=True)
    assert findings and findings[0].severity == "SEVERE"


def test_mixed_content_flags_link_stylesheet():
    findings = a._mixed_content('<link rel="stylesheet" href="http://cdn/x.css">', https=True)
    assert findings and findings[0].severity == "SEVERE"


def test_csp_report_only_is_minor():
    assert a._csp("default-src 'self'", enforced=False).severity == "MINOR"


def test_grade_report_only_csp_is_minor_and_clickjacking_still_flags():
    # report-only CSP protects nothing: csp -> MINOR, and clickjacking must NOT read it as OK
    headers = {"Content-Security-Policy-Report-Only": "default-src 'self'; frame-ancestors 'none'"}
    findings = a.grade(headers, [], https=True, http_status=301, http_location="https://x/", html="")
    by = {f.check: f.severity for f in findings}
    assert by["csp"] == "MINOR"
    assert by["clickjacking"] == "MEDIUM"


def test_referrer_no_referrer_when_downgrade_is_minor():
    assert a._referrer_policy("no-referrer-when-downgrade").severity == "MINOR"


def test_coop_present_ok_missing_minor():
    assert a._coop("same-origin-allow-popups").severity == "OK"
    assert a._coop("same-origin").severity == "OK"
    assert a._coop(None).severity == "MINOR"


def test_redirect_302_to_https_is_medium():
    assert a._redirect(302, "https://x/").severity == "MEDIUM"
    assert a._redirect(307, "https://x/").severity == "MEDIUM"


def test_server_token_product_name_with_digit_is_ok():
    # AmazonS3 has a digit but no version pattern - must not be flagged
    assert a._server_token("AmazonS3").severity == "OK"
    assert a._server_token("nginx/1.24.0").severity == "MINOR"


# ---- same-subnet / internal-target detection (enforce egress for public sites) ----
def test_is_internal_ip_private_loopback_linklocal():
    assert a._is_internal_ip("192.168.168.62")  # same-subnet split-horizon
    assert a._is_internal_ip("10.0.0.1")
    assert a._is_internal_ip("172.16.5.5")
    assert a._is_internal_ip("127.0.0.1")  # loopback
    assert a._is_internal_ip("169.254.1.1")  # link-local


def test_is_internal_ip_public_and_garbage():
    assert not a._is_internal_ip("88.116.105.146")  # public WAN
    assert not a._is_internal_ip("8.8.8.8")
    assert not a._is_internal_ip("not-an-ip")


# --- mixed content: a <link> only counts when its rel actually LOADS something ---------------

def _mixed(html):
    return a._mixed_content(html, https=True)


def test_link_canonical_over_http_is_not_mixed_content():
    """rel=canonical is metadata; it loads nothing, so it cannot be mixed content."""
    assert _mixed('<link rel="canonical" href="http://example.com/page">') == []


def test_non_loading_link_rels_are_not_mixed_content():
    for rel in ("canonical", "alternate", "dns-prefetch", "preconnect", "author", "license", "next"):
        html = '<link rel="%s" href="http://example.com/x">' % rel
        assert _mixed(html) == [], "rel=%s loads nothing" % rel


def test_loading_link_rels_are_still_mixed_content():
    for rel in ("stylesheet", "preload", "icon", "shortcut icon", "manifest", "apple-touch-icon"):
        html = '<link rel="%s" href="http://example.com/x.css">' % rel
        assert _mixed(html), "rel=%s does load a subresource" % rel


def test_a_link_with_no_rel_is_treated_as_loading():
    """Unknown or absent rel stays a finding: a security check fails loud, not silent."""
    assert _mixed('<link href="http://example.com/x.css">')


def test_other_subresource_tags_are_unaffected():
    assert _mixed('<img src="http://example.com/a.png">')
    assert _mixed('<script src="http://example.com/a.js"></script>')
    assert _mixed('<a href="http://example.com/page">x</a>') == []      # navigation, not a load


# ---- mixed content: unquoted attribute values (minified HTML) ----
def test_mixed_content_flags_unquoted_http_src():
    assert _mixed('<script src=http://cdn.example.com/app.js></script>')
    assert _mixed('<img src=http://cdn.example.com/a.png>')


def test_mixed_content_unquoted_https_src_is_clean():
    assert _mixed('<script src=https://cdn.example.com/app.js></script>') == []


# ---- cookies: attributes are compared by NAME, never as substrings of the line ----
def test_cookie_name_containing_secure_is_not_the_secure_attribute():
    findings = a._cookies(["secure_session=abc; HttpOnly; SameSite=Lax"], https=True)
    assert [f.severity for f in findings] == ["SEVERE"]


def test_cookie_path_or_domain_containing_secure_is_not_the_secure_attribute():
    for raw in ("sid=abc; Path=/secure; HttpOnly; SameSite=Lax",
                "sid=abc; Domain=secure.example.com; HttpOnly; SameSite=Lax"):
        assert [f.severity for f in a._cookies([raw], https=True)] == ["SEVERE"], raw


def test_cookie_value_containing_httponly_is_not_the_httponly_attribute():
    findings = a._cookies(["pref=httponly; Secure; SameSite=Lax"], https=True)
    assert [f.severity for f in findings] == ["MEDIUM"]


def test_cookie_attribute_names_are_case_and_space_insensitive():
    assert a._cookies(["sid=abc;secure ;  HTTPONLY; samesite=Strict"], https=True) == []


# ---- clickjacking: frame-ancestors must actually restrict framing ----
def test_clickjacking_frame_ancestors_wildcard_is_medium():
    assert sev(a._clickjacking(None, "default-src 'self'; frame-ancestors *")) == "MEDIUM"


def test_clickjacking_frame_ancestors_scheme_only_source_is_medium():
    assert sev(a._clickjacking(None, "frame-ancestors https:")) == "MEDIUM"
    assert sev(a._clickjacking(None, "frame-ancestors 'self' https:")) == "MEDIUM"


def test_clickjacking_frame_ancestors_wildcard_is_not_rescued_by_xfo():
    # browsers ignore X-Frame-Options when an enforced frame-ancestors is present
    assert sev(a._clickjacking("DENY", "frame-ancestors *")) == "MEDIUM"


def test_clickjacking_frame_ancestors_self_and_explicit_origins_ok():
    assert sev(a._clickjacking(None, "frame-ancestors 'self'")) == "OK"
    assert sev(a._clickjacking(None, "frame-ancestors 'self' https://partner.example.com")) == "OK"
    assert sev(a._clickjacking(None, "FRAME-ANCESTORS 'NONE'")) == "OK"


def test_clickjacking_directive_named_like_frame_ancestors_does_not_count():
    # only a directive whose NAME is frame-ancestors counts, not a substring elsewhere
    assert sev(a._clickjacking(None, "default-src 'self'; report-uri /frame-ancestors")) == "MEDIUM"


# ---- CSP: directives are matched by name, not by prefix ----
def test_csp_script_src_elem_before_script_src_does_not_hide_unsafe_inline():
    policy = "script-src-elem 'self'; script-src 'self' 'unsafe-inline'; object-src 'none'"
    assert sev(a._csp(policy)) == "MEDIUM"


def test_csp_default_src_fallback_is_graded():
    assert sev(a._csp("default-src 'self' 'unsafe-inline'")) == "MEDIUM"


def test_csp_without_object_or_default_src_is_minor():
    assert sev(a._csp("script-src 'self'")) == "MINOR"


def test_csp_nonce_or_hash_makes_fallback_unsafe_inline_ignored():
    strict = "script-src 'nonce-r4nd0m' 'strict-dynamic' 'unsafe-inline' https:; object-src 'none'; base-uri 'none'"
    assert sev(a._csp(strict)) == "OK"
    hashed = "script-src 'sha256-abc=' 'unsafe-inline'; object-src 'none'"
    assert sev(a._csp(hashed)) == "OK"


def test_csp_unsafe_inline_without_nonce_or_hash_still_medium():
    assert sev(a._csp("script-src 'self' 'unsafe-inline'; object-src 'none'")) == "MEDIUM"


# ---- HSTS: the quoted max-age form is legal (RFC 6797) ----
def test_hsts_quoted_max_age_is_read():
    assert sev(a._hsts('max-age="31536000"; includeSubDomains', https=True)) == "OK"


# ---- repeated headers arrive joined with ", " ----
def test_nosniff_repeated_header_is_ok():
    assert sev(a._nosniff("nosniff, nosniff")) == "OK"
    assert sev(a._nosniff("nosniff, garbage")) == "OK"  # Fetch: the FIRST value decides


def test_nosniff_first_value_not_nosniff_is_medium():
    assert sev(a._nosniff("garbage, nosniff")) == "MEDIUM"


def test_xfo_repeated_identical_values_ok_conflicting_medium():
    assert sev(a._clickjacking("DENY, DENY", None)) == "OK"
    assert sev(a._clickjacking("DENY, SAMEORIGIN", None)) == "MEDIUM"


def test_referrer_policy_repeated_header_uses_last_recognised_token():
    assert sev(a._referrer_policy("strict-origin-when-cross-origin, strict-origin-when-cross-origin")) == "OK"
    assert sev(a._referrer_policy("no-referrer, unsafe-url")) == "MINOR"
    assert sev(a._referrer_policy("unsafe-url, no-referrer")) == "OK"


def test_grade_repeated_nosniff_and_xfo_headers_do_not_read_as_missing():
    headers = {"X-Content-Type-Options": "nosniff, nosniff", "X-Frame-Options": "DENY, DENY"}
    by = {f.check: f.severity for f in a.grade(headers, [], https=True, http_status=301,
                                                   http_location="https://x/", html="")}
    assert by["x-content-type-options"] == "OK"
    assert by["clickjacking"] == "OK"


# ---- information leakage: framework version headers ----
def test_grade_flags_x_powered_by_version():
    findings = a.grade({"X-Powered-By": "PHP/8.1.2", "Server": "nginx"}, [], https=True,
                       http_status=301, http_location="https://x/")
    by = {f.check: f for f in findings}
    assert by["server-token"].severity == "OK"
    assert by["x-powered-by-token"].severity == "MINOR"
    assert "8.1.2" in by["x-powered-by-token"].detail


def test_grade_flags_x_aspnet_version():
    findings = a.grade({"X-AspNet-Version": "4.0.30319"}, [], https=True,
                       http_status=301, http_location="https://x/")
    assert {f.check: f.severity for f in findings}["x-aspnet-version-token"] == "MINOR"


def test_grade_x_powered_by_without_version_is_ok_and_absent_adds_nothing():
    by = {f.check: f.severity for f in a.grade({"X-Powered-By": "Express"}, [], https=True,
                                               http_status=301, http_location="https://x/")}
    assert by["x-powered-by-token"] == "OK"
    absent = {f.check for f in a.grade({}, [], https=True, http_status=301, http_location="https://x/")}
    assert "x-powered-by-token" not in absent


# ---- internal-target detection: CGNAT / Tailscale ----
def test_is_internal_ip_cgnat():
    assert a._is_internal_ip("100.101.102.103")
    assert a._is_internal_ip("100.64.0.1")
    assert not a._is_internal_ip("100.128.0.1")  # just outside 100.64.0.0/10
