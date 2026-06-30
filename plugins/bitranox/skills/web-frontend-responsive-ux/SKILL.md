---
name: web-frontend-responsive-ux
description: "Use when a web page must work across mobile/tablet/desktop and the layout or usability is off - horizontal scrollbar on mobile, content not fitting vertically on phone portrait/landscape, cramped or tiny tap targets, swipe/carousel galleries, viewport/breakpoint issues, notch/safe-area overlap, sparse layouts on big screens, or RTL/long-translation layout breakage. Audits and fixes these, verified in a real browser via Playwright or a browser MCP across a device matrix. NOT for performance/SEO scoring (use a pagespeed/Lighthouse skill) or full localization infra."
---

# Responsive & Mobile Usability Audit

## Overview

Audit a page across a **device matrix** (phones/tablets/desktop x portrait/landscape) in a
**real browser**, **measure** the layout/usability defects (never eyeball a single desktop
window), fix them, and **re-verify** until clean. Evidence before claims: a fix is not done
until a re-run shows the dimension green on every profile (cross-ref
`bitranox:process-review-verification-before-completion`).

The skill owns these dimensions and nothing else:

1. **No horizontal overflow** on any device (the "no horizontal scrollbar on mobile/tablet" rule).
2. **Vertical fit** - primary content fits without scrolling on phone portrait AND landscape;
   large screens are not left sparse.
3. **Touch targets** >= 44px with >= 8px spacing (WCAG 2.5.8 floor is 24px).
4. **Swipe & gestures** - swipeable images that ALWAYS keep a button + keyboard alternative
   (WCAG 2.5.1) and honour `prefers-reduced-motion`.
5. **Viewport & notch** - correct viewport meta; safe-area insets when `viewport-fit=cover`.
6. **Responsive images & layout-perf** - `srcset`/`sizes`, reserved space (no image/font CLS).
7. **a11y baseline** - an `axe-core` pass per profile.
8. **i18n layout robustness** - layout survives long/expanded text and `dir="rtl"` (layout only).

Read the reference files (below) for the concrete patterns and thresholds before proposing fixes.

## Reference files

Use the Read tool to load the one(s) relevant to the finding you're fixing.

| Topic                                                                                                                                    | File                                 |
|------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|
| Layout: viewport meta, `svh`/`lvh`/`dvh`, vertical fit, overflow causes, `clamp()`, container queries, safe-area, responsive images/CLS  | `references/responsive-layout.md`    |
| Touch target sizes/spacing (WCAG 2.5.8), accessible swipe/carousel (WCAG 2.5.1), hover/focus on touch, i18n layout (text expansion, RTL) | `references/touch-and-gestures.md`   |
| The two verification backends, **installing the browser MCPs**, device matrix, `storageState` auth, axe injection, CLS scope             | `references/verification-engines.md` |

## Bundled scripts

| Script                  | Purpose                                                                                                                                                                                                  |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `audit_responsive.py`   | Headless Playwright runner: sweeps the device matrix, emits `report.json` + screenshots. Run with `uv run`. `--route GLOB=LOCALPATH` overlays local CSS/JS onto a live page (iterate without deploying). |
| `open_viewports.py`     | Opens one LIVE, interactive window per viewport (same `--route` overlay) so a human can operate every size at once.                                                                                      |
| `make_storage_state.py` | Log in once, save a Playwright `storageState` for auditing user-gated pages.                                                                                                                             |
| `device_profiles.py`    | The device matrix (importable data).                                                                                                                                                                     |
| `analysis.py`           | Pure thresholds/severity/report assembly (unit-tested, no browser).                                                                                                                                      |
| `detectors.js`          | In-page measurement, shared by both backends.                                                                                                                                                            |

## Workflow

```
1. Scope      -> target URL(s) + source files; auth (storageState) if user-gated
2. Choose engine -> browser MCP if connected; else bundled runner (offer MCP install)
3. Audit      -> sweep the device matrix; collect report.json + screenshots
4. Diagnose   -> map each finding to a reference pattern; sort SEVERE -> MEDIUM -> MINOR
5. Propose    -> show concrete diffs; APPLY ONLY AFTER the user confirms
6. Verify     -> re-run the audit; iterate until totals show 0 SEVERE / 0 MEDIUM
```

### 1. Scope & auth

Identify the URL(s) and the source files behind them (templates/CSS/JS). If pages are
user-gated, capture a session first (credentials go into the real login form, never on the
command line):

```bash
uv run make_storage_state.py https://example.com/login --out state.json   # keep secret; never commit
```

If the page is on a **remote server with remote data** (e.g. images from a media host), do
NOT deploy in-progress edits to test them. Audit the live URL but overlay your local CSS/JS
with `--route 'GLOB=LOCALPATH'` (server untouched, real data still loads), or capture
representative fixtures. For multilingual pages, audit each locale URL (incl. RTL). See
"Pages backed by remote data" and "i18n / multilingual pages" in
`references/verification-engines.md`.

