# Link-style

The `link-style` style sets the text style for the link text.

> **Note**
>
>
> `link-style` only applies to Textual action links as described in the [actions guide](../../guide/actions.md#links) and not to regular hyperlinks.


## Syntax

```
link-style: <text-style>;
```

`link-style` will take all the values specified and will apply that styling to text that is enclosed by a Textual action link.

### Defaults

If not provided, a Textual action link will have `link-style` set to `underline`.

## Example

The example below shows some links with different styles applied to their text.
It also shows that `link-style` does not affect hyperlinks.

**link_style.py**


```python
from textual.app import App
from textual.widgets import Label


class LinkStyleApp(App):
    CSS_PATH = "link_style.tcss"

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
    app = LinkStyleApp()
    app.run()
```

2. This label has an "action link" that can be styled with `link-style`.
3. This label has an "action link" that can be styled with `link-style`.
4. This label has an "action link" that can be styled with `link-style`.

**link_style.tcss**


```css
#lbl1, #lbl2 {
    link-style: bold italic;  /* (1)! */
}

#lbl3 {
    link-style: reverse strike;
}

#lbl4 {
    link-style: bold;
}
```


## CSS

```css
link-style: bold;
link-style: bold italic reverse;
```

## Python

```py
widget.styles.link_style = "bold"
widget.styles.link_style = "bold italic reverse"
```

## See also

 - [`link-color`](./link_color.md) to set the color of link text.
 - [`link-background`](./link_background.md) to set the background color of link text.
 - [`link-style-hover`](./link_style_hover.md) to set the style of link text when the mouse pointer is over it.
 - [`text-style`](../text_style.md) to set the style of text in a widget.
