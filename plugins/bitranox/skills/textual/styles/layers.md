# Layers

The `layers` style allows you to define an ordered set of layers.

## Syntax

```
layers: <name>+;
```

The `layers` style accepts one or more [`<name>`](../css_types/name.md) that define the layers that the widget is aware of, and the order in which they will be painted on the screen.

The values used here can later be referenced using the [`layer`](./layer.md) property.
The layers defined first in the list are drawn under the layers that are defined later in the list.

More information on layers can be found in the [guide](../guide/layout.md#layers).

## Example

In the example below, `#box1` is yielded before `#box2`.
However, since `#box1` is on the higher layer, it is drawn on top of `#box2`.


**layers.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class LayersExample(App):
    CSS_PATH = "layers.tcss"

    def compose(self) -> ComposeResult:
        yield Static("box1 (layer = above)", id="box1")
        yield Static("box2 (layer = below)", id="box2")


if __name__ == "__main__":
    app = LayersExample()
    app.run()
```

**layers.tcss**


```css
Screen {
    align: center middle;
    layers: below above;
}

Static {
    width: 28;
    height: 8;
    color: auto;
    content-align: center middle;
}

#box1 {
    layer: above;
    background: darkcyan;
}

#box2 {
    layer: below;
    background: orange;
    offset: 12 6;
}
```
## CSS

```css
/* Bottom layer is called 'below', layer above it is called 'above' */
layers: below above;
```

## Python

```python
# Bottom layer is called 'below', layer above it is called 'above'
widget.style.layers = ("below", "above")
```

## See also

 - The [layout guide](../guide/layout.md#layers) section on layers.
 - [`layer`](./layer.md) to set the layer a widget belongs to.
