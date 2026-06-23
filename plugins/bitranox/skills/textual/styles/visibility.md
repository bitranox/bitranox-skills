# Visibility

The `visibility` style determines whether a widget is visible or not.

## Syntax

```
visibility: hidden | visible;
```

`visibility` takes one of two values to set the visibility of a widget.

### Values

| Value               | Description                             |
|---------------------|-----------------------------------------|
| `hidden`            | The widget will be invisible.           |
| `visible` (default) | The widget will be displayed as normal. |

### Visibility inheritance

> **Note**
>
>
> Children of an invisible container _can_ be visible.


By default, children inherit the visibility of their parents.
So, if a container is set to be invisible, its children widgets will also be invisible by default.
However, those widgets can be made visible if their visibility is explicitly set to `visibility: visible`.
This is shown in the second example below.

## Examples

### Basic usage

Note that the second widget is hidden while leaving a space where it would have been rendered.

**visibility.py**


```python
from textual.app import App
from textual.widgets import Label


class VisibilityApp(App):
    CSS_PATH = "visibility.tcss"

    def compose(self):
        yield Label("Widget 1")
        yield Label("Widget 2", classes="invisible")
        yield Label("Widget 3")


if __name__ == "__main__":
    app = VisibilityApp()
    app.run()
```

**visibility.tcss**


```css
Screen {
    background: green;
}

Label {
    height: 5;
    width: 100%;
    background: white;
    color: blue;
    border: heavy blue;
}

Label.invisible {
    visibility: hidden;
}
```
### Overriding container visibility

The next example shows the interaction of the `visibility` style with invisible containers that have visible children.
The app below has three rows with a `Horizontal` container per row and three placeholders per row.
The containers all have a white background, and then:

 - the top container is visible by default (we can see the white background around the placeholders);
 - the middle container is invisible and the children placeholders inherited that setting;
 - the bottom container is invisible _but_ the children placeholders are visible because they were set to be visible.

**visibility_containers.py**


```python
from textual.app import App
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Placeholder


class VisibilityContainersApp(App):
    CSS_PATH = "visibility_containers.tcss"

    def compose(self):
        yield VerticalScroll(
            Horizontal(
                Placeholder(),
                Placeholder(),
                Placeholder(),
                id="top",
            ),
            Horizontal(
                Placeholder(),
                Placeholder(),
                Placeholder(),
                id="middle",
            ),
            Horizontal(
                Placeholder(),
                Placeholder(),
                Placeholder(),
                id="bot",
            ),
        )


if __name__ == "__main__":
    app = VisibilityContainersApp()
    app.run()
```

**visibility_containers.tcss**


```css
Horizontal {
    padding: 1 2;     /* (1)! */
    background: white;
    height: 1fr;
}

#top {}               /* (2)! */

#middle {             /* (3)! */
    visibility: hidden;
}

#bot {                /* (4)! */
    visibility: hidden;
}

#bot > Placeholder {  /* (5)! */
    visibility: visible;
}

Placeholder {
    width: 1fr;
}
```

2. The top `Horizontal` is visible by default, and so are its children.
3. The middle `Horizontal` is made invisible and its children will inherit that setting.
4. The bottom `Horizontal` is made invisible...
5. ... but its children override that setting and become visible.


## CSS

```css
/* Widget is invisible */
visibility: hidden;

/* Widget is visible */
visibility: visible;
```

## Python

```python
# Widget is invisible
self.styles.visibility = "hidden"

# Widget is visible
self.styles.visibility = "visible"
```

There is also a shortcut to set a Widget's visibility. The `visible` property on `Widget` may be set to `True` or `False`.

```python
# Make a widget invisible
widget.visible = False

# Make the widget visible again
widget.visible = True
```

## See also

 - [`display`](./display.md) to specify whether a widget is displayed or not.
