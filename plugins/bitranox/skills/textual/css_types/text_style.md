# <text-style>

The `<text-style>` CSS type represents styles that can be applied to text.

> **Warning**
>
>
> Not to be confused with the [`text-style`](../styles/text_style.md) CSS rule that sets the style of text in a widget.


## Syntax

A [`<text-style>`](./text_style.md) can be the value `none` for plain text with no styling,
or any _space-separated_ combination of the following values:

| Value       | Description                                                     |
|-------------|-----------------------------------------------------------------|
| `bold`      | **Bold text.**                                                  |
| `italic`    | _Italic text._                                                  |
| `reverse`   | Reverse video text (foreground and background colors reversed). |
| `strike`    | <s>Strikethrough text.</s>                                      |
| `underline` | <u>Underline text.</u>                                          |

## Examples

### CSS

```css
#label1 {
    /* You can specify any value by itself. */
    rule: strike;
}

#label2 {
    /* You can also combine multiple values. */
    rule: strike bold italic reverse;
}
```

### Python

```py
# You can specify any value by itself
widget.styles.text_style = "strike"

# You can also combine multiple values
widget.styles.text_style = "strike bold italic reverse"
```

## Used by

- [`border-subtitle-style`](../styles/border_subtitle_style.md) - Border subtitle text style property
- [`border-title-style`](../styles/border_title_style.md) - Border title text style property
- [`link-style`](../styles/links/link_style.md) - Link text style property
- [`link-style-hover`](../styles/links/link_style_hover.md) - Link hover text style property
- [`text-style`](../styles/text_style.md) - Text style property
