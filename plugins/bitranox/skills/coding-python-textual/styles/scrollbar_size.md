# Scrollbar-size

The `scrollbar-size` style defines the width of the scrollbars.

## Syntax

```
scrollbar-size: <integer> <integer>;
              # horizontal vertical

scrollbar-size-horizontal: <integer>;
scrollbar-size-vertical: <integer>;
```

The `scrollbar-size` style takes two [`<integer>`](../css_types/integer.md) to set the horizontal and vertical scrollbar sizes, respectively.
This customisable size is the width of the scrollbar, given that its length will always be 100% of the container.

The scrollbar widths may also be set individually with `scrollbar-size-horizontal` and `scrollbar-size-vertical`.

## Examples

### Basic usage

In this example we modify the size of the widget's scrollbar to be _much_ larger than usual.

**scrollbar_size.py**


```python
from textual.app import App
from textual.containers import ScrollableContainer
from textual.widgets import Label

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain.
"""


class ScrollbarApp(App):
    CSS_PATH = "scrollbar_size.tcss"

    def compose(self):
        yield ScrollableContainer(Label(TEXT * 5), classes="panel")


if __name__ == "__main__":
    app = ScrollbarApp()
    app.run()
```

**scrollbar_size.tcss**


```css
Screen {
    background: white;
    color: blue 80%;
    layout: horizontal;
}

Label {
    padding: 1 2;
    width: 200;
}

.panel {
    scrollbar-size: 10 4;
    padding: 1 2;
}
```
### Scrollbar sizes comparison

In the next example we show three containers with differently sized scrollbars.

> **Tip**
>
>
> If you want to hide the scrollbar but still allow the container to scroll
> using the mousewheel or keyboard, you can set the scrollbar size to `0`.


**scrollbar_size2.py**


```python
from textual.app import App
from textual.containers import Horizontal, ScrollableContainer
from textual.widgets import Label

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain.
"""


class ScrollbarApp(App):
    CSS_PATH = "scrollbar_size2.tcss"

    def compose(self):
        yield Horizontal(
            ScrollableContainer(Label(TEXT * 5), id="v1"),
            ScrollableContainer(Label(TEXT * 5), id="v2"),
            ScrollableContainer(Label(TEXT * 5), id="v3"),
        )


if __name__ == "__main__":
    app = ScrollbarApp()
    app.run()
```

**scrollbar_size2.tcss**


```css
ScrollableContainer {
    width: 1fr;
}

#v1 {
    scrollbar-size: 5 1;
    background: red 20%;
}

#v2 {
    scrollbar-size-vertical: 1;
    background: green 20%;
}

#v3 {
    scrollbar-size-horizontal: 5;
    background: blue 20%;
}
```
## CSS

```css
/* Set horizontal scrollbar to 10, and vertical scrollbar to 4 */
scrollbar-size: 10 4;

/* Set horizontal scrollbar to 10 */
scrollbar-size-horizontal: 10;

/* Set vertical scrollbar to 4 */
scrollbar-size-vertical: 4;
```

## Python

The style `scrollbar-size` has no Python equivalent.
The scrollbar sizes must be set independently:

```py
# Set horizontal scrollbar to 10:
widget.styles.scrollbar_size_horizontal = 10
# Set vertical scrollbar to 4:
widget.styles.scrollbar_size_vertical = 4
```

## See also

 - [`scrollbar-gutter`](./scrollbar_gutter.md) to reserve space for a vertical scrollbar.
 - [Scrollbar colors](./scrollbar_colors/index.md) to customize scrollbar appearance.
 - [`overflow`](./overflow.md) to control when scrollbars are displayed.
