# Tabs

> **Tip: Added in version 0.15.0**


Displays a number of tab headers which may be activated with a click or navigated with cursor keys.

- [x] Focusable
- [ ] Container

Construct a `Tabs` widget with strings or `Text` objects as positional arguments, which will set the labels in the tabs. Here's an example with three tabs:

```python
def compose(self) -> ComposeResult:
    yield Tabs("First tab", "Second tab", Text.from_markup("[u]Third[/u] tab"))
```

This will create `Tab` widgets internally, with auto-incrementing `id` attributes (`"tab-1"`, `"tab-2"` etc).
You can also supply `Tab` objects directly in the constructor, which will allow you to explicitly set an `id`. Here's an example:

```python
def compose(self) -> ComposeResult:
    yield Tabs(
        Tab("First tab", id="one"),
        Tab("Second tab", id="two"),
    )
```

When the user switches to a tab by clicking or pressing keys, then `Tabs` will send a `Tabs.TabActivated` message which contains the `tab` that was activated.
You can then use `event.tab.id` attribute to perform any related actions.

## Clearing tabs

Clear tabs by calling the `clear` method. Clearing the tabs will send a `Tabs.TabActivated` message with the `tab` attribute set to `None`.

## Adding tabs

Tabs may be added dynamically with the `add_tab` method, which accepts strings, `Text`, or `Tab` objects.

## Example

The following example adds a `Tabs` widget above a text label. Press `A` to add a tab, `C` to clear the tabs.

**tabs.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Footer, Label, Tabs

NAMES = [
    "Paul Atreidies",
    "Duke Leto Atreides",
    "Lady Jessica",
    "Gurney Halleck",
    "Baron Vladimir Harkonnen",
    "Glossu Rabban",
    "Chani",
    "Silgar",
]


class TabsApp(App):
    """Demonstrates the Tabs widget."""

    CSS = """
    Tabs {
        dock: top;
    }
    Screen {
        align: center middle;
    }
    Label {
        margin:1 1;
        width: 100%;
        height: 100%;
        background: $panel;
        border: tall $primary;
        content-align: center middle;
    }
    """

    BINDINGS = [
        ("a", "add", "Add tab"),
        ("r", "remove", "Remove active tab"),
        ("c", "clear", "Clear tabs"),
    ]

    def compose(self) -> ComposeResult:
        yield Tabs(NAMES[0])
        yield Label()
        yield Footer()

    def on_mount(self) -> None:
        """Focus the tabs when the app starts."""
        self.query_one(Tabs).focus()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle TabActivated message sent by Tabs."""
        label = self.query_one(Label)
        if event.tab is None:
            # When the tabs are cleared, event.tab will be None
            label.visible = False
        else:
            label.visible = True
            label.update(event.tab.label)

    def action_add(self) -> None:
        """Add a new tab."""
        tabs = self.query_one(Tabs)
        # Cycle the names
        NAMES[:] = [*NAMES[1:], NAMES[0]]
        tabs.add_tab(NAMES[0])

    def action_remove(self) -> None:
        """Remove active tab."""
        tabs = self.query_one(Tabs)
        active_tab = tabs.active_tab
        if active_tab is not None:
            tabs.remove_tab(active_tab.id)

    def action_clear(self) -> None:
        """Clear the tabs."""
        self.query_one(Tabs).clear()


if __name__ == "__main__":
    app = TabsApp()
    app.run()
```
## Reactive Attributes

| Name     | Type  | Default | Description                                                                        |
|----------|-------|---------|------------------------------------------------------------------------------------|
| `active` | `str` | `""`    | The ID of the active tab. Set this attribute to a tab ID to change the active tab. |


## Messages

- `Tabs.TabActivated`
- `Tabs.Cleared`

## Bindings

The Tabs widget defines the following bindings:

*API reference: `textual.widgets.Tabs.BINDINGS`*


## Component Classes

This widget has no component classes.

## See also

- [TabbedContent](./tabbed_content.md) - Combines Tabs with ContentSwitcher for navigating content
- [ContentSwitcher](./content_switcher.md) - A widget for switching between child widgets
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Tabs`*


---

*API reference: `textual.widgets.Tab`*
