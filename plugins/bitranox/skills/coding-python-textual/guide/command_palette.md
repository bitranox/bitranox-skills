# Command Palette

Textual apps have a built-in *command palette*, which gives users a quick way to access certain functionality within your app.

In this chapter we will explain what a command palette is, how to use it, and how you can add your own commands.

## Launching the command palette

Press `Ctrl+P` to invoke the command palette screen, which contains of a single input widget.
Textual will suggest commands as you type in that input.
Press `Up` or `Down` to select a command from the list, and `Enter` to invoke it.

Commands are looked up via a *fuzzy* search, which means Textual will show commands that match the keys you type in the same order, but not necessarily at the start of the command.
For instance the "Change theme" command will be shown if you type "ch" (for **ch**ange), but you could also type "th" (to match **t**heme).
This scheme allows the user to quickly get to a particular command with fewer key-presses.


## System commands

Textual apps have a number of *system* commands enabled by default.
These are declared in the ``App.get_system_commands`` method.
You can implement this method in your App class to add more commands.

To declare a command, define a `get_system_commands` method on your App.
Textual will call this method with the screen that was active when the user summoned the command palette.

You can add a command by yielding a ``SystemCommand`` object which contains `title` and `help` text to be shown in the command palette, and `callback` which is a callable to run when the user selects the command.
Additionally, there is a `discover` boolean which when `True` (the default) shows the command even if the search import is empty. When set to `False`, the command will show only when there is input.

Here's how we would add a command to ring the terminal bell (a super useful piece of functionality):

**command01.py**


```python
from typing import Iterable

from textual.app import App, SystemCommand
from textual.screen import Screen


class BellCommandApp(App):
    """An app with a 'bell' command."""

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)  # (1)!
        yield SystemCommand("Bell", "Ring the bell", self.bell)  # (2)!


if __name__ == "__main__":
    app = BellCommandApp()
    app.run()
```

2. Adds a new command.


This is a straightforward way of adding commands to your app.
For more advanced integrations you can implement your own *command providers*.


## Command providers

To add your own command(s) to the command palette, define a ``command.Provider`` class then add it to the ``COMMANDS`` class var on your `App` class.

Let's look at a simple example which adds the ability to open Python files via the command palette.

The following example will display a blank screen initially, but if you bring up the command palette and start typing the name of a Python file, it will show the command to open it.

> **Tip**
>
>
> If you are running that example from the repository, you may want to add some additional Python files to see how the examples works with multiple files.


  ```python title="command02.py" hl_lines="12-40 46"
  from __future__ import annotations

  from functools import partial
  from pathlib import Path

  from textual.app import App, ComposeResult
  from textual.command import Hit, Hits, Provider
  from textual.containers import VerticalScroll
  from textual.widgets import Static


  class PythonFileCommands(Provider):
      """A command provider to open a Python file in the current working directory."""

      def read_files(self) -> list[Path]:
          """Get a list of Python files in the current working directory."""
          return list(Path("./").glob("*.py"))

      async def startup(self) -> None:  # (1)!
          """Called once when the command palette is opened, prior to searching."""
          worker = self.app.run_worker(self.read_files, thread=True)
          self.python_paths = await worker.wait()

      async def search(self, query: str) -> Hits:  # (2)!
          """Search for Python files."""
          matcher = self.matcher(query)  # (3)!

          app = self.app
          assert isinstance(app, ViewerApp)

          for path in self.python_paths:
              command = f"open {str(path)}"
              score = matcher.match(command)  # (4)!
              if score > 0:
                  yield Hit(
                      score,
                      matcher.highlight(command),  # (5)!
                      partial(app.open_file, path),
                      help="Open this file in the viewer",
                  )


  class ViewerApp(App):
      """Demonstrate a command source."""

      COMMANDS = App.COMMANDS | {PythonFileCommands}  # (6)!

      def compose(self) -> ComposeResult:
          with VerticalScroll():
              yield Static(id="code", expand=True)

      def open_file(self, path: Path) -> None:
          """Open and display a file with syntax highlighting."""
          from rich.syntax import Syntax

          syntax = Syntax.from_path(
              str(path),
              line_numbers=True,
              word_wrap=False,
              indent_guides=True,
              theme="github-dark",
          )
          self.query_one("#code", Static).update(syntax)


  if __name__ == "__main__":
      app = ViewerApp()
      app.run()
  ```


