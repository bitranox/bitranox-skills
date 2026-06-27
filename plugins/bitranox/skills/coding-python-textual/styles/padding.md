# Padding

The `padding` style specifies spacing around the content of a widget.

## Syntax

```
padding: <integer> # one value for all edges
       | <integer> <integer>
       # top/bot   left/right
       | <integer> <integer> <integer> <integer>;
       # top       right     bot       left

padding-top: <integer>;
padding-right: <integer>;
padding-bottom: <integer>;
padding-left: <integer>;
```

The `padding` specifies spacing around the _content_ of a widget, thus this spacing is added _inside_ the widget.
The values of the [`<integer>`](../css_types/integer.md) determine how much spacing is added and the number of values define what edges get what padding:

 - 1 [`<integer>`](../css_types/integer.md) sets the same padding for the four edges of the widget;
 - 2 [`<integer>`](../css_types/integer.md) set padding for top/bottom and left/right edges, respectively.
 - 4 [`<integer>`](../css_types/integer.md) set padding for the top, right, bottom, and left edges, respectively.

> **Tip**
>
>
> To remember the order of the edges affected by the rule `padding` when it has 4 values, think of a clock.
> Its hand starts at the top and then goes clockwise: top, right, bottom, left.


Alternatively, padding can be set for each edge individually through the rules `padding-top`, `padding-right`, `padding-bottom`, and `padding-left`, respectively.

## Example

### Basic usage

This example adds padding around some text.

**padding.py**


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


class PaddingApp(App):
    CSS_PATH = "padding.tcss"

    def compose(self):
        yield Label(TEXT)


if __name__ == "__main__":
    app = PaddingApp()
    app.run()
```

**padding.tcss**


```css
Screen {
    background: white;
    color: blue;
}

Label {
    padding: 4 8;
    background: blue 20%;
    width: 100%;
}
```
### All padding settings

The next example shows a grid.
In each cell, we have a placeholder that has its padding set in different ways.
The effect of each padding setting is noticeable in the colored background around the text of each placeholder.

**padding_all.py**


```py
from textual.app import App
from textual.containers import Grid
from textual.widgets import Placeholder


class PaddingAllApp(App):
    CSS_PATH = "padding_all.tcss"

    def compose(self):
        yield Grid(
            Placeholder("no padding", id="p1"),
            Placeholder("padding: 1", id="p2"),
            Placeholder("padding: 1 5", id="p3"),
            Placeholder("padding: 1 1 2 6", id="p4"),
            Placeholder("padding-top: 4", id="p5"),
            Placeholder("padding-right: 3", id="p6"),
            Placeholder("padding-bottom: 4", id="p7"),
            Placeholder("padding-left: 3", id="p8"),
        )


if __name__ == "__main__":
    app = PaddingAllApp()
    app.run()
```

**padding_all.tcss**


```css
Screen {
    background: $background;
}

Grid {
    grid-size: 4;
    grid-gutter: 1 2;
}

Placeholder {
    width: auto;
    height: auto;
}

#p1 {
    /* default is no padding */
}

#p2 {
    padding: 1;
}

#p3 {
    padding: 1 5;
}

#p4 {
    padding: 1 1 2 6;
}

#p5 {
    padding-top: 4;
}

#p6 {
    padding-right: 3;
}

#p7 {
    padding-bottom: 4;
}

#p8 {
    padding-left: 3;
}
```
## CSS

```css
/* Set padding of 1 around all edges */
padding: 1;
/* Set padding of 2 on the top and bottom edges, and 4 on the left and right */
padding: 2 4;
/* Set padding of 1 on the top, 2 on the right,
                 3 on the bottom, and 4 on the left */
padding: 1 2 3 4;

padding-top: 1;
padding-right: 2;
padding-bottom: 3;
padding-left: 4;
```

## Python

In Python, you cannot set any of the individual `padding` styles `padding-top`, `padding-right`, `padding-bottom`, and `padding-left`.

However, you _can_ set padding to a single integer, a tuple of 2 integers, or a tuple of 4 integers:

```python
# Set padding of 1 around all edges
widget.styles.padding = 1
# Set padding of 2 on the top and bottom edges, and 4 on the left and right
widget.styles.padding = (2, 4)
# Set padding of 1 on top, 2 on the right, 3 on the bottom, and 4 on the left
widget.styles.padding = (1, 2, 3, 4)
```

## See also

 - [`box-sizing`](./box_sizing.md) to specify how to account for padding in a widget's dimensions.
 - [`margin`](./margin.md) to add spacing around a widget.
