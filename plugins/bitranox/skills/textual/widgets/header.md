# Header

A simple header widget which docks itself to the top of the parent container.

> **Note**
>
>
> The application title which is shown in the header is taken from the ``title`` and ``sub_title`` of the application.


- [ ] Focusable
- [ ] Container

## Example

The example below shows an app with a `Header`.

**header.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Header


class HeaderApp(App):
    def compose(self) -> ComposeResult:
        yield Header()


if __name__ == "__main__":
    app = HeaderApp()
    app.run()
```
This example shows how to set the text in the `Header` using `App.title` and `App.sub_title`:

**header_app_title.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Header


class HeaderApp(App):
    def compose(self) -> ComposeResult:
        yield Header()

    def on_mount(self) -> None:
        self.title = "Header Application"
        self.sub_title = "With title and sub-title"


if __name__ == "__main__":
    app = HeaderApp()
    app.run()
```
## Reactive Attributes

| Name   | Type   | Default | Description                                                                                                                                                                                      |
|--------|--------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `tall` | `bool` | `True`  | Whether the `Header` widget is displayed as tall or not. The tall variant is 3 cells tall by default. The non-tall variant is a single cell tall. This can be toggled by clicking on the header. |

## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.

## See also

- [Footer](./footer.md) - A companion footer widget for the bottom of your app
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Header`*
