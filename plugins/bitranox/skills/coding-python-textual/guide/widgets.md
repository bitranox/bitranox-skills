# Widgets

In this chapter we will explore widgets in more detail, and how you can create custom widgets of your own.


## What is a widget?

A widget is a component of your UI responsible for managing a rectangular region of the screen. Widgets may respond to [events](./events.md) in much the same way as an app. In many respects, widgets are like mini-apps.

> **Information**
>
>
> Every widget runs in its own asyncio task.


## Custom widgets

There is a growing collection of [builtin widgets](../widgets/index.md) in Textual, but you can build entirely custom widgets that work in the same way.

The first step in building a widget is to import and extend a widget class. This can either be `Widget` which is the base class of all widgets, or one of its subclasses.

Let's create a simple custom widget to display a greeting.


```python
from textual.app import App, ComposeResult, RenderResult
from textual.widget import Widget


class Hello(Widget):
    """Display a greeting."""

    def render(self) -> RenderResult:
        return "Hello, [b]World[/b]!"


class CustomApp(App):
    def compose(self) -> ComposeResult:
        yield Hello()


if __name__ == "__main__":
    app = CustomApp()
    app.run()
```

The highlighted lines define a custom widget class with just a `render()` method.
Textual will display whatever is returned from render in the [content](./content.md) area of your widget.

