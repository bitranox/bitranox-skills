# ListView

> **Tip: Added in version 0.6.0**


Displays a vertical list of `ListItem`s which can be highlighted and selected.
Supports keyboard navigation.

- [x] Focusable
- [x] Container

## Example

The example below shows an app with a simple `ListView`.

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

**list_view.tcss**


```css
Screen {
    align: center middle;
}

ListView {
    width: 30;
    height: auto;
    margin: 2 2;
}

Label {
    padding: 1 2;
}
```
## Reactive Attributes

| Name    | Type  | Default | Description                      |
|---------|-------|---------|----------------------------------|
| `index` | `int` | `0`     | The currently highlighted index. |

## Messages

- `ListView.Highlighted`
- `ListView.Selected`

## Bindings

The list view widget defines the following bindings:

*API reference: `textual.widgets.ListView.BINDINGS`*


## Component Classes

This widget has no component classes.

## See also

- [ListItem](./list_item.md) - The items displayed within a ListView
- [OptionList](./option_list.md) - An alternative vertical list widget
- [SelectionList](./selection_list.md) - A list with selectable options
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.ListView`*
