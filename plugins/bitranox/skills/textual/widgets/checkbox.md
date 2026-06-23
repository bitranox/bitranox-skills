# Checkbox

> **Tip: Added in version 0.13.0**


A simple checkbox widget which stores a boolean value.

- [x] Focusable
- [ ] Container

## Example

The example below shows check boxes in various states.

**checkbox.py**


```python
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Checkbox


class CheckboxApp(App[None]):
    CSS_PATH = "checkbox.tcss"

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Checkbox("Arrakis :sweat:")
            yield Checkbox("Caladan")
            yield Checkbox("Chusuk")
            yield Checkbox("[b]Giedi Prime[/b]")
            yield Checkbox("[magenta]Ginaz[/]")
            yield Checkbox("Grumman", True)
            yield Checkbox("Kaitain", id="initial_focus")
            yield Checkbox("Novebruns", True)

    def on_mount(self):
        self.query_one("#initial_focus", Checkbox).focus()


if __name__ == "__main__":
    CheckboxApp().run()
```

**checkbox.tcss**


```css
Screen {
    align: center middle;
}

VerticalScroll {
    width: auto;
    height: auto;
    background: $boost;
    padding: 2;
}
```
## Reactive Attributes

| Name    | Type   | Default | Description                |
|---------|--------|---------|----------------------------|
| `value` | `bool` | `False` | The value of the checkbox. |

## Messages

- `Checkbox.Changed`

## Bindings

The checkbox widget defines the following bindings:

*API reference: `textual.widgets._toggle_button.ToggleButton.BINDINGS`*


## Component Classes

The checkbox widget inherits the following component classes:

*API reference: `textual.widgets._toggle_button.ToggleButton.COMPONENT_CLASSES`*


## See also

- [RadioButton](./radiobutton.md) - A similar toggle widget used in radio groups
- [Switch](./switch.md) - An alternative on/off control
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Checkbox`*
