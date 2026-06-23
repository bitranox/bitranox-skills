# Scrollbar-visibility

The `scrollbar-visibility` is used to show or hide scrollbars.

If scrollbars are hidden, the user may still scroll the container using the mouse wheel / keys / and gestures, but
there will be no scrollbars shown.

## Syntax

```
scrollbar-visibility: hidden | visible;
```
### Values

| Value               | Description                                          |
|---------------------|------------------------------------------------------|
| `hidden`            | The widget's scrollbars will be hidden.              |
| `visible` (default) | The widget's scrollbars will be displayed as normal. |


## Examples

The following example contains two containers with the same text.
The container on the right has its scrollbar hidden.

**scrollbar_visibility.py**


```py
from textual.app import App
from textual.containers import Horizontal, VerticalScroll
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
    CSS_PATH = "scrollbar_visibility.tcss"

    def compose(self):
        yield Horizontal(
            VerticalScroll(Label(TEXT * 10), classes="left"),
            VerticalScroll(Label(TEXT * 10), classes="right"),
        )


if __name__ == "__main__":
    app = ScrollbarApp()
    app.run()
```

**scrollbar_visibility.tcss**


```css
VerticalScroll {
    width: 1fr;
}

.left {
    scrollbar-visibility: visible; # The default
}

.right {
    scrollbar-visibility: hidden;
}
```
## CSS

```css
scrollbar-visibility: visible;
scrollbar-visibility: hidden;
```
## Python

```py
widget.styles.scrollbar_visibility = "visible";
widget.styles.scrollbar_visibility = "hidden";
```

## See also

 - [`scrollbar-size`](./scrollbar_size.md) to set the dimensions of scrollbars.
 - [`overflow`](./overflow.md) to control when scrollbars are displayed.
