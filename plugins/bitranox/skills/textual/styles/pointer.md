# Pointer

The `pointer` style sets the shape of the mouse pointer (cursor) when it is over a widget.

> **Note**
>
> The `pointer` style requires terminal support for the Kitty pointer shapes protocol. Not all terminals support this feature. If your terminal does not support this protocol, the cursor shape will not change.


## Syntax

```
pointer: <pointer>;
```

The `pointer` style accepts a value of the type [`<pointer>`](../css_types/pointer.md) that defines the shape of the cursor when hovering over the widget.

### Defaults

The default value is `default`.

## Example

Many builtin widgets and scrollbars set the mouse pointer.

Run the Textual demo to see the mouse pointer change (hover over buttons or click and drag a scrollbar):

```
python -m textual
```

## CSS

```css
/* Show a pointing hand cursor */
pointer: pointer;

/* Show a text selection cursor */
pointer: text;

/* Show a grab cursor */
pointer: grab;

/* Show a crosshair cursor */
pointer: crosshair;
```

## Python

```python
# Show a pointing hand cursor
widget.styles.pointer = "pointer"

# Show a text selection cursor
widget.styles.pointer = "text"

# Show a grab cursor
widget.styles.pointer = "grab"

# Show a crosshair cursor
widget.styles.pointer = "crosshair"
```
## See also

 - [`<pointer>`](../css_types/pointer.md) data type for all available pointer shapes.
