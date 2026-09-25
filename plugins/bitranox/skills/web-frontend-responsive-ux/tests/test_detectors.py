"""detectors.js run under node against a minimal stub DOM, then judged by analysis.py.

The stub supplies only what detectors.js reads (rects, sizes, computed style), so the test pins
the MEASUREMENT contract without a browser. Skipped only where node is not installed.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import analysis
import device_profiles

DETECTORS = Path(__file__).resolve().parent.parent / "detectors.js"
NODE = shutil.which("node")

# A stub DOM laid out in a viewport of vw x vh. `blocks` are the body's children at full width,
# each [top, height] or [top, height, overflowY, [children...]], and ["#text", top, height] is a
# text node. documentElement.scrollHeight is clamped to the viewport from below, exactly as a
# browser reports it. A child's box may reach past a parent that clips it; the stub keeps that
# box, as a browser's getBoundingClientRect does, so only the detector can decide to ignore it.
STUB = r"""
const [vw, vh, blocks] = JSON.parse(process.argv[2]);
const rect = (top, h, w) => ({top, bottom: top + h, left: 0, right: w, width: w, height: h});
const elements = [];
const mk = (name, r, overflowY) => ({
  nodeType: 1, nodeName: name, id: "", classList: [], parentElement: null, childNodes: [],
  style: {visibility: "visible", display: "block", overflowY},
  getBoundingClientRect: () => r,
  querySelectorAll: (sel) => (sel === "*" ? elements : []),
});
const build = (spec) => {
  if (spec[0] === "#text") {
    return {nodeType: 3, textContent: "words", childNodes: [], box: rect(spec[1], spec[2], vw)};
  }
  const [t, h, overflowY = "visible", kids = []] = spec;
  const el = mk("DIV", rect(t, h, vw), overflowY);
  elements.push(el);
  el.childNodes = kids.map(build);
  return el;
};
const topLevel = blocks.map(build);
const flowBottom = blocks.reduce((m, s) => Math.max(m, s[0] === "#text" ? s[1] + s[2] : s[0] + s[1]), 0);
const body = mk("BODY", rect(0, flowBottom, vw), "visible");
body.childNodes = topLevel;
const html = mk("HTML", rect(0, flowBottom, vw), "visible");
html.clientWidth = vw;
html.scrollWidth = vw;
html.scrollHeight = Math.max(vh, flowBottom);
globalThis.window = {innerHeight: vh, scrollY: 0};
globalThis.document = {
  documentElement: html, body,
  querySelectorAll: (sel) => (sel === "*" ? [html, body, ...elements] : []),
  // A browser Range over an element spans every box inside it, clipped or not.
  createRange: () => {
    let node = null;
    const boxes = (n) => (n.nodeType === 3 ? [n.box]
      : n.childNodes.flatMap((c) => (c.nodeType === 3 ? [c.box] : [c.getBoundingClientRect(), ...boxes(c)])));
    return {
      selectNodeContents(n) { node = n; },
      getBoundingClientRect: () => {
        const all = boxes(node);
        const bottom = all.reduce((m, b) => Math.max(m, b.bottom), 0);
        return rect(0, bottom, vw);
      },
    };
  },
};
globalThis.getComputedStyle = (el) => el.style;
// eval of the skill's OWN detectors.js is the point: it mirrors page.evaluate(source).
const src = require("fs").readFileSync(process.argv[3], "utf8");
process.stdout.write(JSON.stringify(eval(src)));
"""


def run_detectors(tmp_path, vw, vh, blocks):
    harness = tmp_path / "harness.js"
    harness.write_text(STUB, encoding="utf-8")
    proc = subprocess.run([NODE, str(harness), json.dumps([vw, vh, blocks]), str(DETECTORS)],
                          capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def test_short_page_reports_its_real_content_height(tmp_path):
    raw = run_detectors(tmp_path, 1440, 900, [[0, 100]])
    assert raw["content_height"] == 100
    assert raw["viewport_height"] == 900


def test_short_page_on_desktop_gets_the_sparse_finding(tmp_path):
    raw = run_detectors(tmp_path, 1440, 900, [[0, 100]])
    report = analysis.build_device_report(device_profiles.profile_by_name("Laptop 1440"), raw)
    assert [(f["check"], f["severity"]) for f in report["findings"]] == [("vertical-fit", "MINOR")]


def test_tall_page_reports_its_full_height(tmp_path):
    raw = run_detectors(tmp_path, 375, 667, [[0, 400], [400, 1600]])
    assert raw["content_height"] == 2000
    report = analysis.build_device_report(device_profiles.profile_by_name("iPhone SE (portrait)"), raw)
    assert ("vertical-fit", "MEDIUM") in [(f["check"], f["severity"]) for f in report["findings"]]


def _vertical_fit(raw, profile="iPhone SE (portrait)"):
    report = analysis.build_device_report(device_profiles.profile_by_name(profile), raw)
    return [f["severity"] for f in report["findings"] if f["check"] == "vertical-fit"]


@pytest.mark.parametrize("overflow_y", ["auto", "scroll", "hidden", "clip"])
def test_content_a_container_scrolls_or_clips_is_not_page_height(tmp_path, overflow_y):
    """An app shell: the page itself never scrolls, a pane scrolls inside it. What that pane holds
    is reached by scrolling the PANE, so it is not avoidable page scrolling on a phone."""
    raw = run_detectors(tmp_path, 375, 667, [[0, 587, overflow_y, [[0, 3000]]], [587, 80]])
    assert raw["content_height"] == 667
    assert _vertical_fit(raw) == []


def test_text_inside_a_scroll_container_is_not_page_height(tmp_path):
    raw = run_detectors(tmp_path, 375, 667, [[0, 300, "auto", [["#text", 0, 4000]]]])
    assert raw["content_height"] == 300


def test_control_content_overflowing_a_visible_container_does_extend_the_page(tmp_path):
    raw = run_detectors(tmp_path, 375, 667, [[0, 200, "visible", [[0, 5000]]]])
    assert raw["content_height"] == 5000
    assert _vertical_fit(raw) == ["MEDIUM"]


def test_control_nested_visible_containers_are_walked_all_the_way_down(tmp_path):
    raw = run_detectors(tmp_path, 375, 667, [[0, 100, "visible", [[0, 100, "visible", [[0, 2500]]]]]])
    assert raw["content_height"] == 2500


def test_text_directly_in_the_page_still_counts(tmp_path):
    raw = run_detectors(tmp_path, 1440, 900, [["#text", 0, 1200]])
    assert raw["content_height"] == 1200
