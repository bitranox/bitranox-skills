# Digits

> **Tip: Added in version 0.33.0**


A widget to display numerical values in tall multi-line characters.

The digits 0-9 and characters A-F are supported, in addition to `+`, `-`, `^`, `:`, and `×`.
Other characters will be displayed in a regular size font.

You can set the text to be displayed in the constructor, or call ``update()`` to change the text after the widget has been mounted.

> **Note: This widget will respect the [text-align](../styles/text_align.md) rule.**


- [ ] Focusable
- [ ] Container


## Example

The following example displays a few digits of Pi:

**digits.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Digits


class DigitApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    #pi {
        border: double green;
        width: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Digits("3.141,592,653,5897", id="pi")


if __name__ == "__main__":
    app = DigitApp()
    app.run()
```
Here's another example which uses `Digits` to display the current time:


**clock.py**


```python
from datetime import datetime

from textual.app import App, ComposeResult
from textual.widgets import Digits


class ClockApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    #clock {
        width: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Digits("", id="clock")

    def on_ready(self) -> None:
        self.update_clock()
        self.set_interval(1, self.update_clock)

    def update_clock(self) -> None:
        clock = datetime.now().time()
        self.query_one(Digits).update(f"{clock:%T}")


if __name__ == "__main__":
    app = ClockApp()
    app.run(inline=True)
```
## Reactive Attributes

This widget has no reactive attributes.

## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.


## See also

- [Label](./label.md) - Display simple text content
- [Static](./static.md) - Display static Rich renderables
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Digits`*
