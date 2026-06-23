# Link-background-hover

The `link-background-hover` style sets the background color of the link when the mouse cursor is over the link.

> **Note**
>
>
> `link-background-hover` only applies to Textual action links as described in the [actions guide](../../guide/actions.md#links) and not to regular hyperlinks.


## Syntax

```
link-background-hover: <color> [<percentage>];
```

`link-background-hover` accepts a [`<color>`](../../css_types/color.md) (with an optional opacity level defined by a [`<percentage>`](../../css_types/percentage.md)) that is used to define the background color of text enclosed in Textual action links when the mouse pointer is over it.

### Defaults

If not provided, a Textual action link will have `link-background-hover` set to `$accent`.

## Example

The example below shows some links that have their background color changed when the mouse moves over it and it shows that there is a default color for `link-background-hover`.

It also shows that `link-background-hover` does not affect hyperlinks.

**Output**


![](./demos/link_background_hover_demo.gif)

> **Note**
>
>
> The GIF has reduced quality to make it easier to load in the documentation.
> Try running the example yourself with `textual run docs/examples/styles/link_background_hover.py`.


**link_background_hover.py**


```python
from textual.app import App
from textual.widgets import Label


class LinkHoverBackgroundApp(App):
    CSS_PATH = "link_background_hover.tcss"

    def compose(self):
        yield Label(
            "Visit the [link='https://textualize.io']Textualize[/link] website.",
            id="lbl1",  # (1)!
        )
        yield Label(
            "Click [@click=app.bell]here[/] for the bell sound.",
            id="lbl2",  # (2)!
        )
        yield Label(
            "You can also click [@click=app.bell]here[/] for the bell sound.",
            id="lbl3",  # (3)!
        )
        yield Label(
            "[@click=app.quit]Exit this application.[/]",
            id="lbl4",  # (4)!
        )


if __name__ == "__main__":
    app = LinkHoverBackgroundApp()
    app.run()
```

2. This label has an "action link" that can be styled with `link-background-hover`.
3. This label has an "action link" that can be styled with `link-background-hover`.
4. This label has an "action link" that can be styled with `link-background-hover`.

**link_background_hover.tcss**


```css
#lbl1, #lbl2 {
    link-background-hover: red;  /* (1)! */
}

#lbl3 {
    link-background-hover: hsl(60,100%,50%) 50%;
}

#lbl4 {
    /* Empty to show the default hover background */ /* (2)! */
}
```

2. The default behavior for links on hover is to change to a different background color, so we don't need to change anything if all we want is to add emphasis to the link under the mouse.


## CSS

```css
link-background-hover: red 70%;
link-background-hover: $accent;
```

## Python

```py
widget.styles.link_background_hover = "red 70%"
widget.styles.link_background_hover = "$accent"

# You can also use a `Color` object directly:
widget.styles.link_background_hover = Color(100, 30, 173)
```

## See also

 - [`link-background`](./link_background.md) to set the background color of link text.
 - [`link-color-hover`](./link_color_hover.md) to set the color of link text when the mouse pointer is over it.
 - [`link-style-hover`](./link_style_hover.md) to set the style of link text when the mouse pointer is over it.
