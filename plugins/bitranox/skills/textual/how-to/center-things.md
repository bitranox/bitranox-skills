# Center things

If you have ever needed to center something in a web page, you will be glad to know it is **much** easier in Textual.

This article discusses a few different ways in which things can be centered, and the differences between them.

## Aligning widgets

The [align](../styles/align.md) rule will center a widget relative to one or both edges.
This rule is applied to a *container*, and will impact how the container's children are arranged.
Let's see this in practice with a trivial app containing a [Static](../widgets/static.md) widget:

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class CenterApp(App):
    """How to center things."""

    CSS = """
    Screen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Hello, World!")


if __name__ == "__main__":
    app = CenterApp()
    app.run()
```

Here's the output:


The container of the widget is the screen, which has the `align: center middle;` rule applied. The
`center` part tells Textual to align in the horizontal direction, and `middle` tells Textual to align in the vertical direction.

The output *may* surprise you.
The text appears to be aligned in the middle (i.e. vertical edge), but *left* aligned on the horizontal.
This isn't a bug &mdash; I promise.
Let's make a small change to reveal what is happening here.
In the next example, we will add a background and a border to our text:

> **Tip**
>
>
> Adding a border is a very good way of visualizing layout issues, if something isn't behaving as you would expect.


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class CenterApp(App):
    """How to center things."""

    CSS = """
    Screen {
        align: center middle;
    }

    #hello {
        background: blue 50%;
        border: wide white;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Hello, World!", id="hello")


if __name__ == "__main__":
    app = CenterApp()
    app.run()
```

The static widget will now have a blue background and white border:


Note the static widget is as wide as the screen.
Since the widget is as wide as its container, there is no room for it to move in the horizontal direction.

> **Info**
>
>
> The `align` rule applies to *widgets*, not the text.


In order to see the `center` alignment, we will have to make the widget smaller than the width of the screen.
Let's set the width of the Static widget to `auto`, which will make the widget just wide enough to fit the content:

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class CenterApp(App):
    """How to center things."""

    CSS = """
    Screen {
        align: center middle;
    }

    #hello {
        background: blue 50%;
        border: wide white;
        width: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Hello, World!", id="hello")


if __name__ == "__main__":
    app = CenterApp()
    app.run()
```

If you run this now, you should see the widget is aligned on both axis:


## Aligning text

In addition to aligning widgets, you may also want to align *text*.
In order to demonstrate the difference, lets update the example with some longer text.
We will also set the width of the widget to something smaller, to force the text to wrap.

```python
from textual.app import App, ComposeResult
from textual.widgets import Static

QUOTE = "Could not find you in Seattle and no terminal is in operation at your classified address."


class CenterApp(App):
    """How to center things."""

    CSS = """
    Screen {
        align: center middle;
    }

    #hello {
        background: blue 50%;
        border: wide white;
        width: 40;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(QUOTE, id="hello")


if __name__ == "__main__":
    app = CenterApp()
    app.run()
```

Here's what it looks like with longer text:


Note how the widget is centered, but the text within it is flushed to the left edge.
Left aligned text is the default, but you can also center the text with the [text-align](../styles/text_align.md) rule.
Let's center align the longer text by setting this rule:

```python
from textual.app import App, ComposeResult
from textual.widgets import Static

QUOTE = "Could not find you in Seattle and no terminal is in operation at your classified address."


class CenterApp(App):
    """How to center things."""

    CSS = """
    Screen {
        align: center middle;
    }

    #hello {
        background: blue 50%;
        border: wide white;
        width: 40;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(QUOTE, id="hello")


if __name__ == "__main__":
    app = CenterApp()
    app.run()
```

If you run this, you will see that each line of text is individually centered:


You can also use `text-align` to right align text or justify the text (align to both edges).

## Aligning content

There is one last rule that can help us center things.
The [content-align](../styles/content_align.md) rule aligns content *within* a widget.
It treats the text as a rectangular region and positions it relative to the space inside a widget's border.

In order to see why we might need this rule, we need to make the Static widget larger than required to fit the text.
Let's set the height of the Static widget to 9 to give the content room to move:

