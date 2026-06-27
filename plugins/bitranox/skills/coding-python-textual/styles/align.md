# Align

The `align` style defines how a widget's *children* are aligned.

Apply this rule to a container to adjust where its children are positioned.

## Syntax

```
align: <horizontal> <vertical>;

align-horizontal: <horizontal>;
align-vertical: <vertical>;
```

The `align` style takes a [`<horizontal>`](../css_types/horizontal.md) followed by a [`<vertical>`](../css_types/vertical.md).

You can also set the alignment for each axis individually with `align-horizontal` and `align-vertical`.

## Examples

### Basic usage

This example contains a simple app with two labels centered on the screen with `align: center middle;`:

**align.py**


```python
from textual.app import App
from textual.widgets import Label


class AlignApp(App):
    CSS_PATH = "align.tcss"

    def compose(self):
        yield Label("Vertical alignment with [b]Textual[/]", classes="box")
        yield Label("Take note, browsers.", classes="box")


if __name__ == "__main__":
    app = AlignApp()
    app.run()
```

**align.tcss**


```css
Screen {
    align: center middle;
}

.box {
    width: 40;
    height: 5;
    margin: 1;
    padding: 1;
    background: green;
    color: white 90%;
    border: heavy white;
}
```
### All alignments

The next example shows a 3 by 3 grid of containers with text labels.
Each label has been aligned differently inside its container, and its text shows its `align: ...` value.

**align_all.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Label


class AlignAllApp(App):
    """App that illustrates all alignments."""

    CSS_PATH = "align_all.tcss"

    def compose(self) -> ComposeResult:
        yield Container(Label("left top"), id="left-top")
        yield Container(Label("center top"), id="center-top")
        yield Container(Label("right top"), id="right-top")
        yield Container(Label("left middle"), id="left-middle")
        yield Container(Label("center middle"), id="center-middle")
        yield Container(Label("right middle"), id="right-middle")
        yield Container(Label("left bottom"), id="left-bottom")
        yield Container(Label("center bottom"), id="center-bottom")
        yield Container(Label("right bottom"), id="right-bottom")


if __name__ == "__main__":
    AlignAllApp().run()
```

**align_all.tcss**


```css
#left-top {
    /* align: left top; this is the default value and is implied. */
}

#center-top {
    align: center top;
}

#right-top {
    align: right top;
}

#left-middle {
    align: left middle;
}

#center-middle {
    align: center middle;
}

#right-middle {
    align: right middle;
}

#left-bottom {
    align: left bottom;
}

#center-bottom {
    align: center bottom;
}

#right-bottom {
    align: right bottom;
}

Screen {
    layout: grid;
    grid-size: 3 3;
    grid-gutter: 1;
}

Container {
    background: $boost;
    border: solid gray;
    height: 100%;
}

Label {
    width: auto;
    height: 1;
    background: $accent;
}
```
## CSS

```css
/* Align child widgets to the center. */
align: center middle;
/* Align child widget to the top right */
align: right top;

/* Change the horizontal alignment of the children of a widget */
align-horizontal: right;
/* Change the vertical alignment of the children of a widget */
align-vertical: middle;
```

## Python
```python
# Align child widgets to the center
widget.styles.align = ("center", "middle")
# Align child widgets to the top right
widget.styles.align = ("right", "top")

# Change the horizontal alignment of the children of a widget
widget.styles.align_horizontal = "right"
# Change the vertical alignment of the children of a widget
widget.styles.align_vertical = "middle"
```

## See also

 - [`content-align`](./content_align.md) to set the alignment of content inside a widget.
 - [`text-align`](./text_align.md) to set the alignment of text in a widget.
