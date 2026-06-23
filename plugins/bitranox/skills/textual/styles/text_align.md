# Text-align

The `text-align` style sets the text alignment in a widget.

## Syntax

```
text-align: <text-align>;
```

The `text-align` style accepts a value of the type [`<text-align>`](../css_types/text_align.md) that defines how text is aligned inside the widget.

### Defaults

The default value is `start`.

## Example

This example shows, from top to bottom: `left`, `center`, `right`, and `justify` text alignments.

**text_align.py**


```python
from textual.app import App
from textual.containers import Grid
from textual.widgets import Label

TEXT = (
    "I must not fear. Fear is the mind-killer. Fear is the little-death that "
    "brings total obliteration. I will face my fear. I will permit it to pass over "
    "me and through me."
)


class TextAlign(App):
    CSS_PATH = "text_align.tcss"

    def compose(self):
        yield Grid(
            Label("[b]Left aligned[/]\n" + TEXT, id="one"),
            Label("[b]Center aligned[/]\n" + TEXT, id="two"),
            Label("[b]Right aligned[/]\n" + TEXT, id="three"),
            Label("[b]Justified[/]\n" + TEXT, id="four"),
        )


if __name__ == "__main__":
    app = TextAlign()
    app.run()
```

**text_align.tcss**


```css
#one {
    text-align: left;
    background: lightblue;
}

#two {
    text-align: center;
    background: indianred;
}

#three {
    text-align: right;
    background: palegreen;
}

#four {
    text-align: justify;
    background: palevioletred;
}

Label {
    padding: 1 2;
    height: 100%;
    color: auto;
}

Grid {
    grid-size: 2 2;
}
```

## CSS

```css
/* Set text in the widget to be right aligned */
text-align: right;
```

## Python

```python
# Set text in the widget to be right aligned
widget.styles.text_align = "right"
```

## See also

 - [`align`](./align.md) to set the alignment of children widgets inside a container.
 - [`content-align`](./content_align.md) to set the alignment of content inside a widget.
