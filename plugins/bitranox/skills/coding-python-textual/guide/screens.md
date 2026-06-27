# Screens

This chapter covers Textual's screen API. We will discuss how to create screens and switch between them.

## What is a screen?

Screens are containers for widgets that occupy the dimensions of your terminal. There can be many screens in a given app, but only one screen is active at a time.

Textual requires that there be at least one screen object and will create one implicitly in the App class. If you don't change the screen, any widgets you `mount` or `compose` will be added to this default screen.

![DOM diagram](../images/dom1.excalidraw.svg)

## Creating a screen

You can create a screen by extending the `Screen` class which you can import from `textual.screen`. The screen may be styled in the same way as other widgets, with the exception that you can't modify the screen's dimensions (as these will always be the size of your terminal).

Let's look at a simple example of writing a screen class to simulate Window's [blue screen of death](https://en.wikipedia.org/wiki/Blue_screen_of_death).

**screen01.py**


```python
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static

ERROR_TEXT = """
An error has occurred. To continue:

Press Enter to return to Windows, or

Press CTRL+ALT+DEL to restart your computer. If you do this,
you will lose any unsaved information in all open applications.

Error: 0E : 016F : BFF9B3D4
"""


class BSOD(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def compose(self) -> ComposeResult:
        yield Static(" Windows ", id="title")
        yield Static(ERROR_TEXT)
        yield Static("Press any key to continue [blink]_[/]", id="any-key")


class BSODApp(App):
    CSS_PATH = "screen01.tcss"
    SCREENS = {"bsod": BSOD}
    BINDINGS = [("b", "push_screen('bsod')", "BSOD")]


if __name__ == "__main__":
    app = BSODApp()
    app.run()
```

**screen01.tcss**


```css
BSOD {
    align: center middle;
    background: blue;
    color: white;
}

BSOD>Static {
    width: 70;
}

#title {
    content-align-horizontal: center;
    text-style: reverse;
}

#any-key {
    content-align-horizontal: center;
}
```
If you run this you will see an empty screen. Hit the `B` key to show a blue screen of death. Hit `Escape` to return to the default screen.

The `BSOD` class above defines a screen with a key binding and compose method. These should be familiar as they work in the same way as apps.

The app class has a new `SCREENS` class variable. Textual uses this class variable to associate a name with screen object (the name is used to reference screens in the screen API). Also in the app is a key binding associated with the action `"push_screen('bsod')"`. The screen class has a similar action `"pop_screen"` bound to the `Escape` key. We will cover these actions below.

## Named screens

You can associate a screen with a name by defining a `SCREENS` class variable in your app, which should be a `dict` that maps names on to `Screen` objects. The name of the screen may be used interchangeably with screen objects in much of the screen API.

You can also _install_ new named screens dynamically with the `install_screen` method. The following example installs the `BSOD` screen in a mount handler rather than from the `SCREENS` variable.

**screen02.py**


```python
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static

ERROR_TEXT = """
An error has occurred. To continue:

Press Enter to return to Windows, or

Press CTRL+ALT+DEL to restart your computer. If you do this,
you will lose any unsaved information in all open applications.

Error: 0E : 016F : BFF9B3D4
"""


class BSOD(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def compose(self) -> ComposeResult:
        yield Static(" Windows ", id="title")
        yield Static(ERROR_TEXT)
        yield Static("Press any key to continue [blink]_[/]", id="any-key")


class BSODApp(App):
    CSS_PATH = "screen02.tcss"
    BINDINGS = [("b", "push_screen('bsod')", "BSOD")]

    def on_mount(self) -> None:
        self.install_screen(BSOD(), name="bsod")


if __name__ == "__main__":
    app = BSODApp()
    app.run()
```

**screen02.tcss**


```css
BSOD {
    align: center middle;
    background: blue;
    color: white;
}

BSOD>Static {
    width: 70;
}

#title {
    content-align-horizontal: center;
    text-style: reverse;
}

#any-key {
    content-align-horizontal: center;
}
```
Although both do the same thing, we recommend `SCREENS` for screens that exist for the lifetime of your app.

### Uninstalling screens

Screens defined in `SCREENS` or added with `install_screen` are _installed_ screens. Textual will keep these screens in memory for the lifetime of your app.

If you have installed a screen, but you later want it to be removed and cleaned up, you can call `uninstall_screen`.

## Screen stack

Textual apps keep a _stack_ of screens. You can think of this screen stack as a stack of paper, where only the very top sheet is visible. If you remove the top sheet, the paper underneath becomes visible. Screens work in a similar way.

> **Note**
>
>
> You can also make parts of the top screen translucent, so that deeper screens show through. See [Screen opacity](#screen-opacity).


The active screen (top of the stack) will render the screen and receive input events. The following API methods on the App class can manipulate this stack, and let you decide which screen the user can interact with.

### Push screen

The `push_screen` method puts a screen on top of the stack and makes that screen active. You can call this method with the name of an installed screen, or a screen object.

![Push screen](../images/screens/push_screen.excalidraw.svg)

#### Action

You can also push screens with the `"app.push_screen"` action, which requires the name of an installed screen.

### Pop screen

The `pop_screen` method removes the top-most screen from the stack, and makes the new top screen active.

> **Note**
>
>
> The screen stack must always have at least one screen. If you attempt to remove the last screen, Textual will raise a `ScreenStackError` exception.


![Pop screen](../images/screens/pop_screen.excalidraw.svg)


When you pop a screen it will be removed and deleted unless it has been installed or there is another copy of the screen on the stack.

#### Action

You can also pop screens with the `"app.pop_screen"` action.

### Switch screen

The `switch_screen` method replaces the top of the stack with a new screen.

![Switch screen](../images/screens/switch_screen.excalidraw.svg)

Like [pop_screen](#pop-screen), if the screen being replaced is not installed it will be removed and deleted.

#### Action

You can also switch screens with the `"app.switch_screen"` action which accepts the name of the screen to switch to.


## Screen opacity

If a screen has a background color with an *alpha* component, then the background color will be blended with the screen beneath it.
For example, if the top-most screen has a background set to `rgba(0,0,255,0.5)` then anywhere in the screen not occupied with a widget will display the *second* screen from the top, tinted with 50% blue.


![Screen alpha](../images/screens/screen_alpha.excalidraw.svg)


> **Note**
>
>
> Although parts of other screens may be made visible with background alpha, only the top-most is *active* (can respond to mouse and keyboard).


One use of background alpha is to style *modal dialogs* (see below).


## Modal screens

Screens may be used to create modal dialogs, where the main interface is temporarily disabled (but still visible) while the user is entering information.

The following example pushes a screen when you hit the `Q` key to ask you if you really want to quit.
From the quit screen you can click either Quit to exit the app immediately, or Cancel to dismiss the screen and return to the main screen.

**modal01.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class QuitScreen(Screen):
    """Screen with a dialog to quit."""

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Are you sure you want to quit?", id="question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        else:
            self.app.pop_screen()


class ModalApp(App):
    """An app with a modal dialog."""

    CSS_PATH = "modal01.tcss"
    BINDINGS = [("q", "request_quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(TEXT * 8)
        yield Footer()

    def action_request_quit(self) -> None:
        self.push_screen(QuitScreen())


if __name__ == "__main__":
    app = ModalApp()
    app.run()
```

**modal01.tcss**


```css
QuitScreen {
    align: center middle;
}

#dialog {
    grid-size: 2;
    grid-gutter: 1 2;
    grid-rows: 1fr 3;
    padding: 0 1;
    width: 60;
    height: 11;
    border: thick $background 80%;
    background: $surface;
}

#question {
    column-span: 2;
    height: 1fr;
    width: 1fr;
    content-align: center middle;
}

Button {
    width: 100%;
}
```
Note the `request_quit` action in the app which pushes a new instance of `QuitScreen`.
This makes the quit screen active. If you click Cancel, the quit screen calls `pop_screen` to return the default screen. This also removes and deletes the `QuitScreen` object.

There are two flaws with this modal screen, which we can fix in the same way.

The first flaw is that the app adds a new quit screen every time you press `Q`, even when the quit screen is still visible.
Consequently if you press `Q` three times, you will have to click Cancel three times to get back to the main screen.
This is because bindings defined on App are always checked, and we call `push_screen` for every press of `Q`.

The second flaw is that the modal dialog doesn't *look* modal.
There is no indication that the main interface is still there, waiting to become active again.

We can solve both those issues by replacing our use of `Screen` with `ModalScreen`.
This screen sub-class will prevent key bindings on the app from being processed.
It also sets a background with a little alpha to allow the previous screen to show through.

Let's see what happens when we use `ModalScreen`.


**modal02.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class QuitScreen(ModalScreen):
    """Screen with a dialog to quit."""

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Are you sure you want to quit?", id="question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        else:
            self.app.pop_screen()


class ModalApp(App):
    """An app with a modal dialog."""

    CSS_PATH = "modal01.tcss"
    BINDINGS = [("q", "request_quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(TEXT * 8)
        yield Footer()

    def action_request_quit(self) -> None:
        """Action to display the quit dialog."""
        self.push_screen(QuitScreen())


if __name__ == "__main__":
    app = ModalApp()
    app.run()
```

**modal01.tcss**


```css
QuitScreen {
    align: center middle;
}

#dialog {
    grid-size: 2;
    grid-gutter: 1 2;
    grid-rows: 1fr 3;
    padding: 0 1;
    width: 60;
    height: 11;
    border: thick $background 80%;
    background: $surface;
}

#question {
    column-span: 2;
    height: 1fr;
    width: 1fr;
    content-align: center middle;
}

Button {
    width: 100%;
}
```
Now when we press `Q`, the dialog is displayed over the main screen.
The main screen is darkened to indicate to the user that it is not active, and only the dialog will respond to input.

## Returning data from screens

It is a common requirement for screens to be able to return data.
For instance, you may want a screen to show a dialog and have the result of that dialog processed *after* the screen has been popped.

To return data from a screen, call ``dismiss()`` on the screen with the data you wish to return.
This will pop the screen and invoke a callback set when the screen was pushed (with ``push_screen``).

Let's modify the previous example to use `dismiss` rather than an explicit `pop_screen`.

**modal03.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class QuitScreen(ModalScreen[bool]):  # (1)!
    """Screen with a dialog to quit."""

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Are you sure you want to quit?", id="question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.dismiss(True)
        else:
            self.dismiss(False)


class ModalApp(App):
    """An app with a modal dialog."""

    CSS_PATH = "modal01.tcss"
    BINDINGS = [("q", "request_quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(TEXT * 8)
        yield Footer()

    def action_request_quit(self) -> None:
        """Action to display the quit dialog."""

        def check_quit(quit: bool | None) -> None:
            """Called when QuitScreen is dismissed."""
            if quit:
                self.exit()

        self.push_screen(QuitScreen(), check_quit)


if __name__ == "__main__":
    app = ModalApp()
    app.run()
```


**modal01.tcss**


```css
QuitScreen {
    align: center middle;
}

#dialog {
    grid-size: 2;
    grid-gutter: 1 2;
    grid-rows: 1fr 3;
    padding: 0 1;
    width: 60;
    height: 11;
    border: thick $background 80%;
    background: $surface;
}

#question {
    column-span: 2;
    height: 1fr;
    width: 1fr;
    content-align: center middle;
}

Button {
    width: 100%;
}
```
In the `on_button_pressed` message handler we call `dismiss` with a boolean that indicates if the user has chosen to quit the app.
This boolean is passed to the `check_quit` function we provided when `QuitScreen` was pushed.

Although this example behaves the same as the previous code, it is more flexible because it has removed responsibility for exiting from the modal screen to the caller.
This makes it easier for the app to perform any cleanup actions prior to exiting, for example.

Returning data in this way can help keep your code manageable by making it easy to re-use your `Screen` classes in other contexts.

### Typing screen results

You may have noticed in the previous example that we changed the base class to `ModalScreen[bool]`.
The addition of `[bool]` adds typing information that tells the type checker to expect a boolean in the call to `dismiss`, and that any callback set in `push_screen` should also expect the same type. As always, typing is optional in Textual, but this may help you catch bugs.


### Waiting for screens

It is also possible to wait on a screen to be dismissed, which can feel like a more natural way of expressing logic than a callback.
The ``push_screen_wait()`` method will push a screen and wait for its result (the value from ``Screen.dismiss()``).

This can only be done from a [worker](./workers.md), so that waiting for the screen doesn't prevent your app from updating.

Let's look at an example that uses `push_screen_wait` to ask a question and waits for the user to reply by clicking a button.


**questions01.py**


```python
from textual import on, work
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Label


class QuestionScreen(Screen[bool]):
    """Screen with a parameter."""

    def __init__(self, question: str) -> None:
        self.question = question
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(self.question)
        yield Button("Yes", id="yes", variant="success")
        yield Button("No", id="no")

    @on(Button.Pressed, "#yes")
    def handle_yes(self) -> None:
        self.dismiss(True)  # (1)!

    @on(Button.Pressed, "#no")
    def handle_no(self) -> None:
        self.dismiss(False)  # (2)!


class QuestionsApp(App):
    """Demonstrates wait_for_dismiss"""

    CSS_PATH = "questions01.tcss"

    @work  # (3)!
    async def on_mount(self) -> None:
        if await self.push_screen_wait(  # (4)!
            QuestionScreen("Do you like Textual?"),
        ):
            self.notify("Good answer!")
        else:
            self.notify(":-(", severity="error")


if __name__ == "__main__":
    app = QuestionsApp()
    app.run()
```

2. Dismiss with `False` when pressing the No button.
3. The `work` decorator will make this method run in a worker (background task).
4. Will return a result when the user clicks one of the buttons.

**questions01.tcss**


```css
QuestionScreen {
    layout: grid;
    grid-size: 2 2;
    align: center bottom;
}

QuestionScreen > Label {
    margin: 1;
    text-align: center;
    column-span: 2;
    width: 1fr;
}

QuestionScreen Button {
    margin: 2;
    width: 1fr;
}
```
The mount handler on the app is decorated with `@work`, which makes the code run in a worker (background task).
In the mount handler we push the screen with the `push_screen_wait`.
When the user presses one of the buttons, the screen calls ``dismiss()`` with either `True` or `False`.
This value is then returned from the `push_screen_wait` method in the mount handler.


## Modes

Some apps may benefit from having multiple screen stacks, rather than just one.
Consider an app with a dashboard screen, a settings screen, and a help screen.
These are independent in the sense that we don't want to prevent the user from switching between them, even if there are one or more modal screens on the screen stack.
But we may still want each individual screen to have a navigation stack where we can push and pop screens.

In Textual we can manage this with *modes*.
A mode is simply a named screen stack, which we can switch between as required.
When we switch modes, the topmost screen in the new mode becomes the active visible screen.

The following diagram illustrates such an app with modes.
On startup the app switches to the "dashboard" mode which makes the top of the stack visible.

![Modes dashboard](../images/screens/modes1.excalidraw.svg)

If we later change the mode to "settings", the top of that mode's screen stack becomes visible.

![Modes settings](../images/screens/modes2.excalidraw.svg)

To add modes to your app, define a ``MODES`` class variable in your App class which should be a `dict` that maps the name of the mode on to either a screen object, a callable that returns a screen, or the name of an installed screen.
However you specify it, the values in `MODES` set the base screen for each mode's screen stack.

You can switch between these screens at any time by calling ``App.switch_mode``.
When you switch to a new mode, the topmost screen in the new stack becomes visible.
Any calls to ``App.push_screen`` or ``App.pop_screen`` will affect only the active mode.

You can set which mode will be active when the app starts by setting the ``DEFAULT_MODE`` class variable.

Let's look at an example with modes:

**modes01.py**


```python
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Placeholder


class DashboardScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Placeholder("Dashboard Screen")
        yield Footer()


class SettingsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Placeholder("Settings Screen")
        yield Footer()


class HelpScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Placeholder("Help Screen")
        yield Footer()


class ModesApp(App):
    BINDINGS = [
        ("d", "switch_mode('dashboard')", "Dashboard"),  # (1)!
        ("s", "switch_mode('settings')", "Settings"),
        ("h", "switch_mode('help')", "Help"),
    ]
    MODES = {
        "dashboard": DashboardScreen,  # (2)!
        "settings": SettingsScreen,
        "help": HelpScreen,
    }

    def on_mount(self) -> None:
        self.switch_mode("dashboard")  # (3)!


if __name__ == "__main__":
    app = ModesApp()
    app.run()
```

2. Associates `DashboardScreen` with the name "dashboard".
3. Switches to the dashboard mode.


Here we have defined three screens.
One for a dashboard, one for settings, and one for help.
We've bound keys to each of these screens, so the user can switch between the screens.

Pressing `D`, `S`, or `H` switches between these modes.


## Screen events

Textual will send a [ScreenSuspend](../events/screen_suspend.md) event to screens that have become inactive due to another screen being pushed, or switching via a mode.

When a screen becomes active, Textual will send a [ScreenResume](../events/screen_resume.md) event to the newly active screen.

These events can be useful if you want to disable processing for a screen that is no longer visible, for example.

---

**See also**

- [App](./app.md) - The App class and application lifecycle
- [Actions](./actions.md) - Built-in screen navigation actions
- [Widgets](./widgets.md) - Compose screens with widgets
- [Workers](./workers.md) - Run background tasks from screens
- [Events reference](../events/index.md) - Screen suspend and resume events
