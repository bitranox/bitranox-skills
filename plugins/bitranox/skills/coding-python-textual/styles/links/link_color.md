# Link-color

The `link-color` style sets the color of the link text.

> **Note**
>
>
> `link-color` only applies to Textual action links as described in the [actions guide](../../guide/actions.md#links) and not to regular hyperlinks.


## Syntax

```
link-color: <color> [<percentage>];
```

`link-color` accepts a [`<color>`](../../css_types/color.md) (with an optional opacity level defined by a [`<percentage>`](../../css_types/percentage.md)) that is used to define the color of text enclosed in Textual action links.

## Example

The example below shows some links with their color changed.
It also shows that `link-color` does not affect hyperlinks.

**link_color.py**


```python
from textual.app import App
from textual.widgets import Label


class LinkColorApp(App):
    CSS_PATH = "link_color.tcss"

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
    app = LinkColorApp()
    app.run()
```

2. This label has an "action link" that can be styled with `link-color`.
3. This label has an "action link" that can be styled with `link-color`.
4. This label has an "action link" that can be styled with `link-color`.

**link_color.tcss**


```css
#lbl1, #lbl2 {
    link-color: red;  /* (1)! */
}

#lbl3 {
    link-color: hsl(60,100%,50%) 50%;
}

#lbl4 {
    link-color: $accent;
}
```


## CSS

```css
link-color: red 70%;
link-color: $accent;
```

## Python

```py
widget.styles.link_color = "red 70%"
widget.styles.link_color = "$accent"

# You can also use a `Color` object directly:
widget.styles.link_color = Color(100, 30, 173)
```

## See also

 - [`link-background`](./link_background.md) to set the background color of link text.
 - [`link-style`](./link_style.md) to set the text style of link text.
 - [`link-color-hover`](./link_color_hover.md) to set the color of link text when the mouse pointer is over it.