There are four methods you can override in a command provider: ``startup``, ``search``, ``discover`` and ``shutdown``.
All of these methods should be coroutines (`async def`). Only `search` is required, the other methods are optional.
Let's explore those methods in detail.

### startup method

The ``startup`` method is called when the command palette is opened.
You can use this method as way of performing work that needs to be done prior to searching.
In the example, we use this method to get the Python (.py) files in the current working directory.

### search method

The ``search`` method is responsible for finding results (or *hits*) that match the user's input.
This method should *yield* ``Hit`` objects for any command that matches the `query` argument.

Exactly how the matching is implemented is up to the author of the command provider, but we recommend using the builtin fuzzy matcher object, which you can get by calling ``matcher``.
This object has a ``match()`` method which compares the user's search term against the potential command and returns a *score*.
A score of zero means *no hit*, and you can discard the potential command.
A score of above zero indicates the confidence in the result, where 1 is an exact match, and anything lower indicates a less confident match.

The ``Hit`` contains information about the score (used in ordering) and how the hit should be displayed, and an optional help string.
It also contains a callback, which will be run if the user selects that command.

In the example above, the callback is a lambda which calls the `open_file` method in the example app.

> **Note**
>
>
> Unlike most other places in Textual, errors in command provider will not *exit* the app.
> This is a deliberate design decision taken to prevent a single broken `Provider` class from making the command palette unusable.
> Errors in command providers will be logged to the [console](./devtools.md).


### discover method

The ``discover`` method is responsible for providing results (or *discovery hits*) that should be shown to the user when the command palette input is empty;
this is to aid in command discoverability.

> **Note**
>
>
> Because `discover` hits are shown the moment the command palette is opened, these should ideally be quick to generate;
> commands that might take time to generate are best left for `search` -- use `discover` to help the user easily find the most important commands.


`discover` is similar to `search` but with these differences:

- `discover` accepts no parameters (instead of the search value)
- `discover` yields instances of ``DiscoveryHit`` (instead of instances of ``Hit``)

Instances of ``DiscoveryHit`` contain information about how the hit should be displayed, an optional help string, and a callback which will be run if the user selects that command.

### shutdown method

The ``shutdown`` method is called when the command palette is closed.
You can use this as a hook to gracefully close any objects you created in ``startup``.

## Screen commands

You can also associate commands with a screen by adding a `COMMANDS` class var to your Screen class.

Commands defined on a screen are only considered when that screen is active.
You can use this to implement commands that are specific to a particular screen, that wouldn't be applicable everywhere in the app.

## Disabling the command palette

The command palette is enabled by default.
If you would prefer not to have the command palette, you can set `ENABLE_COMMAND_PALETTE = False` on your app class.

Here's an app class with no command palette:

```python
class NoPaletteApp(App):
    ENABLE_COMMAND_PALETTE = False
```

## Changing command palette key

You can change the key that opens the command palette by setting the class variable `COMMAND_PALETTE_BINDING` on your app.

Prior to version 0.77.0, Textual used the binding `ctrl+backslash` to launch the command palette.
Here's how you would restore the older key binding:

```python
class NewPaletteBindingApp(App):
    COMMAND_PALETTE_BINDING = "ctrl+backslash"
```

---

**See also**

- [Input](./input.md#bindings) - Key bindings and input handling
- [Actions](./actions.md) - Define custom actions for the command palette
- [Design](./design.md) - Customize the theme and color scheme via the command palette
