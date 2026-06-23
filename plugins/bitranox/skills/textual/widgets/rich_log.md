# RichLog

A RichLog is a widget which displays scrollable content that may be appended to in realtime.

Call `RichLog.write` with a string or [Rich Renderable](https://rich.readthedocs.io/en/latest/protocol.html) to write content to the end of the RichLog. Call `RichLog.clear` to clear the content.

> **Tip**
>
>
> See also [Log](./log.md) which is an alternative to `RichLog` but specialized for simple text.


- [X] Focusable
- [ ] Container

## Example

The example below shows an application showing a `RichLog` with different kinds of data logged.

**rich_log.py**


```python
import csv
import io

from rich.syntax import Syntax
from rich.table import Table

from textual import events
from textual.app import App, ComposeResult
from textual.widgets import RichLog

CSV = """lane,swimmer,country,time
4,Joseph Schooling,Singapore,50.39
2,Michael Phelps,United States,51.14
5,Chad le Clos,South Africa,51.14
6,László Cseh,Hungary,51.14
3,Li Zhuhao,China,51.26
8,Mehdy Metella,France,51.58
7,Tom Shields,United States,51.73
1,Aleksandr Sadovnikov,Russia,51.84"""


CODE = '''\
def loop_first_last(values: Iterable[T]) -> Iterable[tuple[bool, bool, T]]:
    """Iterate and generate a tuple with a flag for first and last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    first = True
    for value in iter_values:
        yield first, False, previous_value
        first = False
        previous_value = value
    yield first, True, previous_value\
'''


class RichLogApp(App):
    def compose(self) -> ComposeResult:
        yield RichLog(highlight=True, markup=True)

    def on_ready(self) -> None:
        """Called  when the DOM is ready."""
        text_log = self.query_one(RichLog)

        text_log.write(Syntax(CODE, "python", indent_guides=True))

        rows = iter(csv.reader(io.StringIO(CSV)))
        table = Table(*next(rows))
        for row in rows:
            table.add_row(*row)

        text_log.write(table)
        text_log.write("[bold magenta]Write text or any Rich renderable!")

    def on_key(self, event: events.Key) -> None:
        """Write Key events to log."""
        text_log = self.query_one(RichLog)
        text_log.write(event)


if __name__ == "__main__":
    app = RichLogApp()
    app.run()
```
## Reactive Attributes

| Name        | Type   | Default | Description                                                  |
|-------------|--------|---------|--------------------------------------------------------------|
| `highlight` | `bool` | `False` | Automatically highlight content.                             |
| `markup`    | `bool` | `False` | Apply markup.                                                |
| `max_lines` | `int`  | `None`  | Maximum number of lines in the log or `None` for no maximum. |
| `min_width` | `int`  | 78      | Minimum width of renderables.                                |
| `wrap`      | `bool` | `False` | Enable word wrapping.                                        |

## Messages

This widget sends no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.


## See also

- [Log](./log.md) - A simpler text-only log widget
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.RichLog`*
