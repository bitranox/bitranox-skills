# Margin

The `margin` style specifies spacing around a widget.

## Syntax

```
margin: <integer>
      # one value for all edges
      | <integer> <integer>
      # top/bot   left/right
      | <integer> <integer> <integer> <integer>;
      # top       right     bot       left

margin-top: <integer>;
margin-right: <integer>;
margin-bottom: <integer>;
margin-left: <integer>;
```

The `margin` specifies spacing around the four edges of the widget equal to the [`<integer>`](../css_types/integer.md) specified.
The number of values given defines what edges get what margin:

 - 1 [`<integer>`](../css_types/integer.md) sets the same margin for the four edges of the widget;
 - 2 [`<integer>`](../css_types/integer.md) set margin for top/bottom and left/right edges, respectively.
 - 4 [`<integer>`](../css_types/integer.md) set margin for the top, right, bottom, and left edges, respectively.

> **Tip**
>
>
> To remember the order of the edges affected by the rule `margin` when it has 4 values, think of a clock.
> Its hand starts at the top and the goes clockwise: top, right, bottom, left.


Alternatively, margin can be set for each edge individually through the styles `margin-top`, `margin-right`, `margin-bottom`, and `margin-left`, respectively.

## Examples

### Basic usage

In the example below we add a large margin to a label, which makes it move away from the top-left corner of the screen.

**margin.py**


```python
from textual.app import App
from textual.widgets import Label

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class MarginApp(App):
    CSS_PATH = "margin.tcss"

    def compose(self):
        yield Label(TEXT)


if __name__ == "__main__":
    app = MarginApp()
    app.run()
```

**margin.tcss**


```css
Screen {
    background: white;
    color: black;
}

Label {
    margin: 4 8;
    background: blue 20%;
    border: blue wide;
    width: 100%;
}
```
### All margin settings

The next example shows a grid.
In each cell, we have a placeholder that has its margins set in different ways.

**margin_all.py**


```py
from textual.app import App
from textual.containers import Container, Grid
from textual.widgets import Placeholder


class MarginAllApp(App):
    CSS_PATH = "margin_all.tcss"

    def compose(self):
        yield Grid(
            Container(Placeholder("no margin", id="p1"), classes="bordered"),
            Container(Placeholder("margin: 1", id="p2"), classes="bordered"),
            Container(Placeholder("margin: 1 5", id="p3"), classes="bordered"),
            Container(Placeholder("margin: 1 1 2 6", id="p4"), classes="bordered"),
            Container(Placeholder("margin-top: 4", id="p5"), classes="bordered"),
            Container(Placeholder("margin-right: 3", id="p6"), classes="bordered"),
            Container(Placeholder("margin-bottom: 4", id="p7"), classes="bordered"),
            Container(Placeholder("margin-left: 3", id="p8"), classes="bordered"),
        )


if __name__ == "__main__":
    app = MarginAllApp()
    app.run()
```

**margin_all.tcss**


```css
Screen {
    background: $background;
}

Grid {
    grid-size: 4;
    grid-gutter: 1 2;
}

Placeholder {
    width: 100%;
    height: 100%;
}

Container {
    width: 100%;
    height: 100%;
}

.bordered {
    border: white round;
}

#p1 {
    /* default is no margin */
}

#p2 {
    margin: 1;
}

#p3 {
    margin: 1 5;
}

#p4 {
    margin: 1 1 2 6;
}

#p5 {
    margin-top: 4;
}

#p6 {
    margin-right: 3;
}

#p7 {
    margin-bottom: 4;
}

#p8 {
    margin-left: 3;
}
```
## CSS

```css
/* Set margin of 1 around all edges */
margin: 1;
/* Set margin of 2 on the top and bottom edges, and 4 on the left and right */
margin: 2 4;
/* Set margin of 1 on the top, 2 on the right,
                 3 on the bottom, and 4 on the left */
margin: 1 2 3 4;

margin-top: 1;
margin-right: 2;
margin-bottom: 3;
margin-left: 4;
```

## Python

Python does not provide the properties `margin-top`, `margin-right`, `margin-bottom`, and `margin-left`.
However, you _can_ set the margin to a single integer, a tuple of 2 integers, or a tuple of 4 integers:

```python
# Set margin of 1 around all edges
widget.styles.margin = 1
# Set margin of 2 on the top and bottom edges, and 4 on the left and right
widget.styles.margin = (2, 4)
# Set margin of 1 on top, 2 on the right, 3 on the bottom, and 4 on the left
widget.styles.margin = (1, 2, 3, 4)
```

## See also

 - [`padding`](./padding.md) to add spacing around the content of a widget.
 - [`box-sizing`](./box_sizing.md) to specify how to account for border and padding in a widget's dimensions.
