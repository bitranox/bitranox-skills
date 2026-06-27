# Layer

The `layer` style defines the layer a widget belongs to.

## Syntax

```
layer: <name>;
```

The `layer` style accepts a [`<name>`](../css_types/name.md) that defines the layer this widget belongs to.
This [`<name>`](../css_types/name.md) must correspond to a [`<name>`](../css_types/name.md) that has been defined in a [`layers`](./layers.md) style by an ancestor of this widget.

More information on layers can be found in the [guide](../guide/layout.md#layers).

> **Warning**
>
>
> Using a `<name>` that hasn't been defined in a [`layers`](./layers.md) declaration of an ancestor of this widget has no effect.


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
/* Draw the widget on the layer called 'below' */
layer: below;
```

## Python

```python
# Draw the widget on the layer called 'below'
widget.styles.layer = "below"
```

## See also

 - The [layout guide](../guide/layout.md#layers) section on layers.
 - [`layers`](./layers.md) to define an ordered set of layers.
