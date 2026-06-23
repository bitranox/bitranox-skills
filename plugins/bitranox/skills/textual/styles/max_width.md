# Max-width

The `max-width` style sets a maximum width for a widget.

## Syntax

```
max-width: <scalar>;
```

The `max-width` style accepts a [`<scalar>`](../css_types/scalar.md) that defines an upper bound for the [`width`](./width.md) of a widget.
That is, the width of a widget is never allowed to exceed `max-width`.

## Example

The example below shows some placeholders that were defined to span horizontally from the left edge of the terminal to the right edge.
Then, we set `max-width` individually on each placeholder.

**max_width.py**


```py
from textual.app import App
from textual.containers import VerticalScroll
from textual.widgets import Placeholder


class MaxWidthApp(App):
    CSS_PATH = "max_width.tcss"

    def compose(self):
        yield VerticalScroll(
            Placeholder("max-width: 50h", id="p1"),
            Placeholder("max-width: 999", id="p2"),
            Placeholder("max-width: 50%", id="p3"),
            Placeholder("max-width: 30", id="p4"),
        )


if __name__ == "__main__":
    app = MaxWidthApp()
    app.run()
```

**max_width.tcss**


```css
Horizontal {
    height: 100%;
    width: 100%;
}

Placeholder {
    width: 100%;
    height: 1fr;
}

#p1 {
    max-width: 50h;
}

#p2 {
    max-width: 999;  /* (1)! */
}

#p3 {
    max-width: 50%;
}

#p4 {
    max-width: 30;
}
```


## CSS

```css
/* Set the maximum width to 10 rows */
max-width: 10;

/* Set the maximum width to 25% of the viewport width */
max-width: 25vw;
```

## Python

```python
# Set the maximum width to 10 rows
widget.styles.max_width = 10

# Set the maximum width to 25% of the viewport width
widget.styles.max_width = "25vw"
```

## See also

 - [`min-width`](./min_width.md) to set a lower bound on the width of a widget.
 - [`width`](./width.md) to set the width of a widget.
