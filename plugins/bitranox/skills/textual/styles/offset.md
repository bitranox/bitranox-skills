# Offset

The `offset` style defines an offset for the position of the widget.

## Syntax

```
offset: <scalar> <scalar>;

offset-x: <scalar>;
offset-y: <scalar>
```

The two [`<scalar>`](../css_types/scalar.md) in the `offset` define, respectively, the offsets in the horizontal and vertical axes for the widget.

To specify an offset along a single axis, you can use `offset-x` and `offset-y`.

## Example

In this example, we have 3 widgets with differing offsets.

**offset.py**


```python
from textual.app import App
from textual.widgets import Label


class OffsetApp(App):
    CSS_PATH = "offset.tcss"

    def compose(self):
        yield Label("Paul (offset 8 2)", classes="paul")
        yield Label("Duncan (offset 4 10)", classes="duncan")
        yield Label("Chani (offset 0 -3)", classes="chani")


if __name__ == "__main__":
    app = OffsetApp()
    app.run()
```

**offset.tcss**


```css
Screen {
    background: white;
    color: black;
    layout: horizontal;
}
Label {
    width: 20;
    height: 10;
    content-align: center middle;
}

.paul {
    offset: 8 2;
    background: red 20%;
    border: outer red;
    color: red;
}

.duncan {
    offset: 4 10;
    background: green 20%;
    border: outer green;
    color: green;
}

.chani {
    offset: 0 -3;
    background: blue 20%;
    border: outer blue;
    color: blue;
}
```
## CSS

```css
/* Move the widget 8 cells in the x direction and 2 in the y direction */
offset: 8 2;

/* Move the widget 4 cells in the x direction
offset-x: 4;
/* Move the widget -3 cells in the y direction
offset-y: -3;
```

## Python

You cannot change programmatically the offset for a single axis.
You have to set the two axes at the same time.

```python
# Move the widget 2 cells in the x direction, and 4 in the y direction.
widget.styles.offset = (2, 4)
```

## See also

 - The [layout guide](../guide/layout.md#offsets) section on offsets.
