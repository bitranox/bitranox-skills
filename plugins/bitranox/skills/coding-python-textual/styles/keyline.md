# Keyline

The `keyline` style is applied to a container and will draw lines around child widgets.

A keyline is superficially like the [border](./border.md) rule, but rather than draw inside the widget, a keyline is drawn outside of the widget's border. Additionally, unlike `border`, keylines can overlap and cross to create dividing lines between widgets.

Because keylines are drawn in the widget's margin, you will need to apply the [margin](./margin.md) or [grid-gutter](./grid/grid_gutter.md) rule to see the effect.


## Syntax

```
keyline: [<keyline>] [<color>];
```
## Examples

### Horizontal Keyline

The following examples shows a simple horizontal layout with a thin keyline.

**keyline.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Placeholder


class KeylineApp(App):
    CSS_PATH = "keyline_horizontal.tcss"

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Placeholder()
            yield Placeholder()
            yield Placeholder()


if __name__ == "__main__":
    app = KeylineApp()
    app.run()
```

**keyline.tcss**


```css
Placeholder {
    margin: 1;
    width: 1fr;
}

Horizontal {
    keyline: thin $secondary;
}
```
### Grid keyline

The following examples shows a grid layout with a *heavy* keyline.

**keyline.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Placeholder


class KeylineApp(App):
    CSS_PATH = "keyline.tcss"

    def compose(self) -> ComposeResult:
        with Grid():
            yield Placeholder(id="foo")
            yield Placeholder(id="bar")
            yield Placeholder()
            yield Placeholder(classes="hidden")
            yield Placeholder(id="baz")


if __name__ == "__main__":
    KeylineApp().run()
```

**keyline.tcss**


```css
Grid {
    grid-size: 3 3;
    grid-gutter: 1;
    padding: 2 3;
    keyline: heavy green;
}
Placeholder {
    height: 1fr;
}
.hidden {
    visibility: hidden;
}
#foo {
    column-span: 2;
}
#bar {
    row-span: 2;
}
#baz {
    column-span:3;
}
```
## CSS

```css
/* Set a thin green keyline */
/* Note: Must be set on a container or a widget with a layout. */
keyline: thin green;
```

## Python

You can set a keyline in Python with a tuple of type and color:

```python
widget.styles.keyline = ("thin", "green")
```
## See also

 - [`<keyline>`](../css_types/keyline.md) for the accepted keyline style values.
 - [`border`](./border.md) to add a border around a widget.
 - [`margin`](./margin.md) to add spacing around a widget (needed to see the keyline).
 - [Grid gutter](./grid/grid_gutter.md) to set spacing between grid cells.
