# Row-span

The `row-span` style specifies how many rows a widget will span in a grid layout.

> **Note**
>
>
> This style only affects widgets that are direct children of a widget with `layout: grid`.


## Syntax

```
row-span: <integer>;
```

The `row-span` style accepts a single non-negative [`<integer>`](../../css_types/integer.md) that quantifies how many rows the given widget spans.

## Example

The example below shows a 4 by 4 grid where many placeholders span over several rows.

Notice that grid cells are filled from left to right, top to bottom.
After placing the placeholders `#p1`, `#p2`, `#p3`, and `#p4`, the next available cell is in the second row, fourth column, which is where the top of `#p5` is.

**row_span.py**


```py
from textual.app import App
from textual.containers import Grid
from textual.widgets import Placeholder


class MyApp(App):
    CSS_PATH = "row_span.tcss"

    def compose(self):
        yield Grid(
            Placeholder(id="p1"),
            Placeholder(id="p2"),
            Placeholder(id="p3"),
            Placeholder(id="p4"),
            Placeholder(id="p5"),
            Placeholder(id="p6"),
            Placeholder(id="p7"),
        )


if __name__ == "__main__":
    app = MyApp()
    app.run()
```

**row_span.tcss**


```css
#p1 {
    row-span: 4;
}
#p2 {
    row-span: 3;
}
#p3 {
    row-span: 2;
}
#p4 {
    row-span: 1;  /* Didn't need to be set explicitly. */
}
#p5 {
    row-span: 3;
}
#p6 {
    row-span: 2;
}
#p7 {
    /* Default value is 1. */
}

Grid {
    grid-size: 4 4;
    grid-gutter: 1 2;
}

Placeholder {
    height: 100%;
}
```
## CSS

```css
row-span: 3
```

## Python

```py
widget.styles.row_span = 3
```

## See also

 - [`column-span`](./column_span.md) to specify how many columns a widget spans.
 - [`grid-size`](./grid_size.md) to set the number of columns and rows in a grid.
 - [Layout guide](../../guide/layout.md#grid) for an in-depth look at the grid layout.
