# Width

The `width` style sets a widget's width.

## Syntax

```
width: <scalar>;
```

The style `width` needs a [`<scalar>`](../css_types/scalar.md) to determine the horizontal length of the width.
By default, it sets the width of the content area, but if [`box-sizing`](./box_sizing.md) is set to `border-box` it sets the width of the border area.

## Examples

### Basic usage

This example adds a widget with 50% width of the screen.

**width.py**


```python
from textual.app import App
from textual.widget import Widget


class WidthApp(App):
    CSS_PATH = "width.tcss"

    def compose(self):
        yield Widget()


if __name__ == "__main__":
    app = WidthApp()
    app.run()
```

**width.tcss**


```css
Screen > Widget {
    background: green;
    width: 50%;
    color: white;
}
```
### All width formats

**width_comparison.py**


```python
from textual.app import App
from textual.containers import Horizontal
from textual.widgets import Label, Placeholder, Static


class Ruler(Static):
    def compose(self):
        ruler_text = "····•" * 100
        yield Label(ruler_text)


class WidthComparisonApp(App):
    CSS_PATH = "width_comparison.tcss"

    def compose(self):
        yield Horizontal(
            Placeholder(id="cells"),  # (1)!
            Placeholder(id="percent"),
            Placeholder(id="w"),
            Placeholder(id="h"),
            Placeholder(id="vw"),
            Placeholder(id="vh"),
            Placeholder(id="auto"),
            Placeholder(id="fr1"),
            Placeholder(id="fr3"),
        )
        yield Ruler()


if __name__ == "__main__":
    app = WidthComparisonApp()
    app.run()
```


**width_comparison.tcss**


```css
#cells {
    width: 9;      /* (1)! */
}
#percent {
    width: 12.5%;  /* (2)! */
}
#w {
    width: 10w;    /* (3)! */
}
#h {
    width: 25h;    /* (4)! */
}
#vw {
    width: 15vw;   /* (5)! */
}
#vh {
    width: 25vh;   /* (6)! */
}
#auto {
    width: auto;   /* (7)! */
}
#fr1 {
    width: 1fr;    /* (8)! */
}
#fr3 {
    width: 3fr;    /* (9)! */
}

Screen {
    layers: ruler;
}

Ruler {
    layer: ruler;
    dock: bottom;
    overflow: hidden;
    height: 1;
    background: $accent;
}
```

2. This sets the width to 12.5% of the space made available by the container.
The container is 80 columns wide, so 12.5% of 80 is 10.
3. This sets the width to 10% of the width of the direct container, which is the `Horizontal` container.
Because it expands to fit all of the terminal, the width of the `Horizontal` is 80 and 10% of 80 is 8.
4. This sets the width to 25% of the height of the direct container, which is the `Horizontal` container.
Because it expands to fit all of the terminal, the height of the `Horizontal` is 24 and 25% of 24 is 6.
5. This sets the width to 15% of the viewport width, which is 80.
15% of 80 is 12.
6. This sets the width to 25% of the viewport height, which is 24.
25% of 24 is 6.
7. This sets the width of the placeholder to be the optimal size that fits the content without scrolling.
Because the content is the string `"#auto"`, the placeholder has its width set to 5.
8. This sets the width to `1fr`, which means this placeholder will have a third of the width of a placeholder with `3fr`.
9. This sets the width to `3fr`, which means this placeholder will have triple the width of a placeholder with `1fr`.


## CSS

```css
/* Explicit cell width */
width: 10;

/* Percentage width */
width: 50%;

/* Automatic width */
width: auto;
```

## Python

```python
widget.styles.width = 10
widget.styles.width = "50%
widget.styles.width = "auto"
```

## See also

 - [`max-width`](./max_width.md) and [`min-width`](./min_width.md) to limit the width of a widget.
 - [`height`](./height.md) to set the height of a widget.
