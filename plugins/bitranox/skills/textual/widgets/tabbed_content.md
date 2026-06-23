# TabbedContent

> **Tip: Added in version 0.16.0**


Switch between mutually exclusive content panes via a row of tabs.

- [x] Focusable
- [x] Container

This widget combines the [Tabs](./tabs.md) and [ContentSwitcher](./content_switcher.md) widgets to create a convenient way of navigating content.

Only a single child of TabbedContent is visible at once.
Each child has an associated tab which will make it visible and hide the others.

## Composing

There are two ways to provide the titles for the tab.
You can pass them as positional arguments to the `TabbedContent` constructor:

```python
def compose(self) -> ComposeResult:
    with TabbedContent("Leto", "Jessica", "Paul"):
        yield Markdown(LETO)
        yield Markdown(JESSICA)
        yield Markdown(PAUL)
```

Alternatively you can wrap the content in a `TabPane` widget, which takes the tab title as the first parameter:

```python
def compose(self) -> ComposeResult:
    with TabbedContent():
        with TabPane("Leto"):
            yield Markdown(LETO)
        with TabPane("Jessica"):
            yield Markdown(JESSICA)
        with TabPane("Paul"):
            yield Markdown(PAUL)
```

## Switching tabs

If you need to programmatically switch tabs, you should provide an `id` attribute to the `TabPane`s.

```python
def compose(self) -> ComposeResult:
    with TabbedContent():
        with TabPane("Leto", id="leto"):
            yield Markdown(LETO)
        with TabPane("Jessica", id="jessica"):
            yield Markdown(JESSICA)
        with TabPane("Paul", id="paul"):
            yield Markdown(PAUL)
```

You can then switch tabs by setting the `active` reactive attribute:

```python
# Switch to Jessica tab
self.query_one(TabbedContent).active = "jessica"
```

> **Note**
>
>
> If you don't provide `id` attributes to the tab panes, they will be assigned sequentially starting at `tab-1` (then `tab-2` etc).


## Initial tab

The first child of `TabbedContent` will be the initial active tab by default. You can pick a different initial tab by setting the `initial` argument to the `id` of the tab:

```python
def compose(self) -> ComposeResult:
    with TabbedContent(initial="jessica"):
        with TabPane("Leto", id="leto"):
            yield Markdown(LETO)
        with TabPane("Jessica", id="jessica"):
            yield Markdown(JESSICA)
        with TabPane("Paul", id="paul"):
            yield Markdown(PAUL)
```

## Example

The following example contains a `TabbedContent` with three tabs.

**tabbed_content.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Footer, Label, Markdown, TabbedContent, TabPane

LETO = """
# Duke Leto I Atreides

Head of House Atreides.
"""

JESSICA = """
# Lady Jessica

Bene Gesserit and concubine of Leto, and mother of Paul and Alia.
"""

PAUL = """
# Paul Atreides

Son of Leto and Jessica.
"""


class TabbedApp(App):
    """An example of tabbed content."""

    BINDINGS = [
        ("l", "show_tab('leto')", "Leto"),
        ("j", "show_tab('jessica')", "Jessica"),
        ("p", "show_tab('paul')", "Paul"),
    ]

    def compose(self) -> ComposeResult:
        """Compose app with tabbed content."""
        # Footer to show keys
        yield Footer()

        # Add the TabbedContent widget
        with TabbedContent(initial="jessica"):
            with TabPane("Leto", id="leto"):  # First tab
                yield Markdown(LETO)  # Tab content
            with TabPane("Jessica", id="jessica"):
                yield Markdown(JESSICA)
                with TabbedContent("Paul", "Alia"):
                    yield TabPane("Paul", Label("First child"))
                    yield TabPane("Alia", Label("Second child"))

            with TabPane("Paul", id="paul"):
                yield Markdown(PAUL)

    def action_show_tab(self, tab: str) -> None:
        """Switch to a new tab."""
        self.get_child_by_type(TabbedContent).active = tab


if __name__ == "__main__":
    app = TabbedApp()
    app.run()
```
## Styling

The `TabbedContent` widget is composed of two main sub-widgets: a
[`Tabs`](tabs.md) and a [`ContentSwitcher`](content_switcher.md); you can
style them accordingly.

The tabs within the `Tabs` widget will have prefixed IDs; each ID being the
ID of the `TabPane` the `Tab` is for, prefixed with `--content-tab-`. If you
wish to style individual tabs within the `TabbedContent` widget you will
need to use that prefix for the `Tab` IDs.

For example, to create a `TabbedContent` that has red and green labels:

**tabbed_content.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Label, TabbedContent, TabPane


class ColorTabsApp(App):
    CSS = """
    TabbedContent #--content-tab-green {
        color: green;
    }

    TabbedContent #--content-tab-red {
        color: red;
    }
    """

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Red", id="red"):
                yield Label("Red!")
            with TabPane("Green", id="green"):
                yield Label("Green!")


if __name__ == "__main__":
    ColorTabsApp().run()
```
## Reactive Attributes

| Name     | Type  | Default | Description                                                    |
|----------|-------|---------|----------------------------------------------------------------|
| `active` | `str` | `""`    | The `id` attribute of the active tab. Set this to switch tabs. |


## Messages

- `TabbedContent.Cleared`
- `TabbedContent.TabActivated`

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.

## See also

- [Tabs](./tabs.md) - The row of tab headers used by TabbedContent
- [ContentSwitcher](./content_switcher.md) - The underlying content switching widget
- [Collapsible](./collapsible.md) - An alternative for toggling content visibility
- [Widgets guide](../guide/widgets.md) - How to build and use widgets


---


*API reference: `textual.widgets.TabbedContent`*


---


*API reference: `textual.widgets.TabPane`*
