"""Behaviour tests for the pure analysis core (no browser)."""

import analysis


# --- touch targets ----------------------------------------------------------

def test_classify_touch_target_below_aa_is_severe():
    assert analysis.classify_touch_target(20, 20) == "SEVERE"
    assert analysis.classify_touch_target(48, 18) == "SEVERE"  # smaller axis decides


def test_classify_touch_target_passes_aa_but_below_recommended_is_medium():
    assert analysis.classify_touch_target(40, 40) == "MEDIUM"  # the real 40px mobile nav case


def test_classify_touch_target_recommended_is_ok():
    assert analysis.classify_touch_target(46, 46) == "OK"
    assert analysis.classify_touch_target(44, 100) == "OK"


def test_touch_target_findings_drops_ok_keeps_small():
    targets = [
        {"selector": ".big", "width": 48, "height": 48, "min_gap": 20},
        {"selector": ".nav", "width": 40, "height": 40, "min_gap": 20},
        {"selector": ".tiny", "width": 18, "height": 18, "min_gap": 20},
    ]
    findings = analysis.touch_target_findings(targets)
    selectors = {f["selector"]: f["severity"] for f in findings}
    assert ".big" not in selectors
    assert selectors[".nav"] == "MEDIUM"
    assert selectors[".tiny"] == "SEVERE"


def test_touch_target_cramped_spacing_flags_even_when_size_ok():
    findings = analysis.touch_target_findings([{"selector": ".x", "width": 48, "height": 48, "min_gap": 3}])
    assert len(findings) == 1
    assert findings[0]["severity"] == "MEDIUM"
    assert "gap" in findings[0]["detail"]


# --- horizontal overflow ----------------------------------------------------

def test_overflow_none_when_fits():
    assert analysis.overflow_finding(375, 375, "phone") is None
    assert analysis.overflow_finding(375.4, 375, "phone") is None  # within tolerance


def test_overflow_severe_on_mobile_medium_on_desktop():
    assert analysis.overflow_finding(420, 375, "phone")["severity"] == "SEVERE"
    assert analysis.overflow_finding(420, 375, "tablet")["severity"] == "SEVERE"
    assert analysis.overflow_finding(1500, 1440, "desktop")["severity"] == "MEDIUM"


def test_overflow_truncates_offenders():
    offenders = [{"selector": f".e{i}"} for i in range(30)]
    f = analysis.overflow_finding(500, 375, "phone", offenders=offenders)
    assert len(f["offenders"]) == 10


# --- vertical fit -----------------------------------------------------------

def test_vertical_fit_flags_phone_scroll_in_both_orientations():
    assert analysis.vertical_fit_finding(900, 667, "phone", "portrait")["severity"] == "MEDIUM"
    assert analysis.vertical_fit_finding(500, 375, "phone", "landscape")["severity"] == "MEDIUM"


def test_vertical_fit_ok_when_content_fits_phone():
    assert analysis.vertical_fit_finding(600, 667, "phone", "portrait") is None


def test_vertical_fit_flags_sparse_desktop():
    f = analysis.vertical_fit_finding(300, 900, "desktop", "landscape")
    assert f is not None and f["severity"] == "MINOR"


def test_vertical_fit_desktop_well_filled_is_ok():
    assert analysis.vertical_fit_finding(800, 900, "desktop", "landscape") is None


def test_vertical_fit_guards_zero_viewport():
    assert analysis.vertical_fit_finding(100, 0, "phone", "portrait") is None


# --- i18n layout slice ------------------------------------------------------

def test_text_expansion_finding_only_when_overflowed():
    assert analysis.text_expansion_finding(False, "phone") is None
    f = analysis.text_expansion_finding(True, "phone")
    assert f["severity"] == "MEDIUM" and f["check"] == "i18n-layout"


# --- axe summary ------------------------------------------------------------

def test_summarize_axe_maps_impacts_to_severity():
    violations = [
        {"id": "color-contrast", "impact": "serious", "help": "contrast", "nodes": [1, 2]},
        {"id": "label", "impact": "critical", "help": "labels", "nodes": [1]},
        {"id": "region", "impact": "moderate", "help": "landmark", "nodes": [1]},
        {"id": "x", "impact": "minor", "help": "x", "nodes": []},
    ]
    summary = analysis.summarize_axe(violations)
    assert summary["counts"] == {"SEVERE": 2, "MEDIUM": 1, "MINOR": 1}
    assert len(summary["findings"]) == 4


def test_summarize_axe_empty():
    assert analysis.summarize_axe([])["counts"] == {"SEVERE": 0, "MEDIUM": 0, "MINOR": 0}


# --- report assembly --------------------------------------------------------

def _phone_profile():
    return {"name": "iPhone SE (portrait)", "kind": "phone", "orientation": "portrait", "width": 375, "height": 667}


def test_build_device_report_sorts_severe_first():
    raw = {
        "scroll_width": 500, "client_width": 375,        # overflow -> SEVERE
        "content_height": 900, "viewport_height": 667,   # vertical -> MEDIUM
        "targets": [{"selector": ".nav", "width": 40, "height": 40, "min_gap": 20}],  # MEDIUM
        "axe_violations": [{"id": "label", "impact": "critical", "help": "h", "nodes": [1]}],  # SEVERE
    }
    report = analysis.build_device_report(_phone_profile(), raw)
    severities = [f["severity"] for f in report["findings"]]
    assert severities == sorted(severities, key=analysis.severity_rank)
    assert severities[0] == "SEVERE"
    assert report["axe_counts"]["SEVERE"] == 1


def test_aggregate_report_passes_only_without_severe_or_medium():
    clean = analysis.build_device_report(_phone_profile(), {
        "scroll_width": 375, "client_width": 375, "content_height": 600, "viewport_height": 667,
        "targets": [{"selector": ".ok", "width": 48, "height": 48, "min_gap": 20}],
    })
    agg = analysis.aggregate_report([clean], url="http://example.com")
    assert agg["passed"] is True
    assert agg["totals"] == {"SEVERE": 0, "MEDIUM": 0, "MINOR": 0}


def test_aggregate_report_fails_on_severe():
    bad = analysis.build_device_report(_phone_profile(), {"scroll_width": 500, "client_width": 375})
    agg = analysis.aggregate_report([bad], url="http://example.com")
    assert agg["passed"] is False
    assert agg["totals"]["SEVERE"] == 1
