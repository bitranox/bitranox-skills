# Placeholder

> **Tip: Added in version 0.6.0**


A widget that is meant to have no complex functionality.
Use the placeholder widget when studying the layout of your app before having to develop your custom widgets.

The placeholder widget has variants that display different bits of useful information.
Clicking a placeholder will cycle through its variants.

- [ ] Focusable
- [ ] Container

## Example

The example below shows each placeholder variant.

**placeholder.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Placeholder


class PlaceholderApp(App):
    CSS_PATH = "placeholder.tcss"

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Container(
                Placeholder("This is a custom label for p1.", id="p1"),
                Placeholder("Placeholder p2 here!", id="p2"),
                Placeholder(id="p3"),
                Placeholder(id="p4"),
                Placeholder(id="p5"),
                Placeholder(),
                Horizontal(
                    Placeholder(variant="size", id="col1"),
                    Placeholder(variant="text", id="col2"),
                    Placeholder(variant="size", id="col3"),
                    id="c1",
                ),
                id="bot",
            ),
            Container(
                Placeholder(variant="text", id="left"),
                Placeholder(variant="size", id="topright"),
                Placeholder(variant="text", id="botright"),
                id="top",
            ),
            id="content",
        )


if __name__ == "__main__":
    app = PlaceholderApp()
    app.run()
```

**placeholder.tcss**


```css
Placeholder {
    height: 100%;
}

#top {
    height: 50%;
    width: 100%;
    layout: grid;
    grid-size: 2 2;
}

#left {
    row-span: 2;
}

#bot {
    height: 50%;
    width: 100%;
    layout: grid;
    grid-size: 8 8;
}

#c1 {
    row-span: 4;
    column-span: 8;
    height: 100%;
}

#col1, #col2, #col3 {
    width: 1fr;
}

#p1 {
    row-span: 4;
    column-span: 4;
}

#p2 {
    row-span: 2;
    column-span: 4;
}

#p3 {
    row-span: 2;
    column-span: 2;
}

#p4 {
    row-span: 1;
    column-span: 2;
}
```
## Reactive Attributes

| Name      | Type  | Default     | Description                                        |
|-----------|-------|-------------|----------------------------------------------------|
| `variant` | `str` | `"default"` | Styling variant. One of `default`, `size`, `text`. |


## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.

## See also

- [How to design a layout](../how-to/design-a-layout.md) - Guide on using placeholders to prototype layouts
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Placeholder`*
