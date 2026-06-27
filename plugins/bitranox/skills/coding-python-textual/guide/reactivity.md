# Reactivity

Textual's reactive attributes are attributes _with superpowers_. In this chapter we will look at how reactive attributes can simplify your apps.

> **Quote**
>
>
> With great power comes great responsibility.
>
> &mdash; Uncle Ben


## Reactive attributes

Textual provides an alternative way of adding attributes to your widget or App, which doesn't require adding them to your class constructor (`__init__`). To create these attributes import `reactive` from `textual.reactive`, and assign them in the class scope.

The following code illustrates how to create reactive attributes:

```python
from textual.reactive import reactive
from textual.widget import Widget

class Reactive(Widget):

    name = reactive("Paul")  # (1)!
    count = reactive(0) # (2)!
    is_cool = reactive(True)  # (3)!
```

2. Creates an integer attribute with a default of `0`.
3. Creates a boolean attribute with a default of `True`.

The `reactive` constructor accepts a default value as the first positional argument.

> **Information**
>
>
> Textual uses Python's _descriptor protocol_ to create reactive attributes, which is the same protocol used by the builtin `property` decorator.


You can get and set these attributes in the same way as if you had assigned them in an `__init__` method. For instance `self.name = "Jessica"`, `self.count += 1`, or `print(self.is_cool)`.

### Dynamic defaults

You can also set the default to a function (or other callable). Textual will call this function to get the default value. The following code illustrates a reactive value which will be automatically assigned the current time when the widget is created:

```python
from time import time
from textual.reactive import reactive
from textual.widget import Widget

class Timer(Widget):

    start_time = reactive(time)  # (1)!
```


### Typing reactive attributes

There is no need to specify a type hint if a reactive attribute has a default value, as type checkers will assume the attribute is the same type as the default.

You may want to add explicit type hints if the attribute type is a superset of the default type. For instance if you want to make an attribute optional. Here's how you would create a reactive string attribute which may be `None`:

```python
    name: reactive[str | None] = reactive("Paul")
```

## Smart refresh

The first superpower we will look at is "smart refresh". When you modify a reactive attribute, Textual will make note of the fact that it has changed and refresh automatically by calling the widget's ``render()`` method to get updated content.

> **Information**
>
>
> If you modify multiple reactive attributes, Textual will only do a single refresh to minimize updates.


Let's look at an example which illustrates this. In the following app, the value of an input is used to update a "Hello, World!" type greeting.

**refresh01.py**


```python
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input


class Name(Widget):
    """Generates a greeting."""

    who = reactive("name")

    def render(self) -> str:
        return f"Hello, {self.who}!"


class WatchApp(App):
    CSS_PATH = "refresh01.tcss"

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Enter your name")
        yield Name()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one(Name).who = event.value


if __name__ == "__main__":
    app = WatchApp()
    app.run()
```

**refresh01.tcss**


```css
Input {
    dock: top;
    margin-top: 1;
}

Name {
    height: 100%;
    content-align: center middle;
}
```
The `Name` widget has a reactive `who` attribute. When the app modifies that attribute, a refresh happens automatically.

> **Information**
>
>
> Textual will check if a value has really changed, so assigning the same value wont prompt an unnecessary refresh.


### Disabling refresh

If you *don't* want an attribute to prompt a refresh or layout but you still want other reactive superpowers, you can use `var` to create an attribute. You can import `var` from `textual.reactive`.

The following code illustrates how you create non-refreshing reactive attributes.

```python
class MyWidget(Widget):
    count = var(0)  # (1)!
```


### Layout

The smart refresh feature will update the content area of a widget, but will not change its size. If modifying an attribute should change the size of the widget, you can set `layout=True` on the reactive attribute. This ensures that your CSS layout will update accordingly.

The following example modifies "refresh01.py" so that the greeting has an automatic width.

**refresh02.py**


```python
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input


class Name(Widget):
    """Generates a greeting."""

    who = reactive("name", layout=True)  # (1)!

    def render(self) -> str:
        return f"Hello, {self.who}!"


class WatchApp(App):
    CSS_PATH = "refresh02.tcss"

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Enter your name")
        yield Name()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one(Name).who = event.value


if __name__ == "__main__":
    app = WatchApp()
    app.run()
```


**refresh02.tcss**


```css
Input {
    dock: top;
    margin-top: 1;
}

Name {
    width: auto;
    height: auto;
    border: heavy $secondary;
}
```
If you type into the input now, the greeting will expand to fit the content. If you were to set `layout=False` on the reactive attribute, you should see that the box remains the same size when you type.

