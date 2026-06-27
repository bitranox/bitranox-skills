# DirectoryTree

A tree control to navigate the contents of your filesystem.

- [x] Focusable
- [ ] Container


## Example

The example below creates a simple tree to navigate the current working directory.

```python
from textual.app import App, ComposeResult
from textual.widgets import DirectoryTree


class DirectoryTreeApp(App):
    def compose(self) -> ComposeResult:
        yield DirectoryTree("./")


if __name__ == "__main__":
    app = DirectoryTreeApp()
    app.run()
```

## Filtering

There may be times where you want to filter what appears in the
`DirectoryTree`. To do this inherit from `DirectoryTree` and implement your
own version of the `filter_paths` method. It should take an iterable of
Python `Path` objects, and return those that pass the filter. For example,
if you wanted to take the above code an filter out all of the "hidden" files
and directories:

**directory_tree_filtered.py**


~~~python
from pathlib import Path
from typing import Iterable

from textual.app import App, ComposeResult
from textual.widgets import DirectoryTree


class FilteredDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not path.name.startswith(".")]


class DirectoryTreeApp(App):
    def compose(self) -> ComposeResult:
        yield FilteredDirectoryTree("./")


if __name__ == "__main__":
    app = DirectoryTreeApp()
    app.run()
~~~


## Reactive Attributes

| Name          | Type   | Default | Description                                     |
|---------------|--------|---------|-------------------------------------------------|
| `show_root`   | `bool` | `True`  | Show the root node.                             |
| `show_guides` | `bool` | `True`  | Show guide lines between levels.                |
| `guide_depth` | `int`  | `4`     | Amount of indentation between parent and child. |

## Messages

- `DirectoryTree.FileSelected`

## Bindings

The directory tree widget inherits `the bindings from the tree widget`.

## Component Classes

The directory tree widget provides the following component classes:

*API reference: `textual.widgets.DirectoryTree.COMPONENT_CLASSES`*


## See Also

- [Tree](./tree.md) - The base tree widget that DirectoryTree inherits from
- [Widgets guide](../guide/widgets.md) - How to build and use widgets


---


*API reference: `textual.widgets.DirectoryTree`*