Note that the text contains tags in square brackets, i.e. `[b]`.
This is [content markup](./content.md#markup) which allows you to embed various styles within your content.
If you run this you will find that `World` is in bold.


This (very simple) custom widget may be [styled](./styles.md) in the same way as builtin widgets, and targeted with CSS. Let's add some CSS to this app.


**hello02.py**


```python
from textual.app import App, ComposeResult, RenderResult
from textual.widget import Widget


class Hello(Widget):
    """Display a greeting."""

    def render(self) -> RenderResult:
        return "Hello, [b]World[/b]!"


class CustomApp(App):
    CSS_PATH = "hello02.tcss"

    def compose(self) -> ComposeResult:
        yield Hello()


if __name__ == "__main__":
    app = CustomApp()
    app.run()
```

**hello02.tcss**


```css
Screen {
    align: center middle;
}

Hello {
    width: 40;
    height: 9;
    padding: 1 2;
    background: $panel;
    color: $text;
    border: $secondary tall;
    content-align: center middle;
}
```
The addition of the CSS has completely transformed our custom widget.


## Static widget

While you can extend the Widget class, a subclass will typically be a better starting point. The `Static` class is a widget subclass which caches the result of render, and provides an `update()` method to update the content area.

Let's use Static to create a widget which cycles through "hello" in various languages.

**hello03.py**


```python
from itertools import cycle

from textual.app import App, ComposeResult
from textual.widgets import Static

hellos = cycle(
    [
        "Hola",
        "Bonjour",
        "Guten tag",
        "Salve",
        "Nǐn hǎo",
        "Olá",
        "Asalaam alaikum",
        "Konnichiwa",
        "Anyoung haseyo",
        "Zdravstvuyte",
        "Hello",
    ]
)


class Hello(Static):
    """Display a greeting."""

    def on_mount(self) -> None:
        self.next_word()

    def on_click(self) -> None:
        self.next_word()

    def next_word(self) -> None:
        """Get a new hello and update the content area."""
        hello = next(hellos)
        self.update(f"{hello}, [b]World[/b]!")


class CustomApp(App):
    CSS_PATH = "hello03.tcss"

    def compose(self) -> ComposeResult:
        yield Hello()


if __name__ == "__main__":
    app = CustomApp()
    app.run()
```

**hello03.tcss**


```css
Screen {
    align: center middle;
}

Hello {
    width: 40;
    height: 9;
    padding: 1 2;
    background: $panel;
    border: $secondary tall;
    content-align: center middle;
}
```
Note that there is no `render()` method on this widget. The Static class is handling the render for us. Instead we call `update()` when we want to update the content within the widget.

The `next_word` method updates the greeting. We call this method from the mount handler to get the first word, and from a click handler to cycle through the greetings when we click the widget.

### Default CSS

When building an app it is best to keep your CSS in an external file. This allows you to see all your CSS in one place, and to enable live editing. However if you intend to distribute a widget (via PyPI for instance) it can be convenient to bundle the code and CSS together. You can do this by adding a `DEFAULT_CSS` class variable inside your widget class.

Textual's builtin widgets bundle CSS in this way, which is why you can see nicely styled widgets without having to copy any CSS code.

Here's the Hello example again, this time the widget has embedded default CSS:

**hello04.py**


```python
from itertools import cycle

from textual.app import App, ComposeResult
from textual.widgets import Static

hellos = cycle(
    [
        "Hola",
        "Bonjour",
        "Guten tag",
        "Salve",
        "Nǐn hǎo",
        "Olá",
        "Asalaam alaikum",
        "Konnichiwa",
        "Anyoung haseyo",
        "Zdravstvuyte",
        "Hello",
    ]
)


class Hello(Static):
    """Display a greeting."""

    DEFAULT_CSS = """
    Hello {
        width: 40;
        height: 9;
        padding: 1 2;
        background: $panel;
        border: $secondary tall;
        content-align: center middle;
    }
    """

    def on_mount(self) -> None:
        self.next_word()

    def on_click(self) -> None:
        self.next_word()

    def next_word(self) -> None:
        """Get a new hello and update the content area."""
        hello = next(hellos)
        self.update(f"{hello}, [b]World[/b]!")


class CustomApp(App):
    CSS_PATH = "hello04.tcss"

    def compose(self) -> ComposeResult:
        yield Hello()


if __name__ == "__main__":
    app = CustomApp()
    app.run()
```

**hello04.tcss**


```css
Screen {
    align: center middle;
}
```
#### Scoped CSS

Default CSS is *scoped* by default.
All this means is that CSS defined in `DEFAULT_CSS` will affect the widget and potentially its children only.
This is to prevent you from inadvertently breaking an unrelated widget.

You can disable scoped CSS by setting the class var `SCOPED_CSS` to `False`.

#### Default specificity

CSS defined within `DEFAULT_CSS` has an automatically lower [specificity](./CSS.md#specificity) than CSS read from either the App's `CSS` class variable or an external stylesheet. In practice this means that your app's CSS will take precedence over any CSS bundled with widgets.


## Text links

Text in a widget may be marked up with links which perform an action when clicked.
Links in markup use the following format:

```
"Click [@click=app.bell]Me[/]"
```

The `@click` tag introduces a click handler, which runs the `app.bell` action.

Let's use links in the hello example so that the greeting becomes a link which updates the widget.


**hello05.py**


```python
from itertools import cycle

from textual.app import App, ComposeResult
from textual.widgets import Static

hellos = cycle(
    [
        "Hola",
        "Bonjour",
        "Guten tag",
        "Salve",
        "Nǐn hǎo",
        "Olá",
        "Asalaam alaikum",
        "Konnichiwa",
        "Anyoung haseyo",
        "Zdravstvuyte",
        "Hello",
    ]
)


class Hello(Static):
    """Display a greeting."""

    def on_mount(self) -> None:
        self.action_next_word()

    def action_next_word(self) -> None:
        """Get a new hello and update the content area."""
        hello = next(hellos)
        self.update(f"[@click='next_word']{hello}[/], [b]World[/b]!")


class CustomApp(App):
    CSS_PATH = "hello05.tcss"

    def compose(self) -> ComposeResult:
        yield Hello()


if __name__ == "__main__":
    app = CustomApp()
    app.run()
```

**hello05.tcss**


```css
Screen {
    align: center middle;
}

Hello {
    width: 40;
    height: 9;
    padding: 1 2;
    background: $panel;
    border: $secondary tall;
    content-align: center middle;
}
```
If you run this example you will see that the greeting has been underlined, which indicates it is clickable. If you click on the greeting it will run the `next_word` action which updates the next word.


## Border titles

Every widget has a ``border_title`` and ``border_subtitle`` attribute.
Setting `border_title` will display text within the top border, and setting `border_subtitle` will display text within the bottom border.

> **Note**
>
>
> Border titles will only display if the widget has a [border](../styles/border.md) enabled.


The default value for these attributes is empty string, which disables the title.
You can change the default value for the title attributes with the ``BORDER_TITLE`` and ``BORDER_SUBTITLE`` class variables.

Let's demonstrate setting a title, both as a class variable and an instance variable:


**hello06.py**


```python
from itertools import cycle

from textual.app import App, ComposeResult
from textual.widgets import Static

hellos = cycle(
    [
        "Hola",
        "Bonjour",
        "Guten tag",
        "Salve",
        "Nǐn hǎo",
        "Olá",
        "Asalaam alaikum",
        "Konnichiwa",
        "Anyoung haseyo",
        "Zdravstvuyte",
        "Hello",
    ]
)


class Hello(Static):
    """Display a greeting."""

    BORDER_TITLE = "Hello Widget"  # (1)!

    def on_mount(self) -> None:
        self.action_next_word()
        self.border_subtitle = "Click for next hello"  # (2)!

    def action_next_word(self) -> None:
        """Get a new hello and update the content area."""
        hello = next(hellos)
        self.update(f"[@click='next_word']{hello}[/], [b]World[/b]!")


class CustomApp(App):
    CSS_PATH = "hello05.tcss"

    def compose(self) -> ComposeResult:
        yield Hello()


if __name__ == "__main__":
    app = CustomApp()
    app.run()
```

2. Setting `subtitle` via an instance attribute.

**hello06.tcss**


```css
Screen {
    align: center middle;
}

Hello {
    width: 40;
    height: 9;
    padding: 1 2;
    background: $panel;
    border: $secondary tall;
    content-align: center middle;
}
```
Note that titles are limited to a single line of text.
If the supplied text is too long to fit within the widget, it will be cropped (and an ellipsis added).

There are a number of styles that influence how titles are displayed (color and alignment).
See the [style reference](../styles/index.md) for details.

## Focus & keybindings

Widgets can have a list of associated key [bindings](../guide/input.md#bindings),
which let them call [actions](../guide/actions.md) in response to key presses.

A widget is able to handle key presses if it or one of its descendants has [focus](../guide/input.md#input-focus).

Widgets aren't focusable by default.
To allow a widget to be focused, we need to set `can_focus=True` when defining a widget subclass.
Here's an example of a simple focusable widget:

**counter01.py**


```python
from textual.app import App, ComposeResult, RenderResult
from textual.reactive import reactive
from textual.widgets import Footer, Static


class Counter(Static, can_focus=True):  # (1)!
    """A counter that can be incremented and decremented by pressing keys."""

    count = reactive(0)

    def render(self) -> RenderResult:
        return f"Count: {self.count}"


class CounterApp(App[None]):
    CSS_PATH = "counter.tcss"

    def compose(self) -> ComposeResult:
        yield Counter()
        yield Counter()
        yield Counter()
        yield Footer()


if __name__ == "__main__":
    app = CounterApp()
    app.run()
```


**counter.tcss**


```css
Counter {
    background: $panel-darken-1;
    padding: 1 2;
    color: $text-muted;

    &:focus {  /* (1)! */
        background: $primary;
        color: $text;
        text-style: bold;
        outline-left: thick $accent;
    }
}
```


The app above contains three `Counter` widgets, which we can focus by clicking or using `Tab` and `Shift+Tab`.

Now that our counter is focusable, let's add some keybindings to it to allow us to change the count using the keyboard.
To do this, we add a `BINDINGS` class variable to `Counter`, with bindings for `Up` and `Down`.
These new bindings are linked to the `change_count` action, which updates the `count` reactive attribute.

With our bindings in place, we can now change the count of the _currently focused_ counter using `Up` and `Down`.

**counter02.py**


```python
from textual.app import App, ComposeResult, RenderResult
from textual.reactive import reactive
from textual.widgets import Footer, Static


class Counter(Static, can_focus=True):
    """A counter that can be incremented and decremented by pressing keys."""

    BINDINGS = [
        ("up,k", "change_count(1)", "Increment"),  # (1)!
        ("down,j", "change_count(-1)", "Decrement"),
    ]

    count = reactive(0)

    def render(self) -> RenderResult:
        return f"Count: {self.count}"

    def action_change_count(self, amount: int) -> None:  # (2)!
        self.count += amount


class CounterApp(App[None]):
    CSS_PATH = "counter.tcss"

    def compose(self) -> ComposeResult:
        yield Counter()
        yield Counter()
        yield Counter()
        yield Footer()


if __name__ == "__main__":
    app = CounterApp()
    app.run()
```

2. Called when the binding is triggered. Take care to add the `action_` prefix to the method name.

**counter.tcss**


```css
Counter {
    background: $panel-darken-1;
    padding: 1 2;
    color: $text-muted;

    &:focus {  /* (1)! */
        background: $primary;
        color: $text;
        text-style: bold;
        outline-left: thick $accent;
    }
}
```


## Rich renderables

In previous examples we've set strings as content for Widgets. You can also use special objects called [renderables](https://rich.readthedocs.io/en/latest/protocol.html) for advanced visuals. You can use any renderable defined in [Rich](https://github.com/Textualize/rich) or third party libraries.

Lets make a widget that uses a Rich table for its content. The following app is a solution to the classic [fizzbuzz](https://en.wikipedia.org/wiki/Fizz_buzz) problem often used to screen software engineers in job interviews. The problem is this: Count up from 1 to 100, when the number is divisible by 3, output "fizz"; when the number is divisible by 5, output "buzz"; and when the number is divisible by both 3 and 5 output "fizzbuzz".

This app will "play" fizz buzz by displaying a table of the first 15 numbers and columns for fizz and buzz.

**fizzbuzz01.py**


```python
from rich.table import Table

from textual.app import App, ComposeResult
from textual.widgets import Static


class FizzBuzz(Static):
    def on_mount(self) -> None:
        table = Table("Number", "Fizz?", "Buzz?")
        for n in range(1, 16):
            fizz = not n % 3
            buzz = not n % 5
            table.add_row(
                str(n),
                "fizz" if fizz else "",
                "buzz" if buzz else "",
            )
        self.update(table)


class FizzBuzzApp(App):
    CSS_PATH = "fizzbuzz01.tcss"

    def compose(self) -> ComposeResult:
        yield FizzBuzz()


if __name__ == "__main__":
    app = FizzBuzzApp()
    app.run()
```

**fizzbuzz01.tcss**


```css
Screen {
    align: center middle;
}

FizzBuzz {
    width: auto;
    height: auto;
    background: $primary;
    color: $text;
}
```
## Content size

Textual will auto-detect the dimensions of the content area from rich renderables if width or height is set to `auto`. You can override auto dimensions by implementing `get_content_width()` or `get_content_height()`.

Let's modify the default width for the fizzbuzz example. By default, the table will be just wide enough to fix the columns. Let's force it to be 50 characters wide.


**fizzbuzz02.py**


```python
from rich.table import Table

from textual.app import App, ComposeResult
from textual.geometry import Size
from textual.widgets import Static


class FizzBuzz(Static):
    def on_mount(self) -> None:
        table = Table("Number", "Fizz?", "Buzz?", expand=True)
        for n in range(1, 16):
            fizz = not n % 3
            buzz = not n % 5
            table.add_row(
                str(n),
                "fizz" if fizz else "",
                "buzz" if buzz else "",
            )
        self.update(table)

    def get_content_width(self, container: Size, viewport: Size) -> int:
        """Force content width size."""
        return 50


class FizzBuzzApp(App):
    CSS_PATH = "fizzbuzz02.tcss"

    def compose(self) -> ComposeResult:
        yield FizzBuzz()


if __name__ == "__main__":
    app = FizzBuzzApp()
    app.run()
```

**fizzbuzz02.tcss**


```css
Screen {
    align: center middle;
}

FizzBuzz {
    width: auto;
    height: auto;
    background: $primary;
    color: $text;
}
```
Note that we've added `expand=True` to tell the `Table` to expand beyond the optimal width, so that it fills the 50 characters returned by `get_content_width`.

## Tooltips

Widgets can have *tooltips* which is content displayed when the user hovers the mouse over the widget.
You can use tooltips to add supplementary information or help messages.

> **Tip**
>
>
> It is best not to rely on tooltips for essential information.
> Some users prefer to use the keyboard exclusively and may never see tooltips.


To add a tooltip, assign to the widget's ``tooltip`` property.
You can set text or any other [Rich](https://github.com/Textualize/rich) renderable.

The following example adds a tooltip to a button:

**tooltip01.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Button

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear."""


class TooltipApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("Click me", variant="success")

    def on_mount(self) -> None:
        self.query_one(Button).tooltip = TEXT


if __name__ == "__main__":
    app = TooltipApp()
    app.run()
```
### Customizing the tooltip

If you don't like the default look of the tooltips, you can customize them to your liking with CSS.
Add a rule to your CSS that targets `Tooltip`. Here's an example:

**tooltip02.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Button

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear."""


class TooltipApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    Tooltip {
        padding: 2 4;
        background: $primary;
        color: auto 90%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("Click me", variant="success")

    def on_mount(self) -> None:
        self.query_one(Button).tooltip = TEXT


if __name__ == "__main__":
    app = TooltipApp()
    app.run()
```
## Loading indicator

Widgets have a ``loading`` reactive which when set to `True` will temporarily replace your widget with a [`LoadingIndicator`](../widgets/loading_indicator.md).

You can use this to indicate to the user that the app is currently working on getting data, and there will be content when that data is available.
Let's look at an example of this.

**loading01.py**


```python
from asyncio import sleep
from random import randint

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import DataTable

ROWS = [
    ("lane", "swimmer", "country", "time"),
    (4, "Joseph Schooling", "Singapore", 50.39),
    (2, "Michael Phelps", "United States", 51.14),
    (5, "Chad le Clos", "South Africa", 51.14),
    (6, "László Cseh", "Hungary", 51.14),
    (3, "Li Zhuhao", "China", 51.26),
    (8, "Mehdy Metella", "France", 51.58),
    (7, "Tom Shields", "United States", 51.73),
    (1, "Aleksandr Sadovnikov", "Russia", 51.84),
    (10, "Darren Burns", "Scotland", 51.84),
]


class DataApp(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
    }
    DataTable {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable()
        yield DataTable()
        yield DataTable()
        yield DataTable()

    def on_mount(self) -> None:
        for data_table in self.query(DataTable):
            data_table.loading = True  # (1)!
            self.load_data(data_table)

    @work
    async def load_data(self, data_table: DataTable) -> None:
        await sleep(randint(2, 10))  # (2)!
        data_table.add_columns(*ROWS[0])
        data_table.add_rows(ROWS[1:])
        data_table.loading = False  # (3)!


if __name__ == "__main__":
    app = DataApp()
    app.run()
```

2. Insert a random sleep to simulate a network request.
3. Show the new data.


In this example we have four [DataTable](../widgets/data_table.md) widgets, which we put into a loading state by setting the widget's `loading` property to `True`.
This will temporarily replace the widget with a loading indicator animation.
When the (simulated) data has been retrieved, we reset the `loading` property to show the new data.

> **Tip**
>
>
> See the guide on [Workers](./workers.md) if you want to know more about the `@work` decorator.


## Line API

A downside of widgets that return Rich renderables is that Textual will redraw the entire widget when its state is updated or it changes size.
If a widget is large enough to require scrolling, or updates frequently, then this redrawing can make your app feel less responsive.
Textual offers an alternative API which reduces the amount of work required to refresh a widget, and makes it possible to update portions of a widget (as small as a single character) without a full redraw. This is known as the *line API*.

> **Note**
>
>
> The Line API requires a little more work that typical Rich renderables, but can produce powerful widgets such as the builtin [DataTable](../widgets/data_table.md) which can handle thousands or even millions of rows.


### Render Line method

To build a widget with the line API, implement a `render_line` method rather than a `render` method. The `render_line` method takes a single integer argument `y` which is an offset from the top of the widget, and should return a `Strip` object containing that line's content.
Textual will call this method as required to get content for every row of characters in the widget.

![Render line](../images/render_line.excalidraw.svg)

Let's look at an example before we go into the details. The following Textual app implements a widget with the line API that renders a checkerboard pattern. This might form the basis of a chess / checkers game. Here's the code:

**checker01.py**


```python
from rich.segment import Segment
from rich.style import Style

from textual.app import App, ComposeResult
from textual.strip import Strip
from textual.widget import Widget


class CheckerBoard(Widget):
    """Render an 8x8 checkerboard."""

    def render_line(self, y: int) -> Strip:
        """Render a line of the widget. y is relative to the top of the widget."""

        row_index = y // 4  # A checkerboard square consists of 4 rows

        if row_index >= 8:  # Generate blank lines when we reach the end
            return Strip.blank(self.size.width)

        is_odd = row_index % 2  # Used to alternate the starting square on each row

        white = Style.parse("on white")  # Get a style object for a white background
        black = Style.parse("on black")  # Get a style object for a black background

        # Generate a list of segments with alternating black and white space characters
        segments = [
            Segment(" " * 8, black if (column + is_odd) % 2 else white)
            for column in range(8)
        ]
        strip = Strip(segments, 8 * 8)
        return strip


class BoardApp(App):
    """A simple app to show our widget."""

    def compose(self) -> ComposeResult:
        yield CheckerBoard()


if __name__ == "__main__":
    app = BoardApp()
    app.run()
```
The `render_line` method above calculates a `Strip` for every row of characters in the widget. Each strip contains alternating black and white space characters which form the squares in the checkerboard.

You may have noticed that the checkerboard widget makes use of some objects we haven't covered before. Let's explore those.

#### Segment and Style

A [Segment](https://rich.readthedocs.io/en/latest/protocol.html#low-level-render) is a class borrowed from the [Rich](https://github.com/Textualize/rich) project. It is small object (actually a named tuple) which bundles a string to be displayed and a [Style](https://rich.readthedocs.io/en/latest/style.html) which tells Textual how the text should look (color, bold, italic etc).

Let's look at a simple segment which would produce the text "Hello, World!" in bold.

```python
greeting = Segment("Hello, World!", Style(bold=True))
```

This would create the following object:

![Segment](../images/segment.excalidraw.svg)

Both Rich and Textual work with segments to generate content. A Textual app is the result of combining hundreds, or perhaps thousands, of segments,

#### Strips

A `Strip` is a container for a number of segments covering a single *line* (or row) in the Widget. A Strip will contain at least one segment, but often many more.

A `Strip` is constructed from a list of `Segment` objects. Here's now you might construct a strip that displays the text "Hello, World!", but with the second word in bold:

```python
segments = [
    Segment("Hello, "),
    Segment("World", Style(bold=True)),
    Segment("!")
]
strip = Strip(segments)
```

The first and third `Segment` omit a style, which results in the widget's default style being used. The second segment has a style object which applies bold to the text "World". If this were part of a widget it would produce the text: <code>Hello, **World**!</code>

The `Strip` constructor has an optional second parameter, which should be the *cell length* of the strip. The strip above has a length of 13, so we could have constructed it like this:

```python
strip = Strip(segments, 13)
```

Note that the cell length parameter is _not_ the total number of characters in the string. It is the number of terminal "cells". Some characters (such as Asian language characters and certain emoji) take up the space of two Western alphabet characters. If you don't know in advance the number of cells your segments will occupy, it is best to omit the length parameter so that Textual calculates it automatically.

### Component classes

When applying styles to widgets we can use CSS to select the child widgets. Widgets rendered with the line API don't have children per-se, but we can still use CSS to apply styles to parts of our widget by defining *component classes*. Component classes are associated with a widget by defining a `COMPONENT_CLASSES` class variable which should be a `set` of strings containing CSS class names.

In the checkerboard example above we hard-coded the color of the squares to "white" and "black". But what if we want to create a checkerboard with different colors? We can do this by defining two component classes, one for the "white" squares and one for the "dark" squares. This will allow us to change the colors with CSS.

The following example replaces our hard-coded colors with component classes.

**checker02.py**


```python
from rich.segment import Segment

from textual.app import App, ComposeResult
from textual.strip import Strip
from textual.widget import Widget


class CheckerBoard(Widget):
    """Render an 8x8 checkerboard."""

    COMPONENT_CLASSES = {
        "checkerboard--white-square",
        "checkerboard--black-square",
    }

    DEFAULT_CSS = """
    CheckerBoard .checkerboard--white-square {
        background: #A5BAC9;
    }
    CheckerBoard .checkerboard--black-square {
        background: #004578;
    }
    """

    def render_line(self, y: int) -> Strip:
        """Render a line of the widget. y is relative to the top of the widget."""

        row_index = y // 4  # four lines per row

        if row_index >= 8:
            return Strip.blank(self.size.width)

        is_odd = row_index % 2

        white = self.get_component_rich_style("checkerboard--white-square")
        black = self.get_component_rich_style("checkerboard--black-square")

        segments = [
            Segment(" " * 8, black if (column + is_odd) % 2 else white)
            for column in range(8)
        ]
        strip = Strip(segments, 8 * 8)
        return strip


class BoardApp(App):
    """A simple app to show our widget."""

    def compose(self) -> ComposeResult:
        yield CheckerBoard()


if __name__ == "__main__":
    app = BoardApp()
    app.run()
```
The `COMPONENT_CLASSES` class variable above adds two class names: `checkerboard--white-square` and `checkerboard--black-square`. These are set in the `DEFAULT_CSS` but can modified in the app's `CSS` class variable or external CSS.

> **Tip**
>
>
> Component classes typically begin with the name of the widget followed by *two* hyphens. This is a convention to avoid potential name clashes.


The `render_line` method calls `get_component_rich_style` to get `Style` objects from the CSS, which we apply to the segments to create a more colorful looking checkerboard.

### Scrolling

A Line API widget can be made to scroll by extending the `ScrollView` class (rather than `Widget`).
The `ScrollView` class will do most of the work, but we will need to manage the following details:

2. We need to update the `render_line` method to generate strips for the visible area of the widget, taking into account the current position of the scrollbars.

Let's add scrolling to our checkerboard example. A standard 8 x 8 board isn't sufficient to demonstrate scrolling so we will make the size of the board configurable and set it to 100 x 100, for a total of 10,000 squares.

**checker03.py**


```python
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.geometry import Size
from textual.strip import Strip
from textual.scroll_view import ScrollView

from rich.segment import Segment


class CheckerBoard(ScrollView):
    COMPONENT_CLASSES = {
        "checkerboard--white-square",
        "checkerboard--black-square",
    }

    DEFAULT_CSS = """
    CheckerBoard .checkerboard--white-square {
        background: #A5BAC9;
    }
    CheckerBoard .checkerboard--black-square {
        background: #004578;
    }
    """

    def __init__(self, board_size: int) -> None:
        super().__init__()
        self.board_size = board_size
        # Each square is 4 rows and 8 columns
        self.virtual_size = Size(board_size * 8, board_size * 4)

    def render_line(self, y: int) -> Strip:
        """Render a line of the widget. y is relative to the top of the widget."""

        scroll_x, scroll_y = self.scroll_offset  # The current scroll position
        y += scroll_y  # The line at the top of the widget is now `scroll_y`, not zero!
        row_index = y // 4  # four lines per row

        white = self.get_component_rich_style("checkerboard--white-square")
        black = self.get_component_rich_style("checkerboard--black-square")

        if row_index >= self.board_size:
            return Strip.blank(self.size.width)

        is_odd = row_index % 2

        segments = [
            Segment(" " * 8, black if (column + is_odd) % 2 else white)
            for column in range(self.board_size)
        ]
        strip = Strip(segments, self.board_size * 8)
        # Crop the strip so that it covers the visible area
        strip = strip.crop(scroll_x, scroll_x + self.size.width)
        return strip


class BoardApp(App):
    def compose(self) -> ComposeResult:
        yield CheckerBoard(100)


if __name__ == "__main__":
    app = BoardApp()
    app.run()
```
The virtual size is set in the constructor to match the total size of the board, which will enable scrollbars (unless you have your terminal zoomed out very far). You can update the `virtual_size` attribute dynamically as required, but our checkerboard isn't going to change size so we only need to set it once.

The `render_line` method gets the *scroll offset* which is an `Offset` containing the current position of the scrollbars. We add `scroll_offset.y` to the `y` argument because `y` is relative to the top of the widget, and we need a Y coordinate relative to the scrollable content.

We also need to compensate for the position of the horizontal scrollbar. This is done in the call to `strip.crop` which *crops* the strip to the visible area between `scroll_x` and `scroll_x + self.size.width`.

> **Tip**
>
>
> `Strip` objects are immutable, so methods will return a new Strip rather than modifying the original.


![Scroll view](../images/scroll_view.excalidraw.svg)

### Region updates

The Line API makes it possible to refresh parts of a widget, as small as a single character.
Refreshing smaller regions makes updates more efficient, and keeps your widget feeling responsive.

To demonstrate this we will update the checkerboard to highlight the square under the mouse pointer.
Here's the code:

**checker04.py**


```python
from __future__ import annotations

from textual import events
from textual.app import App, ComposeResult
from textual.geometry import Offset, Region, Size
from textual.reactive import var
from textual.strip import Strip
from textual.scroll_view import ScrollView

from rich.segment import Segment
from rich.style import Style


class CheckerBoard(ScrollView):
    COMPONENT_CLASSES = {
        "checkerboard--white-square",
        "checkerboard--black-square",
        "checkerboard--cursor-square",
    }

    DEFAULT_CSS = """
    CheckerBoard > .checkerboard--white-square {
        background: #A5BAC9;
    }
    CheckerBoard > .checkerboard--black-square {
        background: #004578;
    }
    CheckerBoard > .checkerboard--cursor-square {
        background: darkred;
    }
    """

    cursor_square = var(Offset(0, 0))

    def __init__(self, board_size: int) -> None:
        super().__init__()
        self.board_size = board_size
        # Each square is 4 rows and 8 columns
        self.virtual_size = Size(board_size * 8, board_size * 4)

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Called when the user moves the mouse over the widget."""
        mouse_position = event.offset + self.scroll_offset
        self.cursor_square = Offset(mouse_position.x // 8, mouse_position.y // 4)

    def watch_cursor_square(
        self, previous_square: Offset, cursor_square: Offset
    ) -> None:
        """Called when the cursor square changes."""

        def get_square_region(square_offset: Offset) -> Region:
            """Get region relative to widget from square coordinate."""
            x, y = square_offset
            region = Region(x * 8, y * 4, 8, 4)
            # Move the region into the widgets frame of reference
            region = region.translate(-self.scroll_offset)
            return region

        # Refresh the previous cursor square
        self.refresh(get_square_region(previous_square))

        # Refresh the new cursor square
        self.refresh(get_square_region(cursor_square))

    def render_line(self, y: int) -> Strip:
        """Render a line of the widget. y is relative to the top of the widget."""

        scroll_x, scroll_y = self.scroll_offset  # The current scroll position
        y += scroll_y  # The line at the top of the widget is now `scroll_y`, not zero!
        row_index = y // 4  # four lines per row

        white = self.get_component_rich_style("checkerboard--white-square")
        black = self.get_component_rich_style("checkerboard--black-square")
        cursor = self.get_component_rich_style("checkerboard--cursor-square")

        if row_index >= self.board_size:
            return Strip.blank(self.size.width)

        is_odd = row_index % 2

        def get_square_style(column: int, row: int) -> Style:
            """Get the cursor style at the given position on the checkerboard."""
            if self.cursor_square == Offset(column, row):
                square_style = cursor
            else:
                square_style = black if (column + is_odd) % 2 else white
            return square_style

        segments = [
            Segment(" " * 8, get_square_style(column, row_index))
            for column in range(self.board_size)
        ]
        strip = Strip(segments, self.board_size * 8)
        # Crop the strip so that is covers the visible area
        strip = strip.crop(scroll_x, scroll_x + self.size.width)
        return strip


class BoardApp(App):
    def compose(self) -> ComposeResult:
        yield CheckerBoard(100)


if __name__ == "__main__":
    app = BoardApp()
    app.run()
```
We've added a style to the checkerboard which is the color of the highlighted square, with a default of "darkred".
We will need this when we come to render the highlighted square.

We've also added a [reactive variable](./reactivity.md) called `cursor_square` which will hold the coordinate of the square underneath the mouse. Note that we have used `var` which gives us reactive superpowers but won't automatically refresh the whole widget, because we want to update only the squares under the cursor.

The `on_mouse_move` handler takes the mouse coordinates from the `MouseMove` object and calculates the coordinate of the square underneath the mouse. There's a little math here, so let's break it down.

- The event contains the coordinates of the mouse relative to the top left of the widget, but we need the coordinate relative to the top left of board which depends on the position of the scrollbars.
We can perform this conversion by adding `self.scroll_offset` to `event.offset`.
- Once we have the board coordinate underneath the mouse we divide the x coordinate by 8 and divide the y coordinate by 4 to give us the coordinate of a square.

If the cursor square coordinate calculated in `on_mouse_move` changes, Textual will call `watch_cursor_square` with the previous coordinate and new coordinate of the square. This method works out the regions of the widget to update and essentially does the reverse of the steps we took to go from mouse coordinates to square coordinates.
The `get_square_region` function calculates a `Region` object for each square and uses them as a positional argument in a call to `refresh`. Passing Region objects to `refresh` tells Textual to update only the cells underneath those regions, and not the entire widget.

> **Note**
>
>
> Textual is smart about performing updates. If you refresh multiple regions, Textual will combine them into as few non-overlapping regions as possible.


The final step is to update the `render_line` method to use the cursor style when rendering the square underneath the mouse.

You should find that if you move the mouse over the widget now, it will highlight the square underneath the mouse pointer in red.

### Line API examples

The following builtin widgets use the Line API. If you are building advanced widgets, it may be worth looking through the code for inspiration!

- [DataTable](https://github.com/Textualize/textual/blob/main/src/textual/widgets/_data_table.py)
- [RichLog](https://github.com/Textualize/textual/blob/main/src/textual/widgets/_rich_log.py)
- [Tree](https://github.com/Textualize/textual/blob/main/src/textual/widgets/_tree.py)

## Compound widgets

Widgets may be combined to create new widgets with additional features.
Such widgets are known as *compound widgets*.
The stopwatch in the [tutorial](../tutorial.md) is an example of a compound widget.

A compound widget can be used like any other widget.
The only thing that differs is that when you build a compound widget, you write a `compose()` method which yields *child* widgets, rather than implement a `render` or `render_line` method.

The following is an example of a compound widget.

**compound01.py**


```python
from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import Input, Label


class InputWithLabel(Widget):
    """An input with a label."""

    DEFAULT_CSS = """
    InputWithLabel {
        layout: horizontal;
        height: auto;
    }
    InputWithLabel Label {
        padding: 1;
        width: 12;
        text-align: right;
    }
    InputWithLabel Input {
        width: 1fr;
    }
    """

    def __init__(self, input_label: str) -> None:
        self.input_label = input_label
        super().__init__()

    def compose(self) -> ComposeResult:  # (1)!
        yield Label(self.input_label)
        yield Input()


class CompoundApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    InputWithLabel {
        width: 80%;
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield InputWithLabel("First Name")
        yield InputWithLabel("Last Name")
        yield InputWithLabel("Email")


if __name__ == "__main__":
    app = CompoundApp()
    app.run()
```


The `InputWithLabel` class bundles an [Input](../widgets/input.md) with a [Label](../widgets/label.md) to create a new widget that displays a right-aligned label next to an input control. You can re-use this `InputWithLabel` class anywhere in a Textual app, including in other widgets.

## Coordinating widgets

Widgets rarely exist in isolation, and often need to communicate or exchange data with other parts of your app.
This is not difficult to do, but there is a risk that widgets can become dependant on each other, making it impossible to reuse a widget without copying a lot of dependant code.

In this section we will show how to design and build a fully-working app, while keeping widgets reusable.

### Designing the app

We are going to build a *byte editor* which allows you to enter a number in both decimal and binary. You could use this as a teaching aid for binary numbers.

Here's a sketch of what the app should ultimately look like:

> **Tip**
>
>
> There are plenty of resources on the web, such as this [excellent video from Khan Academy](https://www.khanacademy.org/math/algebra-home/alg-intro-to-algebra/algebra-alternate-number-bases/v/number-systems-introduction) if you want to brush up on binary numbers.


![Byte widget design](../images/byte01.excalidraw.svg)

There are three types of built-in widget in the sketch, namely ([Input](../widgets/input.md), [Label](../widgets/label.md), and [Switch](../widgets/switch.md)). Rather than manage these as a single collection of widgets, we can arrange them into logical groups with compound widgets. This will make our app easier to work with.

###  Identifying components

We will divide this UI into three compound widgets:

2. `ByteInput` which contains 8 `BitSwitch` widgets.
3. `ByteEditor` which contains a `ByteInput` and an [Input](../widgets/input.md) to show the decimal value.

This is not the only way we could implement our design with compound widgets.
So why these three widgets?
As a rule of thumb, a widget should handle one piece of data, which is why we have an independent widget for a bit, a byte, and the decimal value.

![Byte widget breakdown](../images/byte02.excalidraw.svg)

In the following code we will implement the three widgets. There will be no functionality yet, but it should look like our design.

**byte01.py**


```python
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widget import Widget
from textual.widgets import Input, Label, Switch


class BitSwitch(Widget):
    """A Switch with a numeric label above it."""

    DEFAULT_CSS = """
    BitSwitch {
        layout: vertical;
        width: auto;
        height: auto;
    }
    BitSwitch > Label {
        text-align: center;
        width: 100%;
    }
    """

    def __init__(self, bit: int) -> None:
        self.bit = bit
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(str(self.bit))
        yield Switch()


class ByteInput(Widget):
    """A compound widget with 8 switches."""

    DEFAULT_CSS = """
    ByteInput {
        width: auto;
        height: auto;
        border: blank;
        layout: horizontal;
    }
    ByteInput:focus-within {
        border: heavy $secondary;
    }
    """

    def compose(self) -> ComposeResult:
        for bit in reversed(range(8)):
            yield BitSwitch(bit)


class ByteEditor(Widget):
    DEFAULT_CSS = """
    ByteEditor > Container {
        height: 1fr;
        align: center middle;
    }
    ByteEditor > Container.top {
        background: $boost;
    }
    ByteEditor Input {
        width: 16;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(classes="top"):
            yield Input(placeholder="byte")
        with Container():
            yield ByteInput()


class ByteInputApp(App):
    def compose(self) -> ComposeResult:
        yield ByteEditor()


if __name__ == "__main__":
    app = ByteInputApp()
    app.run()
```
Note the `compose()` methods of each of the widgets.

- The `BitSwitch` yields a [Label](../widgets/label.md) which displays the bit number, and a [Switch](../widgets/switch.md) control for that bit. The default CSS for `BitSwitch` aligns its children vertically, and sets the label's [text-align](../styles/text_align.md) to center.

- The `ByteInput` yields 8 `BitSwitch` widgets and arranges them horizontally. It also adds a `focus-within` style in its CSS to draw an accent border when any of the switches are focused.

- The `ByteEditor` yields a `ByteInput` and an `Input` control. The default CSS stacks the two controls on top of each other to divide the screen into two parts.

With these three widgets, the [DOM](CSS.md#the-dom) for our app will look like this:

![Byte input DOM](../images/byte_input_dom.excalidraw.svg)

Now that we have the design in place, we can implement the behavior.


### Data flow

We want to ensure that our widgets are re-usable, which we can do by following the guideline of "attributes down, messages up". This means that a widget can update a child by setting its attributes or calling its methods, but widgets should only ever send [messages](./events.md) to their *parent* (or other ancestors).

> **Info**
>
>
> This pattern of only setting attributes in one direction and using messages for the opposite direction is known as *uni-directional data flow*.


In practice, this means that to update a child widget you get a reference to it and use it like any other Python object. Here's an example of an [action](actions.md) that updates a child widget:

```python
def action_set_true(self):
    self.query_one(Switch).value = 1
```

If a child needs to update a parent, it should send a message with `post_message`.

Here's an example of posting message:

```python
def on_click(self):
    self.post_message(MyWidget.Change(active=True))
```

Note that *attributes down and messages up* means that you can't modify widgets on the same level directly. If you want to modify a *sibling*, you will need to send a message to the parent, and the parent would make the changes.

The following diagram illustrates this concept:


![Attributes and messages](../images/attributes_messages.excalidraw.svg)

### Messages up

Let's extend the `ByteEditor` so that clicking any of the 8 `BitSwitch` widgets updates the decimal value. To do this we will add a custom message to `BitSwitch` that we catch in the `ByteEditor`.

**byte02.py**


```python
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, Label, Switch


class BitSwitch(Widget):
    """A Switch with a numeric label above it."""

    DEFAULT_CSS = """
    BitSwitch {
        layout: vertical;
        width: auto;
        height: auto;
    }
    BitSwitch > Label {
        text-align: center;
        width: 100%;
    }
    """

    class BitChanged(Message):
        """Sent when the 'bit' changes."""

        def __init__(self, bit: int, value: bool) -> None:
            super().__init__()
            self.bit = bit
            self.value = value

    value = reactive(0)  # (1)!

    def __init__(self, bit: int) -> None:
        self.bit = bit
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(str(self.bit))
        yield Switch()

    def on_switch_changed(self, event: Switch.Changed) -> None:  # (2)!
        """When the switch changes, notify the parent via a message."""
        event.stop()  # (3)!
        self.value = event.value  # (4)!
        self.post_message(self.BitChanged(self.bit, event.value))


class ByteInput(Widget):
    """A compound widget with 8 switches."""

    DEFAULT_CSS = """
    ByteInput {
        width: auto;
        height: auto;
        border: blank;
        layout: horizontal;
    }
    ByteInput:focus-within {
        border: heavy $secondary;
    }
    """

    def compose(self) -> ComposeResult:
        for bit in reversed(range(8)):
            yield BitSwitch(bit)


class ByteEditor(Widget):
    DEFAULT_CSS = """
    ByteEditor > Container {
        height: 1fr;
        align: center middle;
    }
    ByteEditor > Container.top {
        background: $boost;
    }
    ByteEditor Input {
        width: 16;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(classes="top"):
            yield Input(placeholder="byte")
        with Container():
            yield ByteInput()

    def on_bit_switch_bit_changed(self, event: BitSwitch.BitChanged) -> None:
        """When a switch changes, update the value."""
        value = 0
        for switch in self.query(BitSwitch):
            value |= switch.value << switch.bit
        self.query_one(Input).value = str(value)


class ByteInputApp(App):
    def compose(self) -> ComposeResult:
        yield ByteEditor()


if __name__ == "__main__":
    app = ByteInputApp()
    app.run()
```

2. This is sent by the builtin `Switch` widgets, when it changes state.
3. Stop the event, because we don't want it to go to the parent.
4. Store the new value of the "bit".


- The `BitSwitch` widget now has an `on_switch_changed` method which will handle a ``Switch.Changed`` message, sent when the user clicks a switch. We use this to store the new value of the bit, and sent a new custom message, `BitSwitch.BitChanged`.
- The `ByteEditor` widget handles the `BitSwitch.Changed` message by calculating the decimal value and setting it on the input.

The following is a (simplified) DOM diagram to show how the new message is processed:

![Bit switch message](../images/bit_switch_message.excalidraw.svg)


### Attributes down

We also want the switches to update if the user edits the decimal value.

Since the switches are children of `ByteEditor` we can update them by setting their attributes directly.
This is an example of "attributes down".

**byte03.py**


```python
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.geometry import clamp
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, Label, Switch


class BitSwitch(Widget):
    """A Switch with a numeric label above it."""

    DEFAULT_CSS = """
    BitSwitch {
        layout: vertical;
        width: auto;
        height: auto;
    }
    BitSwitch > Label {
        text-align: center;
        width: 100%;
    }
    """

    class BitChanged(Message):
        """Sent when the 'bit' changes."""

        def __init__(self, bit: int, value: bool) -> None:
            super().__init__()
            self.bit = bit
            self.value = value

    value = reactive(0)

    def __init__(self, bit: int) -> None:
        self.bit = bit
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(str(self.bit))
        yield Switch()

    def watch_value(self, value: bool) -> None:  # (1)!
        """When the value changes we want to set the switch accordingly."""
        self.query_one(Switch).value = value

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """When the switch changes, notify the parent via a message."""
        event.stop()
        self.value = event.value
        self.post_message(self.BitChanged(self.bit, event.value))


class ByteInput(Widget):
    """A compound widget with 8 switches."""

    DEFAULT_CSS = """
    ByteInput {
        width: auto;
        height: auto;
        border: blank;
        layout: horizontal;
    }
    ByteInput:focus-within {
        border: heavy $secondary;
    }
    """

    def compose(self) -> ComposeResult:
        for bit in reversed(range(8)):
            yield BitSwitch(bit)


class ByteEditor(Widget):
    DEFAULT_CSS = """
    ByteEditor > Container {
        height: 1fr;
        align: center middle;
    }
    ByteEditor > Container.top {
        background: $boost;
    }
    ByteEditor Input {
        width: 16;
    }
    """

    value = reactive(0)

    def validate_value(self, value: int) -> int:  # (2)!
        """Ensure value is between 0 and 255."""
        return clamp(value, 0, 255)

    def compose(self) -> ComposeResult:
        with Container(classes="top"):
            yield Input(placeholder="byte")
        with Container():
            yield ByteInput()

    def on_bit_switch_bit_changed(self, event: BitSwitch.BitChanged) -> None:
        """When a switch changes, update the value."""
        value = 0
        for switch in self.query(BitSwitch):
            value |= switch.value << switch.bit
        self.query_one(Input).value = str(value)

    def on_input_changed(self, event: Input.Changed) -> None:  # (3)!
        """When the text changes, set the value of the byte."""
        try:
            self.value = int(event.value or "0")
        except ValueError:
            pass

    def watch_value(self, value: int) -> None:  # (4)!
        """When self.value changes, update switches."""
        for switch in self.query(BitSwitch):
            with switch.prevent(BitSwitch.BitChanged):  # (5)!
                switch.value = bool(value & (1 << switch.bit))  # (6)!


class ByteInputApp(App):
    def compose(self) -> ComposeResult:
        yield ByteEditor()


if __name__ == "__main__":
    app = ByteInputApp()
    app.run()
```

2. Ensure the value is in a the range of a byte.
3. Handle the `Input.Changed` event when the user modified the value in the input.
4. When the `ByteEditor` value changes, update all the switches to match.
5. Prevent the `BitChanged` message from being sent.
6. Because `switch` is a child, we can set its attributes directly.


- When the user edits the input, the [Input](../widgets/input.md) widget sends a `Changed` event, which we handle with `on_input_changed` by setting `self.value`, which is a reactive value we added to `ByteEditor`.
- If the value has changed, Textual will call `watch_value` which sets the value of each of the eight switches. Because we are working with children of the `ByteEditor`, we can set attributes directly without going via a message.

---

**See also**

- [Widget Gallery](../widget_gallery.md) - Visual overview of all built-in widgets
- [Widget reference](../widgets/index.md) - Detailed reference for each widget
- [Content](./content.md) - Control widget content with markup and the Content class
- [Events and Messages](./events.md) - Handle widget events
- [Reactivity](./reactivity.md) - Reactive attributes for automatic UI updates
