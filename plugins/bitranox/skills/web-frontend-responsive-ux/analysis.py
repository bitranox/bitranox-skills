"""Pure analysis core for the responsive/usability audit - no browser, no I/O.

The browser backends (the bundled Playwright runner or an MCP session) collect raw
measurements per device profile and hand them to these functions, which apply the
thresholds and produce a structured, sorted report. Keeping the judgment here (and out
of the browser code) is what lets the whole decision layer be unit-tested without a real
browser - the same split `coding-python-performance-review` uses for its analyzers.

Threshold rationale (see references/touch-and-gestures.md for citations):
  * Touch target  >= 24x24 CSS px is WCAG 2.5.8 (AA); 44 (Apple HIG) / 48 (Material) is
    the recommended comfortable size. Below 24 fails AA -> SEVERE; 24..rec passes AA but
    is cramped -> MEDIUM; spacing < 8 px between targets is itself a finding.
  * Horizontal overflow: a scrollWidth wider than the viewport on a small screen is the
    "no horizontal scrollbar on mobile/tablet" defect -> SEVERE on mobile/tablet.
  * Vertical fit: content taller than the viewport on a phone (portrait or landscape)
    means avoidable vertical scrolling -> MEDIUM; content that fills very little of a
    large viewport with no scroll is over-sparse -> MINOR (advisory).
"""

from __future__ import annotations

# --- thresholds (CSS pixels) -------------------------------------------------

TOUCH_MIN_AA = 24.0  # WCAG 2.5.8 Target Size (Minimum), Level AA
TOUCH_RECOMMENDED = 44.0  # Apple HIG; Material uses 48 - 44 is the floor we require
TOUCH_SPACING_MIN = 8.0  # minimum gap between adjacent interactive targets
OVERFLOW_TOLERANCE = 1.0  # sub-pixel rounding slack before calling it overflow
SPARSE_FILL_RATIO = 0.55  # below this content/viewport fill on a big screen = over-sparse

SEVERITY_ORDER = ("SEVERE", "MEDIUM", "MINOR", "OK")


def severity_rank(severity: str) -> int:
    """Sort key: SEVERE first, OK last. Unknown severities sort after known ones."""
    try:
        return SEVERITY_ORDER.index(severity)
    except ValueError:
        return len(SEVERITY_ORDER)


def classify_touch_target(width: float, height: float) -> str:
    """Severity for one interactive target's rendered box (CSS px).

    < 24 in either axis fails WCAG 2.5.8 (SEVERE); 24..44 passes AA but is below the
    recommended comfortable size (MEDIUM); >= 44 in both axes is OK.
    """
    smaller = min(width, height)
    if smaller < TOUCH_MIN_AA:
        return "SEVERE"
    if smaller < TOUCH_RECOMMENDED:
        return "MEDIUM"
    return "OK"


def touch_target_findings(targets: list[dict]) -> list[dict]:
    """Map raw target measurements to findings, dropping OK ones.

    Each target dict carries at least ``selector``, ``width``, ``height`` and optionally
    ``min_gap`` (smallest gap to a neighbouring target, CSS px). Returns findings with a
    severity, the failing dimension(s), and a concrete remediation hint.
    """
    findings: list[dict] = []
    for t in targets:
        width = float(t.get("width", 0.0))
        height = float(t.get("height", 0.0))
        severity = classify_touch_target(width, height)
        gap = t.get("min_gap")
        cramped_gap = gap is not None and float(gap) < TOUCH_SPACING_MIN
        if severity == "OK" and not cramped_gap:
            continue
        reasons = []
        if severity != "OK":
            reasons.append(f"target {width:.0f}x{height:.0f}px < {int(TOUCH_RECOMMENDED)}px recommended")
        if cramped_gap:
            reasons.append(f"gap {float(gap):.0f}px < {int(TOUCH_SPACING_MIN)}px to neighbour")
            if severity == "OK":
                severity = "MEDIUM"
        findings.append(
            {
                "check": "touch-target",
                "severity": severity,
                "selector": t.get("selector", "?"),
                "detail": "; ".join(reasons),
                "fix": "enlarge the hit area to >=44px (min-block/inline-size or padding) and keep >=8px spacing",
            }
        )
    return findings


def overflow_finding(scroll_width: float, client_width: float, device_kind: str, *, offenders: list | None = None) -> dict | None:
    """Flag horizontal overflow (scrollWidth wider than the viewport).

    SEVERE on phones/tablets (the explicit "no horizontal scrollbar on mobile/tablet"
    rule); MEDIUM on desktop where a stray overflow is less harmful but still a defect.
    Returns ``None`` when the page fits.
    """
    if scroll_width <= client_width + OVERFLOW_TOLERANCE:
        return None
    severity = "SEVERE" if device_kind in ("phone", "tablet") else "MEDIUM"
    return {
        "check": "horizontal-overflow",
        "severity": severity,
        "detail": f"scrollWidth {scroll_width:.0f}px > viewport {client_width:.0f}px (overflow {scroll_width - client_width:.0f}px)",
        "offenders": list(offenders or [])[:10],
        "fix": "find the element wider than the viewport; use max-width:100%, min-width:0 on flex/grid children, box-sizing:border-box, and avoid fixed widths/100vw with scrollbars",
    }


