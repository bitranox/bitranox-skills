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
    content_height: doc.scrollHeight,
    viewport_height: vh,
    overflow_offenders: offenders,
    targets: targets,
  };

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
