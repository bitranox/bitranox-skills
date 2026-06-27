# RadioSet

> **Tip: Added in version 0.13.0**


A container widget that groups [`RadioButton`](./radiobutton.md)s together.

- [ ] Focusable
- [x] Container

## Example

### Simple example

The example below shows two radio sets, one built using a collection of
[radio buttons](./radiobutton.md), the other a collection of simple strings.

**radio_set.py**


```python
from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import RadioButton, RadioSet


class RadioChoicesApp(App[None]):
    CSS_PATH = "radio_set.tcss"

    def compose(self) -> ComposeResult:
        with Horizontal():
            # A RadioSet built up from RadioButtons.
            with RadioSet(id="focus_me"):
                yield RadioButton("Battlestar Galactica")
                yield RadioButton("Dune 1984")
                yield RadioButton("Dune 2021")
                yield RadioButton("Serenity", value=True)
                yield RadioButton("Star Trek: The Motion Picture")
                yield RadioButton("Star Wars: A New Hope")
                yield RadioButton("The Last Starfighter")
                yield RadioButton(
                    Text.from_markup(
                        "Total Recall :backhand_index_pointing_right: :red_circle:"
                    )
                )
                yield RadioButton("Wing Commander")
            # A RadioSet built up from a collection of strings.
            yield RadioSet(
                "Amanda",
                "Connor MacLeod",
                "Duncan MacLeod",
                "Heather MacLeod",
                "Joe Dawson",
                "Kurgan, [bold italic red]The[/]",
                "Methos",
                "Rachel Ellenstein",
                "Ramírez",
            )

    def on_mount(self) -> None:
        self.query_one("#focus_me").focus()


if __name__ == "__main__":
    RadioChoicesApp().run()
```

**radio_set.tcss**


```css
Screen {
    align: center middle;
}

Horizontal {
    align: center middle;
    height: auto;
}

RadioSet {
    width: 45%;
}
```
### Reacting to Changes in a Radio Set

Here is an example of using the message to react to changes in a `RadioSet`:

**radio_set_changed.py**


```python
from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Label, RadioButton, RadioSet


class RadioSetChangedApp(App[None]):
    CSS_PATH = "radio_set_changed.tcss"

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            with Horizontal():
                with RadioSet(id="focus_me"):
                    yield RadioButton("Battlestar Galactica")
                    yield RadioButton("Dune 1984")
                    yield RadioButton("Dune 2021")
                    yield RadioButton("Serenity", value=True)
                    yield RadioButton("Star Trek: The Motion Picture")
                    yield RadioButton("Star Wars: A New Hope")
                    yield RadioButton("The Last Starfighter")
                    yield RadioButton(
                        Text.from_markup(
                            "Total Recall :backhand_index_pointing_right: :red_circle:"
                        )
                    )
                    yield RadioButton("Wing Commander")
            with Horizontal():
                yield Label(id="pressed")
            with Horizontal():
                yield Label(id="index")

    def on_mount(self) -> None:
        self.query_one(RadioSet).focus()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self.query_one("#pressed", Label).update(
            f"Pressed button label: {event.pressed.label}"
        )
        self.query_one("#index", Label).update(
            f"Pressed button index: {event.radio_set.pressed_index}"
        )


if __name__ == "__main__":
    RadioSetChangedApp().run()
```

**radio_set_changed.tcss**


```css
VerticalScroll {
    align: center middle;
}

Horizontal {
    align: center middle;
    height: auto;
}

RadioSet {
    width: 45%;
}
```
## Messages

-  `RadioSet.Changed`

## Bindings

The `RadioSet` widget defines the following bindings:

*API reference: `textual.widgets.RadioSet.BINDINGS`*


## Component Classes

This widget has no component classes.

## See Also

- [RadioButton](./radiobutton.md) - The individual buttons used within a RadioSet
- [SelectionList](./selection_list.md) - For multiple selections from a list
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.RadioSet`*