## Validation

The next superpower we will look at is _validation_, which can check and potentially modify a value you assign to a reactive attribute.

If you add a method that begins with `validate_` followed by the name of your attribute, it will be called when you assign a value to that attribute. This method should accept the incoming value as a positional argument, and return the value to set (which may be the same or a different value).

A common use for this is to restrict numbers to a given range. The following example keeps a count. There is a button to increase the count, and a button to decrease it. The validation ensures that the count will never go above 10 or below zero.

**validate01.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Button, RichLog


class ValidateApp(App):
    CSS_PATH = "validate01.tcss"

    count = reactive(0)

    def validate_count(self, count: int) -> int:
        """Validate value."""
        if count < 0:
            count = 0
        elif count > 10:
            count = 10
        return count

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Button("+1", id="plus", variant="success"),
            Button("-1", id="minus", variant="error"),
            id="buttons",
        )
        yield RichLog(highlight=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "plus":
            self.count += 1
        else:
            self.count -= 1
        self.query_one(RichLog).write(f"count = {self.count}")


if __name__ == "__main__":
    app = ValidateApp()
    app.run()
```

**validate01.tcss**


```css
#buttons {
    dock: top;
    height: auto;
}
```
If you click the buttons in the above example it will show the current count. When `self.count` is modified in the button handler, Textual runs `validate_count` which performs the validation to limit the value of count.

## Watch methods

Watch methods are another superpower.
Textual will call watch methods when reactive attributes are modified.
Watch method names begin with `watch_` followed by the name of the attribute, and should accept one or two arguments.
If the method accepts a single argument, it will be called with the new assigned value.
If the method accepts *two* positional arguments, it will be called with both the *old* value and the *new* value.

The following app will display any color you type into the input. Try it with a valid color in Textual CSS. For example `"darkorchid"` or `"#52de44"`.

**watch01.py**


```python
from textual.app import App, ComposeResult
from textual.color import Color, ColorParseError
from textual.containers import Grid
from textual.reactive import reactive
from textual.widgets import Input, Static


class WatchApp(App):
    CSS_PATH = "watch01.tcss"

    color = reactive(Color.parse("transparent"))  # (1)!

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Enter a color")
        yield Grid(Static(id="old"), Static(id="new"), id="colors")

    def watch_color(self, old_color: Color, new_color: Color) -> None:  # (2)!
        self.query_one("#old").styles.background = old_color
        self.query_one("#new").styles.background = new_color

    def on_input_submitted(self, event: Input.Submitted) -> None:
        try:
            input_color = Color.parse(event.value)
        except ColorParseError:
            pass
        else:
            self.query_one(Input).value = ""
            self.color = input_color  # (3)!


if __name__ == "__main__":
    app = WatchApp()
    app.run()
```

2. Called when `self.color` is changed.
3. New color is assigned here.

**watch01.tcss**


```css
Input {
    dock: top;
    margin-top: 1;
}

#colors {
    grid-size: 2 1;
    grid-gutter: 2 4;
    grid-columns: 1fr;
    margin: 0 1;
}

#old {
    height: 100%;
    border: wide $secondary;
}

#new {
    height: 100%;
    border: wide $secondary;
}
```
The color is parsed in `on_input_submitted` and assigned to `self.color`. Because `color` is reactive, Textual also calls `watch_color` with the old and new values.

### When are watch methods called?

Textual only calls watch methods if the value of a reactive attribute _changes_.
If the newly assigned value is the same as the previous value, the watch method is not called.
You can override this behavior by passing `always_update=True` to `reactive`.


### Dynamically watching reactive attributes

You can programmatically add watchers to reactive attributes with the method ``watch``.
This is useful when you want to react to changes to reactive attributes for which you can't edit the watch methods.

The example below shows a widget `Counter` that defines a reactive attribute `counter`.
The app that uses `Counter` uses the method `watch` to keep its progress bar synced with the reactive attribute:

**dynamic_watch.py**


```python
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, ProgressBar


class Counter(Widget):
    DEFAULT_CSS = "Counter { height: auto; }"
    counter = reactive(0)  # (1)!

    def compose(self) -> ComposeResult:
        yield Label()
        yield Button("+10")

    def on_button_pressed(self) -> None:
        self.counter += 10

    def watch_counter(self, counter_value: int):
        self.query_one(Label).update(str(counter_value))


