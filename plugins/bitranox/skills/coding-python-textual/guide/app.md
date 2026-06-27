# App Basics

In this chapter we will cover how to use Textual's App class to create an application. Just enough to get you up to speed. We will go into more detail in the following chapters.

## The App class

The first step in building a Textual app is to import the `App` class and create a subclass. Let's look at the simplest app class:

```python
from textual.app import App


class MyApp(App):
    pass
```
### The run method

To run an app we create an instance and call `run()`.

```python
from textual.app import App


class MyApp(App):
    pass


if __name__ == "__main__":
    app = MyApp()
    app.run()
```

Apps don't get much simpler than this&mdash;don't expect it to do much.

> **Tip**
>
>
> The `__name__ == "__main__":` condition is true only if you run the file with `python` command. This allows us to import `app` without running the app immediately. It also allows the [devtools run](devtools.md#run) command to run the app in development mode. See the [Python docs](https://docs.python.org/3/library/__main__.html#idiomatic-usage) for more information.


If we run this app with `python simple02.py` you will see a blank terminal, something like the following:


When you call `App.run()` Textual puts the terminal into a special state called *application mode*. When in application mode the terminal will no longer echo what you type. Textual will take over responding to user input (keyboard and mouse) and will update the visible portion of the terminal (i.e. the *screen*).

If you hit `Ctrl+Q` Textual will exit application mode and return you to the command prompt. Any content you had in the terminal prior to application mode will be restored.


#### Run inline

> **Tip: Added in version 0.55.0**


You can also run apps in _inline_ mode, which will cause the app to appear beneath the prompt (and won't go into application mode).
Inline apps are useful for tools that integrate closely with the typical workflow of a terminal.

To run an app in inline mode set the `inline` parameter to `True` when you call `App.run()`. See [Style Inline Apps](../how-to/style-inline-apps.md) for how to apply additional styles to inline apps.

> **Note**
>
>
> Inline mode is not currently supported on Windows.


#### ANSI colors

> **Tip: Added in version 0.80.0**


Terminals support 16 theme-able *ANSI* colors, which you can personalize from your terminal settings.
By default, Textual will replace these colors with its own color choices (see the [FAQ for details](../FAQ.md#why-doesnt-textual-support-ansi-themes)).

You can disable this behavior by setting `ansi_color=True` in the `App constructor`.

We recommend the default behavior for full-screen apps, but you may want to preserve ANSI colors in [inline](#run-inline) apps.

## Events

Textual has an [event system](./events.md) you can use to respond to key presses, mouse actions, and internal state changes. Event handlers are methods prefixed with `on_` followed by the name of the event.

One such event is the *mount* event which is sent to an application after it enters application mode. You can respond to this event by defining a method called `on_mount`.

Another such event is the *key* event which is sent when the user presses a key. The following example contains handlers for both those events:

```python
from textual.app import App
from textual import events


class EventApp(App):

    COLORS = [
        "white",
        "maroon",
        "red",
        "purple",
        "fuchsia",
        "olive",
        "yellow",
        "navy",
        "teal",
        "aqua",
    ]

    def on_mount(self) -> None:
        self.screen.styles.background = "darkblue"

    def on_key(self, event: events.Key) -> None:
        if event.key.isdecimal():
            self.screen.styles.background = self.COLORS[int(event.key)]


if __name__ == "__main__":
    app = EventApp()
    app.run()
```

The `on_mount` handler sets the `self.screen.styles.background` attribute to `"darkblue"` which (as you can probably guess) turns the background blue. Since the mount event is sent immediately after entering application mode, you will see a blue screen when you run this code.


When you press a key, the key event handler (`on_key`) which will receive a `Key` instance.
If you don't require the event in your handler, you can omit it.

Events may contain additional information which you can inspect in the handler.
In the case of the `Key` event, there is a `key` attribute which is the name of the key that was pressed.
The `on_key` method above uses this attribute to change the background color if any of the keys from `0` to `9` are pressed.

### Async events

Textual is powered by Python's [asyncio](https://docs.python.org/3/library/asyncio.html) framework which uses the `async` and `await` keywords.

Textual knows to *await* your event handlers if they are coroutines (i.e. prefixed with the `async` keyword). Regular functions are generally fine unless you plan on integrating other async libraries (such as [httpx](https://www.python-httpx.org/) for reading data from the internet).

> **Tip**
>
>
> For a friendly introduction to async programming in Python, see FastAPI's [concurrent burgers](https://fastapi.tiangolo.com/async/) article.


## Widgets

Widgets are self-contained components responsible for generating the output for a portion of the screen. Widgets respond to events in much the same way as the App. Most apps that do anything interesting will contain at least one (and probably many) widgets which together form a User Interface.

Widgets can be as simple as a piece of text, a button, or a fully-fledged component like a text editor or file browser (which may contain widgets of their own).

### Composing

To add widgets to your app implement a ``compose()`` method which should return an iterable of `Widget` instances. A list would work, but it is convenient to yield widgets, making the method a *generator*.

The following example imports a builtin `Welcome` widget and yields it from `App.compose()`.

```python
from textual.app import App, ComposeResult
from textual.widgets import Welcome


class WelcomeApp(App):
    def compose(self) -> ComposeResult:
        yield Welcome()

    def on_button_pressed(self) -> None:
        self.exit()


if __name__ == "__main__":
    app = WelcomeApp()
    app.run()
```

When you run this code, Textual will *mount* the `Welcome` widget which contains Markdown content and a button:


Notice the `on_button_pressed` method which handles the `Button.Pressed` event sent by a button contained in the `Welcome` widget. The handler calls `App.exit()` to exit the app.

### Mounting

While composing is the preferred way of adding widgets when your app starts it is sometimes necessary to add new widget(s) in response to events. You can do this by calling `mount()` which will add a new widget to the UI.

Here's an app which adds a welcome widget in response to any key press:

```python
from textual.app import App
from textual.widgets import Welcome


class WelcomeApp(App):
    def on_key(self) -> None:
        self.mount(Welcome())

    def on_button_pressed(self) -> None:
        self.exit()


if __name__ == "__main__":
    app = WelcomeApp()
    app.run()
```

When you first run this you will get a blank screen. Press any key to add the welcome widget. You can even press a key multiple times to add several widgets.


#### Awaiting mount

When you mount a widget, Textual will mount everything the widget *composes*.
Textual guarantees that the mounting will be complete by the *next* message handler, but not immediately after the call to `mount()`.
This may be a problem if you want to make any changes to the widget in the same message handler.

Let's first illustrate the problem with an example.
The following code will mount the Welcome widget in response to a key press.
It will also attempt to modify the Button in the Welcome widget by changing its label from "OK" to "YES!".

```python
from textual.app import App
from textual.widgets import Button, Welcome


class WelcomeApp(App):
    def on_key(self) -> None:
        self.mount(Welcome())
        self.query_one(Button).label = "YES!" # (1)!


if __name__ == "__main__":
    app = WelcomeApp()
    app.run()
```


If you run this example, you will find that Textual raises a `NoMatches` exception when you press a key.
This is because the mount process has not yet completed when we attempt to change the button.

To solve this we can optionally await the result of `mount()`, which requires we make the function `async`.
This guarantees that by the following line, the Button has been mounted, and we can change its label.


```python
from textual.app import App
from textual.widgets import Button, Welcome


class WelcomeApp(App):
    async def on_key(self) -> None:
        await self.mount(Welcome())
        self.query_one(Button).label = "YES!"


if __name__ == "__main__":
    app = WelcomeApp()
    app.run()
```

Here's the output. Note the changed button text:


## Exiting

An app will run until you call `App.exit()` which will exit application mode and the `run` method will return. If this is the last line in your code you will return to the command prompt.

The exit method will also accept an optional positional value to be returned by `run()`. The following example uses this to return the `id` (identifier) of a clicked button.

```python
from textual.app import App, ComposeResult
from textual.widgets import Label, Button


class QuestionApp(App[str]):
    def compose(self) -> ComposeResult:
        yield Label("Do you love Textual?")
        yield Button("Yes", id="yes", variant="primary")
        yield Button("No", id="no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)


if __name__ == "__main__":
    app = QuestionApp()
    reply = app.run()
    print(reply)
```

Running this app will give you the following:


Clicking either of those buttons will exit the app, and the `run()` method will return either `"yes"` or `"no"` depending on button clicked.

### Return type

You may have noticed that we subclassed `App[str]` rather than the usual `App`.

```python
from textual.app import App, ComposeResult
from textual.widgets import Label, Button


class QuestionApp(App[str]):
    def compose(self) -> ComposeResult:
        yield Label("Do you love Textual?")
        yield Button("Yes", id="yes", variant="primary")
        yield Button("No", id="no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)


if __name__ == "__main__":
    app = QuestionApp()
    reply = app.run()
    print(reply)
```

The addition of `[str]` tells mypy that `run()` is expected to return a string. It may also return `None` if `App.exit()` is called without a return value, so the return type of `run` will be `str | None`. Replace the `str` in `[str]` with the type of the value you intend to call the exit method with.

> **Note: Typing in Textual**
>
>
> Type annotations are entirely optional (but recommended) with Textual.


### Return code

When you exit a Textual app with ``App.exit()``, you can optionally specify a *return code* with the `return_code` parameter.


> **Info: What are return codes?**
>
>
> Returns codes are a standard feature provided by your operating system.
> When any application exits it can return an integer to indicate if it was successful or not.
> A return code of `0` indicates success, any other value indicates that an error occurred.
> The exact meaning of a non-zero return code is application-dependant.


When a Textual app exits normally, the return code will be `0`. If there is an unhandled exception, Textual will set a return code of `1`.
You may want to set a different value for the return code if there is error condition that you want to differentiate from an unhandled exception.

Here's an example of setting a return code for an error condition:

```python
if critical_error:
    self.exit(return_code=4, message="Critical error occurred")
```

The app's return code can be queried with `app.return_code`, which will be `None` if it hasn't been set, or an integer.

Textual won't explicitly exit the process.
To exit the app with a return code, you should call `sys.exit`.
Here's how you might do that:

```python
if __name__ == "__main__"
    app = MyApp()
    app.run()
    import sys
    sys.exit(app.return_code or 0)
```

## Suspending

A Textual app may be suspended so you can leave application mode for a period of time.
This is often used to temporarily replace your app with another terminal application.

You could use this to allow the user to edit content with their preferred text editor, for example.

> **Info**
>
>
> App suspension is unavailable with [textual-web](https://github.com/Textualize/textual-web).


### Suspend context manager

You can use the [App.suspend](../api/app.md#textual.app.App.suspend) context manager to suspend your app.
The following Textual app will launch [vim](https://www.vim.org/) (a text editor) when the user clicks a button:

**suspend.py**


```python
from os import system

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Button


class SuspendingApp(App[None]):

    def compose(self) -> ComposeResult:
        yield Button("Open the editor", id="edit")

    @on(Button.Pressed, "#edit")
    def run_external_editor(self) -> None:
        with self.suspend():  # (1)!
            system("vim")


if __name__ == "__main__":
    SuspendingApp().run()
```


### Suspending from foreground

On Unix and Unix-like systems (GNU/Linux, macOS, etc) Textual has support for the user pressing a key combination to suspend the application as the foreground process.
Ordinarily this key combination is <kbd>Ctrl</kbd>+<kbd>Z</kbd>;
in a Textual application this is disabled by default, but an action is provided ([`action_suspend_process`](../api/app.md#textual.app.App.action_suspend_process)) that you can bind in the usual way.
For example:

**suspend_process.py**


```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Label


class SuspendKeysApp(App[None]):

    BINDINGS = [Binding("ctrl+z", "suspend_process")]

    def compose(self) -> ComposeResult:
        yield Label("Press Ctrl+Z to suspend!")


if __name__ == "__main__":
    SuspendKeysApp().run()
```
> **Note**
>
>
> If `suspend_process` is called on Windows, or when your application is being hosted under Textual Web, the call will be ignored.


## CSS

Textual apps can reference [CSS](CSS.md) files which define how your app and widgets will look, while keeping your project free of messy display related code.

> **Info**
>
>
> Textual apps typically use the extension `.tcss` for external CSS files to differentiate them from browser (`.css`) files.


The chapter on [Textual CSS](CSS.md) describes how to use CSS in detail. For now let's look at how your app references external CSS files.

The following example enables loading of CSS by adding a `CSS_PATH` class variable:

```python
from textual.app import App, ComposeResult
from textual.widgets import Button, Label


class QuestionApp(App[str]):
    CSS_PATH = "question02.tcss"

    def compose(self) -> ComposeResult:
        yield Label("Do you love Textual?", id="question")
        yield Button("Yes", id="yes", variant="primary")
        yield Button("No", id="no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)


if __name__ == "__main__":
    app = QuestionApp()
    reply = app.run()
    print(reply)
```

> **Note**
>
>
> We also added an `id` to the `Label`, because we want to style it in the CSS.


If the path is relative (as it is above) then it is taken as relative to where the app is defined. Hence this example references `"question01.tcss"` in the same directory as the Python code. Here is that CSS file:

```css
Screen {
    layout: grid;
    grid-size: 2;
    grid-gutter: 2;
    padding: 2;
}
#question {
    width: 100%;
    height: 100%;
    column-span: 2;
    content-align: center bottom;
    text-style: bold;
}

Button {
    width: 100%;
}
```

When `"question02.py"` runs it will load `"question02.tcss"` and update the app and widgets accordingly. Even though the code is almost identical to the previous sample, the app now looks quite different:


### Classvar CSS

While external CSS files are recommended for most applications, and enable some cool features like *live editing*, you can also specify the CSS directly within the Python code.

To do this set a `CSS` class variable on the app to a string containing your CSS.

Here's the question app with classvar CSS:

```python
from textual.app import App, ComposeResult
from textual.widgets import Label, Button


class QuestionApp(App[str]):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-gutter: 2;
        padding: 2;
    }
    #question {
        width: 100%;
        height: 100%;
        column-span: 2;
        content-align: center bottom;
        text-style: bold;
    }

    Button {
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Do you love Textual?", id="question")
        yield Button("Yes", id="yes", variant="primary")
        yield Button("No", id="no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)


if __name__ == "__main__":
    app = QuestionApp()
    reply = app.run()
    print(reply)
```
## Title and subtitle

Textual apps have a `title` attribute which is typically the name of your application, and an optional `sub_title` attribute which adds additional context (such as the file your are working on).
By default, `title` will be set to the name of your App class, and `sub_title` is empty.
You can change these defaults by defining `TITLE` and `SUB_TITLE` class variables. Here's an example of that:

```python
from textual.app import App, ComposeResult
from textual.widgets import Button, Header, Label


class MyApp(App[str]):
    CSS_PATH = "question02.tcss"
    TITLE = "A Question App"
    SUB_TITLE = "The most important question"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Do you love Textual?", id="question")
        yield Button("Yes", id="yes", variant="primary")
        yield Button("No", id="no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)


if __name__ == "__main__":
    app = MyApp()
    reply = app.run()
    print(reply)
```

Note that the title and subtitle are displayed by the builtin [Header](../widgets/header.md) widget at the top of the screen:


You can also set the title attributes dynamically within a method of your app. The following example sets the title and subtitle in response to a key press:

```python
from textual.app import App, ComposeResult
from textual.events import Key
from textual.widgets import Button, Header, Label


class MyApp(App[str]):
    CSS_PATH = "question02.tcss"
    TITLE = "A Question App"
    SUB_TITLE = "The most important question"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Do you love Textual?", id="question")
        yield Button("Yes", id="yes", variant="primary")
        yield Button("No", id="no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)

    def on_key(self, event: Key):
        self.title = event.key
        self.sub_title = f"You just pressed {event.key}!"


if __name__ == "__main__":
    app = MyApp()
    reply = app.run()
    print(reply)
```

If you run this app and press the `T` key, you should see the header update accordingly:


> **Info**
>
>
> Note that there is no need to explicitly refresh the screen when setting the title attributes. This is an example of [reactivity](./reactivity.md), which we will cover later in the guide.


## What's next

In the following chapter we will learn more about how to apply styles to your widgets and app.

---

**See also**

- [Tutorial](../tutorial.md) - Build a complete app step-by-step
- [Widgets](./widgets.md) - Learn about composing and building widgets
- [Textual CSS](./CSS.md) - Style your application with CSS
- [Testing](./testing.md) - Test your Textual applications
- [Screens](./screens.md) - Manage multiple screens in your app
