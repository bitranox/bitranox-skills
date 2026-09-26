"""detectors.js in a REAL browser, for what a stub DOM cannot know: which computed overflow a
browser gives an element, how far a clipped child's box reports, which side of the page scrolls
in RTL, where real client rects of adjacent targets meet, and whether the file survives each MCP
caller's wrapping. Skipped where Playwright or a Chromium to drive is missing; run it with
`uv run --with playwright python -m pytest ...`.
"""

import shutil
from pathlib import Path

import pytest

import analysis

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


def _measure(page, html):
    page.set_content(html)
    return page.evaluate(DETECTORS.read_text(encoding="utf-8"))


# --- touch-target spacing ---------------------------------------------------------------------

_BUTTON_CSS = ("<style>button{width:44px;height:44px;padding:0;border:0;margin:0;"
               "position:absolute;top:10px}</style>")


def _button_pair(left_b):
    """Two 44x44 buttons, #a at x=10 and #b at x=left_b: the gap is left_b - 54."""
    return (META + "<body style='margin:0'>" + _BUTTON_CSS
            + f"<button id=a style='left:10px'>a</button><button id=b style='left:{left_b}px'>b</button>")


@pytest.mark.parametrize(("gap", "cramped"), [(0, True), (1, True), (7, True), (8, False)])
def test_spacing_between_side_by_side_targets_is_their_edge_to_edge_gap(page, gap, cramped):
    """The gap is monotonic down to zero: two targets that share an edge are the MOST cramped
    pair, not an overlap the spacing rule may skip."""
    raw = _measure(page, _button_pair(54 + gap))
    assert [(t["selector"], t["min_gap"]) for t in raw["targets"]] == [("#a", gap), ("#b", gap)]
    findings = analysis.touch_target_findings(raw["targets"])
    expected = [("#a", "MEDIUM"), ("#b", "MEDIUM")] if cramped else []
    assert [(f["selector"], f["severity"]) for f in findings] == expected
    if cramped:
        assert all(f"gap {gap}px < 8px" in f["detail"] for f in findings)


def test_targets_that_overlap_are_skipped_by_the_spacing_rule(page):
    """The documented escape hatch: controls floated OVER a surface intersect it."""
    raw = _measure(page, _button_pair(40))
    assert [t["min_gap"] for t in raw["targets"]] == [9999, 9999]
    assert analysis.touch_target_findings(raw["targets"]) == []


def test_a_target_nested_inside_another_is_skipped_by_the_spacing_rule(page):
    raw = _measure(page, META + "<body style='margin:0'><a id=outer href=# "
                   "style='display:block;width:200px;height:60px'>"
                   "<button id=inner style='width:44px;height:44px'>x</button></a>")
    assert [(t["selector"], t["min_gap"]) for t in raw["targets"]] == [("#outer", 9999), ("#inner", 9999)]
    assert analysis.touch_target_findings(raw["targets"]) == []


# --- horizontal-overflow offenders ------------------------------------------------------------

def _offenders(raw):
    return [o["selector"] for o in raw["overflow_offenders"]]


def test_the_real_offender_is_named_past_off_screen_and_carousel_noise(page):
    """A skip link parked at left:-9999px and 30 slides inside a sideways-scrolling rail add no
    document scroll, so neither may take an offender slot from the 900px table that does."""
    html = (META + "<body style='margin:0'>"
            "<a id=skip href=#main style='position:absolute;left:-9999px'>skip</a>"
            "<div id=rail style='display:flex;overflow-x:auto;width:100%'>"
            + "".join(f"<div class=slide style='flex:0 0 300px;height:50px'>s{i}</div>" for i in range(30))
            + "</div><main id=main><table id=wide-table style='width:900px'><tr><td>x</td></tr></table></main>")
    raw = _measure(page, html)
    assert raw["scroll_width"] == 900
    assert _offenders(raw) == ["#wide-table"]
    finding = analysis.overflow_finding(raw["scroll_width"], raw["client_width"], "phone",
                                        offenders=raw["overflow_offenders"])
    assert [o["selector"] for o in finding["offenders"]] == ["#wide-table"]