class WatchApp(App[None]):
    def compose(self) -> ComposeResult:
        yield Counter()
        yield ProgressBar(total=100, show_eta=False)

    def on_mount(self):
        def update_progress(counter_value: int):  # (2)!
            self.query_one(ProgressBar).update(progress=counter_value)

        self.watch(self.query_one(Counter), "counter", update_progress)  # (3)!


if __name__ == "__main__":
    WatchApp().run()
```

2. `update_progress` is a custom callback that will update the progress bar when `counter` changes.
3. We use the method `watch` to set `update_progress` as an additional watcher for the reactive attribute `counter`.


## Recompose

An alternative to a refresh is *recompose*.
If you set `recompose=True` on a reactive, then Textual will remove all the child widgets and call ``compose()`` again, when the reactive attribute changes.
The process of removing and mounting new widgets occurs in a single update, so it will appear as though the content has simply updated.

The following example uses recompose:

**refresh03.py**


```python
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, Label


class Name(Widget):
    """Generates a greeting."""

    who = reactive("name", recompose=True)  # (1)!

    def compose(self) -> ComposeResult:  # (2)!
        yield Label(f"Hello, {self.who}!")


class WatchApp(App):
    CSS_PATH = "refresh02.tcss"

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Enter your name")
        yield Name()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one(Name).who = event.value


if __name__ == "__main__":
    app = WatchApp()
    app.run()
```

2. This `compose()` method will be called when `who` is changed.

**refresh03.tcss**


```css
Input {
    dock: top;
    margin-top: 1;
}

Name {
    width: auto;
    height: auto;
    border: heavy $secondary;
}
```
While the end-result is identical to `refresh02.py`, this code works quite differently.
The main difference is that recomposing creates an entirely new set of child widgets rather than updating existing widgets.
So when the `who` attribute changes, the `Name` widget will replace its `Label` with a new instance (containing updated content).

> **Warning**
>
>
> You should avoid storing a reference to child widgets when using recompose.
> Better to [query](../guide/queries.md) for a child widget when you need them.


It is important to note that any child widgets will have their state reset after a recompose.
For simple content, that doesn't matter much.
But widgets with an internal state (such as [`DataTable`](../widgets/data_table.md), [`Input`](../widgets/input.md), or [`TextArea`](../widgets/text_area.md)) would not be particularly useful if recomposed.

Recomposing is slightly less efficient than a simple refresh, and best avoided if you need to update rapidly or you have many child widgets.
That said, it can often simplify your code.
Let's look at a practical example.
First a version *without* recompose:

**recompose01.py**


```python
from datetime import datetime

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Digits


class Clock(App):

    CSS = """
    Screen {align: center middle}
    Digits {width: auto}
    """

    time: reactive[datetime] = reactive(datetime.now, init=False)

    def compose(self) -> ComposeResult:
        yield Digits(f"{self.time:%X}")

    def watch_time(self) -> None:  # (1)!
        self.query_one(Digits).update(f"{self.time:%X}")

    def update_time(self) -> None:
        self.time = datetime.now()

    def on_mount(self) -> None:
        self.set_interval(1, self.update_time)  # (2)!


if __name__ == "__main__":
    app = Clock()
    app.run()
```

2. Update the time once a second.


This displays a clock which updates once a second.
The code is straightforward, but note how we format the time in two places: `compose()` *and* `watch_time()`.
We can simplify this by recomposing rather than refreshing:

**recompose02.py**


```python
from datetime import datetime

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Digits


class Clock(App):

    CSS = """
    Screen {align: center middle}
    Digits {width: auto}
    """

    time: reactive[datetime] = reactive(datetime.now, recompose=True)

    def compose(self) -> ComposeResult:
        yield Digits(f"{self.time:%X}")

    def update_time(self) -> None:
        self.time = datetime.now()

    def on_mount(self) -> None:
        self.set_interval(1, self.update_time)


if __name__ == "__main__":
    app = Clock()
    app.run()
```
In this version, the app is recomposed when the `time` attribute changes, which replaces the `Digits` widget with a new instance and updated time.
There's no need for the `watch_time` method, because the new `Digits` instance will already show the current time.


## Compute methods

Compute methods are the final superpower offered by the `reactive` descriptor. Textual runs compute methods to calculate the value of a reactive attribute. Compute methods begin with `compute_` followed by the name of the reactive value.

You could be forgiven in thinking this sounds a lot like Python's property decorator. The difference is that Textual will cache the value of compute methods, and update them when any other reactive attribute changes.

The following example uses a computed attribute. It displays three inputs for each color component (red, green, and blue). If you enter numbers into these inputs, the background color of another widget changes.

**computed01.py**


```python
from textual.app import App, ComposeResult
from textual.color import Color
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Input, Static


