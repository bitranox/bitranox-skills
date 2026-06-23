# Column-span

The `column-span` style specifies how many columns a widget will span in a grid layout.

> **Note**
>
>
> This style only affects widgets that are direct children of a widget with `layout: grid`.


## Syntax

```
column-span: <integer>;
```

The `column-span` style accepts a single non-negative [`<integer>`](../../css_types/integer.md) that quantifies how many columns the given widget spans.

## Example

The example below shows a 4 by 4 grid where many placeholders span over several columns.

**column_span.py**


```py
from textual.app import App
from textual.containers import Grid
from textual.widgets import Placeholder


class MyApp(App):
    CSS_PATH = "column_span.tcss"

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

**column_span.tcss**


```css
#p1 {
    column-span: 4;
}
#p2 {
    column-span: 3;
}
#p3 {
    column-span: 1;  /* Didn't need to be set explicitly. */
}
#p4 {
    column-span: 2;
}
#p5 {
    column-span: 2;
}
#p6 {
    /* Default value is 1. */
}
#p7 {
    column-span: 3;
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
column-span: 3;
```

## Python

```py
widget.styles.column_span = 3
```

## See also

 - [`row-span`](./row_span.md) to specify how many rows a widget spans.
 - [`grid-size`](./grid_size.md) to set the number of columns and rows in a grid.
 - [Layout guide](../../guide/layout.md#grid) for an in-depth look at the grid layout.
