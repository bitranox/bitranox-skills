# Display

The `display` style defines whether a widget is displayed or not.

## Syntax

```
display: block | none;
```

### Values

| Value             | Description                                                              |
|-------------------|--------------------------------------------------------------------------|
| `block` (default) | Display the widget as normal.                                            |
| `none`            | The widget is not displayed and space will no longer be reserved for it. |

## Example

Note that the second widget is hidden by adding the `"remove"` class which sets the display style to `none`.

**display.py**


```python
from textual.app import App
from textual.widgets import Static


class DisplayApp(App):
    CSS_PATH = "display.tcss"

    def compose(self):
        yield Static("Widget 1")
        yield Static("Widget 2", classes="remove")
        yield Static("Widget 3")


if __name__ == "__main__":
    app = DisplayApp()
    app.run()
```

**display.tcss**


```css
Screen {
    background: green;
}

Static {
    height: 5;
    background: white;
    color: blue;
    border: heavy blue;
}

Static.remove {
    display: none;
}
```
## CSS

```css
/* Widget is shown */
display: block;

/* Widget is not shown */
display: none;
```

## Python

```python
# Hide the widget
self.styles.display = "none"

# Show the widget again
self.styles.display = "block"
```

There is also a shortcut to show / hide a widget. The `display` property on `Widget` may be set to `True` or `False` to show or hide the widget.

```python
# Hide the widget
widget.display = False

# Show the widget
widget.display = True
```

## See also

 - [`visibility`](./visibility.md) to specify whether a widget is visible or not.
