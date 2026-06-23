# Static

A widget which displays static content.
Can be used for Rich renderables and can also be the base for other types of widgets.

- [ ] Focusable
- [ ] Container

## Example

The example below shows how you can use a `Static` widget as a simple text label (but see [Label](./label.md) as a way of displaying text).

**static.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class StaticApp(App):
    def compose(self) -> ComposeResult:
        yield Static("Hello, world!")


if __name__ == "__main__":
    app = StaticApp()
    app.run()
```
## Reactive Attributes

This widget has no reactive attributes.

## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.

## See Also

- [Label](./label.md) - A text label that extends Static
- [Pretty](./pretty.md) - Display pretty-formatted objects
- [Digits](./digits.md) - Display numbers in tall characters
- [Widgets guide](../guide/widgets.md) - How to build and use widgets


---


*API reference: `textual.widgets.Static`*