class ComputedApp(App):
    CSS_PATH = "computed01.tcss"

    red = reactive(0)
    green = reactive(0)
    blue = reactive(0)
    color = reactive(Color.parse("transparent"))

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Input("0", placeholder="Enter red 0-255", id="red"),
            Input("0", placeholder="Enter green 0-255", id="green"),
            Input("0", placeholder="Enter blue 0-255", id="blue"),
            id="color-inputs",
        )
        yield Static(id="color")

    def compute_color(self) -> Color:  # (1)!
        return Color(self.red, self.green, self.blue).clamped

    def watch_color(self, color: Color) -> None:  # (2)
        self.query_one("#color").styles.background = color

    def on_input_changed(self, event: Input.Changed) -> None:
        try:
            component = int(event.value)
        except ValueError:
            self.bell()
        else:
            if event.input.id == "red":
                self.red = component
            elif event.input.id == "green":
                self.green = component
            else:
                self.blue = component


if __name__ == "__main__":
    app = ComputedApp()
    app.run()
```

2. The watch method is called when the _result_ of `compute_color` changes.

**computed01.tcss**


```css
#color-inputs {
    dock: top;
    height: auto;
}

Input {
    width: 1fr;
}

#color {
    height: 100%;
    border: tall $secondary;
}
```
Note the `compute_color` method which combines the color components into a `Color` object. It will be recalculated when any of the `red` , `green`, or `blue` attributes are modified.

When the result of `compute_color` changes, Textual will also call `watch_color` since `color` still has the [watch method](#watch-methods) superpower.

> **Note**
>
>
> Textual will first attempt to call the compute method for a reactive attribute, followed by the validate method, and finally the watch method.


> **Note**
>
>
> It is best to avoid doing anything slow or CPU-intensive in a compute method. Textual calls compute methods on an object when _any_ reactive attribute changes.


## Setting reactives without superpowers

You may find yourself in a situation where you want to set a reactive value, but you *don't* want to invoke watchers or the other super powers.
This is fairly common in constructors which run prior to mounting; any watcher which queries the DOM may break if the widget has not yet been mounted.

To work around this issue, you can call `set_reactive` as an alternative to setting the attribute.
The `set_reactive` method accepts the reactive attribute (as a class variable) and the new value.

Let's look at an example.
The following app is intended to cycle through various greeting when you press `Space`, however it contains a bug.

```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive, var
from textual.widgets import Label

GREETINGS = [
    "Bonjour",
    "Hola",
    "こんにちは",
    "你好",
    "안녕하세요",
    "Hello",
]


class Greeter(Horizontal):
    """Display a greeting and a name."""

    DEFAULT_CSS = """
    Greeter {
        width: auto;
        height: 1;
        & Label {
            margin: 0 1;
        }
    }
    """
    greeting: reactive[str] = reactive("")
    who: reactive[str] = reactive("")

    def __init__(self, greeting: str = "Hello", who: str = "World!") -> None:
        super().__init__()
        self.greeting = greeting  # (1)!
        self.who = who

    def compose(self) -> ComposeResult:
        yield Label(self.greeting, id="greeting")
        yield Label(self.who, id="name")

    def watch_greeting(self, greeting: str) -> None:
        self.query_one("#greeting", Label).update(greeting)  # (2)!

    def watch_who(self, who: str) -> None:
        self.query_one("#who", Label).update(who)


class NameApp(App):

    CSS = """
    Screen {
        align: center middle;
    }
    """
    greeting_no: var[int] = var(0)
    BINDINGS = [("space", "greeting")]

    def compose(self) -> ComposeResult:
        yield Greeter(who="Textual")

    def action_greeting(self) -> None:
        self.greeting_no = (self.greeting_no + 1) % len(GREETINGS)
        self.query_one(Greeter).greeting = GREETINGS[self.greeting_no]


if __name__ == "__main__":
    app = NameApp()
    app.run()
