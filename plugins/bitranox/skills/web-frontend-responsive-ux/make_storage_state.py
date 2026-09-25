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
import json
import os
import sys
from pathlib import Path


def write_secret_json(path: Path, data: dict) -> None:
    """Write ``data`` as JSON readable by the owner only (0600), whatever the umask.

    The file holds live session tokens. The mode is set on the open descriptor BEFORE any byte
    is written, and also when the file already existed (O_CREAT keeps an old file's mode)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        if hasattr(os, "fchmod"):
            os.fchmod(fh.fileno(), 0o600)
        json.dump(data, fh, indent=2)


def capture(login_url: str, out_path: Path, *, prompt=None, launch=None) -> Path:
    """Open a headed browser, wait for manual login, then persist storageState.

    ``prompt`` defaults to ``input`` (resolved at call time); ``launch`` replaces the real
    Chromium launch (tests inject a scripted browser)."""
    from audit_responsive import launch_chromium

    prompt = prompt or input
    launch = launch or (lambda: launch_chromium(headless=False))
    with launch() as browser:
        context = browser.new_context()
        page = context.new_page()
        page.goto(login_url)
        prompt("Log in in the opened browser, then press Enter here to save the session... ")
        state = context.storage_state()
    write_secret_json(out_path, state)
    return out_path


def parse_args(argv):
    p = argparse.ArgumentParser(description="Save a Playwright storageState after manual login.")
    p.add_argument("login_url", help="URL of the login page")
    p.add_argument("--out", default="state.json", help="output storageState JSON path (keep secret, do not commit)")
    return p.parse_args(argv)


def main(argv=None, *, launch=None):
    """CLI entry: 0 saved, 1 capture failed, 3 Chromium cannot start."""
    from audit_responsive import launch_failure, make_console_safe

    make_console_safe()
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        path = capture(args.login_url, Path(args.out), launch=launch)
    except Exception as exc:  # noqa: BLE001
        failure = launch_failure(exc)
        if failure:
            print(failure[1], file=sys.stderr)
            return failure[0]
        print(f"Could not capture session: {exc}", file=sys.stderr)
        return 1
    print(f"Saved session to {path} - pass it as --storage-state to audit_responsive.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
