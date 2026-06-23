# Switch

A simple switch widget which stores a boolean value.

- [x] Focusable
- [ ] Container

## Example

The example below shows switches in various states.

**switch.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Switch


class SwitchApp(App):
    def compose(self) -> ComposeResult:
        yield Static("[b]Example switches\n", classes="label")
        yield Horizontal(
            Static("off:     ", classes="label"),
            Switch(animate=False),
            classes="container",
        )
        yield Horizontal(
            Static("on:      ", classes="label"),
            Switch(value=True),
            classes="container",
        )

        focused_switch = Switch()
        focused_switch.focus()
        yield Horizontal(
            Static("focused: ", classes="label"), focused_switch, classes="container"
        )

        yield Horizontal(
            Static("custom:  ", classes="label"),
            Switch(id="custom-design"),
            classes="container",
        )


app = SwitchApp(css_path="switch.tcss")
if __name__ == "__main__":
    app.run()
```

**switch.tcss**


```css
Screen {
    align: center middle;
}

.container {
    height: auto;
    width: auto;
}

Switch {
    height: auto;
    width: auto;
}

.label {
    height: 3;
    content-align: center middle;
    width: auto;
}

#custom-design {
    background: darkslategrey;
}

#custom-design > .switch--slider {
    color: dodgerblue;
    background: darkslateblue;
}
```
## Reactive Attributes

| Name    | Type   | Default | Description              |
|---------|--------|---------|--------------------------|
| `value` | `bool` | `False` | The value of the switch. |

## Messages

- `Switch.Changed`

## Bindings

The switch widget defines the following bindings:

*API reference: `textual.widgets.Switch.BINDINGS`*


## Component Classes

The switch widget provides the following component classes:

*API reference: `textual.widgets.Switch.COMPONENT_CLASSES`*


## Additional Notes

- To remove the spacing around a `Switch`, set `border: none;` and `padding: 0;`.

## See also

- [Checkbox](./checkbox.md) - An alternative boolean toggle widget
- [RadioButton](./radiobutton.md) - A toggle used in exclusive radio groups
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Switch`*
