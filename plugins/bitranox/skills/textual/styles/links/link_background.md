# Link-background

The `link-background` style sets the background color of the link.

> **Note**
>
>
> `link-background` only applies to Textual action links as described in the [actions guide](../../guide/actions.md#links) and not to regular hyperlinks.


## Syntax

```
link-background: <color> [<percentage>];
```

`link-background` accepts a [`<color>`](../../css_types/color.md) (with an optional opacity level defined by a [`<percentage>`](../../css_types/percentage.md)) that is used to define the background color of text enclosed in Textual action links.

## Example

The example below shows some links with their background color changed.
It also shows that `link-background` does not affect hyperlinks.

**link_background.py**


```python
from textual.app import App
from textual.widgets import Label


class LinkBackgroundApp(App):
    CSS_PATH = "link_background.tcss"

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
    app = LinkBackgroundApp()
    app.run()
```

2. This label has an "action link" that can be styled with `link-background`.
3. This label has an "action link" that can be styled with `link-background`.
4. This label has an "action link" that can be styled with `link-background`.

**link_background.tcss**


```css
#lbl1, #lbl2 {
    link-background: red;  /* (1)! */
}

#lbl3 {
    link-background: hsl(60,100%,50%) 50%;
}

#lbl4 {
    link-background: $accent;
}
```


## CSS

```css
link-background: red 70%;
link-background: $accent;
```

## Python

```py
widget.styles.link_background = "red 70%"
widget.styles.link_background = "$accent"

# You can also use a `Color` object directly:
widget.styles.link_background = Color(100, 30, 173)
```

## See also

 - [`link-color`](./link_color.md) to set the color of link text.
 - [`link-style`](./link_style.md) to set the text style of link text.
 - [`link-background-hover`](./link_background_hover.md) to set the background color of link text when the mouse pointer is over it.
