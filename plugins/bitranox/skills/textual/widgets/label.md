# Label

> **Tip: Added in version 0.5.0**


A widget which displays static text, but which can also contain more complex Rich renderables.

- [ ] Focusable
- [ ] Container

## Example

The example below shows how you can use a `Label` widget to display some text.

**label.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Label


class LabelApp(App):
    def compose(self) -> ComposeResult:
        yield Label("Hello, world!")


if __name__ == "__main__":
    app = LabelApp()
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

## See also

- [Static](./static.md) - The base class for Label
- [Pretty](./pretty.md) - Display pretty-formatted objects
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Label`*
