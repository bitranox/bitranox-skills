# ContentSwitcher

> **Tip: Added in version 0.14.0**


A widget for containing and switching display between multiple child
widgets.

- [ ] Focusable
- [X] Container

## Example

The example below uses a `ContentSwitcher` in combination with two `Button`s
to create a simple tabbed view. Note how each `Button` has an ID set, and
how each child of the `ContentSwitcher` has a corresponding ID; then a
`Button.Clicked` handler is used to set `ContentSwitcher.current` to switch
between the different views.

**content_switcher.py**


~~~python
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, ContentSwitcher, DataTable, Markdown

MARKDOWN_EXAMPLE = """# Three Flavours Cornetto

The Three Flavours Cornetto trilogy is an anthology series of British
comedic genre films directed by Edgar Wright.

## Shaun of the Dead

| Flavour | UK Release Date | Director |
| -- | -- | -- |
| Strawberry | 2004-04-09 | Edgar Wright |

## Hot Fuzz

| Flavour | UK Release Date | Director |
| -- | -- | -- |
| Classico | 2007-02-17 | Edgar Wright |

## The World's End

| Flavour | UK Release Date | Director |
| -- | -- | -- |
| Mint | 2013-07-19 | Edgar Wright |
"""


class ContentSwitcherApp(App[None]):
    CSS_PATH = "content_switcher.tcss"

    def compose(self) -> ComposeResult:
        with Horizontal(id="buttons"):  # (1)!
            yield Button("DataTable", id="data-table")  # (2)!
            yield Button("Markdown", id="markdown")  # (3)!

        with ContentSwitcher(initial="data-table"):  # (4)!
            yield DataTable(id="data-table")
            with VerticalScroll(id="markdown"):
                yield Markdown(MARKDOWN_EXAMPLE)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.query_one(ContentSwitcher).current = event.button.id  # (5)!

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Book", "Year")
        table.add_rows(
            [
                (title.ljust(35), year)
                for title, year in (
                    ("Dune", 1965),
                    ("Dune Messiah", 1969),
                    ("Children of Dune", 1976),
                    ("God Emperor of Dune", 1981),
                    ("Heretics of Dune", 1984),
                    ("Chapterhouse: Dune", 1985),
                )
            ]
        )


if __name__ == "__main__":
    ContentSwitcherApp().run()
~~~

2. This button will select the `DataTable` in the `ContentSwitcher`.
3. This button will select the `Markdown` in the `ContentSwitcher`.
4. Note that the initial visible content is set by its ID, see below.
5. When a button is pressed, its ID is used to switch to a different widget in the `ContentSwitcher`. Remember that IDs are unique within parent, so the buttons and the widgets in the `ContentSwitcher` can share IDs.

**content_switcher.tcss**


~~~sass
Screen {
    align: center middle;
    padding: 1;
}

#buttons {
    height: 3;
    width: auto;
}

ContentSwitcher {
    border: round $primary;
    width: 90%;
    height: 1fr;
}

MarkdownH2 {
    background: $panel;
    color: yellow;
    border: none;
    padding: 0 1;
}
~~~


When the user presses the "Markdown" button the view is switched:


## Reactive Attributes

| Name      | Type            | Default | Description                                                             |
|-----------|-----------------|---------|-------------------------------------------------------------------------|
| `current` | `str` \| `None` | `None`  | The ID of the currently-visible child. `None` means nothing is visible. |

## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.


## See also

- [TabbedContent](./tabbed_content.md) - Combines Tabs and ContentSwitcher into a single widget
- [Tabs](./tabs.md) - A row of tabs commonly used with ContentSwitcher
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.ContentSwitcher`*
