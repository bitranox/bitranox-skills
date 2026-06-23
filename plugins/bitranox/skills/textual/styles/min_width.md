# Min-width

The `min-width` style sets a minimum width for a widget.

## Syntax

```
min-width: <scalar>;
```

The `min-width` style accepts a [`<scalar>`](../css_types/scalar.md) that defines a lower bound for the [`width`](./width.md) of a widget.
That is, the width of a widget is never allowed to be under `min-width`.

## Example

The example below shows some placeholders with their width set to `50%`.
Then, we set `min-width` individually on each placeholder.

**min_width.py**


```py
from textual.app import App
from textual.containers import VerticalScroll
from textual.widgets import Placeholder


class MinWidthApp(App):
    CSS_PATH = "min_width.tcss"

    def compose(self):
        yield VerticalScroll(
            Placeholder("min-width: 25%", id="p1"),
            Placeholder("min-width: 75%", id="p2"),
            Placeholder("min-width: 100", id="p3"),
            Placeholder("min-width: 400h", id="p4"),
        )


if __name__ == "__main__":
    app = MinWidthApp()
    app.run()
```

**min_width.tcss**


```css
VerticalScroll {
    height: 100%;
    width: 100%;
    overflow-x: auto;
}

Placeholder {
    height: 1fr;
    width: 50%;
}

#p1 {
    min-width: 25%;
    /* (1)! */
}

#p2 {
    min-width: 75%;
}

#p3 {
    min-width: 100;
}

#p4 {
    min-width: 400h;
}
```


## CSS

```css
/* Set the minimum width to 10 rows */
min-width: 10;

/* Set the minimum width to 25% of the viewport width */
min-width: 25vw;
```

## Python

```python
# Set the minimum width to 10 rows
widget.styles.min_width = 10

# Set the minimum width to 25% of the viewport width
widget.styles.min_width = "25vw"
```

## See also

 - [`max-width`](./max_width.md) to set an upper bound on the width of a widget.
 - [`width`](./width.md) to set the width of a widget.
