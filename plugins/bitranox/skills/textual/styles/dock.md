# Dock

The `dock` style is used to fix a widget to the edge of a container (which may be the entire terminal window).

## Syntax

```
dock: bottom | left | right | top;
```

The option chosen determines the edge to which the widget is docked.

## Examples

### Basic usage

The example below shows a `left` docked sidebar.
Notice that even though the content is scrolled, the sidebar remains fixed.

**dock_layout1_sidebar.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static

TEXT = """\
Docking a widget removes it from the layout and fixes its position, aligned to either the top, right, bottom, or left edges of a container.

Docked widgets will not scroll out of view, making them ideal for sticky headers, footers, and sidebars.

"""


class DockLayoutExample(App):
    CSS_PATH = "dock_layout1_sidebar.tcss"

    def compose(self) -> ComposeResult:
        yield Static("Sidebar", id="sidebar")
        yield Static(TEXT * 10, id="body")


if __name__ == "__main__":
    app = DockLayoutExample()
    app.run()
```

**dock_layout1_sidebar.tcss**


```css
#sidebar {
    dock: left;
    width: 15;
    height: 100%;
    color: #0f2b41;
    background: dodgerblue;
}
```
### Advanced usage

The second example shows how one can use full-width or full-height containers to dock labels to the edges of a larger container.
The labels will remain in that position (docked) even if the container they are in scrolls horizontally and/or vertically.

**dock_all.py**


```py
from textual.app import App
from textual.containers import Container
from textual.widgets import Label


class DockAllApp(App):
    CSS_PATH = "dock_all.tcss"

    def compose(self):
        yield Container(
            Container(Label("left"), id="left"),
            Container(Label("top"), id="top"),
            Container(Label("right"), id="right"),
            Container(Label("bottom"), id="bottom"),
            id="big_container",
        )


if __name__ == "__main__":
    app = DockAllApp()
    app.run()
```

**dock_all.tcss**


```css
#left {
    dock: left;
    height: 100%;
    width: auto;
    align-vertical: middle;
}
#top {
    dock: top;
    height: auto;
    width: 100%;
    align-horizontal: center;
}
#right {
    dock: right;
    height: 100%;
    width: auto;
    align-vertical: middle;
}
#bottom {
    dock: bottom;
    height: auto;
    width: 100%;
    align-horizontal: center;
}

Screen {
    align: center middle;
}

#big_container {
    width: 75%;
    height: 75%;
    border: round white;
}
```
## CSS

```css
dock: bottom;  /* Docks on the bottom edge of the parent container. */
dock: left;    /* Docks on the   left edge of the parent container. */
dock: right;   /* Docks on the  right edge of the parent container. */
dock: top;     /* Docks on the    top edge of the parent container. */
```

## Python

```python
widget.styles.dock = "bottom"  # Dock bottom.
widget.styles.dock = "left"    # Dock   left.
widget.styles.dock = "right"   # Dock  right.
widget.styles.dock = "top"     # Dock    top.
```

## See also

 - The [layout guide](../guide/layout.md#docking) section on docking.
