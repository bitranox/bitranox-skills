# <percentage>

The `<percentage>` CSS type represents a percentage value.
It is often used to represent values that are relative to the parent's values.

> **Warning**
>
>
> Not to be confused with the [`<scalar>`](./scalar.md) type.


## Syntax

A [`<percentage>`](./percentage.md) is a [`<number>`](./number.md) followed by the percent sign `%` (without spaces).
Some rules may clamp the values between `0%` and `100%`.

## Examples

### CSS

```css
#footer {
    /* Integer followed by % */
    color: red 70%;

    /* The number can be negative/decimal, although that may not make sense */
    offset: -30% 12.5%;
}
```

### Python

```py
# Integer followed by %
widget.styles.color = "red 70%"

# The number can be negative/decimal, although that may not make sense
widget.styles.offset = ("-30%", "12.5%")
```

## Used by

- [`background`](../styles/background.md) - Background color opacity modifier
- [`background-tint`](../styles/background_tint.md) - Background tint opacity modifier
- [`border`](../styles/border.md) - Border color opacity modifier
- [`border-title-background`](../styles/border_title_background.md) - Border title background opacity modifier
- [`border-title-color`](../styles/border_title_color.md) - Border title color opacity modifier
- [`border-subtitle-background`](../styles/border_subtitle_background.md) - Border subtitle background opacity modifier
- [`border-subtitle-color`](../styles/border_subtitle_color.md) - Border subtitle color opacity modifier
- [`color`](../styles/color.md) - Text color opacity modifier
- [`hatch`](../styles/hatch.md) - Hatch color opacity modifier
- [`link-background`](../styles/links/link_background.md) - Link background opacity modifier
- [`link-background-hover`](../styles/links/link_background_hover.md) - Link background hover opacity modifier
- [`link-color`](../styles/links/link_color.md) - Link color opacity modifier
- [`link-color-hover`](../styles/links/link_color_hover.md) - Link color hover opacity modifier
- [`opacity`](../styles/opacity.md) - Opacity style property
- [`scrollbar-background`](../styles/scrollbar_colors/scrollbar_background.md) - Scrollbar background opacity modifier
- [`scrollbar-background-active`](../styles/scrollbar_colors/scrollbar_background_active.md) - Scrollbar background active opacity modifier
- [`scrollbar-background-hover`](../styles/scrollbar_colors/scrollbar_background_hover.md) - Scrollbar background hover opacity modifier
- [`scrollbar-color`](../styles/scrollbar_colors/scrollbar_color.md) - Scrollbar color opacity modifier
- [`scrollbar-color-active`](../styles/scrollbar_colors/scrollbar_color_active.md) - Scrollbar active color opacity modifier
- [`scrollbar-color-hover`](../styles/scrollbar_colors/scrollbar_color_hover.md) - Scrollbar hover color opacity modifier
- [`scrollbar-corner-color`](../styles/scrollbar_colors/scrollbar_corner_color.md) - Scrollbar corner color opacity modifier
- [`text-opacity`](../styles/text_opacity.md) - Text opacity style property
