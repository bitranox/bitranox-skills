# Background

The `background` style sets the background color of a widget.

## Syntax

```
background: <color> [<percentage>];
```

The `background` style requires a [`<color>`](../css_types/color.md) optionally followed by [`<percentage>`](../css_types/percentage.md) to specify the color's opacity (clamped between `0%` and `100%`).

## Examples

### Basic usage

This example creates three widgets and applies a different background to each.

**background.py**


```python
from textual.app import App
from textual.widgets import Label


class BackgroundApp(App):
    CSS_PATH = "background.tcss"

    def compose(self):
        yield Label("Widget 1", id="static1")
        yield Label("Widget 2", id="static2")
        yield Label("Widget 3", id="static3")


if __name__ == "__main__":
    app = BackgroundApp()
    app.run()
```

**background.tcss**


```css
Label {
    width: 100%;
    height: 1fr;
    content-align: center middle;
    color: white;
}

#static1 {
    background: red;
}

#static2 {
    background: rgb(0, 255, 0);
}

#static3 {
    background: hsl(240, 100%, 50%);
}
```
### Different opacity settings

The next example creates ten widgets laid out side by side to show the effect of setting different percentages for the background color's opacity.

**background_transparency.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class BackgroundTransparencyApp(App):
    """Simple app to exemplify different transparency settings."""

    CSS_PATH = "background_transparency.tcss"

    def compose(self) -> ComposeResult:
        yield Static("10%", id="t10")
        yield Static("20%", id="t20")
        yield Static("30%", id="t30")
        yield Static("40%", id="t40")
        yield Static("50%", id="t50")
        yield Static("60%", id="t60")
        yield Static("70%", id="t70")
        yield Static("80%", id="t80")
        yield Static("90%", id="t90")
        yield Static("100%", id="t100")


if __name__ == "__main__":
    app = BackgroundTransparencyApp()
    app.run()
```

**background_transparency.tcss**


```css
#t10 {
    background: red 10%;
}

#t20 {
    background: red 20%;
}

#t30 {
    background: red 30%;
}

#t40 {
    background: red 40%;
}

#t50 {
    background: red 50%;
}

#t60 {
    background: red 60%;
}

#t70 {
    background: red 70%;
}

#t80 {
    background: red 80%;
}

#t90 {
    background: red 90%;
}

#t100 {
    background: red 100%;
}

Screen {
    layout: horizontal;
}

Static {
    height: 100%;
    width: 1fr;
    content-align: center middle;
}
```
## CSS

```css
/* Blue background */
background: blue;

/* 20% red background */
background: red 20%;

/* RGB color */
background: rgb(100, 120, 200);

/* HSL color */
background: hsl(290, 70%, 80%);
```

## Python

You can use the same syntax as CSS, or explicitly set a `Color` object for finer-grained control.

```python
# Set blue background
widget.styles.background = "blue"
# Set through HSL model
widget.styles.background = "hsl(351,32%,89%)"

from textual.color import Color
# Set with a color object by parsing a string
widget.styles.background = Color.parse("pink")
widget.styles.background = Color.parse("#FF00FF")
# Set with a color object instantiated directly
widget.styles.background = Color(120, 60, 100)
```

## See also

 - [`background-tint`](./background_tint.md) to blend a color with the background.
 - [`color`](./color.md) to set the color of text in a widget.
