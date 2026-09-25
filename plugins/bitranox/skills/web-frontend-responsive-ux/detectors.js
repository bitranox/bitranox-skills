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

(() => {
  const doc = document.documentElement;
  const vw = doc.clientWidth;
  const vh = window.innerHeight;

  // --- horizontal overflow: elements whose right edge passes the viewport -------------
  const offenders = [];
  const all = document.querySelectorAll("*");
  for (const el of all) {
    const r = el.getBoundingClientRect();
    // ignore zero-size and intentionally off-screen-left elements
    if (r.width === 0 && r.height === 0) continue;
    if (r.right > vw + 1 || r.left < -1) {
      offenders.push({
        selector: cssPath(el),
        right: Math.round(r.right),
        width: Math.round(r.width),
      });
      if (offenders.length >= 25) break;
    }
  }

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

  // Smallest centre-to-edge gap from rect `i` to any other interactive rect; Infinity
  // when isolated (reported as a large number so analysis.py treats it as "not cramped").
  function minGap(r, list, i) {
    let best = Infinity;
    for (let j = 0; j < list.length; j++) {
      if (j === i) continue;
      const o = list[j];
      const dx = Math.max(0, Math.max(r.left - o.right, o.left - r.right));
      const dy = Math.max(0, Math.max(r.top - o.bottom, o.top - r.bottom));
      if (dx === 0 && dy === 0) continue; // overlapping / nested - not a spacing gap
      best = Math.min(best, Math.hypot(dx, dy));
    }
    return best === Infinity ? 9999 : best;
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
})();