def test_offenders_are_ranked_by_how_far_they_overflow(page):
    raw = _measure(page, META + "<body style='margin:0'>"
                   "<div id=small style='width:400px;height:10px'></div>"
                   "<div id=big style='width:1200px;height:10px'></div>")
    assert _offenders(raw) == ["#big", "#small"]


@pytest.mark.parametrize("wrapper", ["overflow-x:hidden", "overflow-x:clip", "overflow-x:auto",
                                     "overflow-y:auto"])
def test_content_clipped_or_scrolled_by_an_ancestor_is_not_an_offender(page, wrapper):
    raw = _measure(page, META + f"<body style='margin:0'><div style='{wrapper}'>"
                   "<div id=inner style='width:900px;height:20px'>x</div></div>")
    assert raw["scroll_width"] == 375
    assert _offenders(raw) == []


def test_control_an_absolute_box_escaping_a_static_clipping_parent_is_still_an_offender(page):
    """overflow clips only what the box CONTAINS: an absolutely positioned child whose containing
    block lies above the clipping parent escapes it and does widen the page."""
    raw = _measure(page, META + "<body style='margin:0'><div style='overflow:hidden;height:20px'>"
                   "<div id=esc style='position:absolute;left:300px;width:300px;height:20px'>x</div>"
                   "</div>")
    assert raw["scroll_width"] == 600
    assert _offenders(raw) == ["#esc"]


def test_ltr_an_element_past_the_left_edge_does_not_scroll_and_is_not_an_offender(page):
    raw = _measure(page, META + "<body style='margin:0'><div id=x "
                   "style='position:relative;left:-500px;width:300px;height:20px'>x</div>")
    assert raw["scroll_width"] == 375
    assert _offenders(raw) == []


# Chrome takes the page's scroll direction from <body> when it has one (the CSS principal
# writing mode), so a dir on <body> alone flips it while <html> still computes ltr.
_RTL = {"html dir=rtl": "<html dir=rtl><body style='margin:0'>",
        "body dir=rtl": "<body dir=rtl style='margin:0'>"}


@pytest.mark.parametrize("where", list(_RTL))
def test_rtl_an_element_past_the_left_edge_scrolls_and_is_the_offender(page, where):
    raw = _measure(page, META + _RTL[where] + "<div id=x style='width:875px;height:20px'>x</div>")
    assert raw["scroll_width"] == 875
    assert _offenders(raw) == ["#x"]


@pytest.mark.parametrize("where", list(_RTL))
def test_rtl_an_element_past_the_right_edge_does_not_scroll_and_is_not_an_offender(page, where):
    raw = _measure(page, META + _RTL[where]
                   + "<div id=x style='position:absolute;left:300px;width:300px;height:20px'>x</div>")
    assert raw["scroll_width"] == 375
    assert _offenders(raw) == []


# --- file shape: every documented caller can evaluate it --------------------------------------

# chrome-devtools-mcp evaluate_script: evaluateHandle(`(${fnString})`), then `await fn(...args)`.
# @playwright/mcp browser_evaluate: eval(`(${expr})`), then calls it when it is a function.
_WRAPPERS = {
    "chrome-devtools-mcp evaluate_script":
        "async (src) => { const fn = (0, eval)('(' + src + ')'); return await fn(); }",
    "@playwright/mcp browser_evaluate":
        "async (src) => { const v = (0, eval)('(' + src + ')');"
        " return await (typeof v === 'function' ? v() : v); }",
}


@pytest.mark.parametrize("caller", list(_WRAPPERS))
def test_the_file_evaluates_under_each_mcp_wrapper(page, caller):
    page.set_content(PAGES["short page"][0])
    raw = page.evaluate(_WRAPPERS[caller], DETECTORS.read_text(encoding="utf-8"))
    assert set(raw) == {"scroll_width", "client_width", "content_height", "viewport_height",
                        "overflow_offenders", "targets"}
    assert raw["content_height"] == 100
