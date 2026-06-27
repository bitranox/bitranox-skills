# Log

> **Tip: Added in version 0.32.0**


A Log widget displays lines of text which may be appended to in realtime.

Call `Log.write_line` to write a line at a time, or `Log.write_lines` to write multiple lines at once. Call `Log.clear` to clear the Log widget.

> **Tip**
>
>
> See also [RichLog](./rich_log.md) which can write more than just text, and supports a number of advanced features.


- [X] Focusable
- [ ] Container

## Example

The example below shows how to write text to a `Log` widget:

**log.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Log

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class LogApp(App):
    """An app with a simple log."""

    def compose(self) -> ComposeResult:
        yield Log()

    def on_ready(self) -> None:
        log = self.query_one(Log)
        log.write_line("Hello, World!")
        for _ in range(10):
            log.write_line(TEXT)


if __name__ == "__main__":
    app = LogApp()
    app.run()
```
## Reactive Attributes

| Name          | Type   | Default | Description                                                  |
|---------------|--------|---------|--------------------------------------------------------------|
| `max_lines`   | `int`  | `None`  | Maximum number of lines in the log or `None` for no maximum. |
| `auto_scroll` | `bool` | `False` | Scroll to end of log when new lines are added.               |

## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.


## See also

- [RichLog](./rich_log.md) - A richer alternative that supports Rich renderables
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Log`*
