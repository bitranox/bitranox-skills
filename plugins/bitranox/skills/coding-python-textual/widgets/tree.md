# Tree

> **Tip: Added in version 0.6.0**


A tree control widget.

- [x] Focusable
- [ ] Container


## Example

The example below creates a simple tree.

**tree.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Tree


class TreeApp(App):
    def compose(self) -> ComposeResult:
        tree: Tree[str] = Tree("Dune")
        tree.root.expand()
        characters = tree.root.add("Characters", expand=True)
        characters.add_leaf("Paul")
        characters.add_leaf("Jessica")
        characters.add_leaf("Chani")
        yield tree


if __name__ == "__main__":
    app = TreeApp()
    app.run()
```
Tree widgets have a "root" attribute which is an instance of a `TreeNode`. Call `add()` or `add_leaf()` to add new nodes underneath the root. Both these methods return a TreeNode for the child which you can use to add additional levels.


## Reactive Attributes

| Name          | Type   | Default | Description                                     |
|---------------|--------|---------|-------------------------------------------------|
| `show_root`   | `bool` | `True`  | Show the root node.                             |
| `show_guides` | `bool` | `True`  | Show guide lines between levels.                |
| `guide_depth` | `int`  | `4`     | Amount of indentation between parent and child. |

## Messages

- `Tree.NodeCollapsed`
- `Tree.NodeExpanded`
- `Tree.NodeHighlighted`
- `Tree.NodeSelected`

## Bindings

The tree widget defines the following bindings:

*API reference: `textual.widgets.Tree.BINDINGS`*


## Component Classes

The tree widget provides the following component classes:

*API reference: `textual.widgets.Tree.COMPONENT_CLASSES`*


## See also

- [DirectoryTree](./directory_tree.md) - A tree specialized for filesystem navigation
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Tree`*


---

*API reference: `textual.widgets.tree`*
