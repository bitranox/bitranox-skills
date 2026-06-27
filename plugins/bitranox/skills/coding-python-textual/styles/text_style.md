# Text-style

The `text-style` style sets the style for the text in a widget.

## Syntax

```
text-style: <text-style>;
```

`text-style` will take all the values specified and will apply that styling combination to the text in the widget.

## Examples

### Basic usage

Each of the three text panels has a different text style, respectively `bold`, `italic`, and `reverse`, from left to right.

**text_style.py**


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


class TextStyleApp(App):
    CSS_PATH = "text_style.tcss"

    def compose(self):
        yield Label(TEXT, id="lbl1")
        yield Label(TEXT, id="lbl2")
        yield Label(TEXT, id="lbl3")


if __name__ == "__main__":
    app = TextStyleApp()
    app.run()
```

**text_style.tcss**


```css
Screen {
    layout: horizontal;
}
Label {
    width: 1fr;
}
#lbl1 {
    background: red 30%;
    text-style: bold;
}
#lbl2 {
    background: green 30%;
    text-style: italic;
}
#lbl3 {
    background: blue 30%;
    text-style: reverse;
}
```
### All text styles

The next example shows all different text styles on their own, as well as some combinations of styles in a single widget.

**text_style_all.py**


```python
from textual.app import App
from textual.containers import Grid
from textual.widgets import Label

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class AllTextStyleApp(App):
    CSS_PATH = "text_style_all.tcss"

    def compose(self):
        yield Grid(
            Label("none\n" + TEXT, id="lbl1"),
            Label("bold\n" + TEXT, id="lbl2"),
            Label("italic\n" + TEXT, id="lbl3"),
            Label("reverse\n" + TEXT, id="lbl4"),
            Label("strike\n" + TEXT, id="lbl5"),
            Label("underline\n" + TEXT, id="lbl6"),
            Label("bold italic\n" + TEXT, id="lbl7"),
            Label("reverse strike\n" + TEXT, id="lbl8"),
        )


if __name__ == "__main__":
    app = AllTextStyleApp()
    app.run()
```

**text_style_all.tcss**


```css
#lbl1 {
    text-style: none;
}

#lbl2 {
    text-style: bold;
}

#lbl3 {
    text-style: italic;
}

#lbl4 {
    text-style: reverse;
}

#lbl5 {
    text-style: strike;
}

#lbl6 {
    text-style: underline;
}

#lbl7 {
    text-style: bold italic;
}

#lbl8 {
    text-style: reverse strike;
}

Grid {
    grid-size: 4;
    grid-gutter: 1 2;
    margin: 1 2;
    height: 100%;
}

Label {
    height: 100%;
}
```
## CSS

```css
text-style: italic;
```

## Python

```python
widget.styles.text_style = "italic"
```

## See also

 - [`<text-style>`](../css_types/text_style.md) for the accepted text style values.
 - [`color`](./color.md) to set the color of text in a widget.
