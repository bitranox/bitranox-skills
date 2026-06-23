# Layout

The `layout` style defines how a widget arranges its children.

## Syntax

```
layout: grid | horizontal | vertical;
```

The `layout` style takes an option that defines how child widgets will be arranged, as per the table shown below.

### Values

| Value                | Description                                                                   |
|----------------------|-------------------------------------------------------------------------------|
| `grid`               | Child widgets will be arranged in a grid.                                     |
| `horizontal`         | Child widgets will be arranged along the horizontal axis, from left to right. |
| `vertical` (default) | Child widgets will be arranged along the vertical axis, from top to bottom.   |

See the [layout](../guide/layout.md) guide for more information.

## Example

Note how the `layout` style affects the arrangement of widgets in the example below.
To learn more about the grid layout, you can see the [layout guide](../guide/layout.md) or the [grid reference](./grid/index.md).

**layout.py**


```python
from textual.app import App
from textual.containers import Container
from textual.widgets import Label


class LayoutApp(App):
    CSS_PATH = "layout.tcss"

    def compose(self):
        yield Container(
            Label("Layout"),
            Label("Is"),
            Label("Vertical"),
            id="vertical-layout",
        )
        yield Container(
            Label("Layout"),
            Label("Is"),
            Label("Horizontal"),
            id="horizontal-layout",
        )


if __name__ == "__main__":
    app = LayoutApp()
    app.run()
```

**layout.tcss**


```css
#vertical-layout {
    layout: vertical;
    background: darkmagenta;
    height: auto;
}

#horizontal-layout {
    layout: horizontal;
    background: darkcyan;
    height: auto;
}

Label {
    margin: 1;
    width: 12;
    color: black;
    background: yellowgreen;
}
```
## CSS

```css
layout: horizontal;
```

## Python

```python
widget.styles.layout = "horizontal"
```

## See also

 - [Layout guide](../guide/layout.md).
 - [Grid reference](./grid/index.md).
