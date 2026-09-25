"""A scripted stand-in for the Playwright browser, injected at the scripts' ``launch`` seam.

Only the calls the three scripts make are implemented. ``Script`` decides what each page
answers: the raw detector measurements, the axe result (or an exception to raise), the
i18n result (or an exception), a navigation error, and whether the page is already closed.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

CLEAN_RAW = {
    "scroll_width": 375, "client_width": 375, "content_height": 600, "viewport_height": 667,
    "overflow_offenders": [], "targets": [],
}


@dataclass
class Script:
    raw: dict = field(default_factory=lambda: dict(CLEAN_RAW))
    axe: object = field(default_factory=list)  # list of violations, or an Exception to raise
    axe_tag_error: Exception | None = None  # raised by add_script_tag (a 404 / CSP block)
    i18n: object = False  # bool, or an Exception to raise
    goto_error: Exception | None = None
    storage_state: dict = field(default_factory=lambda: {"cookies": [{"name": "sid", "value": "SECRET"}]})


class FakeRoute:
    def __init__(self, url: str):
        self.url = url
        self.served: bytes | None = None
        self.continued = False

    def fulfill(self, *, path: str, content_type: str) -> None:
        self.served = Path(path).read_bytes()  # raises like Playwright when the file is gone
        self.content_type = content_type

    def continue_(self) -> None:
        self.continued = True


class FakePage:
    def __init__(self, script: Script, pages_log: list):
        self.script = script
        self.routes: list = []
        self.closed = False
        self.close_waits = 0
        pages_log.append(self)

    def route(self, glob, handler) -> None:
        self.routes.append((glob, handler))

    def goto(self, url, **_kw) -> None:
        self.url = url
        if self.script.goto_error:
            raise self.script.goto_error

    def evaluate(self, source, arg=None):
        if "axe.run" in source:
            return _answer(self.script.axe)
        if "createTreeWalker" in source:
            return _answer(self.script.i18n)
        if "document.title" in source:
            self.title = arg
            return None
        return dict(self.script.raw)  # detectors.js

    def screenshot(self, *, path, **_kw) -> None:
        Path(path).write_bytes(b"\x89PNG fake")

    def add_script_tag(self, *, url) -> None:
        if self.script.axe_tag_error:
            raise self.script.axe_tag_error

    def is_closed(self) -> bool:
        return self.closed

    def wait_for_event(self, event, timeout=None):
        # The human closing the window: the wait returns once, and the page is closed after.
        assert event == "close"
        self.close_waits += 1
        self.closed = True


def _answer(value):
    if isinstance(value, Exception):
        raise value
    return value


class FakeContext:
    def __init__(self, browser: FakeBrowser, options: dict):
        self.browser = browser
        self.options = options
        self.closed = False

    def new_page(self) -> FakePage:
        return FakePage(self.browser.script, self.browser.pages)

    def storage_state(self, path=None):
        state = dict(self.browser.script.storage_state)
        if path is not None:  # like Playwright: a plain write, mode left to the umask
            Path(path).write_text(json.dumps(state), encoding="utf-8")
        return state

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self, script: Script):
        self.script = script
        self.contexts_made: list[FakeContext] = []
        self.pages: list[FakePage] = []
        self.closed = False
        self.contexts_polls = 0

    @property
    def contexts(self):
        # A human cannot close a context, so a wait loop polling this never ends. Fail the test
        # loudly instead of hanging it.
        self.contexts_polls += 1
        if self.contexts_polls > 2:
            raise AssertionError("wait loop polls browser.contexts, which a closed window never empties")
        return [c for c in self.contexts_made if not c.closed]

    def new_context(self, **options) -> FakeContext:
        ctx = FakeContext(self, options)
        self.contexts_made.append(ctx)
        return ctx

    def close(self) -> None:
        self.closed = True


def fake_launcher(script: Script | None = None, *, error: Exception | None = None):
    """A ``launch`` seam value: a zero-arg callable returning a context manager of a browser."""
    browser = FakeBrowser(script or Script())

    @contextmanager
    def launch():
        if error is not None:
            raise error
        yield browser

    launch.browser = browser
    return launch


# The texts Playwright itself raises, trimmed to the parts the scripts key on.
MISSING_EXECUTABLE = (
    "BrowserType.launch: Executable doesn't exist at /root/.cache/ms-playwright/chromium-1243/chrome\n"
    "Looks like Playwright was just installed or updated. Please run the following command to "
    "download new browsers:\n    playwright install"
)
MISSING_HOST_DEPS = (
    "BrowserType.launch: \nHost system is missing dependencies to run browsers.\n"
    "Please install them with the following command:\n\n    sudo playwright install-deps\n\n"
    "Alternatively, use apt:\n    sudo apt-get install libnss3"
)
