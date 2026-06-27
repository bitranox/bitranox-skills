# Grid-rows

The `grid-rows` style allows to define the height of the rows of the grid.

> **Note**
>
>
> This style only affects widgets with `layout: grid`.


## Syntax

```
grid-rows: <scalar>+;
```

The `grid-rows` style takes one or more [`<scalar>`](../../css_types/scalar.md) that specify the length of the rows of the grid.

If there are more rows in the grid than scalars specified in `grid-rows`, they are reused cyclically.
If the number of [`<scalar>`](../../css_types/scalar.md) is in excess, the excess is ignored.

## Example

The example below shows a grid with 10 labels laid out in a grid with 5 rows and 2 columns.

We set `grid-rows: 1fr 6 25%`.
Because there are more rows than scalars in the style definition, the scalars will be reused:

 - rows 1 and 4 have height `1fr`;
 - rows 2 and 5 have height `6`; and
 - row 3 has height `25%`.


**grid_rows.py**


```py
from textual.app import App
from textual.containers import Grid
from textual.widgets import Label


class MyApp(App):
    CSS_PATH = "grid_rows.tcss"

    def compose(self):
        yield Grid(
            Label("1fr"),
            Label("1fr"),
            Label("height = 6"),
            Label("height = 6"),
            Label("25%"),
            Label("25%"),
            Label("1fr"),
            Label("1fr"),
            Label("height = 6"),
            Label("height = 6"),
        )


if __name__ == "__main__":
    app = MyApp()
    app.run()
```

**grid_rows.tcss**


```css
Grid {
    grid-size: 2 5;
    grid-rows: 1fr 6 25%;
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
/* Set all rows to have 50% height */
grid-rows: 50%;

/* Every other row is twice as tall as the first one */
grid-rows: 1fr 2fr;
```

## Python

```py
grid.styles.grid_rows = "50%"
grid.styles.grid_rows = "1fr 2fr"
```

## See also

 - [`grid-columns`](./grid_columns.md) to specify the width of the grid columns.
 - [`grid-size`](./grid_size.md) to set the number of columns and rows in a grid.
 - [Layout guide](../../guide/layout.md#grid) for an in-depth look at the grid layout.
