# Responsive layout reference

Concrete, modern patterns for the layout dimensions this skill owns: no horizontal
overflow, vertical fit on phones, and fluid (not sparse) layouts on big screens. Prefer
these over media-query-heavy fixed breakpoints.

## Viewport meta + notch (safe areas)

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

`viewport-fit=cover` lets content reach the screen edges on notched phones - but then you
MUST pad interactive/edge content by the safe-area insets, or the notch / home indicator /
rounded corners cover it (worst in landscape):

```css
.hud  { padding-top: max(0.6rem, env(safe-area-inset-top)); }
.rail { padding-bottom: max(0.6rem, env(safe-area-inset-bottom)); }
.nav-prev { left:  max(0.5rem, env(safe-area-inset-left)); }
.nav-next { right: max(0.5rem, env(safe-area-inset-right)); }
```

Shipping `viewport-fit=cover` with NO `env(safe-area-inset-*)` anywhere is a defect. The
automated audit does NOT detect this - check it by hand (grep the CSS for
`safe-area-inset` when the meta tag sets `viewport-fit=cover`).

## Dynamic viewport units: svh / lvh / dvh

Mobile browser chrome (address bar) grows/shrinks the viewport. `100vh` is the *large*
state and overflows when the bar is showing.

| Unit  | Height basis                  | Use for                                                            |
|-------|-------------------------------|--------------------------------------------------------------------|
| `svh` | smallest (UI shown)           | full-screen sections that must fit on first paint - safest default |
| `lvh` | largest (UI hidden)           | immersive layouts that intentionally fill the max area             |
| `dvh` | dynamic (tracks the bar live) | when the section should track the bar; can cause reflow on scroll  |

Default to `svh` for "fit one screen"; reserve `dvh` for elements that should follow the
bar. Provide a `vh` fallback for old engines: `height: 100vh; height: 100svh;`.

## Vertical fit without scrolling (phones, portrait AND landscape)

Make the page a single column grid that owns the viewport and let ONE region absorb the
slack, so chrome stays fixed-height and the primary content fits:

```css
.app {
  min-height: 100svh;
  display: grid;
  grid-template-rows: auto 1fr auto;   /* header | content (absorbs) | footer */
  overflow: hidden;                    /* no page scroll; content fits the 1fr cell */
}
.content { min-height: 0; display: grid; place-items: center; }  /* min-height:0 lets it shrink */
.content img { max-width: 100%; max-height: 100%; object-fit: contain; }
```

Key gotchas:
- A grid/flex child will NOT shrink below its content unless you set `min-height: 0`
  (or `min-width: 0` for the inline axis). This is the #1 cause of "it overflows anyway".
- Cap media to the cell (`max-height: 100%` inside a `1fr` row), not to a fixed `vh`, so
  it reflows when landscape shortens the row.
- Don't place the last row's child with `grid-row: -1` (single value). It sets only
  `grid-row-start` to the last *explicit* line and spans 1, creating a **phantom implicit
  row** below the grid - the intended last row sits empty, the `1fr` row shrinks, and your
  hero content renders smaller than it should. Let it auto-place, or use an explicit line
  (`grid-row: 3 / 4`). Symptom: an unexplained empty band and `getComputedStyle(grid).gridTemplateRows`
  showing one more row than you defined.
- Landscape phones are short: collapse header/footer heights with a
  `@media (orientation: landscape) and (max-height: 480px)` query.

## No horizontal overflow

Common causes and fixes:

| Cause                                                   | Fix                                                                 |
|---------------------------------------------------------|---------------------------------------------------------------------|
| Fixed pixel widths wider than small viewports           | `max-width: 100%`; `width: min(100%, 40rem)`                        |
| Flex/grid child refusing to shrink                      | `min-width: 0` on the child (and `overflow-wrap: anywhere` on text) |
| `100vw` (includes scrollbar) on a page with a scrollbar | use `100%` or `100dvw`; avoid `100vw` for full-bleed                |
| Long unbroken strings / URLs (outside table cells)      | `overflow-wrap: anywhere`                                           |
| Text columns of a table collapse letter by letter       | `overflow-wrap: break-word`, never `word-break`; see below          |
| Negative margins / absolute elements off-canvas         | constrain with a positioned, `overflow: clip` container             |
| Images without a max                                    | `img { max-width: 100%; height: auto; }`                            |