def vertical_fit_finding(content_height: float, viewport_height: float, device_kind: str, orientation: str) -> dict | None:
    """Flag avoidable vertical scrolling on phones, and over-sparse big screens.

    On a phone (portrait OR landscape) content taller than the viewport is avoidable
    scrolling -> MEDIUM. On a large screen, content filling less than ``SPARSE_FILL_RATIO``
    of the viewport with no need to scroll is over-sparse -> MINOR (advisory). Otherwise
    ``None``.
    """
    if viewport_height <= 0:
        return None
    fill = content_height / viewport_height
    if device_kind == "phone" and content_height > viewport_height + OVERFLOW_TOLERANCE:
        return {
            "check": "vertical-fit",
            "severity": "MEDIUM",
            "detail": f"content {content_height:.0f}px exceeds {orientation} viewport {viewport_height:.0f}px (fill {fill:.0%})",
            "fix": "distribute with a grid/flex column (1fr regions), size to svh/dvh, and use clamp() spacing so the primary content fits without scrolling",
        }
    if device_kind == "desktop" and fill < SPARSE_FILL_RATIO and content_height <= viewport_height:
        return {
            "check": "vertical-fit",
            "severity": "MINOR",
            "detail": f"content fills only {fill:.0%} of the {viewport_height:.0f}px viewport - layout may look sparse",
            "fix": "let primary content grow with min(1fr) regions / max-inline-size, or add fluid clamp() padding so large screens are not under-filled",
        }
    return None


def text_expansion_finding(overflowed: bool, device_kind: str, *, sample: str = "") -> dict | None:
    """Flag clipping/overflow under pseudo-localized (expanded) text or RTL mirroring.

    ``overflowed`` is True when the detector saw an element clip or push past the viewport
    after pseudo-localization. This is the layout-only slice of i18n; full localization
    infra belongs to the ``web-frontend-i18n`` sibling skill.
    """
    if not overflowed:
        return None
    return {
        "check": "i18n-layout",
        "severity": "MEDIUM",
        "detail": f"layout breaks under expanded/pseudo-localized text{(' near ' + sample) if sample else ''}",
        "fix": "avoid fixed widths on text containers, allow wrapping, reserve space for ~30-40% longer strings, and test dir=rtl mirroring",
    }


def summarize_axe(violations: list[dict]) -> dict:
    """Reduce axe-core violations to counts by impact and a flat finding list.

    Each axe violation dict has ``id``, ``impact`` (critical|serious|moderate|minor) and
    ``nodes``. ``critical``/``serious`` map to SEVERE, ``moderate`` to MEDIUM, ``minor`` to
    MINOR.
    """
    impact_to_sev = {"critical": "SEVERE", "serious": "SEVERE", "moderate": "MEDIUM", "minor": "MINOR"}
    counts = {"SEVERE": 0, "MEDIUM": 0, "MINOR": 0}
    findings: list[dict] = []
    for v in violations:
        sev = impact_to_sev.get(v.get("impact") or "", "MINOR")
        nodes = v.get("nodes") or []
        counts[sev] += 1
        findings.append(
            {
                "check": "a11y",
                "severity": sev,
                "detail": f"{v.get('id', 'rule')}: {v.get('help', '')}".strip(": ").strip(),
                "nodes": len(nodes),
                "fix": v.get("helpUrl", ""),
            }
        )
    return {"counts": counts, "findings": findings}


def build_device_report(profile: dict, raw: dict) -> dict:
    """Assemble one device profile's findings from its raw measurements.

    ``raw`` keys (all optional): ``scroll_width``, ``client_width``, ``content_height``,
    ``viewport_height``, ``targets`` (list), ``overflow_offenders`` (list),
    ``axe_violations`` (list), ``text_expansion_overflow`` (bool).
    """
    kind = profile.get("kind", "desktop")
    orientation = profile.get("orientation", "portrait")
    findings: list[dict] = []

    of = overflow_finding(
        float(raw.get("scroll_width", 0.0)),
        float(raw.get("client_width", 0.0)),
        kind,
        offenders=raw.get("overflow_offenders"),
    )
    if of:
        findings.append(of)

    vf = vertical_fit_finding(
        float(raw.get("content_height", 0.0)),
        float(raw.get("viewport_height", 0.0)),
        kind,
        orientation,
    )
    if vf:
        findings.append(vf)

    findings.extend(touch_target_findings(raw.get("targets") or []))

    te = text_expansion_finding(bool(raw.get("text_expansion_overflow")), kind)
    if te:
        findings.append(te)

    axe = summarize_axe(raw.get("axe_violations") or [])
    findings.extend(axe["findings"])

    findings.sort(key=lambda f: severity_rank(f.get("severity", "MINOR")))
    return {
        "profile": profile.get("name", "?"),
        "kind": kind,
        "orientation": orientation,
        "viewport": [profile.get("width"), profile.get("height")],
        "findings": findings,
        "axe_counts": axe["counts"],
    }


def aggregate_report(device_reports: list[dict], *, url: str = "") -> dict:
    """Roll per-device reports into one report with overall severity tallies and a verdict.

    ``passed`` is True only when there is no SEVERE or MEDIUM finding anywhere - the
    "we target 100%" bar for the dimensions this skill owns.
    """
    totals = {"SEVERE": 0, "MEDIUM": 0, "MINOR": 0}
    for dr in device_reports:
        for f in dr.get("findings", []):
            sev = f.get("severity", "MINOR")
            if sev in totals:
                totals[sev] += 1
    passed = totals["SEVERE"] == 0 and totals["MEDIUM"] == 0
    return {
        "url": url,
        "totals": totals,
        "passed": passed,
        "devices": device_reports,
    }