```

2. The watcher attempts to update a label before it is mounted.

If you run this app, you will find Textual raises a `NoMatches` error in `watch_greeting`.
This is because the constructor has assigned the reactive before the widget has fully mounted.

The following app contains a fix for this issue:

**set_reactive02.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive, var
from textual.widgets import Label

GREETINGS = [
    "Bonjour",
    "Hola",
    "こんにちは",
    "你好",
    "안녕하세요",
    "Hello",
]


class Greeter(Horizontal):
    """Display a greeting and a name."""

    DEFAULT_CSS = """
    Greeter {
        width: auto;
        height: 1;
        & Label {
            margin: 0 1;
        }
    }
    """
    greeting: reactive[str] = reactive("")
    who: reactive[str] = reactive("")

    def __init__(self, greeting: str = "Hello", who: str = "World!") -> None:
        super().__init__()
        self.set_reactive(Greeter.greeting, greeting)  # (1)!
        self.set_reactive(Greeter.who, who)

    def compose(self) -> ComposeResult:
        yield Label(self.greeting, id="greeting")
        yield Label(self.who, id="name")

    def watch_greeting(self, greeting: str) -> None:
        self.query_one("#greeting", Label).update(greeting)

    def watch_who(self, who: str) -> None:
        self.query_one("#who", Label).update(who)


class NameApp(App):

    CSS = """
    Screen {
        align: center middle;
    }
    """
    greeting_no: var[int] = var(0)
    BINDINGS = [("space", "greeting")]

    def compose(self) -> ComposeResult:
        yield Greeter(who="Textual")

    def action_greeting(self) -> None:
        self.greeting_no = (self.greeting_no + 1) % len(GREETINGS)
        self.query_one(Greeter).greeting = GREETINGS[self.greeting_no]


if __name__ == "__main__":
    app = NameApp()
    app.run()
```


The line `self.set_reactive(Greeter.greeting, greeting)` sets the `greeting` attribute but doesn't immediately invoke the watcher.

## Mutable reactives

Textual can detect when you set a reactive to a new value, but it can't detect when you _mutate_ a value.
In practice, this means that Textual can detect changes to basic types (int, float, str, etc.), but not if you update a collection, such as a list or dict.

You can still use collections and other mutable objects in reactives, but you will need to call ``mutate_reactive`` after making changes for the reactive superpowers to work.

Here's an example, that uses a reactive list:

**set_reactive03.py**


```python
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Input, Label


class MultiGreet(App):
    names: reactive[list[str]] = reactive(list, recompose=True)  # (1)!

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Give me a name")
        for name in self.names:
            yield Label(f"Hello, {name}")

    def on_input_submitted(self, event: Input.Changed) -> None:
        self.names.append(event.value)
        self.mutate_reactive(MultiGreet.names)  # (2)!


if __name__ == "__main__":
    app = MultiGreet()
    app.run()
```

2. Explicitly mutate the reactive list.


Note the call to `mutate_reactive`. Without it, the display would not update when a new name is appended to the list.

## Data binding

Reactive attributes may be *bound* (connected) to attributes on child widgets, so that changes to the parent are automatically reflected in the children.
This can simplify working with compound widgets where the value of an attribute might be used in multiple places.

To bind reactive attributes, call `data_bind` on a widget.
This method accepts reactives (as class attributes) in positional arguments or keyword arguments.

Let's look at an app that could benefit from data binding.
In the following code we have a `WorldClock` widget which displays the time in any given timezone.