### 2. Choose the verification engine

If a browser MCP is connected (`mcp__chrome-devtools__*` or `mcp__playwright__*`), use it for
interactive diagnosis. If neither is installed and the user wants interactive work, offer to
install one (see `references/verification-engines.md`). For repeatable/CI sweeps, use the
bundled runner - it needs only `uv`:

```bash
uv run --with playwright playwright install chromium   # one-time
```

### 3. Audit across the matrix

```bash
uv run audit_responsive.py http://localhost:8000/view/ABC123 --out ./audit-out --i18n
# add --storage-state state.json for gated pages
```

This sweeps phones/tablets/desktop in BOTH orientations and writes
`audit-out/report.json` + a screenshot per profile. **Never** conclude from one desktop
window - landscape phones and the smallest phone are where defects hide.

### 4. Diagnose

Read `report.json`. For each finding, open the matching reference file and pick the concrete
fix. Sort SEVERE -> MEDIUM -> MINOR. Confirm a flagged overflow/target against its screenshot.

### 5. Propose fixes (gated apply)

Present the fixes as concrete diffs (exact CSS/HTML/JS, real values), then **apply only after
the user confirms** - diagnose first, never auto-edit. Group related fixes so the diff is
reviewable.

### 6. Verify

Re-run the audit on the same matrix. The dimension is done only when the totals show
**0 SEVERE and 0 MEDIUM** across every profile (`passed: true`, exit 0). State the result with
the numbers; do not claim "responsive now" without the re-run.

## Preferred patterns (opinionated defaults)

When a fix has several valid shapes, default to these - they are the design decisions this skill
prescribes (proven in real galleries). Deviate only with a reason.

- **Swipe galleries = enhancement, never the only nav.** Add horizontal swipe with Pointer Events
  (threshold ~40px, horizontal-dominant), but ALWAYS keep visible prev/next buttons + ArrowLeft/Right
  keys (WCAG 2.5.1), honour `prefers-reduced-motion`, set `touch-action: pan-y` on the slider, and
  suppress the tap-to-zoom click that fires right after a swipe.
- **Phone landscape: thumbnail strip goes to a vertical rail on the LEFT.** A bottom film-strip wastes
  the scarce landscape height and squeezes/clips the hero image. Switch to a 2-column grid
  (`"hud hud" / "rail stage"`) under `(orientation: landscape) and (max-height: 600px)`; the rail
  scrolls vertically. (Portrait keeps the bottom strip, scrolling horizontally.) The strip must scroll
  when there are many items: horizontal in portrait/bottom, vertical in landscape/left.
- **Thumbnail/film-strip rails: scrollable AND mouse-drag-pannable.** They must scroll when items
  overflow (horizontal for a bottom strip, vertical for a side rail). Add click-and-drag panning with
  Pointer Events (mouse only - leave touch to native momentum scroll): on drag set
  `scrollLeft`/`scrollTop`, show `cursor: grab`/`grabbing`, and suppress the click ONLY after a real
  drag (capture-phase) so a plain click still selects the thumbnail. Do NOT `setPointerCapture` on
  pointerdown - it redirects the subsequent `click` to the rail and silently kills the thumbnail
  link's navigation; instead gate "dragging" on actual movement past a threshold and persist a
  `dragged` flag for the click-suppression.
- **Size the hero media to the actual cell, not a fixed `svh`.** A magic `max-height: 78svh` clips in
  landscape and leaves dead space. Make the image the grid item of a definite-height cell
  (`.frame-pic { display: contents }` + `img { max-height: 100%; max-width: 100% }`) so it fits both
  orientations.
- **Grow tap targets, don't shrink them on mobile.** Keep >=44px; enlarge the hit area with
  `min-block/inline-size` or padding while the icon stays small.
- **Float controls OVER a large interactive surface, don't sit them beside it.** A full-bleed
  interactive surface (a deep-zoom/OSD canvas, a map, an image-pan area) trips the touch-target
  spacing check against nearby controls (arrows, a thumbnail rail) whenever the gap is a few px - the
  detector flags `gap < 8px` between any two interactive boxes. A fixed inset only relocates the
  failing viewport (the gap shifts with the breakpoint). Fix by making the controls OVERLAP the
  surface (position them inside it / above it so the rects intersect) - the detector skips overlapping
  boxes - rather than parking them in a gutter a sliver away.
