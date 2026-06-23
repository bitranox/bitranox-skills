# Height

The `height` style sets a widget's height.

## Syntax

```
height: <scalar>;
```

The `height` style needs a [`<scalar>`](../css_types/scalar.md) to determine the vertical length of the widget.
By default, it sets the height of the content area, but if [`box-sizing`](./box_sizing.md) is set to `border-box` it sets the height of the border area.

## Examples

### Basic usage

This examples creates a widget with a height of 50% of the screen.

**height.py**


```python
from textual.app import App
from textual.widget import Widget


class HeightApp(App):
    CSS_PATH = "height.tcss"

    def compose(self):
        yield Widget()


if __name__ == "__main__":
    app = HeightApp()
    app.run()
```

**height.tcss**


```css
Screen > Widget {
    background: green;
    height: 50%;
    color: white;
}
```
### All height formats

The next example creates a series of wide widgets with heights set with different units.
Open the CSS file tab to see the comments that explain how each height is computed.
(The output includes a vertical ruler on the right to make it easier to check the height of each widget.)

**height_comparison.py**


```python
from textual.app import App
from textual.containers import VerticalScroll
from textual.widgets import Label, Placeholder, Static


class Ruler(Static):
    def compose(self):
        ruler_text = "·\n·\n·\n·\n•\n" * 100
        yield Label(ruler_text)


class HeightComparisonApp(App):
    CSS_PATH = "height_comparison.tcss"

    def compose(self):
        yield VerticalScroll(
            Placeholder(id="cells"),  # (1)!
            Placeholder(id="percent"),
            Placeholder(id="w"),
            Placeholder(id="h"),
            Placeholder(id="vw"),
            Placeholder(id="vh"),
            Placeholder(id="auto"),
            Placeholder(id="fr1"),
            Placeholder(id="fr2"),
        )
        yield Ruler()


if __name__ == "__main__":
    app = HeightComparisonApp()
    app.run()
```


**height_comparison.tcss**


```css
#cells {
    height: 2;       /* (1)! */
}
#percent {
    height: 12.5%;   /* (2)! */
}
#w {
    height: 5w;      /* (3)! */
}
#h {
    height: 12.5h;   /* (4)! */
}
#vw {
    height: 6.25vw;  /* (5)! */
}
#vh {
    height: 12.5vh;  /* (6)! */
}
#auto {
    height: auto;    /* (7)! */
}
#fr1 {
    height: 1fr;     /* (8)! */
}
#fr2 {
    height: 2fr;     /* (9)! */
}

Screen {
    layers: ruler;
    overflow: hidden;
}

Ruler {
    layer: ruler;
    dock: right;
    width: 1;
    background: $accent;
}
```

2. This sets the height to 12.5% of the space made available by the container. The container is 24 lines tall, so 12.5% of 24 is 3.
3. This sets the height to 5% of the width of the direct container, which is the `VerticalScroll` container. Because it expands to fit all of the terminal, the width of the `VerticalScroll` is 80 and 5% of 80 is 4.
4. This sets the height to 12.5% of the height of the direct container, which is the `VerticalScroll` container. Because it expands to fit all of the terminal, the height of the `VerticalScroll` is 24 and 12.5% of 24 is 3.
5. This sets the height to 6.25% of the viewport width, which is 80. 6.25% of 80 is 5.
6. This sets the height to 12.5% of the viewport height, which is 24. 12.5% of 24 is 3.
7. This sets the height of the placeholder to be the optimal size that fits the content without scrolling.
Because the content only spans one line, the placeholder has its height set to 1.
8. This sets the height to `1fr`, which means this placeholder will have half the height of a placeholder with `2fr`.
9. This sets the height to `2fr`, which means this placeholder will have twice the height of a placeholder with `1fr`.


## CSS

```css
/* Explicit cell height */
height: 10;

/* Percentage height */
height: 50%;

/* Automatic height */
height: auto
```

## Python

```python
self.styles.height = 10  # Explicit cell height can be an int
self.styles.height = "50%"
self.styles.height = "auto"
```

## See also

 - [`max-height`](./max_height.md) and [`min-height`](./min_height.md) to limit the height of a widget.
 - [`width`](./width.md) to set the width of a widget.
