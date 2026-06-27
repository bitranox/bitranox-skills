# Grid-size

The `grid-size` style sets the number of columns and rows in a grid layout.

The number of rows can be left unspecified and it will be computed automatically.

> **Note**
>
>
> This style only affects widgets with `layout: grid`.


## Syntax

```
grid-size: <integer> [<integer>];
```

The `grid-size` style takes one or two non-negative [`<integer>`](../../css_types/integer.md).
The first defines how many columns there are in the grid.
If present, the second one sets the number of rows – regardless of the number of children of the grid –, otherwise the number of rows is computed automatically.

## Examples

### Columns and rows

In the first example, we create a grid with 2 columns and 5 rows, although we do not have enough labels to fill in the whole grid:

**grid_size_both.py**


```py
from textual.app import App
from textual.containers import Grid
from textual.widgets import Label


class MyApp(App):
    CSS_PATH = "grid_size_both.tcss"

    def compose(self):
        yield Grid(
            Label("1"),
            Label("2"),
            Label("3"),
            Label("4"),
            Label("5"),
        )


if __name__ == "__main__":
    app = MyApp()
    app.run()
```

**grid_size_both.tcss**


```css
Grid {
    grid-size: 2 4;  /* (1)! */
}

Label {
    border: round white;
    content-align: center middle;
    width: 100%;
    height: 100%;
}
```


### Columns only

In the second example, we create a grid with 2 columns and however many rows are needed to display all of the grid children:

**grid_size_columns.py**


```py
from textual.app import App
from textual.containers import Grid
from textual.widgets import Label


class MyApp(App):
    CSS_PATH = "grid_size_columns.tcss"

    def compose(self):
        yield Grid(
            Label("1"),
            Label("2"),
            Label("3"),
            Label("4"),
            Label("5"),
        )


if __name__ == "__main__":
    app = MyApp()
    app.run()
```

**grid_size_columns.tcss**


```css
Grid {
    grid-size: 2;  /* (1)! */
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
/* Grid with 3 columns and 5 rows */
grid-size: 3 5;

/* Grid with 4 columns and as many rows as needed */
grid-size: 4;
```

## Python

To programmatically change the grid size, the number of rows and columns must be specified separately:

```py
widget.styles.grid_size_rows = 3
widget.styles.grid_size_columns = 6
```

## See also

 - [`grid-columns`](./grid_columns.md) to specify the width of grid columns.
 - [`grid-rows`](./grid_rows.md) to specify the height of grid rows.
 - [`grid-gutter`](./grid_gutter.md) to set the spacing between grid cells.
 - [`column-span`](./column_span.md) to make a widget span multiple columns.
 - [`row-span`](./row_span.md) to make a widget span multiple rows.
 - [Layout guide](../../guide/layout.md#grid) for an in-depth look at the grid layout.
