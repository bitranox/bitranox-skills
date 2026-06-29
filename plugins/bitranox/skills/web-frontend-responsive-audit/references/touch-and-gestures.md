# Touch targets, gestures & i18n layout reference

## Touch target size & spacing

| Standard                         | Minimum      | Notes                                               |
|----------------------------------|--------------|-----------------------------------------------------|
| WCAG 2.5.8 Target Size (AA)      | 24x24 CSS px | hard floor; below this fails AA                     |
| Apple Human Interface Guidelines | 44x44 pt     | the practical recommended minimum                   |
| Material Design                  | 48x48 dp     | Google's recommended minimum                        |
| Spacing between targets          | >= 8 px      | or an exclusion zone so adjacent taps don't collide |

The skill requires **>= 44px** (Apple floor) as the comfortable target and flags 24-43px as
MEDIUM (passes AA, cramped), < 24px as SEVERE. Enlarging the *hit area* need not enlarge the
visual: keep the icon small, grow the box with padding or a pseudo-element:

```css
.icon-btn {                      /* visual stays compact, hit area is comfortable */
  min-block-size: 44px;
  min-inline-size: 44px;
  display: inline-grid;
  place-items: center;
}
/* or extend a small control's hit area without affecting layout: */
.small-link { position: relative; }
.small-link::after { content: ""; position: absolute; inset: -8px; }
```

Never shrink targets below 44px at mobile breakpoints - that is the exact opposite of what
small screens need (a real-world miss: nav arrows scaled from 46px down to 40px under
`@media (max-width: 640px)`).

## Swipe / carousel gestures (accessible)

A swipeable image gallery must satisfy WCAG 2.5.1 Pointer Gestures: any swipe MUST have a
single-pointer, non-path alternative. So swipe is an *enhancement layered on top of* buttons
+ keyboard, never the only way.

Checklist for a swipeable gallery:
- Visible **Prev/Next buttons** (>=44px) AND **ArrowLeft/ArrowRight** keyboard support - the
  non-gesture alternative (WCAG 2.5.1).
- Swipe via **Pointer Events** (`pointerdown`/`pointermove`/`pointerup`), not legacy
  `touchstart` only - Pointer Events unify mouse/touch/pen and let you `setPointerCapture`.
- Honour **`prefers-reduced-motion: reduce`**: drop slide animation, snap instantly.
- Use `touch-action: pan-y` on the slider so horizontal swipes don't fight vertical page
  scroll (and the browser doesn't wait on a 300ms gesture).
- Expose state to AT: a live region or `aria-roledescription="carousel"` + slide
  `aria-label="3 of 8"`; move focus sensibly on change.

Minimal Pointer-Events swipe that coexists with buttons/keyboard:

```js
let x0 = null;
slider.addEventListener("pointerdown", (e) => { x0 = e.clientX; slider.setPointerCapture(e.pointerId); });
slider.addEventListener("pointerup", (e) => {
  if (x0 === null) return;
  const dx = e.clientX - x0; x0 = null;
  if (Math.abs(dx) > 40) (dx < 0 ? next : prev)();   // same next()/prev() the buttons call
});
```

```css
.slider { touch-action: pan-y; }
@media (prefers-reduced-motion: reduce) { .slide { transition: none; } }
```

## Thumbnail rails: scrollable + mouse-drag-pannable

A film-strip / thumbnail rail must (a) scroll when items overflow and (b) be draggable with the
mouse, not only the wheel. Direction follows the layout: a bottom strip scrolls horizontally, a
side rail vertically. Leave touch to native momentum scroll; add drag-to-pan for the mouse only:

```js
const rail = document.querySelector(".rail");
let down = false, moved = false, sx, sy, sl, st;
rail.addEventListener("pointerdown", e => {
  if (e.pointerType !== "mouse" || e.button !== 0) return;   // touch uses native scroll
  down = true; moved = false; sx = e.clientX; sy = e.clientY; sl = rail.scrollLeft; st = rail.scrollTop;
  rail.classList.add("is-dragging"); rail.setPointerCapture(e.pointerId);
});
rail.addEventListener("pointermove", e => {
  if (!down) return;
  if (Math.abs(e.clientX - sx) + Math.abs(e.clientY - sy) > 4) moved = true;
  rail.scrollLeft = sl - (e.clientX - sx);     // pan both axes; the rail scrolls in whichever it can
  rail.scrollTop  = st - (e.clientY - sy);
});
rail.addEventListener("pointerup",   () => { down = false; rail.classList.remove("is-dragging"); });
rail.addEventListener("click", e => { if (moved) { e.preventDefault(); e.stopPropagation(); moved = false; } }, true);
```

```css
.rail { cursor: grab; overflow: auto; }
.rail.is-dragging { cursor: grabbing; user-select: none; }
.rail.is-dragging img { pointer-events: none; }  /* no native image-drag ghost while panning */
```

## Landscape phones: vertical film strip on the LEFT

On a short landscape viewport a bottom strip wastes the scarce height and squeezes/clips the hero
image. Switch the page grid to two columns with the strip as a scrollable left rail:

```css
@media (orientation: landscape) and (max-height: 600px) {
  .app {
    grid-template-rows: auto minmax(0, 1fr);
    grid-template-columns: auto minmax(0, 1fr);
    grid-template-areas: "hud  hud" "rail stage";
  }
  .hud { grid-area: hud; }  .stage { grid-area: stage; }
  .rail {
    grid-area: rail;
    flex-direction: column;            /* vertical thumbnails */
    width: clamp(68px, 16vw, 104px);
    overflow-x: hidden; overflow-y: auto;
    border-top: none; border-inline-end: 1px solid var(--line);
  }
}
```

## Hover/focus on touch

- Don't hide essential affordances behind `:hover` only - touch has no hover. Pair every
  `:hover` with a `:focus-visible` and a default-visible state on touch.
- Provide `:focus-visible` outlines (>=2px, good contrast) for keyboard users.

## i18n layout robustness (the layout-only slice)

Full localization (message catalogs, locale routing, formatting, `hreflang`) belongs to the
`web-frontend-i18n` sibling skill. What the responsive audit owns is whether the *layout
survives* translation:

- **Text expansion:** translated strings run ~30-40% longer (German, Finnish) and can be
  much longer for single words. Containers must wrap and grow, not clip or push width.
  Avoid fixed widths/heights on text; allow `overflow-wrap: anywhere`; test with
  pseudo-localization (the audit's `--i18n` pass expands text and re-checks overflow).
- **RTL mirroring:** under `dir="rtl"` the layout must mirror. Use logical properties
  (`margin-inline-start`, `inset-inline`, `padding-block`) instead of physical
  (`margin-left`, `left`, `padding-top`) so mirroring is automatic.
- **`lang` / `dir`:** `<html lang="..">` is set (correct language) and `dir` is set when
  serving an RTL locale.
