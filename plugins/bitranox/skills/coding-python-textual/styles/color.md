# Color

The `color` style sets the text color of a widget.

## Syntax

```
color: (<color> | auto) [<percentage>];
```

The `color` style requires a [`<color>`](../css_types/color.md) followed by an optional [`<percentage>`](../css_types/percentage.md) to specify the color's opacity.

You can also use the special value of `"auto"` in place of a color. This tells Textual to automatically select either white or black text for best contrast against the background.

## Examples

### Basic usage

This example sets a different text color for each of three different widgets.

**color.py**


```python
from textual.app import App
from textual.widgets import Label


class ColorApp(App):
    CSS_PATH = "color.tcss"

    def compose(self):
        yield Label("I'm red!", id="label1")
        yield Label("I'm rgb(0, 255, 0)!", id="label2")
        yield Label("I'm hsl(240, 100%, 50%)!", id="label3")


if __name__ == "__main__":
    app = ColorApp()
    app.run()
```

**color.tcss**


```css
Label {
    height: 1fr;
    content-align: center middle;
    width: 100%;
}

#label1 {
    color: red;
}

#label2 {
    color: rgb(0, 255, 0);
}

#label3 {
    color: hsl(240, 100%, 50%);
}
```
### Auto

The next example shows how `auto` chooses between a lighter or a darker text color to increase the contrast and improve readability.

**color_auto.py**


```py
from textual.app import App
from textual.widgets import Label


class ColorApp(App):
    CSS_PATH = "color_auto.tcss"

    def compose(self):
        yield Label("The quick brown fox jumps over the lazy dog!", id="lbl1")
        yield Label("The quick brown fox jumps over the lazy dog!", id="lbl2")
        yield Label("The quick brown fox jumps over the lazy dog!", id="lbl3")
        yield Label("The quick brown fox jumps over the lazy dog!", id="lbl4")
        yield Label("The quick brown fox jumps over the lazy dog!", id="lbl5")


if __name__ == "__main__":
    app = ColorApp()
    app.run()
```

**color_auto.tcss**


```css
Label {
    color: auto 80%;
    content-align: center middle;
    height: 1fr;
    width: 100%;
}

#lbl1 {
    background: red 80%;
}

#lbl2 {
    background: yellow 80%;
}

#lbl3 {
    background: blue 80%;
}

#lbl4 {
    background: pink 80%;
}

#lbl5 {
    background: green 80%;
}
```
## CSS

```css
/* Blue text */
color: blue;

/* 20% red text */
color: red 20%;

/* RGB color */
color: rgb(100, 120, 200);

/* Automatically choose color with suitable contrast for readability */
color: auto;
```

## Python

You can use the same syntax as CSS, or explicitly set a `Color` object.

```python
# Set blue text
widget.styles.color = "blue"

from textual.color import Color
# Set with a color object
widget.styles.color = Color.parse("pink")
```

## See also

 - [`background`](./background.md) to set the background color in a widget.
 - [`<color>`](../css_types/color.md) for the accepted color value formats.
 - [`text-opacity`](./text_opacity.md) to blend the text color with the background.
