# MarkdownViewer

> **Tip: Added in version 0.11.0**


A Widget to display Markdown content with an optional Table of Contents.

- [x] Focusable
- [ ] Container

> **Note**
>
>
> This Widget adds browser-like functionality on top of the [Markdown](./markdown.md) widget.


## Example

The following example displays Markdown from a string and a Table of Contents.

**markdown.py**


~~~python
from textual.app import App, ComposeResult
from textual.widgets import MarkdownViewer

EXAMPLE_MARKDOWN = """\
# Markdown Viewer

This is an example of Textual's `MarkdownViewer` widget.


## Features

Markdown syntax and extensions are supported.

- Typography *emphasis*, **strong**, `inline code` etc.
- Headers
- Lists (bullet and ordered)
- Syntax highlighted code blocks
- Tables!

## Tables

Tables are displayed in a DataTable widget.

| Name            | Type   | Default | Description                        |
| --------------- | ------ | ------- | ---------------------------------- |
| `show_header`   | `bool` | `True`  | Show the table header              |
| `fixed_rows`    | `int`  | `0`     | Number of fixed rows               |
| `fixed_columns` | `int`  | `0`     | Number of fixed columns            |
| `zebra_stripes` | `bool` | `False` | Display alternating colors on rows |
| `header_height` | `int`  | `1`     | Height of header row               |
| `show_cursor`   | `bool` | `True`  | Show a cell cursor                 |


## Code Blocks

Code blocks are syntax highlighted.

```python
class ListViewExample(App):
    def compose(self) -> ComposeResult:
        yield ListView(
            ListItem(Label("One")),
            ListItem(Label("Two")),
            ListItem(Label("Three")),
        )
        yield Footer()
```

## Litany Against Fear

I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain.
"""


class MarkdownExampleApp(App):
    def compose(self) -> ComposeResult:
        markdown_viewer = MarkdownViewer(EXAMPLE_MARKDOWN, show_table_of_contents=True)
        markdown_viewer.code_indent_guides = False
        yield markdown_viewer


if __name__ == "__main__":
    app = MarkdownExampleApp()
    app.run()
~~~


## Reactive Attributes

| Name                     | Type | Default | Description                                                        |
|--------------------------|------|---------|--------------------------------------------------------------------|
| `show_table_of_contents` | bool | True    | Whether a Table of Contents should be displayed with the Markdown. |

## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.

## See Also

- [Markdown](./markdown.md) - The underlying Markdown rendering widget
- [Widgets guide](../guide/widgets.md) - How to build and use widgets


---


*API reference: `textual.widgets.MarkdownViewer`*


*API reference: `textual.widgets.markdown`*
