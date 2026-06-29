# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.44"]
# ///
"""Headless responsive/usability audit runner (bundled backend).

Sweeps a URL across the device matrix in a real Chromium (via Playwright), collects raw
measurements with ``detectors.js`` plus an optional axe-core a11y pass, screenshots each
profile, and writes a structured JSON report. All judgement is delegated to ``analysis.py``
so the decision layer is unit-tested without a browser; this file is the thin I/O shell.

Run it with uv so the dependency is isolated and fetched on demand:

    uv run audit_responsive.py http://localhost:8000/view/ABC123 --out ./audit-out

First run needs the browser binary once:

    uv run --with playwright playwright install chromium

Authenticated (user-gated) pages: pass a Playwright storageState JSON saved by
``make_storage_state.py`` via ``--storage-state state.json``.

This module is import-safe: all work is inside functions guarded by ``__main__`` so the
helpers can be imported in tests; the heavy browser path is only reached when run directly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Pinned axe-core from a CDN; injected at runtime so nothing is vendored (and no
# redistribution/attribution obligation). Override with --axe-url for an offline mirror.
DEFAULT_AXE_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"

# Expands visible text ~40% and checks whether that overflows - the layout-only i18n slice.
# Mutation is not restored: it runs last, after the screenshot, just before the context closes.
PSEUDO_LOCALIZE_JS = r"""
() => {
  const before = document.documentElement.scrollWidth;
  const vw = document.documentElement.clientWidth;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) {
    const t = walker.currentNode;
    if (t.nodeValue && t.nodeValue.trim().length > 2) nodes.push(t);
  }
  for (const t of nodes) {
    const s = t.nodeValue;
    t.nodeValue = s + " " + s.slice(0, Math.ceil(s.length * 0.4));
  }
  const after = document.documentElement.scrollWidth;
  return after > vw + 1 && after > before;
}
"""


def _detectors_source() -> str:
    return (Path(__file__).resolve().parent / "detectors.js").read_text(encoding="utf-8")


def slugify(text: str) -> str:
    """Filesystem-safe slug for screenshot filenames."""
    keep = [c if c.isalnum() else "-" for c in text.lower()]
    slug = "".join(keep)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "page"


_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


def guess_content_type(path) -> str:
    """Content-Type for a fulfilled local asset, by suffix (defaults to octet-stream)."""
    return _CONTENT_TYPES.get(Path(path).suffix.lower(), "application/octet-stream")


def parse_route_specs(specs):
    """Parse ``--route 'GLOB=LOCALPATH'`` strings into ``(glob, Path)`` overlay rules.

    Lets you audit the LIVE remote URL (real images/data stream from the real host) while
    the browser fulfills matching requests - your edited CSS/JS - from local files, so you
    iterate on the layout WITHOUT deploying anything to the server. The split is on the
    first ``=`` so a path may contain ``=``. Raises ValueError on a malformed spec.
    """
    rules = []
    for spec in specs or []:
        if "=" not in spec:
            raise ValueError(f"route spec must be 'GLOB=LOCALPATH', got: {spec!r}")
        glob, local = spec.split("=", 1)
        glob, local = glob.strip(), local.strip()
        if not glob or not local:
            raise ValueError(f"route spec must be 'GLOB=LOCALPATH', got: {spec!r}")
        rules.append((glob, Path(local)))
    return rules


def _make_route_handler(local_path):
    """Build a ONE-argument route handler that fulfills from ``local_path``.

    A single positional arg is deliberate: Playwright calls a two-arg handler with
    ``(route, request)``, which would clobber a captured-via-default path. The factory
    closes over ``local_path`` instead, sidestepping both that and late-binding-in-loop.
    """
    def handler(route):
        try:
            route.fulfill(path=str(local_path), content_type=guess_content_type(local_path))
        except Exception:  # noqa: BLE001 - if the local file is unreadable, let the real one load
            route.continue_()

    return handler


def _apply_routes(page, route_rules):
    """Register request-interception overlays: fulfill matching URLs from local files."""
    for glob, local in route_rules:
        page.route(glob, _make_route_handler(local))


def audit_one_profile(browser, profile: dict, url: str, *, storage_state, axe_url, do_axe, do_i18n, out_dir, route_rules=()):
    """Open one device profile, collect raw measurements, return its device report."""
    from analysis import build_device_report  # local import: only when actually running

    context = browser.new_context(
        viewport={"width": profile["width"], "height": profile["height"]},
        device_scale_factor=profile["dpr"],
        is_mobile=profile["is_mobile"],
        has_touch=profile["has_touch"],
        storage_state=storage_state,
    )
    page = context.new_page()
    _apply_routes(page, route_rules)  # overlay local assets onto the (possibly remote) page
    raw: dict = {}
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        raw = page.evaluate(_detectors_source())
        # Screenshot the clean page BEFORE axe injection / text mutation.
        page.screenshot(path=str(out_dir / f"{slugify(profile['name'])}.png"), full_page=False)
        if do_axe:
            try:
                page.add_script_tag(url=axe_url)
                raw["axe_violations"] = page.evaluate("async () => (await axe.run()).violations")
            except Exception as exc:  # noqa: BLE001 - axe is best-effort, never fail the run
                raw["axe_error"] = str(exc)
        if do_i18n:
            try:
                raw["text_expansion_overflow"] = page.evaluate(PSEUDO_LOCALIZE_JS)
            except Exception:  # noqa: BLE001
                raw["text_expansion_overflow"] = False
    finally:
        context.close()
    report = build_device_report(profile, raw)
    report["screenshot"] = f"{slugify(profile['name'])}.png"
    return report


def run_audit(url, profiles, *, storage_state_path=None, axe_url=DEFAULT_AXE_URL, do_axe=True, do_i18n=False, out_dir=Path("audit-out"), route_rules=()):
    """Drive the whole sweep and return the aggregated report dict."""
    from playwright.sync_api import sync_playwright

    from analysis import aggregate_report

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    storage_state = str(storage_state_path) if storage_state_path else None

    device_reports = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for profile in profiles:
                device_reports.append(
                    audit_one_profile(
                        browser, profile, url,
                        storage_state=storage_state, axe_url=axe_url,
                        do_axe=do_axe, do_i18n=do_i18n, out_dir=out_dir,
                        route_rules=route_rules,
                    )
                )
        finally:
            browser.close()
    return aggregate_report(device_reports, url=url)


def parse_args(argv):
    p = argparse.ArgumentParser(description="Responsive/usability audit across a device matrix.")
    p.add_argument("url", help="page URL to audit (e.g. http://localhost:8000/view/ABC123)")
    p.add_argument("--out", default="audit-out", help="output directory for report.json + screenshots")
    p.add_argument("--storage-state", default=None, help="Playwright storageState JSON for user-gated pages")
    p.add_argument("--profiles", nargs="*", default=None, help="subset of profile display names; default = full matrix")
    p.add_argument("--no-landscape", action="store_true", help="portrait/native orientations only")
    p.add_argument("--no-axe", action="store_true", help="skip the axe-core accessibility pass")
    p.add_argument("--i18n", action="store_true", help="also run the pseudo-localization text-expansion check")
    p.add_argument("--axe-url", default=DEFAULT_AXE_URL, help="axe-core script URL (point to a local mirror for offline)")
    p.add_argument(
        "--route", action="append", default=None, metavar="GLOB=LOCALPATH",
        help="overlay a local file onto matching requests, e.g. '**/static/css/app.css=src/static/css/app.css'; "
             "repeatable. Lets you audit the LIVE remote URL while testing your edited CSS/JS locally - no deploy.",
    )
    return p.parse_args(argv)


def main(argv=None):
    from device_profiles import default_profiles, profile_by_name

    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.profiles:
        profiles = [p for p in (profile_by_name(n) for n in args.profiles) if p]
        if not profiles:
            print("No matching profiles; run without --profiles to see the full matrix.", file=sys.stderr)
            return 2
    else:
        profiles = default_profiles(include_landscape=not args.no_landscape)

    try:
        route_rules = parse_route_specs(args.route)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        report = run_audit(
            args.url, profiles,
            storage_state_path=args.storage_state, axe_url=args.axe_url,
            do_axe=not args.no_axe, do_i18n=args.i18n, out_dir=Path(args.out),
            route_rules=route_rules,
        )
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "Executable doesn't exist" in msg or "playwright install" in msg:
            print("Chromium not installed. Run: uv run --with playwright playwright install chromium", file=sys.stderr)
            return 3
        print(f"Audit failed: {exc}", file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    t = report["totals"]
    verdict = "PASS" if report["passed"] else "FAIL"
    print(f"Audit {verdict}: SEVERE={t['SEVERE']} MEDIUM={t['MEDIUM']} MINOR={t['MINOR']}")
    print(f"Report: {out_dir / 'report.json'}  (screenshots alongside)")
    return 0 if report["passed"] else 4


if __name__ == "__main__":
    sys.exit(main())
