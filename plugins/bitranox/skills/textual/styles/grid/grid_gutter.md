# Grid-gutter

The `grid-gutter` style sets the size of the gutter in the grid layout.
That is, it sets the space between adjacent cells in the grid.

Gutter is only applied _between_ the edges of cells.
No spacing is added between the edges of the cells and the edges of the container.

> **Note**
>
>
> This style only affects widgets with `layout: grid`.


## Syntax

```
grid-gutter: <integer> [<integer>];
```

The `grid-gutter` style takes one or two [`<integer>`](../../css_types/integer.md) that set the length of the gutter along the vertical and horizontal axes.
If only one [`<integer>`](../../css_types/integer.md) is supplied, it sets the vertical and horizontal gutters.
If two are supplied, they set the vertical and horizontal gutters, respectively.

## Example

The example below employs a common trick to apply visually consistent spacing around all grid cells.

**grid_gutter.py**


```py
from textual.app import App
from textual.containers import Grid
from textual.widgets import Label


class MyApp(App):
    CSS_PATH = "grid_gutter.tcss"

    def compose(self):
        yield Grid(
            Label("1"),
            Label("2"),
            Label("3"),
            Label("4"),
            Label("5"),
            Label("6"),
            Label("7"),
            Label("8"),
        )


if __name__ == "__main__":
    app = MyApp()
    app.run()
```

**grid_gutter.tcss**


```css
Grid {
    grid-size: 2 4;
    grid-gutter: 1 2;  /* (1)! */
}

Label {
    border: round white;
    content-align: center middle;
    width: 100%;
    height: 100%;
}
```


## CSS

```css
/* Set vertical and horizontal gutters to be the same */
grid-gutter: 5;

/* Set vertical and horizontal gutters separately */
grid-gutter: 1 2;
```

## Python

Vertical and horizontal gutters correspond to different Python properties, so they must be set separately:

```py
widget.styles.grid_gutter_vertical = "1"
widget.styles.grid_gutter_horizontal = "2"
```

## See also

 - [`grid-size`](./grid_size.md) to set the number of columns and rows in a grid.
 - [`grid-columns`](./grid_columns.md) to specify the width of grid columns.
 - [`grid-rows`](./grid_rows.md) to specify the height of grid rows.
 - [Layout guide](../../guide/layout.md#grid) for an in-depth look at the grid layout.
