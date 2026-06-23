# Hatch

The `hatch` style fills a widget's background with a repeating character for a pleasing textured effect.

## Syntax

```
hatch: (<hatch> | CHARACTER) <color> [<percentage>]
```

The hatch type can be specified with a constant, or a string. For example, `cross` for cross hatch, or `"T"` for a custom character.

The color can be any Textual color value.

An optional percentage can be used to set the opacity.

## Examples


An app to show a few hatch effects.

**hatch.py**


```py
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

HATCHES = ("cross", "horizontal", "custom", "left", "right")


class HatchApp(App):
    CSS_PATH = "hatch.tcss"

    def compose(self) -> ComposeResult:
        with Horizontal():
            for hatch in HATCHES:
                static = Static(classes=f"hatch {hatch}")
                static.border_title = hatch
                with Vertical():
                    yield static


if __name__ == "__main__":
    app = HatchApp()
    app.run()
```

**hatch.tcss**


```css
.hatch {
    height: 1fr;
    border: solid $secondary;

    &.cross {
        hatch: cross $success;
    }
    &.horizontal {
        hatch: horizontal $success 80%;
    }
    &.custom {
        hatch: "T" $success 60%;
    }
    &.left {
        hatch: left $success 40%;
    }
    &.right {
        hatch: right $success 20%;
    }
}
```
## CSS

```css
/* Red cross hatch */
hatch: cross red;
/* Right diagonals, 50% transparent green. */
hatch: right green 50%;
/* T custom character in 80% blue. **/
hatch: "T" blue 80%;
```
## Python

```py
widget.styles.hatch = ("cross", "red")
widget.styles.hatch = ("right", "rgba(0,255,0,128)")
widget.styles.hatch = ("T", "blue")
```

## See also

 - [`background`](./background.md) to set the background color of a widget.
 - [`<hatch>`](../css_types/hatch.md) for the accepted hatch pattern types.
