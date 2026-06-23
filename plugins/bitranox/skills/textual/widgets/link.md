# Link

> **Tip: Added in version 0.84.0**


A widget to display a piece of text that opens a URL when clicked, like a web browser link.

- [x] Focusable
- [ ] Container


## Example

A trivial app with a link.
Clicking the link open's a web-browser&mdash;as you might expect!

**link.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Link


class LabelApp(App):
    AUTO_FOCUS = None
    CSS = """
    Screen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Link(
            "Go to textualize.io",
            url="https://textualize.io",
            tooltip="Click me",
        )


if __name__ == "__main__":
    app = LabelApp()
    app.run()
```
## Reactive Attributes

| Name   | Type  | Default | Description                               |
|--------|-------|---------|-------------------------------------------|
| `text` | `str` | `""`    | The text of the link.                     |
| `url`  | `str` | `""`    | The URL to open when the link is clicked. |


## Messages

This widget sends no messages.

## Bindings

The Link widget defines the following bindings:

*API reference: `textual.widgets.Link.BINDINGS`*


## Component classes

This widget contains no component classes.


## See also

- [Label](./label.md) - Display static text without a URL
- [Markdown](./markdown.md) - Render Markdown which can contain links
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Link`*
