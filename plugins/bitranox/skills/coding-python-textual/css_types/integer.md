# <integer>

The `<integer>` CSS type represents an integer number.

## Syntax

An [`<integer>`](./integer.md) is any valid integer number like `-10` or `42`.

> **Note**
>
>
> Some CSS rules may expect an `<integer>` within certain bounds. If that is the case, it will be noted in that rule.


## Examples

### CSS

```css
.classname {
    offset: 10 -20
}
```

### Python

In Python, a rule that expects a CSS type `<integer>` will expect a value of the type `int`:

```py
widget.styles.offset = (10, -20)
```

## Used by

- [`column-span`](../styles/grid/column_span.md) - Grid column span property
- [`grid-gutter`](../styles/grid/grid_gutter.md) - Grid gutter property
- [`grid-size`](../styles/grid/grid_size.md) - Grid size property
- [`margin`](../styles/margin.md) - Margin property
- [`padding`](../styles/padding.md) - Padding property
- [`row-span`](../styles/grid/row_span.md) - Grid row span property
- [`scrollbar-size`](../styles/scrollbar_size.md) - Scrollbar size property