- **Iterate without deploying, and release ONCE.** Overlay your local CSS/JS onto the LIVE remote page
  with `audit_responsive.py --route GLOB=LOCALPATH`; use `open_viewports.py` to open one interactive
  window per viewport and operate each by hand; re-run the headless matrix to confirm 0 SEVERE/MEDIUM.
  Never edit the real server to test a layout change. Converge the WHOLE change on the overlay (every
  dimension green) BEFORE cutting a single production release - never release-then-hotfix. If perf
  matters, note that `--route` cannot drive Lighthouse (it audits a URL): run the app LOCALLY and
  Lighthouse THAT, or reason the metric from observable local behaviour (e.g. a heavy viewer/canvas
  that paints on load will own the LCP), rather than deploying first and measuring after.
- **Stagger when opening many windows.** Opening a dozen headed windows at once floods a
  single-worker backend (transient 5xx/404 under load) and the windows paint incompletely.
  `open_viewports.py` opens them one at a time with a `--delay` (default 1s) and waits for each to
  load; keep the stagger rather than firing them all simultaneously.
- **Match a reference page's ACTUAL tokens.** When a page should look like a sibling/landing page,
  extract that page's real `@font-face`/family stack and color variables and reuse them verbatim -
  don't invent new shades. A custom faint shade that isn't in the reference palette is usually the
  thing that looks "off" and fails contrast.
- **Center/position an overlay over variable content with JS, not a fixed CSS offset.** When an
  overlay (a caption, a "click to zoom" hint, a badge) must sit relative to content whose size
  changes with viewport/orientation/aspect (e.g. an `object-fit` image), a fixed `bottom`/`top` can't
  stay centered. Compute its position from the live rects on load, resize, and content change.
