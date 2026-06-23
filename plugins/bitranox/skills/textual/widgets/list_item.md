# ListItem

> **Tip: Added in version 0.6.0**


`ListItem` is the type of the elements in a `ListView`.

- [ ] Focusable
- [ ] Container

## Example

The example below shows an app with a simple `ListView`, consisting
of multiple `ListItem`s. The arrow keys can be used to navigate the list.

**list_view.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Footer, Label, ListItem, ListView


class ListViewExample(App):
    CSS_PATH = "list_view.tcss"

    def compose(self) -> ComposeResult:
        yield ListView(
            ListItem(Label("One")),
            ListItem(Label("Two")),
            ListItem(Label("Three")),
        )
        yield Footer()


if __name__ == "__main__":
    app = ListViewExample()
    app.run()
```
## Reactive Attributes

| Name          | Type   | Default | Description                          |
|---------------|--------|---------|--------------------------------------|
| `highlighted` | `bool` | `False` | True if this ListItem is highlighted |

## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.

## See also

- [ListView](./list_view.md) - The container widget that holds ListItems
- [OptionList](./option_list.md) - An alternative vertical list widget
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.ListItem`*
