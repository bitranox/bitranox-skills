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

It blocks while the windows are open and exits when you have closed them all, when the browser
is quit, or on Ctrl-C. Exit 0 when at least one window loaded, 1 when none did (or the browser
failed), 2 for bad arguments, 3 when Chromium cannot start.
Import-safe: the browser only opens under ``__main__``.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def _open_one(browser, prof, url, *, route_rules, storage_state):
    """Open one profile's window; return ``(page, loaded)``. A failed load is reported, not raised."""
    from audit_responsive import _apply_routes

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
        return page, False
    return page, True


def wait_until_closed(pages):
    """Block until every window is closed by hand, or the browser is gone.

    It waits on each page's own "close" event, which pumps Playwright's event loop. Polling
    ``browser.contexts`` with a sleep could never end: closing a window closes its page, not
    its context, and a sleeping sync client receives no events at all.
    """
    for page in pages:
        if page.is_closed():
            continue
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:  # noqa: BLE001 - the browser was quit or crashed: its windows are gone
            continue


def open_windows(url, profiles, *, route_rules=(), storage_state_path=None, delay=1.0, launch=None):
    """Open one headed window per profile; block until every window is closed.

    Returns ``(loaded, failed)``. When no window loaded there is nothing to operate, so it
    returns at once instead of waiting.

    Windows are opened one at a time with a ``delay`` pause between them. Opening many headed
    windows simultaneously hammers a single-worker backend (transient 5xx/404s under load) and
    the windows can paint incompletely; staggering lets each load and settle before the next.
    """
    from audit_responsive import launch_chromium

    launch = launch or (lambda: launch_chromium(headless=False))
    storage_state = str(storage_state_path) if storage_state_path else None
    with launch() as browser:
        pages, loaded = [], 0
        for i, prof in enumerate(profiles):
            if i and delay:
                time.sleep(delay)  # stagger so each window loads correctly and the server isn't flooded
            page, ok = _open_one(browser, prof, url, route_rules=route_rules, storage_state=storage_state)
            pages.append(page)
            loaded += ok
        failed = len(pages) - loaded
        suffix = f" ({failed} failed to load)" if failed else ""
        print(f"Opened {loaded} interactive windows{suffix}.", flush=True)
        if loaded:
            print("Close them all (or quit the browser, or Ctrl-C) to finish.", flush=True)
            wait_until_closed(pages)
    return loaded, failed


def parse_args(argv):
    p = argparse.ArgumentParser(description="Open one interactive browser window per device viewport.")
    p.add_argument("url")
    p.add_argument("--route", action="append", default=None, metavar="GLOB=LOCALPATH",
                   help="overlay a local file onto matching requests (repeatable); same as audit_responsive.py")
    p.add_argument("--profiles", nargs="*", default=None, help="subset of profile display names; default = full matrix")
    p.add_argument("--no-landscape", action="store_true", help="portrait/native orientations only")
    p.add_argument("--storage-state", default=None, help="Playwright storageState JSON for user-gated pages")
    p.add_argument("--delay", type=float, default=1.0,
                   help="seconds to pause between opening windows (stagger so they load correctly and don't flood the server); default 1.0")
    return p.parse_args(argv)


def main(argv=None, *, launch=None):
    """CLI entry. ``launch`` replaces the real Chromium launch (tests inject a scripted browser)."""
    from audit_responsive import launch_failure, make_console_safe, parse_route_specs, select_profiles

    make_console_safe()
    args = parse_args(argv if argv is not None else sys.argv[1:])
    profiles = select_profiles(args.profiles, include_landscape=not args.no_landscape)
    if profiles is None:
        return 2

    try:
        rules = parse_route_specs(args.route)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        loaded, _failed = open_windows(
            args.url, profiles, route_rules=rules,
            storage_state_path=Path(args.storage_state) if args.storage_state else None,
            delay=args.delay, launch=launch,
        )
    except Exception as exc:  # noqa: BLE001
        failure = launch_failure(exc)
        if failure:
            print(failure[1], file=sys.stderr)
            return failure[0]
        print(f"Could not open windows: {exc}", file=sys.stderr)
        return 1
    return 0 if loaded else 1


if __name__ == "__main__":
    sys.exit(main())
