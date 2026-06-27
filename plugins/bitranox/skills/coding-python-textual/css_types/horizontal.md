# <horizontal>

The `<horizontal>` CSS type represents a position along the horizontal axis.

## Syntax

The [`<horizontal>`](./horizontal.md) type can take any of the following values:

| Value            | Description                                  |
|------------------|----------------------------------------------|
| `center`         | Aligns in the center of the horizontal axis. |
| `left` (default) | Aligns on the left of the horizontal axis.   |
| `right`          | Aligns on the right of the horizontal axis.  |

## Examples

### CSS

```css
.container {
    align-horizontal: right;
}
```

### Python

```py
widget.styles.align_horizontal = "right"
```

## Used by

- [`align`](../styles/align.md) - Align style property
- [`border-subtitle-align`](../styles/border_subtitle_align.md) - Border subtitle alignment property
- [`border-title-align`](../styles/border_title_align.md) - Border title alignment property
- [`content-align`](../styles/content_align.md) - Content align style property
