# OptionList

> **Tip: Added in version 0.17.0**


A widget for showing a vertical list of Rich renderable options.

- [x] Focusable
- [ ] Container

## Examples

### Options as simple strings

An `OptionList` can be constructed with a simple collection of string
options:

**option_list_strings.py**


~~~python
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, OptionList


class OptionListApp(App[None]):
    CSS_PATH = "option_list.tcss"

    def compose(self) -> ComposeResult:
        yield Header()
        yield OptionList(
            "Aerilon",
            "Aquaria",
            "Canceron",
            "Caprica",
            "Gemenon",
            "Leonis",
            "Libran",
            "Picon",
            "Sagittaron",
            "Scorpia",
            "Tauron",
            "Virgon",
        )
        yield Footer()


if __name__ == "__main__":
    OptionListApp().run()
~~~

**option_list.tcss**


~~~css
Screen {
    align: center middle;
}

OptionList {
    width: 70%;
    height: 80%;
}
~~~


### Options as `Option` instances

For finer control over the options, the `Option` class can be used; this
allows for setting IDs, setting initial disabled state, etc. The `Separator`
class can be used to add separator lines between options.

**option_list_options.py**


~~~python
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, OptionList
from textual.widgets.option_list import Option


class OptionListApp(App[None]):
    CSS_PATH = "option_list.tcss"

    def compose(self) -> ComposeResult:
        yield Header()
        yield OptionList(
            Option("Aerilon", id="aer"),
            Option("Aquaria", id="aqu"),
            None,
            Option("Canceron", id="can"),
            Option("Caprica", id="cap", disabled=True),
            None,
            Option("Gemenon", id="gem"),
            None,
            Option("Leonis", id="leo"),
            Option("Libran", id="lib"),
            None,
            Option("Picon", id="pic"),
            None,
            Option("Sagittaron", id="sag"),
            Option("Scorpia", id="sco"),
            None,
            Option("Tauron", id="tau"),
            None,
            Option("Virgon", id="vir"),
        )
        yield Footer()


if __name__ == "__main__":
    OptionListApp().run()
~~~

**option_list.tcss**


~~~css
Screen {
    align: center middle;
}

OptionList {
    width: 70%;
    height: 80%;
}
~~~


### Options as Rich renderables

Because the prompts for the options can be [Rich
renderables](https://rich.readthedocs.io/en/latest/protocol.html), this
means they can be any height you wish. As an example, here is an option list
comprised of [Rich
tables](https://rich.readthedocs.io/en/latest/tables.html):

**option_list_tables.py**


~~~python
from __future__ import annotations

from rich.table import Table

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, OptionList

COLONIES: tuple[tuple[str, str, str, str], ...] = (
    ("Aerilon", "Demeter", "1.2 Billion", "Gaoth"),
    ("Aquaria", "Hermes", "75,000", "None"),
    ("Canceron", "Hephaestus", "6.7 Billion", "Hades"),
    ("Caprica", "Apollo", "4.9 Billion", "Caprica City"),
    ("Gemenon", "Hera", "2.8 Billion", "Oranu"),
    ("Leonis", "Artemis", "2.6 Billion", "Luminere"),
    ("Libran", "Athena", "2.1 Billion", "None"),
    ("Picon", "Poseidon", "1.4 Billion", "Queenstown"),
    ("Sagittaron", "Zeus", "1.7 Billion", "Tawa"),
    ("Scorpia", "Dionysus", "450 Million", "Celeste"),
    ("Tauron", "Ares", "2.5 Billion", "Hypatia"),
    ("Virgon", "Hestia", "4.3 Billion", "Boskirk"),
)


class OptionListApp(App[None]):
    CSS_PATH = "option_list.tcss"

    @staticmethod
    def colony(name: str, god: str, population: str, capital: str) -> Table:
        table = Table(title=f"Data for {name}", expand=True)
        table.add_column("Patron God")
        table.add_column("Population")
        table.add_column("Capital City")
        table.add_row(god, population, capital)
        return table

    def compose(self) -> ComposeResult:
        yield Header()
        yield OptionList(*[self.colony(*row) for row in COLONIES])
        yield Footer()


if __name__ == "__main__":
    OptionListApp().run()
~~~

**option_list.tcss**


~~~css
Screen {
    align: center middle;
}

OptionList {
    width: 70%;
    height: 80%;
}
~~~


## Reactive Attributes

| Name          | Type            | Default | Description                                                               |
|---------------|-----------------|---------|---------------------------------------------------------------------------|
| `highlighted` | `int` \| `None` | `None`  | The index of the highlighted option. `None` means nothing is highlighted. |

## Messages

- `OptionList.OptionHighlighted`
- `OptionList.OptionSelected`

Both of the messages above inherit from the common base ``OptionList.OptionMessage``, so refer to its documentation to see what attributes are available.

## Bindings

The option list widget defines the following bindings:

*API reference: `textual.widgets.OptionList.BINDINGS`*


## Component Classes

The option list provides the following component classes:

*API reference: `textual.widgets.OptionList.COMPONENT_CLASSES`*


## See also

- [ListView](./list_view.md) - A list of items that can contain arbitrary widgets
- [SelectionList](./selection_list.md) - A list with togglable selections, built on OptionList
- [Select](./select.md) - A compact dropdown selection widget
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---

*API reference: `textual.widgets.OptionList`*


*API reference: `textual.widgets.option_list`*