- **Use available vertical space on tall/portrait screens (don't just hide).** When a bar/region
  has vertical room (portrait phone), stack `label: value` pairs on two lines aligned at the colon
  (a 2-column grid, labels right-aligned in column 1) rather than hiding the labels or cramming one
  line; hide only where there is genuinely no room (short landscape). Mind the horizontal budget - a
  labelled row still competes with its siblings, so verify the value doesn't truncate
  (`scrollWidth > clientWidth`) and free width from the least-essential sibling (e.g. shrink a pill),
  not by ellipsing the value.
- **Hide a secondary element only when content genuinely doesn't fit (content-aware, JS-gated).**
  Don't unconditionally drop a logo/label on small screens - keep it when there's room. CSS can't
  measure text length, so measure in JS (does the value truncate / does the bar overflow?) and toggle
  a class that drops the least-essential element (e.g. the logo), with a wrap-to-second-line fallback
  for extreme content. Recompute on load, resize, orientationchange, and font load.
- **Test with worst-case content, not the happy sample.** A bar that fits the demo value (a short
  SKU) overflows or truncates with a real long one. Inject a long value and re-verify no overflow / no
  truncation - the audit's screenshots use whatever the page serves, so force the edge case yourself.
- **Use harmonious proportions for sizing/spacing.** Default to a consistent scale rather than ad-hoc
  px values: a logo at the golden-ratio major of its bar (`logo ~= bar-height / 1.618`), a modular
  type/space scale, and tight-but-even gaps. A brand mark usually wants to be a bit larger and closer
  to its container edges than a first draft makes it; size it against the reference page's mark.
- **Pre-mount a deferred heavy viewer HIDDEN so the first gesture works.** Deferring a heavy viewer
  (OpenSeadragon, a map, a video) to the first interaction makes that first gesture get consumed by the
  mount - lost on touch, where there is no hover to pre-warm. Mount it on idle (after `load`) but keep
  it `opacity:0` (opacity:0 excludes an element from being the LCP; and a `<canvas>` like
  OpenSeadragon's is never an LCP candidate by type at all - so the static `<img>` stays the LCP and PSI
  is unaffected) and reveal it on the first zoom intent. Note an `opacity:0` layer still RECEIVES pointer
  events (unlike `display:none`) - that is the point: keep the hidden viewer as the top interactive layer
  so the first gesture lands on the ready viewer (it zooms) AND triggers the reveal. Confirm the LCP
  element with a `PerformanceObserver` on the live page under `--route` (no deploy) - the canvas must not be it.
- **Compact content-rich pages on phones - shrink, don't just reflow.** A page that fits desktop/tablet
  (hero number, headline, lead, cards) overflows a 375x667 phone and especially a ~375-tall landscape.
  Add phone (`max-width`) AND short-height (`max-height`) overrides that SHRINK the big elements (hero
  size, card padding, gaps, spacing) and reflow cards to one row when wide-but-short, not only stack
  them. Drive sizes/spacing with `clamp()` over vw/vh so they scale with the viewport.
- **Keep a shared element the SAME rendered size across pages.** The logo/brand mark (and other shared
  chrome) should measure the same height on every page template at a given viewport - not 40px on one
  page, 34px on another. Render each page at one fixed viewport and compare; reconcile via a shared
  token (brand-token reconciliation itself: `design-brand-consistency`). Error pages (404/50x) are real
  pages too: audit and fit them at every viewport/locale like any other - a permanently-open menu or
  content overflow there is still a bug.

## Scope boundary (hand off to sibling skills)

Stay sharp - these belong elsewhere:

| Concern                                                   | Skill                      |
|-----------------------------------------------------------|----------------------------|
| Performance/SEO scoring, full Lighthouse, Core Web Vitals | `web-frontend-pagespeed`   |
| Localization infra (catalogs, locale routing, hreflang)   | `web-frontend-i18n`        |
| Brand/CI alignment to a reference/landing page            | `design-brand-consistency` |
| Self-hosting fonts (GDPR), font subsetting                | `web-frontend-fonts`       |
| GDPR/privacy compliance (consent, IP-leak, third-party)   | `sec-privacy-web-gdpr`     |
| Deep accessibility beyond the axe baseline                | `web-frontend-a11y-audit`  |
| `sitemap.xml` + SEO sitemap practices                     | `web-frontend-sitemap`     |

## Common mistakes

| Mistake                                          | Reality                                                                                                                                                                                                                                    |
|--------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Testing only desktop / only portrait             | Defects hide in landscape and on the smallest phone - sweep the matrix                                                                                                                                                                     |
| Eyeballing instead of measuring                  | Measure `scrollWidth`/rects/axe; a screenshot alone misses overflow                                                                                                                                                                        |
| Shrinking tap targets at mobile breakpoints      | Mobile needs BIGGER targets (>=44px), not smaller                                                                                                                                                                                          |
| Swipe as the only navigation                     | WCAG 2.5.1: always keep buttons + keyboard alongside swipe                                                                                                                                                                                 |
| `viewport-fit=cover` with no safe-area insets    | Notch/home-indicator covers content; add `env(safe-area-inset-*)`                                                                                                                                                                          |
| `100vh` on mobile                                | Use `svh` (or `dvh`); `100vh` overflows when the address bar shows                                                                                                                                                                         |
| Flex/grid child overflowing                      | Set `min-width: 0` / `min-height: 0` so it can shrink                                                                                                                                                                                      |
| Claiming "responsive now" without a re-run       | Re-run the audit; report 0 SEVERE / 0 MEDIUM with the numbers                                                                                                                                                                              |
| Releasing to prod to test / release-then-hotfix  | Converge the WHOLE change on the `--route` overlay (and a LOCAL app run for Lighthouse) first; cut ONE release - do not deploy to measure then hotfix                                                                                      |
| Insetting a big canvas to clear nearby buttons   | A fixed inset just moves the failing viewport; float controls OVER the surface so the rects overlap (the spacing check skips overlapping boxes)                                                                                            |
| Auto-applying fixes                              | Diagnose and propose diffs; apply only after the user confirms                                                                                                                                                                             |
| Trusting axe for all contrast                    | axe misses SVG-icon buttons + gradient/overlay bg; probe the WCAG ratio explicitly                                                                                                                                                         |
| Patching a revealed symptom, not the cause       | A change that exposes a gap is often a latent bug - measure the model (e.g. `gridTemplateRows`)                                                                                                                                            |
| `display:contents` on a `<picture>` to center    | It exposes the element's children (`<source>`) as grid/flex items - phantom rows push the `<img>` off-center; center/cap with a real `display:flex` box (`width/height:100%`)                                                              |
| "Phone" == narrow width                          | A landscape phone is WIDE (e.g. 852px) but short; a `max-width` rule misses it - gate phone tweaks on width OR `(orientation: landscape) and (max-height: 600px)`                                                                          |
| `margin:auto` shoving a group to the far edge    | On a narrow bar it leaves a big gap after the logo; anchor the brand/identity at the start and put `auto` only on the trailing control                                                                                                     |
| Caption that fits wide but truncates narrow      | Hide it responsively - and landscape phones need the orientation+height query, not just `max-width`                                                                                                                                        |
| All profiles overflow by the same small constant | Phantom scroll, not content - usually the default 8px `<body>` margin under a `min-height:100svh/vh` element (or an unreset `<ul>`/`<h1>`/`<p>`). Reset `margin:0`; shrinking content never moves an identical-constant overage            |
| A `<details>`/disclosure menu shows when closed  | An explicit `display` (e.g. `display:grid`) on the menu overrides the native `<details>` closed-hide, so it is permanently open (and every menu link gets touch-target-audited). Hide it when closed: `.x:not([open]) .menu{display:none}` |
| Editing a `@media` rule has no visible effect    | CSS source-order: the override sits BEFORE the base rule it targets, so the base (later, equal specificity) wins. Put responsive overrides AFTER the base rules, or raise specificity                                                      |
| Pulling in perf/SEO/font/i18n-infra work         | Out of scope - hand off to the sibling skill above                                                                                                                                                                                         |
