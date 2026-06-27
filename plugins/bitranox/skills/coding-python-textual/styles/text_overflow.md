# Text-overflow

The `text-overflow` style defines what happens when text *overflows*.

Text overflow occurs when there is not enough space to fit the text on a line.
This may happen if wrapping is disabled (via [text-wrap](./text_wrap.md)) or if a single word is too large to fit within the width of its container.

## Syntax

```
text-overflow: clip | fold | ellipsis;
```

### Values

| Value      | Description                                                                                          |
|------------|------------------------------------------------------------------------------------------------------|
| `clip`     | Overflowing text will be clipped (the overflow portion is removed from the output).                  |
| `fold`     | Overflowing text will fold on to the next line(s).                                                   |
| `ellipsis` | Overflowing text will be truncated and the last visible character will be replaced with an ellipsis. |


## Example

In the following example we show the output of each of the values of `text_overflow`.

The widgets all have [text wrapping](./text_wrap.md) disabled, which will cause the
example string to overflow as it is longer than the available width.

In the first (top) widget, `text-overflow` is set to "clip" which clips any text that is overflowing, resulting in a single line.

In the second widget, `text-overflow` is set to "fold", which causes the overflowing text to *fold* on to the next line.
When text folds like this, it won't respect word boundaries--so you may get words broken across lines.

In the third widget, `text-overflow` is set to "ellipsis", which is similar to "clip", but with the last character set to an ellipsis.
This option is useful to indicate to the user that there may be more text.

**text_overflow.py**


```py
from textual.app import App, ComposeResult
from textual.widgets import Static

TEXT = """I must not fear. Fear is the mind-killer. Fear is the little-death that brings total obliteration. I will face my fear."""


class WrapApp(App):
    CSS_PATH = "text_overflow.tcss"

    def compose(self) -> ComposeResult:
        yield Static(TEXT, id="static1")
        yield Static(TEXT, id="static2")
        yield Static(TEXT, id="static3")


if __name__ == "__main__":
    app = WrapApp()
    app.run()
```

**text_overflow.tcss**


```css
Static {
    height: 1fr;
    text-wrap: nowrap;
}

#static1 {
    text-overflow: clip;  # Overflowing text is clipped
    background: red 20%;
}
#static2 {
    text-overflow: fold;  # Overflowing text is folded on to the next line
    background: green 20%;
}
#static3 {
    text-overflow: ellipsis;  # Overflowing text is truncated with an ellipsis
    background: blue 20%;
}
```
### CSS

```css
#widget {
    text-overflow: ellipsis;
}
```

### Python

```py
widget.styles.text_overflow = "ellipsis"
```
## See also

 - [`text-wrap`](./text_wrap.md) which is used to enable or disable wrapping.
