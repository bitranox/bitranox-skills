# Overflow

The `overflow` style specifies if and when scrollbars should be displayed.

## Syntax

```
overflow: <overflow> <overflow>;

overflow-x: <overflow>;
overflow-y: <overflow>;
```

The style `overflow` accepts two values that determine when to display scrollbars in a container widget.
The two values set the overflow for the horizontal and vertical axes, respectively.

Overflow may also be set individually for each axis:

 - `overflow-x` sets the overflow for the horizontal axis; and
 - `overflow-y` sets the overflow for the vertical axis.

### Defaults

The default setting for containers is `overflow: auto auto`.

> **Warning**
>
>
> Some built-in containers like `Horizontal` and `VerticalScroll` override these defaults.


## Example

Here we split the screen into left and right sections, each with three vertically scrolling widgets that do not fit into the height of the terminal.

The left side has `overflow-y: auto` (the default) and will automatically show a scrollbar.
The right side has `overflow-y: hidden` which will prevent a scrollbar from being shown.

**overflow.py**


```python
from textual.app import App
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class OverflowApp(App):
    CSS_PATH = "overflow.tcss"

    def compose(self):
        yield Horizontal(
            VerticalScroll(Static(TEXT), Static(TEXT), Static(TEXT), id="left"),
            VerticalScroll(Static(TEXT), Static(TEXT), Static(TEXT), id="right"),
        )


if __name__ == "__main__":
    app = OverflowApp()
    app.run()
```

**overflow.tcss**


```css
Screen {
    background: $background;
    color: black;
}

VerticalScroll {
    width: 1fr;
}

Static {
    margin: 1 2;
    background: green 80%;
    border: green wide;
    color: white 90%;
    height: auto;
}

#right {
    overflow-y: hidden;
}
```
## CSS

```css
/* Automatic scrollbars on both axes (the default) */
overflow: auto auto;

/* Hide the vertical scrollbar */
overflow-y: hidden;

/* Always show the horizontal scrollbar */
overflow-x: scroll;
```

## Python

Overflow cannot be programmatically set for both axes at the same time.

```python
# Hide the vertical scrollbar
widget.styles.overflow_y = "hidden"

# Always show the horizontal scrollbar
widget.styles.overflow_x = "scroll"
```

## See also

 - [`scrollbar-size`](./scrollbar_size.md) to set the dimensions of scrollbars.
 - [`scrollbar-gutter`](./scrollbar_gutter.md) to reserve space for a vertical scrollbar.
