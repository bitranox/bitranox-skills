# Opacity

The `opacity` style sets the opacity of a widget.

While terminals are not capable of true opacity, Textual can create an approximation by blending widgets with their background color.

## Syntax

```
opacity: <number> | <percentage>;
```

The opacity of a widget can be set as a [`<number>`](../css_types/number.md) or a [`<percentage>`](../css_types/percentage.md).
If given as a number, then `opacity` should be a value between 0 and 1, where 0 is the background color and 1 is fully opaque.
If given as a percentage, 0% is the background color and 100% is fully opaque.

Typically, if you set this value it would be somewhere between the two extremes.
For instance, setting the opacity of a widget to `70%` will make it appear dimmer than surrounding widgets, which could be used to display a *disabled* state.


## Example

This example shows, from top to bottom, increasing opacity values for a label with a border and some text.
When the opacity is zero, all we see is the (black) background.

**opacity.py**


```python
from textual.app import App
from textual.widgets import Label


class OpacityApp(App):
    CSS_PATH = "opacity.tcss"

    def compose(self):
        yield Label("opacity: 0%", id="zero-opacity")
        yield Label("opacity: 25%", id="quarter-opacity")
        yield Label("opacity: 50%", id="half-opacity")
        yield Label("opacity: 75%", id="three-quarter-opacity")
        yield Label("opacity: 100%", id="full-opacity")


if __name__ == "__main__":
    app = OpacityApp()
    app.run()
```

**opacity.tcss**


```css
#zero-opacity {
    opacity: 0%;
}

#quarter-opacity {
    opacity: 25%;
}

#half-opacity {
    opacity: 50%;
}

#three-quarter-opacity {
    opacity: 75%;
}

#full-opacity {
    opacity: 100%;
}

Screen {
    background: black;
}

Label {
    width: 100%;
    height: 1fr;
    border: outer dodgerblue;
    background: lightseagreen;
    content-align: center middle;
    text-style: bold;
}
```
## CSS

```css
/* Fade the widget to 50% against its parent's background */
opacity: 50%;
```

## Python

```python
# Fade the widget to 50% against its parent's background
widget.styles.opacity = "50%"
```

## See also

 - [`text-opacity`](./text_opacity.md) to blend the color of a widget's content with its background color.
