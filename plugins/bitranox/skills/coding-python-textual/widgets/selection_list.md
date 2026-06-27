# SelectionList

> **Tip: Added in version 0.27.0**


A widget for showing a vertical list of selectable options.

- [x] Focusable
- [ ] Container

## Typing

The `SelectionList` control is a
[`Generic`](https://docs.python.org/3/library/typing.html#typing.Generic),
which allows you to set the type of the
`selection values`. For instance, if
the data type for your values is an integer, you would type the widget as
follows:

```python
selections = [("First", 1), ("Second", 2)]
my_selection_list: SelectionList[int] =  SelectionList(*selections)
```

> **Note**
>
>
> Typing is entirely optional.
>
> If you aren't familiar with typing or don't want to worry about it right now, feel free to ignore it.


## Examples

A selection list is designed to be built up of single-line prompts (which
can be [Rich `Text`](https://rich.readthedocs.io/en/stable/text.html)) and
an associated unique value.

### Selections as tuples

A selection list can be built with tuples, either of two or three values in
length. Each tuple must contain a prompt and a value, and it can also
optionally contain a flag for the initial selected state of the option.

**selection_list_tuples.py**


~~~python
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, SelectionList


class SelectionListApp(App[None]):
    CSS_PATH = "selection_list.tcss"

    def compose(self) -> ComposeResult:
        yield Header()
        yield SelectionList[int](  # (1)!
            ("Falken's Maze", 0, True),
            ("Black Jack", 1),
            ("Gin Rummy", 2),
            ("Hearts", 3),
            ("Bridge", 4),
            ("Checkers", 5),
            ("Chess", 6, True),
            ("Poker", 7),
            ("Fighter Combat", 8, True),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(SelectionList).border_title = "Shall we play some games?"


if __name__ == "__main__":
    SelectionListApp().run()
~~~


**selection_list.tcss**


~~~css
Screen {
    align: center middle;
}

SelectionList {
    padding: 1;
    border: solid $accent;
    width: 80%;
    height: 80%;
}
~~~


### Selections as Selection objects

Alternatively, selections can be passed in as
``Selection``s:

**selection_list_selections.py**


~~~python
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, SelectionList
from textual.widgets.selection_list import Selection


class SelectionListApp(App[None]):
    CSS_PATH = "selection_list.tcss"

    def compose(self) -> ComposeResult:
        yield Header()
        yield SelectionList[int](  # (1)!
            Selection("Falken's Maze", 0, True),
            Selection("Black Jack", 1),
            Selection("Gin Rummy", 2),
            Selection("Hearts", 3),
            Selection("Bridge", 4),
            Selection("Checkers", 5),
            Selection("Chess", 6, True),
            Selection("Poker", 7),
            Selection("Fighter Combat", 8, True),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(SelectionList).border_title = "Shall we play some games?"


if __name__ == "__main__":
    SelectionListApp().run()
~~~


**selection_list.tcss**


~~~css
Screen {
    align: center middle;
}

SelectionList {
    padding: 1;
    border: solid $accent;
    width: 80%;
    height: 80%;
}
~~~


### Handling changes to the selections

Most of the time, when using the `SelectionList`, you will want to know when
the collection of selected items has changed; this is ideally done using the
``SelectedChanged`` message.
Here is an example of using that message to update a `Pretty` with the
collection of selected values:

**selection_list_selections.py**


~~~python
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.events import Mount
from textual.widgets import Footer, Header, Pretty, SelectionList
from textual.widgets.selection_list import Selection


class SelectionListApp(App[None]):
    CSS_PATH = "selection_list_selected.tcss"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield SelectionList[str](  # (1)!
                Selection("Falken's Maze", "secret_back_door", True),
                Selection("Black Jack", "black_jack"),
                Selection("Gin Rummy", "gin_rummy"),
                Selection("Hearts", "hearts"),
                Selection("Bridge", "bridge"),
                Selection("Checkers", "checkers"),
                Selection("Chess", "a_nice_game_of_chess", True),
                Selection("Poker", "poker"),
                Selection("Fighter Combat", "fighter_combat", True),
            )
            yield Pretty([])
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(SelectionList).border_title = "Shall we play some games?"
        self.query_one(Pretty).border_title = "Selected games"

    @on(Mount)
    @on(SelectionList.SelectedChanged)
    def update_selected_view(self) -> None:
        self.query_one(Pretty).update(self.query_one(SelectionList).selected)


if __name__ == "__main__":
    SelectionListApp().run()
~~~


**selection_list.tcss**


~~~css
Screen {
    align: center middle;
}

Horizontal {
    width: 80%;
    height: 80%;
}

SelectionList {
    padding: 1;
    border: solid $accent;
    width: 1fr;
}

Pretty {
    width: 1fr;
    border: solid $accent;
}
~~~


## Reactive Attributes

| Name          | Type            | Default | Description                                                                  |
|---------------|-----------------|---------|------------------------------------------------------------------------------|
| `highlighted` | `int` \| `None` | `None`  | The index of the highlighted selection. `None` means nothing is highlighted. |

## Messages

- `SelectionList.SelectionHighlighted`
- `SelectionList.SelectionToggled`
- `SelectionList.SelectedChanged`

## Bindings

The selection list widget defines the following bindings:

*API reference: `textual.widgets.SelectionList.BINDINGS`*


It inherits from ``OptionList``
and so also inherits the following bindings:

*API reference: `textual.widgets.OptionList.BINDINGS`*


## Component Classes

The selection list provides the following component classes:

*API reference: `textual.widgets.SelectionList.COMPONENT_CLASSES`*


It inherits from ``OptionList`` and so also
makes use of the following component classes:

*API reference: `textual.widgets.OptionList.COMPONENT_CLASSES`*


## See also

- [Select](./select.md) - A compact dropdown for choosing a single value
- [OptionList](./option_list.md) - The base class for SelectionList
- [Checkbox](./checkbox.md) - Individual toggles for boolean values
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---

*API reference: `textual.widgets.SelectionList`*


*API reference: `textual.widgets.selection_list`*
