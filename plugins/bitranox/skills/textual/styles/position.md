
# Position

The `position` style modifies what [`offset`](./offset.md) is applied to.
The default for `position` is `"relative"`, which means the offset is applied to the normal position of the widget.
In other words, if `offset` is (1, 1), then the widget will be moved 1 cell and 1 line down from its usual position.

The alternative value of `position` is `"absolute"`.
With absolute positioning, the offset is relative to the origin (i.e. the top left of the container).
So a widget with offset (1, 1) and absolute positioning will be 1 cell and 1 line down from the top left corner.

> **Note**
>
>
> Absolute positioning takes precedence over the parent's alignment rule.


## Syntax

```
position: <position>;
```
## Examples


Two labels, the first is absolute positioned and is displayed relative to the top left of the screen.
The second label is relative and is displayed offset from the center.

**position.py**


```py
from textual.app import App, ComposeResult
from textual.widgets import Label


class PositionApp(App):
    CSS_PATH = "position.tcss"

    def compose(self) -> ComposeResult:
        yield Label("Absolute", id="label1")
        yield Label("Relative", id="label2")


if __name__ == "__main__":
    app = PositionApp()
    app.run()
```

**position.tcss**


```css
Screen {
    align: center middle;
}

Label {
    padding: 1;
    background: $panel;
    border: thick $border;
}

Label#label1 {
    position: absolute;
    offset: 2 1;
}

Label#label2 {
    position: relative;
    offset: 2 1;
}
```
## CSS

```css
position: relative;
position: absolute;
```

## Python

```py
widget.styles.position = "relative"
widget.styles.position = "absolute"
```

## See also

 - [`offset`](./offset.md) to define an offset for a widget's position.
 - [`dock`](./dock.md) to fix a widget to the edge of a container.
