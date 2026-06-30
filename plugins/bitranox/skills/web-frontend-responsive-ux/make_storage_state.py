# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.44"]
# ///
"""Capture a Playwright storageState for auditing user-gated (login) pages.

Opens a headed browser at the login URL, you sign in by hand, then press Enter here to
save the session (cookies + localStorage) to a JSON file. Hand that file to
``audit_responsive.py --storage-state state.json`` so the audit runs as the logged-in user.

    uv run make_storage_state.py https://example.com/login --out state.json

No credentials are ever passed on the command line or stored by this tool - you type them
into the real login form, and only the resulting session token is saved. Treat the output
file as a secret (it is git-ignored by convention; never commit it).

Import-safe: logic lives in functions; the browser only opens under ``__main__``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def capture(login_url: str, out_path: Path, *, prompt=input) -> Path:
    """Open a headed browser, wait for manual login, then persist storageState."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(login_url)
        prompt("Log in in the opened browser, then press Enter here to save the session... ")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(out_path))
        browser.close()
    return out_path


def parse_args(argv):
    p = argparse.ArgumentParser(description="Save a Playwright storageState after manual login.")
    p.add_argument("login_url", help="URL of the login page")
    p.add_argument("--out", default="state.json", help="output storageState JSON path (keep secret, do not commit)")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        path = capture(args.login_url, Path(args.out))
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "Executable doesn't exist" in msg or "playwright install" in msg:
            print("Chromium not installed. Run: uv run --with playwright playwright install chromium", file=sys.stderr)
            return 3
        print(f"Could not capture session: {exc}", file=sys.stderr)
        return 1
    print(f"Saved session to {path} - pass it as --storage-state to audit_responsive.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
