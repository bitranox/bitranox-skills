# Save time with Textual containers

Textual's `containers` provide a convenient way of arranging your widgets. Let's look at them in a little detail.

> **Info: Are you in the right place?**
>
>
> We are talking about Textual container widgets here. Not to be confused with [containerization](https://en.wikipedia.org/wiki/Containerization_(computing))&mdash;which is something else entirely!


## What are containers?

Containers are reusable [compound widgets](../guide/widgets.md#compound-widgets) with preset styles to arrange their children.
For instance, there is a `Horizontal` container which arranges all of its children in a horizontal row.
Let's look at a quick example of that:

```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Placeholder


class Box(Placeholder):
    """Example widget."""

    DEFAULT_CSS = """
    Box {
        width: 16;
        height: 8;
    }
    """


class ContainerApp(App):
    """Simple app to play with containers."""

    def compose(self) -> ComposeResult:
        with Horizontal():  # (1)!
            yield Box()  # (2)!
            yield Box()
            yield Box()


if __name__ == "__main__":
    app = ContainerApp()
    app.run()
```

2. Any widgets yielded within the Horizontal block will be arranged in a horizontal row.

Here's the output:


Note that inside the `Horizontal` block new widgets will be placed to the right of previous widgets, forming a row.
This will still be the case if you later add or remove widgets.
Without the container, the widgets would be stacked vertically.

### How are containers implemented?

Before I describe some of the other containers, I would like to show how containers are implemented.
The following is the actual source of the `Horizontal` widget:

```python
class Horizontal(Widget):
    """An expanding container with horizontal layout and no scrollbars."""

    DEFAULT_CSS = """
    Horizontal {
        width: 1fr;
        height: 1fr;
        layout: horizontal;
        overflow: hidden hidden;
    }
    """
```

That's it!
A simple widget with a few preset styles.
The other containers are just as simple.

## Horizontal and Vertical

We've seen the `Horizontal` container in action.
The `Vertical` container, as you may have guessed, work the same but arranges its children vertically, i.e. from top to bottom.

You can probably imagine what this looks like, but for sake of completeness, here is an example with a Vertical container:

```python
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Placeholder


class Box(Placeholder):
    """Example widget."""

    DEFAULT_CSS = """
    Box {
        width: 16;
        height: 8;
    }
    """


class ContainerApp(App):
    """Simple app to play with containers."""

    def compose(self) -> ComposeResult:
        with Vertical():  # (1)!
            yield Box()
            yield Box()
            yield Box()


if __name__ == "__main__":
    app = ContainerApp()
    app.run()
```


And here's the output:


Three boxes, vertically stacked.

> **Tip: Styling layout**
>
>
> You can set the layout of a compound widget with the [layout](../styles/layout.md) rule.


### Size behavior

Something to keep in mind when using `Horizontal` or `Vertical` is that they will consume the remaining space in the screen. Let's look at an example to illustrate that.

The following code adds a `with-border` style which draws a green border around the container.
This will help us visualize the dimensions of the container.

```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Placeholder


class Box(Placeholder):
    """Example widget."""

    DEFAULT_CSS = """
    Box {
        width: 16;
        height: 8;
    }
    """


class ContainerApp(App):
    """Simple app to play with containers."""

    CSS = """
    .with-border {
        border: heavy green;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(classes="with-border"):  # (1)!
            yield Box()
            yield Box()
            yield Box()


if __name__ == "__main__":
    app = ContainerApp()
    app.run()
```


Here's the output:


Notice how the container is as large as the screen.
Let's look at what happens if we add another container:

```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Placeholder


class Box(Placeholder):
    """Example widget."""

    DEFAULT_CSS = """
    Box {
        width: 16;
        height: 8;
    }
    """


class ContainerApp(App):
    """Simple app to play with containers."""

    CSS = """
    .with-border {
        border: heavy green;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(classes="with-border"):
            yield Box()
            yield Box()
            yield Box()
        with Horizontal(classes="with-border"):
            yield Box()
            yield Box()
            yield Box()


if __name__ == "__main__":
    app = ContainerApp()
    app.run()
```

And here's the result:


Two horizontal containers divide the remaining screen space in two.
If you were to add another horizontal it would divide the screen space in to thirds&mdash;and so on.

This makes `Horizontal` and `Vertical` excellent for designing the macro layout of your app's interface, but not for making tightly packed rows or columns. For that you need the *group* containers which I'll cover next.

> **Tip: FR Units**
>
>
> You can implement this behavior of dividing the screen in your own widgets with [FR units](../guide/styles.md#fr-units)


## Group containers

The `HorizontalGroup` and `VerticalGroup` containers are very similar to their non-group counterparts, but don't expand to fill the screen space.

Let's look at an example.
In the following code, we have two HorizontalGroups with a border so we can visualize their size.

```python
from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup
from textual.widgets import Placeholder


class Box(Placeholder):
    """Example widget."""

    DEFAULT_CSS = """
    Box {
        width: 16;
        height: 8;
    }
    """


class ContainerApp(App):
    """Simple app to play with containers."""

    CSS = """
    .with-border {
        border: heavy green;
    }
    """

    def compose(self) -> ComposeResult:
        with HorizontalGroup(classes="with-border"):
            yield Box()
            yield Box()
            yield Box()
        with HorizontalGroup(classes="with-border"):
            yield Box()
            yield Box()
            yield Box()


if __name__ == "__main__":
    app = ContainerApp()
    app.run()
```

Here's the output:


We can see that the widgets are arranged horizontally as before, but they only use as much vertical space as required to fit.

## Scrolling containers

Something to watch out for regarding the previous containers we have discussed, is that they don't scroll by default.
Let's see what happens if we add more boxes than could fit on the screen.

In the following example, we will add 10 boxes:

```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Placeholder


class Box(Placeholder):
    """Example widget."""

    DEFAULT_CSS = """
    Box {
        width: 16;
        height: 8;
    }
    """


class ContainerApp(App):
    """Simple app to play with containers."""

    CSS = """
    .with-border {
        border: heavy green;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(classes="with-border"):
            for n in range(10):
                yield Box(label=f"Box {n+1}")


if __name__ == "__main__":
    app = ContainerApp()
    app.run()
```

Here's the output:


We have add 10 `Box` widgets, but there is not enough room for them to fit.
The remaining boxes are off-screen and can't be viewed unless the user resizes their screen.

If we expect more content that fits, we can replacing the containers with `HorizontalScroll` or `VerticalScroll`, which will automatically add scrollbars if required.

Let's make that change:

```python
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll
from textual.widgets import Placeholder


class Box(Placeholder):
    """Example widget."""

    DEFAULT_CSS = """
    Box {
        width: 16;
        height: 8;
    }
    """


class ContainerApp(App):
    """Simple app to play with containers."""

    CSS = """
    .with-border {
        border: heavy green;
    }
    """

    def compose(self) -> ComposeResult:
        with HorizontalScroll(classes="with-border"):
            for n in range(10):
                yield Box(label=f"Box {n+1}")


if __name__ == "__main__":
    app = ContainerApp()
    app.run()
```

Here's the output:


We now have a scrollbar we can click and drag to see all the boxes.

> **Tip: Automatic scrollbars**
>
>
> You can also implement automatic scrollbars with the [overflow](../styles/overflow.md) style.


## Center, Right, and Middle

The `Center`, `Right`, and `Middle` containers are handy for setting the alignment of select widgets.

First lets look at `Center` and `Right` which align their children on the horizontal axis (there is no `Left` container, as this is the default).

Here's an example:

```python
from textual.app import App, ComposeResult
from textual.containers import Center, Right
from textual.widgets import Placeholder


class Box(Placeholder):
    """Example widget."""

    DEFAULT_CSS = """
    Box {
        width: 16;
        height: 5;
    }
    """


class ContainerApp(App):
    """Simple app to play with containers."""

    CSS = """
    .with-border {
        border: heavy green;
    }
    """

    def compose(self) -> ComposeResult:
        yield Box("Box 1")  # (1)!
        with Center(classes="with-border"):  # (2)!
            yield Box("Box 2")
        with Right(classes="with-border"):  # (3)!
            yield Box("Box 3")


if __name__ == "__main__":
    app = ContainerApp()
    app.run()
```

2. Align the child to the center.
3. Align the child to the right edge.

Here's the output:


Note how `Center` and `Right` expand to fill the horizontal dimension, but are only as tall as they need to be.

> **Tip: Alignment in TCSS**
>
>
> You can set alignment in TCSS with the [align](../styles/align.md) rule.


The `Middle` container aligns its children to the center of the *vertical* axis.
Let's look at an example.
The following code aligns three boxes on the vertical axis:

```python
from textual.app import App, ComposeResult
from textual.containers import Middle
from textual.widgets import Placeholder


class Box(Placeholder):
    """Example widget."""

    DEFAULT_CSS = """
    Box {
        width: 16;
        height: 5;
    }
    """


class ContainerApp(App):
    """Simple app to play with containers."""

    CSS = """
    .with-border {
        border: heavy green;
    }
    """

    def compose(self) -> ComposeResult:
        with Middle(classes="with-border"):  # (1)!
            yield Box("Box 1.")
            yield Box("Box 2.")
            yield Box("Box 3.")


if __name__ == "__main__":
    app = ContainerApp()
    app.run()
```


Here's the output:


Note how the container expands on the vertical axis, but fits on the horizontal axis.

## Other containers

This how-to covers the most common widgets, but isn't exhausted.
Be sure to visit the `container reference` for the full list.
There may be new containers added in future versions of Textual.

## Custom containers

The builtin `containers` cover a number of common layout patterns, but are unlikely to cover every possible requirement.
Fortunately, creating your own is easy.
Just like the builtin containers, you can create a container by extending Widget and adding little TCSS.

Here's a template for a custom container:

```python
class MyContainer(Widget):
    """My custom container."""
    DEFAULT_CSS = """
    MyContainer {
        # Your rules here
    }
    """
```

## Summary

- Containers are compound widgets with preset styles for arranging their children.
- ``Horizontal`` and ``Vertical`` containers stretch to fill available space.
- ``HorizontalGroup`` and ``VerticalGroup`` fit to the height of their contents.
- ``HorizontalScroll`` and ``VerticalScroll`` add automatic scrollbars.
- ``Center``, ``Right``, and ``Middle`` set alignment.
- Custom containers are trivial to create.

## See also

- [API: textual.containers](../api/containers.md) - API reference for all container classes
- [Guide: Layout](../guide/layout.md) - In-depth guide to layout in Textual
