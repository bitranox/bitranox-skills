# Tint

The `tint` style blends a color with the whole widget.

## Syntax

```
tint: <color> [<percentage>];
```

The tint style blends a [`<color>`](../css_types/color.md) with the widget. The color should likely have an _alpha_ component (specified directly in the color used or by the optional [`<percentage>`](../css_types/percentage.md)), otherwise the end result will obscure the widget content.

## Example

This examples shows a green tint with gradually increasing alpha.

**tint.py**


```python
from textual.app import App
from textual.color import Color
from textual.widgets import Label


class TintApp(App):
    CSS_PATH = "tint.tcss"

    def compose(self):
        color = Color.parse("green")
        for tint_alpha in range(0, 101, 10):
            widget = Label(f"tint: green {tint_alpha}%;")
            widget.styles.tint = color.with_alpha(tint_alpha / 100)  # (1)!
            yield widget


if __name__ == "__main__":
    app = TintApp()
    app.run()
```


**tint.tcss**


```css
Label {
    height: 3;
    width: 100%;
    text-style: bold;
    background: white;
    color: black;
    content-align: center middle;
}
```
## CSS

```css
/* A red tint (could indicate an error) */
tint: red 20%;

/* A green tint */
tint: rgba(0, 200, 0, 0.3);
```

## Python

```python
# A red tint
from textual.color import Color
widget.styles.tint = Color.parse("red").with_alpha(0.2);

# A green tint
widget.styles.tint = "rgba(0, 200, 0, 0.3)"
```

## See also

 - [`background-tint`](./background_tint.md) to tint only the background color of a widget.
 - [`opacity`](./opacity.md) to set the opacity of a whole widget.
