# Scrollbar-color-active

The `scrollbar-color-active` style sets the color of the scrollbar when the thumb is being dragged.

## Syntax

```
scrollbar-color-active: <color> [<percentage>];
```

`scrollbar-color-active` accepts a [`<color>`](../../css_types/color.md) (with an optional opacity level defined by a [`<percentage>`](../../css_types/percentage.md)) that is used to define the color of a scrollbar when its thumb is being dragged.

## Example

**Output**


![](scrollbar_colors_demo.gif)

> **Note**
>
>
> The GIF above has reduced quality to make it easier to load in the documentation.
> Try running the example yourself with `textual run docs/examples/styles/scrollbars2.py`.


**scrollbars2.py**


```py
from textual.app import App
from textual.widgets import Label

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain.
"""


class Scrollbar2App(App):
    CSS_PATH = "scrollbars2.tcss"

    def compose(self):
        yield Label(TEXT * 10)


if __name__ == "__main__":
    app = Scrollbar2App()
    app.run()
```

**scrollbars2.tcss**


```css
Screen {
    scrollbar-background: blue;
    scrollbar-background-active: red;
    scrollbar-background-hover: purple;
    scrollbar-color: cyan;
    scrollbar-color-active: yellow;
    scrollbar-color-hover: pink;
}
```
## CSS

```css
scrollbar-color-active: yellow;
```

## Python

```py
widget.styles.scrollbar_color_active = "yellow"
```

## See also

 - [`scrollbar-background-active`](./scrollbar_background_active.md) to set the scrollbar background color when the scrollbar is being dragged.
 - [`scrollbar-color`](./scrollbar_color.md) to set the color of scrollbars.
 - [`scrollbar-color-hover`](./scrollbar_color_hover.md) to set the scrollbar color when the mouse pointer is over it.
