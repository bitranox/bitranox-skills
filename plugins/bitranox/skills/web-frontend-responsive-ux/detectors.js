// In-page measurement collector for the responsive/usability audit.
//
// Runs inside the page (Playwright page.evaluate or an MCP evaluate_script call) and
// returns a plain JSON object of RAW measurements - it makes no judgements. The pure
// thresholds live in analysis.py, so the same numbers produce the same findings whether a
// headless Playwright run or an interactive MCP session collected them.
//
// Returns: { scroll_width, client_width, content_height, viewport_height,
//            overflow_offenders[], targets[] }
// Touch-target spacing is computed here (min gap to any other interactive box) because it
// needs the full set of client rects, which only exist in the page.
//
// The file is ONE bare function expression, never invoked here and with no trailing
// semicolon, because that is the only shape every caller accepts: Playwright's
// page.evaluate(source) calls a string that evaluates to a function, chrome-devtools-mcp
// evaluate_script wraps it as `(${source})` and calls the result, and @playwright/mcp
// browser_evaluate does the same. An IIFE with a `;` is a SyntaxError inside those parens.

() => {
  const doc = document.documentElement;
  const vw = doc.clientWidth;
  const vh = window.innerHeight;

  // --- horizontal overflow: elements that make the DOCUMENT scroll sideways -------------
  // Only one side of the viewport scrolls: the end side of the page's direction (right for
  // LTR, left for RTL). Past the other edge a box is simply unreachable - a skip link parked
  // at left:-9999px in an LTR page adds no scrollbar - so it is not an offender. Browsers take
  // that direction from <body> when there is one (the CSS principal writing mode), which is
  // why a dir="rtl" on <body> alone flips it while <html> still computes ltr.
  const rtl = getComputedStyle(document.body || doc).direction === "rtl";
  const scrollX = window.scrollX || 0;
  const candidates = [];
  for (const el of document.querySelectorAll("*")) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    const overflow = rtl ? -(r.left + scrollX) : r.right + scrollX - vw;
    if (overflow <= 1) continue;
    // A box an ancestor clips or scrolls sideways (a carousel rail) never widens the page.
    if (clippedByAncestor(el)) continue;
    // querySelectorAll is document order, so an ancestor is seen before its descendants:
    // the table's rows and cells would otherwise take the slots that should name more culprits.
    if (candidates.some((c) => c.el.contains(el))) continue;
    candidates.push({ el, r, overflow });
  }
  // Worst first, so truncating to 25 (and analysis.py to 10) drops the least harmful.
  candidates.sort((a, b) => b.overflow - a.overflow);
  const offenders = candidates.slice(0, 25).map(({ el, r }) => ({
    selector: cssPath(el),
    left: Math.round(r.left),
    right: Math.round(r.right),
    width: Math.round(r.width),
  }));

  // --- interactive targets: size + spacing --------------------------------------------
  const interactiveSel =
    'a[href], button, input:not([type="hidden"]), select, textarea, ' +
    '[role="button"], [role="link"], [role="tab"], [onclick], [tabindex]:not([tabindex="-1"])';
  const nodes = Array.from(document.querySelectorAll(interactiveSel)).filter(isVisible);
  const rects = nodes.map((n) => n.getBoundingClientRect());
  const targets = nodes.map((n, i) => {
    const r = rects[i];
    return {
      selector: cssPath(n),
      width: Math.round(r.width),
      height: Math.round(r.height),
      min_gap: Math.round(minGap(r, rects, i)),
    };
  });

  return {
    scroll_width: doc.scrollWidth,
    client_width: vw,
    content_height: contentExtent(),
    viewport_height: vh,
    overflow_offenders: offenders,
    targets: targets,
  };

  // How far the page's CONTENT reaches, in document px. documentElement.scrollHeight is
  // clamped to the viewport from below (a 100px page reports 900 in a 900px window), so it
  // can never show an under-filled large screen. Take the bottom of every element and text
  // node the PAGE scrolls to (absolutely positioned ones too), walking down from the body.
  //
  // The walk stops at an element that scrolls or clips vertically (overflow-y other than
  // visible): its own box counts, what it holds does not. getBoundingClientRect reports a
  // child's full box however far it reaches past such a container, so counting it made an app
  // shell - a 100dvh grid whose pane scrolls inside itself - measure as thousands of px of
  // page on a phone that never scrolls. A Range over the whole body spans those clipped boxes
  // too, which is why text is measured one node at a time.
  function contentExtent() {
    const body = document.body;
    if (!body) return doc.scrollHeight;
    const range = document.createRange ? document.createRange() : null;
    let bottom = 0;
    const pending = Array.from(body.childNodes);
    while (pending.length) {
      const node = pending.pop();
      const r = boxOf(node, range);
      if (r && (r.width !== 0 || r.height !== 0)) bottom = Math.max(bottom, r.bottom + window.scrollY);
      if (node.nodeType !== 1 || getComputedStyle(node).overflowY !== "visible") continue;
      for (const child of node.childNodes) pending.push(child);
    }
    return Math.round(bottom);
  }

  function boxOf(node, range) {
    if (node.nodeType === 1) return node.getBoundingClientRect();
    if (node.nodeType !== 3 || !range || !node.textContent.trim()) return null;
    range.selectNodeContents(node);
    return range.getBoundingClientRect();
  }

  function isVisible(el) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    const s = getComputedStyle(el);
    return s.visibility !== "hidden" && s.display !== "none";
  }

  // Smallest edge-to-edge gap from rect `i` to any other interactive rect; 9999 when it
  // has no neighbour (a large number, so analysis.py treats it as "not cramped").
  //
  // Boxes that OVERLAP are skipped: a control floated over a swipe surface, or a button
  // nested in a link, intersects it by design and has no gap to measure. Overlap means an
  // intersection with area, more than 1px on both axes, which also covers one box containing
  // the other. Boxes that merely share an edge (or overlap by a sub-pixel rounding sliver)
  // do NOT overlap: they are the most cramped pair of all and report a gap of 0.
  function minGap(r, list, i) {
    let best = Infinity;
    for (let j = 0; j < list.length; j++) {
      if (j === i) continue;
      const o = list[j];
      const ix = Math.min(r.right, o.right) - Math.max(r.left, o.left);
      const iy = Math.min(r.bottom, o.bottom) - Math.max(r.top, o.top);
      if (ix > 1 && iy > 1) continue;
      const dx = Math.max(0, r.left - o.right, o.left - r.right);
      const dy = Math.max(0, r.top - o.bottom, o.top - r.bottom);
      best = Math.min(best, Math.hypot(dx, dy));
    }
    return best === Infinity ? 9999 : best;
  }

  // Whether `el` cannot widen the page: an ancestor that clips or scrolls sideways contains it,
  // or it is fixed to the viewport itself. Only ancestors on its containing-block chain count:
  // an absolutely positioned box escapes a clipping parent that is not positioned and does not
  // establish a containing block (see establishesContainingBlock), and a fixed one escapes every
  // ancestor but such a block. A fixed box whose containing block IS the viewport never moves
  // with the page, so it adds nothing to the document's scroll width (measured in Chrome 148).
  // <html> and <body> are not asked about clipping: their overflow applies to the viewport,
  // and whether THAT scrolls is what scroll_width already reports.
  function clippedByAncestor(el) {
    let position = getComputedStyle(el).position;
    for (let a = el.parentElement; a && a !== document.body && a !== doc; a = a.parentElement) {
      const s = getComputedStyle(a);
      const block = establishesContainingBlock(s);
      const contains =
        position === "fixed" ? block
        : position === "absolute" ? s.position !== "static" || block
        : true;
      if (!contains) continue;
      if (s.overflowX !== "visible") return true;
      position = s.position;
    }
    if (position !== "fixed") return false;
    const roots = [document.body, doc].filter(Boolean);
    return !roots.some((r) => establishesContainingBlock(getComputedStyle(r)));
  }

  // Whether an element is the containing block for its fixed and absolute descendants even when
  // it is not positioned. Measured in Chrome 148 against the page's own scroll width: transform,
  // translate, rotate, scale, perspective, filter, backdrop-filter, contain paint/layout/strict/
  // content, will-change naming one of those, and content-visibility:auto do; contain:size,
  // container-type and will-change:opacity do not.
  function establishesContainingBlock(s) {
    const props = ["transform", "translate", "rotate", "scale", "perspective", "filter", "backdropFilter"];
    if (props.some((p) => s[p] && s[p] !== "none")) return true;
    if (/\b(paint|layout|strict|content)\b/.test(s.contain || "")) return true;
    const willChange = /\b(transform|translate|rotate|scale|perspective|filter|backdrop-filter)\b/;
    if (willChange.test(s.willChange || "")) return true;
    return s.contentVisibility === "auto";
  }

  function cssPath(el) {
    if (el.id) return "#" + el.id;
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 4) {
      let part = node.nodeName.toLowerCase();
      if (node.classList && node.classList.length) {
        part += "." + Array.from(node.classList).slice(0, 2).join(".");
      }
      parts.unshift(part);
      node = node.parentElement;
    }
    return parts.join(" > ");
  }
}
