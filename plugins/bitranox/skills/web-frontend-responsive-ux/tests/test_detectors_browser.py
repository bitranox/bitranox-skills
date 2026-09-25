"""detectors.js in a REAL browser, for what a stub DOM cannot know: which computed overflow-y a
browser gives an element, and how far a clipped child's box reports. Skipped where Playwright or
a Chromium to drive is missing; run it with `uv run --with playwright python -m pytest ...`.
"""

import shutil
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

DETECTORS = Path(__file__).resolve().parent.parent / "detectors.js"
META = '<!doctype html><meta name=viewport content="width=device-width">'

PAGES = {
    # A 100dvh grid app shell: the pane scrolls inside itself and a thumbnail rail scrolls
    # sideways, so the document never scrolls at all.
    "app shell": (META + "<style>html,body{margin:0;height:100%}"
                  ".shell{display:grid;grid-template-rows:1fr 80px;height:100dvh}"
                  "main{overflow-y:auto}.rail{display:flex;overflow-x:auto;gap:8px}"
                  ".rail i{flex:0 0 72px;height:72px;background:#ccc}</style>"
                  "<div class=shell><main><div style='height:3000px'>list</div></main>"
                  "<div class=rail>" + "<i></i>" * 12 + "</div></div>", 667),
    "clipped": (META + "<body style='margin:0'><div style='height:200px;overflow:hidden'>"
                "<div style='height:5000px'>clipped</div></div>", 200),
    "long page": (META + "<body style='margin:0'><div style='height:3000px'>long</div>", 3000),
    "short page": (META + "<body style='margin:0'><div style='height:100px'>short</div>", 100),
}


@pytest.fixture(scope="module")
def page():
    with sync_api.sync_playwright() as p:
        browser = _launch(p.chromium)
        pg = browser.new_page(viewport={"width": 375, "height": 667})
        yield pg
        browser.close()


def _launch(chromium):
    try:
        return chromium.launch()
    except sync_api.Error:
        pass
    for name in ("google-chrome", "chromium", "chromium-browser"):
        exe = shutil.which(name)
        if exe:
            return chromium.launch(executable_path=exe, args=["--no-sandbox"])
    pytest.skip("no Chromium for Playwright to drive")


@pytest.mark.parametrize("name", list(PAGES))
def test_content_height_is_what_the_page_itself_scrolls_to(page, name):
    html, expected = PAGES[name]
    page.set_content(html)
    raw = page.evaluate(DETECTORS.read_text(encoding="utf-8"))
    assert raw["viewport_height"] == 667
    assert raw["content_height"] == expected