`* { box-sizing: border-box; }` everywhere prevents padding/border from adding width.

### Wrapping inside a table (HTML e-mail included)

In an auto-layout table, `word-break: break-word` or `overflow-wrap: anywhere` on a cell does more
than wrap long words: it drops that column's min-content width to about one character. Next to
`white-space: nowrap` columns the table then shrinks the text columns until names and addresses
break letter by letter, and a `width` on the header cell does not stop it, because column widths
are only hints in auto layout. Give each kind of column its own rule:

- **Identifiers** (order and invoice numbers, dates, tracking ids): `white-space: nowrap`.
- **Free text** (names, addresses): `overflow-wrap: break-word`. It breaks a word only when the word
  cannot fit at all, so the column's min-content width stays at its longest word.
- **A value with no break points that can be very long** (an e-mail address, a URL): put it in a
  block of real width so only that block breaks and the column cannot collapse,
  `<div style="width:150px;max-width:100%;overflow-wrap:anywhere;word-break:break-all">`, and give
  it a phone media-query rule (`width: auto !important`) or it stays narrow in a full-width card.
- **A block outside the table** (a legend, a footer note) inherits none of the table's styling: set
  `font-family` on every inline element, or a pill falls back to the mail client's serif default.
  Lay it out as flowing blocks (one `div` per entry, pill then text), never as a two-column
  pill-plus-text table, which squeezes the text column to a sliver on a phone.

Confirm the layout by rendering it with REAL data and screenshotting it at a desktop and a phone
width (for example 1200 and 390 px) before the page or mail goes out. For a mail, save the
rendered HTML, serve its directory with `python3 -m http.server`, and point `audit_responsive.py`
at that URL; Chromium only approximates a mail client, so also send one test mail. Each fix here
looks right in the code and in tests, and the next long value can break what the previous fix
repaired.

## Fluid sizing: clamp(), not breakpoint steps

Scale space and type continuously so layouts are neither cramped on phones nor sparse on
big screens (fewer breakpoints, no dead zones):

```css
:root { --pad: clamp(1rem, 4vw, 3rem); }
.section { padding-inline: var(--pad); }
h1 { font-size: clamp(1.5rem, 1rem + 3vw, 3rem); }
.wrap { width: min(100% - 2 * var(--pad), 72rem); margin-inline: auto; }  /* centered, never edge-to-edge */
```

## Proportions: the golden ratio (1.618) and a modular scale

Pick sizes/spacing from a harmonious scale instead of ad-hoc px values - it reads as "designed,"
not arbitrary. The golden ratio (`phi ~= 1.618`, "goldener Schnitt") is a reliable default for
relating a part to its whole:

- A brand mark at the golden-ratio major of its bar: `logo-height ~= bar-height / 1.618`
  (e.g. a 54px header -> ~34px logo), which also keeps the mark tight to the bar edges.
- A type scale stepped by ~1.2-1.618 (`--step` multiplier), and spacing tokens on the same scale.
- Content vs whitespace, or a sidebar vs main split, near `1 : 1.618`.

```css
:root { --phi: 1.618; --bar-h: 54px; }
.brand img { height: calc(var(--bar-h) / var(--phi)); }   /* ~34px - the bar's golden major */
```

Treat it as a guide, not a straitjacket: round to tidy px, respect the >=44px touch-target floor,
and size a brand mark against the reference page's actual mark.

## Container queries for component-level responsiveness

Size a component to its container, not the viewport - lets the same card work in a
sidebar or full-width without viewport media queries:

```css
.card-host { container-type: inline-size; }
@container (min-width: 30rem) { .card { grid-template-columns: 1fr 2fr; } }
```

## Responsive images

```html
<img src="p-800.jpg"
     srcset="p-400.jpg 400w, p-800.jpg 800w, p-1600.jpg 1600w"
     sizes="(max-width: 640px) 100vw, 50vw"
     width="1600" height="1200" loading="lazy" decoding="async" alt="...">
```

Always set intrinsic `width`/`height` (or `aspect-ratio`) so the browser reserves space -
this prevents image-driven layout shift (CLS), the layout-perf slice this skill owns.
