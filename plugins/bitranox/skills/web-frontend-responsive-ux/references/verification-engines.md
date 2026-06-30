# Verification engines reference

Two backends collect the same raw measurements; pick by what's available. The shared
`detectors.js` makes findings identical whichever drives the browser, and the thresholds
live in `analysis.py`.

## Decide which backend

```
Is a browser MCP connected (Playwright MCP or Chrome DevTools MCP)?
  yes -> use it for interactive diagnosis (resize, screenshot, evaluate detectors.js, lighthouse)
  no  -> is this a one-off interactive check, or a repeatable/CI sweep?
           interactive -> offer to install an MCP (commands below), or fall back to the bundled runner
           repeatable  -> use the bundled runner (headless, scriptable, what the tests cover)
```

The bundled Python runner is always available (needs only `uv`) and is the backend for
unattended / CI runs and for the device-matrix sweep. The MCPs shine for interactive
poke-around, the live Chrome DevTools performance/CLS signal, and visual confirmation.

## Installing the browser MCPs (guide the user when absent)

Both are official, npx-launched MCP servers. **Chrome DevTools MCP** (Google) is the best
default - real Chrome, performance traces, `lighthouse_audit`, console/network. **Playwright
MCP** (Microsoft) adds cross-browser and scripted multi-device navigation.

```bash
# Chrome DevTools MCP (Google) - real Chrome, perf/CLS, lighthouse
claude mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest

# Playwright MCP (Microsoft) - cross-browser, scripted navigation
claude mcp add playwright -- npx -y @playwright/mcp@latest
```

Equivalent JSON (`~/.claude.json` / project `.mcp.json`), e.g. for Chrome DevTools MCP:

```json
{ "mcpServers": { "chrome-devtools": { "command": "npx", "args": ["-y", "chrome-devtools-mcp@latest"] } } }
```

After adding, the tools appear as `mcp__chrome-devtools__*` / `mcp__playwright__*`. The
official `chrome-devtools-mcp` and `playwright` plugin skills cover their tool surfaces -
use those rather than re-deriving them; for accessibility specifically,
`chrome-devtools-mcp:a11y-debugging` pairs well.

## Bundled runner

```bash
# one-time browser install
uv run --with playwright playwright install chromium

# full device-matrix sweep -> ./audit-out/report.json + screenshots
uv run audit_responsive.py http://localhost:8000/view/ABC123 --out ./audit-out

# subset, add the i18n text-expansion pass, point axe at an offline mirror
uv run audit_responsive.py "$URL" --profiles "iPhone SE (landscape)" "iPad mini (portrait)" --i18n
```

`report.json` is `{ url, totals:{SEVERE,MEDIUM,MINOR}, passed, devices:[...] }`; exit code is
0 only when `passed` (no SEVERE/MEDIUM anywhere) - the "100%" bar for the owned dimensions.

## User-gated (login) pages

```bash
# 1. log in by hand once; save the session (keep the file secret, never commit it)
uv run make_storage_state.py https://example.com/login --out state.json

# 2. audit as the logged-in user
uv run audit_responsive.py https://example.com/app/dashboard --storage-state state.json
```

For an MCP session, log in interactively in the driven browser first, then run the checks -
the session persists for that browser.

## Pages backed by remote data (audit + iterate without deploying)

Common case: the page lives on a remote server and pulls heavy remote data (e.g. product
images from a media host). You should NOT push your in-progress CSS/JS to the real server to
test a layout change. Three modes, by purpose:

**A. Audit the live remote URL (final verification).** Point the runner straight at the
deployed page so you measure against real data and the real backend. Add `--storage-state`
for gated pages. This is the source of truth for "is it actually fixed in production".

```bash
uv run audit_responsive.py https://app.example.com/view/ABC123 --storage-state state.json
```

**B. Overlay local edits onto the live page (the iteration loop - server untouched).** Audit
the real remote URL but fulfill your edited assets from local files via `--route
'GLOB=LOCALPATH'` (repeatable). The remote server is never modified; the real images/data
still stream from the remote host, while the browser sees YOUR working-copy CSS/JS. Edit
locally, re-run, repeat - no deploy.

```bash
uv run audit_responsive.py https://app.example.com/view/ABC123 \
  --storage-state state.json \
  --route "**/static/css/app.css=src/.../static/css/app.css" \
  --route "**/static/js/app.js=src/.../static/js/app.js"
```

(`--route` uses Playwright request interception. It only intercepts network requests, so it
needs an `http(s)` page - a `file://` page's subresources bypass it. An MCP session can do the
same with its route/intercept tool.)