```python
from textual.app import App, ComposeResult
from textual.widgets import Static

QUOTE = "Could not find you in Seattle and no terminal is in operation at your classified address."


class CenterApp(App):
    """How to center things."""

    CSS = """
    Screen {
        align: center middle;
    }

    #hello {
        background: blue 50%;
        border: wide white;
        width: 40;
        height: 9;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(QUOTE, id="hello")


if __name__ == "__main__":
    app = CenterApp()
    app.run()
```

Here's what it looks like with the larger widget:


Textual aligns a widget's content to the top border by default, which is why the space is below the text.
We can tell Textual to align the content to the center by setting `content-align: center middle`;

> **Note**
>
>
> Strictly speaking, we only need to align the content vertically here (there is no room to move the content left or right)
> So we could have done `content-align-vertical: middle;`


```python
from textual.app import App, ComposeResult
from textual.widgets import Static

QUOTE = "Could not find you in Seattle and no terminal is in operation at your classified address."


class CenterApp(App):
    """How to center things."""

    CSS = """
    Screen {
        align: center middle;
    }

    #hello {
        background: blue 50%;
        border: wide white;
        width: 40;
        height: 9;
        text-align: center;
        content-align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(QUOTE, id="hello")


if __name__ == "__main__":
    app = CenterApp()
    app.run()
```

If you run this now, the content will be centered within the widget:


## Aligning multiple widgets

It's just as easy to align multiple widgets as it is a single widget.
Applying `align: center middle;` to the parent widget (screen or other container) will align all its children.

Let's create an example with two widgets.
The following code adds two widgets with auto dimensions:

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class CenterApp(App):
    """How to center things."""

    CSS = """
    .words {
        background: blue 50%;
        border: wide white;
        width: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("How about a nice game", classes="words")
        yield Static("of chess?", classes="words")


if __name__ == "__main__":
    app = CenterApp()
    app.run()
```

This produces the following output:


We can center both those widgets by applying the `align` rule as before:

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class CenterApp(App):
    """How to center things."""

    CSS = """
    Screen {
        align: center middle;
    }

    .words {
        background: blue 50%;
        border: wide white;
        width: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("How about a nice game", classes="words")
        yield Static("of chess?", classes="words")


if __name__ == "__main__":
    app = CenterApp()
    app.run()
```

Here's the output:


Note how the widgets are aligned as if they are a single group.
In other words, their position relative to each other didn't change, just their position relative to the screen.

If you do want to center each widget independently, you can place each widget inside its own container, and set `align` for those containers.
Textual has a builtin ``Center`` container for just this purpose.

Let's wrap our two widgets in a `Center` container:

```python
from textual.app import App, ComposeResult
from textual.containers import Center
from textual.widgets import Static


class CenterApp(App):
    """How to center things."""

    CSS = """
    Screen {
        align: center middle;
    }

    .words {
        background: blue 50%;
        border: wide white;
        width: auto;
    }
    """

    def compose(self) -> ComposeResult:
        with Center():
            yield Static("How about a nice game", classes="words")
        with Center():
            yield Static("of chess?", classes="words")


if __name__ == "__main__":
    app = CenterApp()
    app.run()
```

If you run this, you will see that the widgets are centered relative to each other, not just the screen:


## Summary

Keep the following in mind when you want to center content in Textual:

- In order to center a widget, it needs to be smaller than its container.
- The `align` rule is applied to the *parent* of the widget you want to center (i.e. the widget's container).
- The `text-align` rule aligns text on a line by line basis.
- The `content-align` rule aligns content *within* a widget.
- Use the ``Center`` container if you want to align multiple widgets relative to each other.
- Add a border if the alignment isn't working as you would expect.

## See also

- [Guide: Layout](../guide/layout.md) - In-depth guide to layout in Textual
- [Style: align](../styles/align.md) - Reference for the align CSS rule
- [Style: content-align](../styles/content_align.md) - Reference for the content-align CSS rule

---

If you need further help, we are here to [help](../help.md).
