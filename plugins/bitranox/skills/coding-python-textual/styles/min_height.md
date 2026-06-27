# Min-height

The `min-height` style sets a minimum height for a widget.

## Syntax

```
min-height: <scalar>;
```

The `min-height` style accepts a [`<scalar>`](../css_types/scalar.md) that defines a lower bound for the [`height`](./height.md) of a widget.
That is, the height of a widget is never allowed to be under `min-height`.

## Example

The example below shows some placeholders with their height set to `50%`.
Then, we set `min-height` individually on each placeholder.

**min_height.py**


```py
from textual.app import App
from textual.containers import Horizontal
from textual.widgets import Placeholder


class MinHeightApp(App):
    CSS_PATH = "min_height.tcss"

    def compose(self):
        yield Horizontal(
            Placeholder("min-height: 25%", id="p1"),
            Placeholder("min-height: 75%", id="p2"),
            Placeholder("min-height: 30", id="p3"),
            Placeholder("min-height: 40w", id="p4"),
        )


if __name__ == "__main__":
    app = MinHeightApp()
    app.run()
```

**min_height.tcss**


```css
Horizontal {
    height: 100%;
    width: 100%;
    overflow-y: auto;
}

Placeholder {
    width: 1fr;
    height: 50%;
}

#p1 {
    min-height: 25%;  /* (1)! */
}

#p2 {
    min-height: 75%;
}

#p3 {
    min-height: 30;
}

#p4 {
    min-height: 40w;
}
```


## CSS

```css
/* Set the minimum height to 10 rows */
min-height: 10;

/* Set the minimum height to 25% of the viewport height */
min-height: 25vh;
```

## Python

```python
# Set the minimum height to 10 rows
widget.styles.min_height = 10

# Set the minimum height to 25% of the viewport height
widget.styles.min_height = "25vh"
```

## See also

 - [`max-height`](./max_height.md) to set an upper bound on the height of a widget.
 - [`height`](./height.md) to set the height of a widget.
