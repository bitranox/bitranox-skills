# MaskedInput

> **Tip: Added in version 0.80.0**


A masked input derived from `Input`, allowing to restrict user input and give visual aid via a simple template mask, which also acts as an implicit *`validator`*.

- [x] Focusable
- [ ] Container

## Example

The example below shows a masked input to ease entering a credit card number.

**masked_input.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Label, MaskedInput


class MaskedInputApp(App):
    # (1)!
    CSS = """
    MaskedInput.-valid {
        border: tall $success 60%;
    }
    MaskedInput.-valid:focus {
        border: tall $success;
    }
    MaskedInput {
        margin: 1 1;
    }
    Label {
        margin: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Enter a valid credit card number.")
        yield MaskedInput(
            template="9999-9999-9999-9999;0",  # (2)!
        )


app = MaskedInputApp()

if __name__ == "__main__":
    app.run()
```

2. This example shows how to define a template mask for a credit card number, which requires 16 digits in groups of 4.


## Reactive Attributes

| Name       | Type  | Default | Description               |
|------------|-------|---------|---------------------------|
| `template` | `str` | `""`    | The template mask string. |

### The template string format

A `MaskedInput` template length defines the maximum length of the input value. Each character of the mask defines a regular expression used to restrict what the user can insert in the corresponding position, and whether the presence of the character in the user input is required for the `MaskedInput` value to be considered valid, according to the following table:

| Mask character | Regular expression | Required? |
|----------------|--------------------|-----------|
| `A`            | `[A-Za-z]`         | Yes       |
| `a`            | `[A-Za-z]`         | No        |
| `N`            | `[A-Za-z0-9]`      | Yes       |
| `n`            | `[A-Za-z0-9]`      | No        |
| `X`            | `[^ ]`             | Yes       |
| `x`            | `[^ ]`             | No        |
| `9`            | `[0-9]`            | Yes       |
| `0`            | `[0-9]`            | No        |
| `D`            | `[1-9]`            | Yes       |
| `d`            | `[1-9]`            | No        |
| `#`            | `[0-9+\-]`         | No        |
| `H`            | `[A-Fa-f0-9]`      | Yes       |
| `h`            | `[A-Fa-f0-9]`      | No        |
| `B`            | `[0-1]`            | Yes       |
| `b`            | `[0-1]`            | No        |

There are some special characters that can be used to control automatic case conversion during user input: `>` converts all subsequent user input to uppercase; `<` to lowercase; `!` disables automatic case conversion. Any other character that appears in the template mask is assumed to be a separator, which is a character that is automatically inserted when user reaches its position. All mask characters can be escaped by placing `\` in front of them, allowing any character to be used as separator.
The mask can be terminated by `;c`, where `c` is any character you want to be used as placeholder character. The `placeholder` parameter inherited by `Input` can be used to override this allowing finer grain tuning of the placeholder string.

## Messages

- `MaskedInput.Changed`
- `MaskedInput.Submitted`

## Bindings

The masked input widget defines the following bindings:

*API reference: `textual.widgets.MaskedInput.BINDINGS`*


## Component Classes

The masked input widget provides the following component classes:

*API reference: `textual.widgets.MaskedInput.COMPONENT_CLASSES`*


## See also

- [Input](./input.md) - The base input widget that MaskedInput extends
- [TextArea](./text_area.md) - A multi-line text editing widget
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.MaskedInput`*
