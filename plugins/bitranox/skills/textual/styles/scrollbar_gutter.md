# Scrollbar-gutter

The `scrollbar-gutter` style allows reserving space for a vertical scrollbar.

## Syntax

```
scrollbar-gutter: auto | stable;
```

### Values

| Value            | Description                                    |
|------------------|------------------------------------------------|
| `auto` (default) | No space is reserved for a vertical scrollbar. |
| `stable`         | Space is reserved for a vertical scrollbar.    |

Setting the value to `stable` prevents unwanted layout changes when the scrollbar becomes visible, whereas the default value of `auto` means that the layout of your application is recomputed when a vertical scrollbar becomes needed.

## Example

In the example below, notice the gap reserved for the scrollbar on the right side of the
terminal window.

**scrollbar_gutter.py**


```python
from textual.app import App
from textual.widgets import Static

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class ScrollbarGutterApp(App):
    CSS_PATH = "scrollbar_gutter.tcss"

    def compose(self):
        yield Static(TEXT, id="text-box")


if __name__ == "__main__":
    app = ScrollbarGutterApp()
    app.run()
```

**scrollbar_gutter.tcss**


```css
Screen {
    scrollbar-gutter: stable;
}

#text-box {
    color: floralwhite;
    background: darkmagenta;
}
```
## CSS

```css
scrollbar-gutter: auto;    /* Don't reserve space for a vertical scrollbar. */
scrollbar-gutter: stable;  /* Reserve space for a vertical scrollbar. */
```

## Python

```python
self.styles.scrollbar_gutter = "auto"    # Don't reserve space for a vertical scrollbar.
self.styles.scrollbar_gutter = "stable"  # Reserve space for a vertical scrollbar.
```

## See also

 - [`scrollbar-size`](./scrollbar_size.md) to set the dimensions of scrollbars.
 - [Scrollbar colors](./scrollbar_colors/index.md) to customize scrollbar appearance.
 - [`overflow`](./overflow.md) to control when scrollbars are displayed.
