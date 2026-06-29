# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.44"]
# ///
"""Open one LIVE, INTERACTIVE browser window per device viewport.

Companion to the headless ``audit_responsive.py``: instead of measuring and screenshotting, this
opens a real window for each profile in the device matrix so a human can operate the page by hand
(click, scroll, zoom, swipe on a touchscreen) at every size at once. It reuses the same ``--route``
overlay, so you can drive the LIVE remote page with your local edited CSS/JS - no deploy.

    uv run open_viewports.py https://app.example.com/view/ABC123 \
      --route "**/static/css/app.css=src/.../app.css" \
      --route "**/static/js/app.js=src/.../app.js"

It blocks while the windows are open and exits when you close them all (or kill the process).
Import-safe: the browser only opens under ``__main__``.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def open_windows(url, profiles, *, route_rules=(), storage_state_path=None, poll=2.0, delay=1.0):
    """Open one headed window per profile; block until every window is closed.

    Windows are opened one at a time with a ``delay`` pause between them. Opening many headed
    windows simultaneously hammers a single-worker backend (transient 5xx/404s under load) and
    the windows can paint incompletely; staggering lets each load and settle before the next.
    """
    from playwright.sync_api import sync_playwright

    from audit_responsive import _apply_routes

    storage_state = str(storage_state_path) if storage_state_path else None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        opened = 0
        for i, prof in enumerate(profiles):
            if i and delay:
                time.sleep(delay)  # stagger so each window loads correctly and the server isn't flooded
            ctx = browser.new_context(
                viewport={"width": prof["width"], "height": prof["height"]},
                device_scale_factor=prof["dpr"], is_mobile=prof["is_mobile"],
                has_touch=prof["has_touch"], storage_state=storage_state,
            )
            page = ctx.new_page()
            _apply_routes(page, route_rules)
            try:
                page.goto(url, wait_until="load", timeout=30000)  # let it fully paint before the next opens
                page.evaluate("t => { document.title = t; }", f"{prof['name']}  {prof['width']}x{prof['height']}")
            except Exception as exc:  # noqa: BLE001 - one bad window must not abort the rest
                print(f"  {prof['name']}: {exc}", file=sys.stderr)
            opened += 1
        print(f"Opened {opened} interactive windows. Close them all (or kill this process) to finish.", flush=True)
        while browser.contexts:  # exits once the user closes every window
            time.sleep(poll)
    return opened


def main(argv=None):
    from audit_responsive import parse_route_specs
    from device_profiles import default_profiles, profile_by_name

    p = argparse.ArgumentParser(description="Open one interactive browser window per device viewport.")
    p.add_argument("url")
    p.add_argument("--route", action="append", default=None, metavar="GLOB=LOCALPATH",
                   help="overlay a local file onto matching requests (repeatable); same as audit_responsive.py")
    p.add_argument("--profiles", nargs="*", default=None, help="subset of profile display names; default = full matrix")
    p.add_argument("--no-landscape", action="store_true", help="portrait/native orientations only")
    p.add_argument("--storage-state", default=None, help="Playwright storageState JSON for user-gated pages")
    p.add_argument("--delay", type=float, default=1.0,
                   help="seconds to pause between opening windows (stagger so they load correctly and don't flood the server); default 1.0")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    if args.profiles:
        profiles = [pr for pr in (profile_by_name(n) for n in args.profiles) if pr]
        if not profiles:
            print("No matching profiles; run without --profiles for the full matrix.", file=sys.stderr)
            return 2
    else:
        profiles = default_profiles(include_landscape=not args.no_landscape)

    try:
        rules = parse_route_specs(args.route)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        open_windows(args.url, profiles, route_rules=rules,
                     storage_state_path=Path(args.storage_state) if args.storage_state else None,
                     delay=args.delay)
    except Exception as exc:  # noqa: BLE001
        if "Executable doesn't exist" in str(exc) or "playwright install" in str(exc):
            print("Chromium not installed. Run: uv run --with playwright playwright install chromium", file=sys.stderr)
            return 3
        print(f"Could not open windows: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