> **Note**
>
>
> This example uses the [pytz](https://pypi.org/project/pytz/) library for working with timezones.
> You can install pytz with `pip install pytz`.


**world_clock01.py**


```python
from datetime import datetime

from pytz import timezone

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Digits, Label


class WorldClock(Widget):

    time: reactive[datetime] = reactive(datetime.now)

    def __init__(self, timezone: str) -> None:
        self.timezone = timezone
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(self.timezone)
        yield Digits()

    def watch_time(self, time: datetime) -> None:
        localized_time = time.astimezone(timezone(self.timezone))
        self.query_one(Digits).update(localized_time.strftime("%H:%M:%S"))


class WorldClockApp(App):
    CSS_PATH = "world_clock01.tcss"

    time: reactive[datetime] = reactive(datetime.now)

    def compose(self) -> ComposeResult:
        yield WorldClock("Europe/London")
        yield WorldClock("Europe/Paris")
        yield WorldClock("Asia/Tokyo")

    def update_time(self) -> None:
        self.time = datetime.now()

    def watch_time(self, time: datetime) -> None:
        for world_clock in self.query(WorldClock):  # (1)!
            world_clock.time = time

    def on_mount(self) -> None:
        self.update_time()
        self.set_interval(1, self.update_time)


if __name__ == "__main__":
    app = WorldClockApp()
    app.run()
```


**world_clock01.tcss**


```css
Screen {
    align: center middle;
}

WorldClock {
    width: auto;
    height: auto;
    padding: 1 2;
    background: $panel;
    border: wide $background;

    & Digits {
        width: auto;
        color: $secondary;
    }
}
```
We've added three world clocks for London, Paris, and Tokyo.
The clocks are kept up-to-date by watching the app's `time` reactive, and updating the clocks in a loop.

While this approach works fine, it does require we take care to update every `WorldClock` we mount.
Let's see how data binding can simplify this.

The following app calls `data_bind` on the world clock widgets to connect the app's `time` with the widget's `time` attribute:

**world_clock02.py**


```python
from datetime import datetime

from pytz import timezone

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Digits, Label


class WorldClock(Widget):

    time: reactive[datetime] = reactive(datetime.now)

    def __init__(self, timezone: str) -> None:
        self.timezone = timezone
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(self.timezone)
        yield Digits()

    def watch_time(self, time: datetime) -> None:
        localized_time = time.astimezone(timezone(self.timezone))
        self.query_one(Digits).update(localized_time.strftime("%H:%M:%S"))


class WorldClockApp(App):
    CSS_PATH = "world_clock01.tcss"

    time: reactive[datetime] = reactive(datetime.now)

    def compose(self) -> ComposeResult:
        yield WorldClock("Europe/London").data_bind(WorldClockApp.time)  # (1)!
        yield WorldClock("Europe/Paris").data_bind(WorldClockApp.time)
        yield WorldClock("Asia/Tokyo").data_bind(WorldClockApp.time)

    def update_time(self) -> None:
        self.time = datetime.now()

    def on_mount(self) -> None:
        self.update_time()
        self.set_interval(1, self.update_time)


if __name__ == "__main__":
    WorldClockApp().run()
```


**world_clock01.tcss**


```css
Screen {
    align: center middle;
}

WorldClock {
    width: auto;
    height: auto;
    padding: 1 2;
    background: $panel;
    border: wide $background;

    & Digits {
        width: auto;
        color: $secondary;
    }
}
```
Note how the addition of the `data_bind` methods negates the need for the watcher in `world_clock01.py`.


> **Note**
>
>
> Data binding works in a single direction.
> Setting `time` on the app updates the clocks.
> But setting `time` on the clocks will *not* update `time` on the app.


In the previous example app, the call to `data_bind(WorldClockApp.time)` worked because both reactive attributes were named `time`.
If you want to bind a reactive attribute which has a different name, you can use keyword arguments.

In the following app we have changed the attribute name on `WorldClock` from `time` to `clock_time`.
We can make the app continue to work by changing the `data_bind` call to `data_bind(clock_time=WorldClockApp.time)`:


**world_clock03.py**


```python
from datetime import datetime

from pytz import timezone

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Digits, Label


class WorldClock(Widget):

    clock_time: reactive[datetime] = reactive(datetime.now)

    def __init__(self, timezone: str) -> None:
        self.timezone = timezone
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(self.timezone)
        yield Digits()

    def watch_clock_time(self, time: datetime) -> None:
        localized_time = time.astimezone(timezone(self.timezone))
        self.query_one(Digits).update(localized_time.strftime("%H:%M:%S"))


class WorldClockApp(App):
    CSS_PATH = "world_clock01.tcss"

    time: reactive[datetime] = reactive(datetime.now)

    def compose(self) -> ComposeResult:
        yield WorldClock("Europe/London").data_bind(
            clock_time=WorldClockApp.time  # (1)!
        )
        yield WorldClock("Europe/Paris").data_bind(clock_time=WorldClockApp.time)
        yield WorldClock("Asia/Tokyo").data_bind(clock_time=WorldClockApp.time)

    def update_time(self) -> None:
        self.time = datetime.now()

    def on_mount(self) -> None:
        self.update_time()
        self.set_interval(1, self.update_time)


if __name__ == "__main__":
    WorldClockApp().run()
```


**world_clock01.tcss**


```css
Screen {
    align: center middle;
}

WorldClock {
    width: auto;
    height: auto;
    padding: 1 2;
    background: $panel;
    border: wide $background;

    & Digits {
        width: auto;
        color: $secondary;
    }
}
```

---

**See also**

- [Widgets](./widgets.md) - Build custom widgets with reactive attributes
- [Events and Messages](./events.md) - Message-driven communication between widgets
- [DOM Queries](./queries.md) - Query and manipulate widgets from Python
- [DataTable widget](../widgets/data_table.md) - A widget that uses reactivity extensively