**`--route` overlays SUB-RESOURCES (CSS/JS/images), not the main HTML.** The page document itself
is server-rendered, so a **template / HTML change cannot be previewed by overlaying it on the live
page** - the live page keeps serving the old markup with your new CSS. To preview an HTML/template
change against the live page, inject the DOM change with a `page.evaluate(...)` that mimics the new
markup (preview only), or run the app locally with the new template. Verify such a change with a
**DOM-accurate probe** (inject the markup, then measure) - a bare-DOM probe can pass while the real
template overflows or truncates, because the added wrappers/labels change widths.

To OPERATE every size by hand (click, scroll, zoom, swipe on a touchscreen) while iterating, open
one live window per viewport with the same overlay:

```bash
uv run open_viewports.py https://app.example.com/view/ABC123 \
  --route "**/static/css/app.css=src/.../app.css" \
  --route "**/static/js/app.js=src/.../app.js"
```

It opens a headed window per profile and stays up until you close them all. Prefer this for
manual interaction; keep the headless `audit_responsive.py` run as the pass/fail gate.

**C. Capture representative fixtures for fast offline iteration.** Drawing sample content from
the existing page is good - just cover the layout-stressing cases, not one happy SKU. Save a
handful: the smallest gallery (1 image), the largest (many images / longest thumbnail rail),
a missing-data / 404 case, the longest-text record, and one RTL locale. Either keep the real
remote asset URLs absolute so images still load from the host, or download a few sample images
locally. Iterate against these, then always finish with mode A against the live page.

Trade-off: fixtures/overlays are fast but can drift from production (stale markup, fewer real
data shapes). They are for iteration speed; the green verdict that counts is mode A on the
real URL.

## i18n / multilingual pages

The same modes apply per locale. Two angles:

- **Real locales:** audit each language's URL - set it however the site selects language: a
  query param (`?lang=de`), a cookie captured into `state.json` via `make_storage_state.py`,
  or a localized path (`/de/...`). Sweep the matrix per locale, and include the RTL locale
  (e.g. Arabic, `dir="rtl"`) so mirroring is checked. `--route` overlays work unchanged.
- **Synthetic (before translations exist):** `--i18n` pseudo-localizes whatever page is
  loaded (expands text ~40%) to stress text-expansion early. Use it to catch fixed-width /
  clipping bugs without waiting for real translations; once real long locales (German, etc.)
  exist, auditing those URLs directly is stronger.

## Driving an MCP manually (when you want a quick interactive check)

The same `detectors.js` works through an MCP `evaluate_script` call after you resize/emulate
a device; read the file and pass its contents. Use `lighthouse_audit` (Chrome DevTools MCP)
only for the layout-perf/CLS signal - full performance/SEO scoring is the future
`web-frontend-pagespeed` skill's job, not this one.

## Diagnose AND verify by probing computed values (not screenshots alone)

A screenshot shows *that* something is off; a `page.evaluate` probe returns *the number* that
proves it - and proves the fix. For any "looks wrong" report, write a tiny probe that returns the
exact computed value for the elements in question, fix, then re-probe. Cheap, exact, regression-proof.

- **Contrast** - compute the WCAG ratio of an element's computed `color` against its real
  background. Do this for icon buttons too: **axe-core misses SVG-icon controls and struggles with
  gradient/overlay backgrounds**, so it can report "0 contrast violations" while a label sits at 2.4
  and an arrow button looks washed out. Faint custom shades (a light taupe like `#a89a8e`) routinely
  fail - measure, don't trust the swatch.

  ```js
  const lin = c => (c/=255, c<=0.03928 ? c/12.92 : Math.pow((c+0.055)/1.055, 2.4));
  const L = ([r,g,b]) => 0.2126*lin(r)+0.7152*lin(g)+0.0722*lin(b);
  const ratio = (fg,bg) => (Math.max(L(fg),L(bg))+0.05)/(Math.min(L(fg),L(bg))+0.05);
  ```
- **Typography** - `getComputedStyle(el).fontFamily` per element + `document.fonts.check("16px 'Family'")`
  to confirm the intended face actually loaded (not a silent system fallback).
- **Geometry / fit** - element `getBoundingClientRect()`, `naturalWidth/Height`, the gap between two
  elements, and `getComputedStyle(grid).gridTemplateRows`. An unexplained empty band or an
  off-center overlay shows up immediately as a number that doesn't match what you defined.

## Layout-perf (CLS) scope

This skill checks only *layout-driven* shift: images/iframes without reserved space
(`width`/`height`/`aspect-ratio`), late-loading webfonts causing reflow (`font-display`,
`size-adjust`). Reserve space and the CLS contribution disappears. Everything else in
Core Web Vitals / Lighthouse performance is out of scope here.
