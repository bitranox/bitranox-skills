# RadioButton

> **Tip: Added in version 0.13.0**


A simple radio button which stores a boolean value.

- [x] Focusable
- [ ] Container

A radio button is best used with others inside a [`RadioSet`](./radioset.md).

## Example

The example below shows radio buttons, used within a [`RadioSet`](./radioset.md).

**radio_button.py**


```python
from rich.text import Text

from textual.app import App, ComposeResult
from textual.widgets import RadioButton, RadioSet


class RadioChoicesApp(App[None]):
    CSS_PATH = "radio_button.tcss"

    def compose(self) -> ComposeResult:
        with RadioSet():
            yield RadioButton("Battlestar Galactica")
            yield RadioButton("Dune 1984")
            yield RadioButton("Dune 2021", id="focus_me")
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

    def on_mount(self) -> None:
        self.query_one(RadioSet).focus()


if __name__ == "__main__":
    RadioChoicesApp().run()
```

**radio_button.tcss**


```css
Screen {
    align: center middle;
}

RadioSet {
    width: 50%;
}
```
## Reactive Attributes

| Name    | Type   | Default | Description                    |
|---------|--------|---------|--------------------------------|
| `value` | `bool` | `False` | The value of the radio button. |

## Messages

- `RadioButton.Changed`

## Bindings

The radio button widget defines the following bindings:

*API reference: `textual.widgets._toggle_button.ToggleButton.BINDINGS`*


## Component Classes

The checkbox widget inherits the following component classes:

*API reference: `textual.widgets._toggle_button.ToggleButton.COMPONENT_CLASSES`*


## See Also

- [RadioSet](./radioset.md) - Container that groups RadioButtons together
- [Checkbox](./checkbox.md) - A similar toggle widget for independent boolean values
- [Switch](./switch.md) - An alternative on/off toggle control
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.RadioButton`*
