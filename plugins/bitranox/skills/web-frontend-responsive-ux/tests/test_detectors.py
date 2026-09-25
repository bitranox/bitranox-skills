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

# A stub DOM: `blocks` are the body's element children as [top, height] at full width, laid
# out in a viewport of vw x vh. documentElement.scrollHeight is clamped to the viewport from
# below, exactly as a browser reports it.
STUB = r"""
const [vw, vh, blocks] = JSON.parse(process.argv[2]);
const rect = (top, h, w) => ({top, bottom: top + h, left: 0, right: w, width: w, height: h});
const contentBottom = blocks.reduce((m, [t, h]) => Math.max(m, t + h), 0);
const mk = (name, r, kids) => ({
  nodeType: 1, nodeName: name, id: "", classList: [], parentElement: null,
  getBoundingClientRect: () => r,
  querySelectorAll: (sel) => (sel === "*" ? kids : []),
});
const children = blocks.map(([t, h]) => mk("DIV", rect(t, h, vw), []));
const body = mk("BODY", rect(0, contentBottom, vw), children);
const html = mk("HTML", rect(0, contentBottom, vw), [body, ...children]);
html.clientWidth = vw;
html.scrollWidth = vw;
html.scrollHeight = Math.max(vh, contentBottom);
globalThis.window = {innerHeight: vh, scrollY: 0};
globalThis.document = {
  documentElement: html, body,
  querySelectorAll: (sel) => (sel === "*" ? [html, body, ...children] : []),
  createRange: () => ({selectNodeContents() {}, getBoundingClientRect: () => rect(0, contentBottom, vw)}),
};
globalThis.getComputedStyle = () => ({visibility: "visible", display: "block"});
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
