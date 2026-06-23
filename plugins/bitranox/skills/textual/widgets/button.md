# Button


A simple button widget which can be pressed using a mouse click or by pressing `Return`
when it has focus.

- [x] Focusable
- [ ] Container

## Example

The example below shows each button variant, and its disabled equivalent.
Clicking any of the non-disabled buttons in the example app below will result in the app exiting and the details of the selected button being printed to the console.

**button.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Static


class ButtonsApp(App[str]):
    CSS_PATH = "button.tcss"

    def compose(self) -> ComposeResult:
        yield Horizontal(
            VerticalScroll(
                Static("Standard Buttons", classes="header"),
                Button("Default"),
                Button("Primary!", variant="primary"),
                Button.success("Success!"),
                Button.warning("Warning!"),
                Button.error("Error!"),
            ),
            VerticalScroll(
                Static("Disabled Buttons", classes="header"),
                Button("Default", disabled=True),
                Button("Primary!", variant="primary", disabled=True),
                Button.success("Success!", disabled=True),
                Button.warning("Warning!", disabled=True),
                Button.error("Error!", disabled=True),
            ),
            VerticalScroll(
                Static("Flat Buttons", classes="header"),
                Button("Default", flat=True),
                Button("Primary!", variant="primary", flat=True),
                Button.success("Success!", flat=True),
                Button.warning("Warning!", flat=True),
                Button.error("Error!", flat=True),
            ),
            VerticalScroll(
                Static("Disabled Flat Buttons", classes="header"),
                Button("Default", disabled=True, flat=True),
                Button("Primary!", variant="primary", disabled=True, flat=True),
                Button.success("Success!", disabled=True, flat=True),
                Button.warning("Warning!", disabled=True, flat=True),
                Button.error("Error!", disabled=True, flat=True),
            ),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(str(event.button))


if __name__ == "__main__":
    app = ButtonsApp()
    print(app.run())
```

**button.tcss**


```css
Button {
    margin: 1 2;
}

Horizontal > VerticalScroll {
    width: 24;
}

.header {
    margin: 1 0 0 2;
    text-style: bold;
}
```
## Reactive Attributes

| Name       | Type            | Default     | Description                                                                                                                       |
|------------|-----------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `label`    | `str`           | `""`        | The text that appears inside the button.                                                                                          |
| `variant`  | `ButtonVariant` | `"default"` | Semantic styling variant. One of `default`, `primary`, `success`, `warning`, `error`.                                             |
| `disabled` | `bool`          | `False`     | Whether the button is disabled or not. Disabled buttons cannot be focused or clicked, and are styled in a way that suggests this. |

## Messages

- `Button.Pressed`

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.

## Additional Notes

- The spacing between the text and the edges of a button are _not_ due to padding. The default styling for a `Button` includes borders and a `min-width` of 16 columns. To remove the spacing, set `border: none;` in your CSS and adjust the minimum width as needed.

## See also

- [Events guide](../guide/events.md) - Introduction to Textual's event system
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Button`*


*API reference: `textual.widgets.button`*
