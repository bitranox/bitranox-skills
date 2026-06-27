# Scrollbar-corner-color

The `scrollbar-corner-color` style sets the color of the gap between the horizontal and vertical scrollbars.

## Syntax

```
scrollbar-corner-color: <color> [<percentage>];
```

`scrollbar-corner-color` accepts a [`<color>`](../../css_types/color.md) (with an optional opacity level defined by a [`<percentage>`](../../css_types/percentage.md)) that is used to define the color of the gap between the horizontal and vertical scrollbars of a widget.

## Example

The example below sets the scrollbar corner (bottom-right corner of the screen) to white.

**scrollbar_corner_color.py**


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


class ScrollbarCornerColorApp(App):
    CSS_PATH = "scrollbar_corner_color.tcss"

    def compose(self):
        yield Label(TEXT.replace("\n", " ") + "\n" + TEXT * 10)


if __name__ == "__main__":
    app = ScrollbarCornerColorApp()
    app.run()
```

**scrollbar_corner_color.tcss**


```css
Screen {
    overflow: auto auto;
    scrollbar-corner-color: white;
}
```
## CSS

```css
scrollbar-corner-color: white;
```

## Python

```py
widget.styles.scrollbar_corner_color = "white"
```

## See also

 - [`scrollbar-background`](./scrollbar_background.md) to set the background color of scrollbars.
 - [`scrollbar-color`](./scrollbar_color.md) to set the color of scrollbars.
 - [`scrollbar-size`](../scrollbar_size.md) to set the dimensions of scrollbars.
