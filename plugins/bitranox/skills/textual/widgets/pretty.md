# Pretty

Display a pretty-formatted object.

- [ ] Focusable
- [ ] Container

## Example

The example below shows a pretty-formatted `dict`, but `Pretty` can display any Python object.

**pretty.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Pretty

DATA = {
    "title": "Back to the Future",
    "releaseYear": 1985,
    "director": "Robert Zemeckis",
    "genre": "Adventure, Comedy, Sci-Fi",
    "cast": [
        {"actor": "Michael J. Fox", "character": "Marty McFly"},
        {"actor": "Christopher Lloyd", "character": "Dr. Emmett Brown"},
    ],
}


class PrettyExample(App):
    def compose(self) -> ComposeResult:
        yield Pretty(DATA)


app = PrettyExample()

if __name__ == "__main__":
    app.run()
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

- [Static](./static.md) - Display static Rich renderables
- [Label](./label.md) - Display simple text
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Pretty`*
