# Border

The `border` style enables the drawing of a box around a widget.

A border style may also be applied to individual edges with `border-top`, `border-right`, `border-bottom`, and `border-left`.

> **Note**
>
>
> [`border`](./border.md) and [`outline`](./outline.md) cannot coexist in the same edge of a widget.


## Syntax

```
border: [<border>] [<color>] [<percentage>];

border-top: [<border>] [<color>] [<percentage>];
border-right: [<border>] [<color> [<percentage>]];
border-bottom: [<border>] [<color> [<percentage>]];
border-left: [<border>] [<color> [<percentage>]];
```

In CSS, the border is set with a [border style](./border.md) and a color. Both are optional. An optional percentage may be added to blend the border with the background color.

In Python, the border is set with a tuple of [border style](./border.md) and a color.


## Border command

The `textual` CLI has a subcommand which will let you explore the various border types interactively:

```
textual borders
```

Alternatively, you can see the examples below.

## Examples

### Basic usage

This examples shows three widgets with different border styles.

**border.py**


```python
from textual.app import App
from textual.widgets import Label


class BorderApp(App):
    CSS_PATH = "border.tcss"

    def compose(self):
        yield Label("My border is solid red", id="label1")
        yield Label("My border is dashed green", id="label2")
        yield Label("My border is tall blue", id="label3")


if __name__ == "__main__":
    app = BorderApp()
    app.run()
```

**border.tcss**


```css
#label1 {
    background: red 20%;
    color: red;
    border: solid red;
}

#label2 {
    background: green 20%;
    color: green;
    border: dashed green;
}

#label3 {
    background: blue 20%;
    color: blue;
    border: tall blue;
}

Screen {
    background: white;
}

Screen > Label {
    width: 100%;
    height: 5;
    content-align: center middle;
    color: white;
    margin: 1;
    box-sizing: border-box;
}
```
### All border types

The next example shows a grid with all the available border types.

**border_all.py**


```py
from textual.app import App
from textual.containers import Grid
from textual.widgets import Label


class AllBordersApp(App):
    CSS_PATH = "border_all.tcss"

    def compose(self):
        yield Grid(
            Label("ascii", id="ascii"),
            Label("blank", id="blank"),
            Label("dashed", id="dashed"),
            Label("double", id="double"),
            Label("heavy", id="heavy"),
            Label("hidden/none", id="hidden"),
            Label("hkey", id="hkey"),
            Label("inner", id="inner"),
            Label("outer", id="outer"),
            Label("panel", id="panel"),
            Label("round", id="round"),
            Label("solid", id="solid"),
            Label("tall", id="tall"),
            Label("thick", id="thick"),
            Label("vkey", id="vkey"),
            Label("wide", id="wide"),
        )


if __name__ == "__main__":
    app = AllBordersApp()
    app.run()
```

**border_all.tcss**


```css
#ascii {
    border: ascii $accent;
}

#blank {
    border: blank $accent;
}

#dashed {
    border: dashed $accent;
}

#double {
    border: double $accent;
}

#heavy {
    border: heavy $accent;
}

#hidden {
    border: hidden $accent;
}

#hkey {
    border: hkey $accent;
}

#inner {
    border: inner $accent;
}

#outer {
    border: outer $accent;
}

#panel {
    border: panel $accent;
}

#round {
    border: round $accent;
}

#solid {
    border: solid $accent;
}

#tall {
    border: tall $accent;
}

#thick {
    border: thick $accent;
}

#vkey {
    border: vkey $accent;
}

#wide {
    border: wide $accent;
}

Grid {
    grid-size: 4 4;
    align: center middle;
    grid-gutter: 1 2;
}

Label {
    width: 20;
    height: 3;
    content-align: center middle;
}
```
### Borders and outlines

The next example makes the difference between [`border`](../styles/border.md) and [`outline`](../styles/outline.md) clearer by having three labels side-by-side.
They contain the same text, have the same width and height, and are styled exactly the same up to their [`border`](../styles/border.md) and [`outline`](../styles/outline.md) styles.

This example also shows that a widget cannot contain both a `border` and an `outline`:

**outline_vs_border.py**


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


class OutlineBorderApp(App):
    CSS_PATH = "outline_vs_border.tcss"

    def compose(self):
        yield Label(TEXT, classes="outline")
        yield Label(TEXT, classes="border")
        yield Label(TEXT, classes="outline border")


if __name__ == "__main__":
    app = OutlineBorderApp()
    app.run()
```

**outline_vs_border.tcss**


```css
Label {
    height: 8;
}

.outline {
    outline: $error round;
}

.border {
    border: $success heavy;
}
```

## CSS

```css
/* Set a heavy white border */
border: heavy white;

/* Set a red border on the left */
border-left: outer red;

/* Set a rounded orange border, 50% opacity. */
border: round orange 50%;
```

## Python

```python
# Set a heavy white border
widget.styles.border = ("heavy", "white")

# Set a red border on the left
widget.styles.border_left = ("outer", "red")
```

## See also

 - [`<border>`](../css_types/border.md) for the accepted border style values.
 - [`box-sizing`](./box_sizing.md) to specify how to account for the border in a widget's dimensions.
 - [`outline`](./outline.md) to add an outline around the content of a widget.
- [`border-title-align`](./border_title_align.md) to set the title's alignment.
- [`border-title-color`](./border_title_color.md) to set the title's color.
- [`border-title-background`](./border_title_background.md) to set the title's background color.
- [`border-title-style`](./border_title_style.md) to set the title's text style.

- [`border-subtitle-align`](./border_subtitle_align.md) to set the sub-title's alignment.
- [`border-subtitle-color`](./border_subtitle_color.md) to set the sub-title's color.
- [`border-subtitle-background`](./border_subtitle_background.md) to set the sub-title's background color.
- [`border-subtitle-style`](./border_subtitle_style.md) to set the sub-title's text style.
