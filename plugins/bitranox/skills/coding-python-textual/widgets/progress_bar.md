# ProgressBar


A widget that displays progress on a time-consuming task.

- [ ] Focusable
- [ ] Container

## Examples

### Progress Bar in Isolation

The example below shows a progress bar in isolation.
It shows the progress bar in:

 - its indeterminate state, when the `total` progress hasn't been set yet;
 - the middle of the progress; and
 - the completed state.

**progress_bar_isolated.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Center, Middle
from textual.timer import Timer
from textual.widgets import Footer, ProgressBar


class IndeterminateProgressBar(App[None]):
    BINDINGS = [("s", "start", "Start")]

    progress_timer: Timer
    """Timer to simulate progress happening."""

    def compose(self) -> ComposeResult:
        with Center():
            with Middle():
                yield ProgressBar()
        yield Footer()

    def on_mount(self) -> None:
        """Set up a timer to simulate progess happening."""
        self.progress_timer = self.set_interval(1 / 10, self.make_progress, pause=True)

    def make_progress(self) -> None:
        """Called automatically to advance the progress bar."""
        self.query_one(ProgressBar).advance(1)

    def action_start(self) -> None:
        """Start the progress tracking."""
        self.query_one(ProgressBar).update(total=100)
        self.progress_timer.resume()


if __name__ == "__main__":
    IndeterminateProgressBar().run()
```
### Complete App Example

The example below shows a simple app with a progress bar that is keeping track of a fictitious funding level for an organisation.

**progress_bar.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Center, VerticalScroll
from textual.widgets import Button, Header, Input, Label, ProgressBar


class FundingProgressApp(App[None]):
    CSS_PATH = "progress_bar.tcss"

    TITLE = "Funding tracking"

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            yield Label("Funding: ")
            yield ProgressBar(total=100, show_eta=False)  # (1)!
        with Center():
            yield Input(placeholder="$$$")
            yield Button("Donate")

        yield VerticalScroll(id="history")

    def on_button_pressed(self) -> None:
        self.add_donation()

    def on_input_submitted(self) -> None:
        self.add_donation()

    def add_donation(self) -> None:
        text_value = self.query_one(Input).value
        try:
            value = int(text_value)
        except ValueError:
            return
        self.query_one(ProgressBar).advance(value)
        self.query_one(VerticalScroll).mount(Label(f"Donation for ${value} received!"))
        self.query_one(Input).value = ""


if __name__ == "__main__":
    FundingProgressApp().run()
```


**progress_bar.tcss**


```css
Container {
    overflow: hidden hidden;
    height: auto;
}

Center {
    margin-top: 1;
    margin-bottom: 1;
    layout: horizontal;
}

ProgressBar {
    padding-left: 3;
}

Input {
    width: 16;
}

VerticalScroll {
    height: auto;
}
```
### Gradient Bars

Progress bars support an optional `gradient` parameter, which renders a smooth gradient rather than a solid bar.
To use a gradient, create and set a `Gradient` object on the ProgressBar widget.

> **Note**
>
>
> Setting a gradient will override styles set in CSS.


Here's an example:

**progress_bar_gradient.py**


```python
from textual.app import App, ComposeResult
from textual.color import Gradient
from textual.containers import Center, Middle
from textual.widgets import ProgressBar


class ProgressApp(App[None]):
    """Progress bar with a rainbow gradient."""

    def compose(self) -> ComposeResult:
        gradient = Gradient.from_colors(
            "#881177",
            "#aa3355",
            "#cc6666",
            "#ee9944",
            "#eedd00",
            "#99dd55",
            "#44dd88",
            "#22ccbb",
            "#00bbcc",
            "#0099cc",
            "#3366bb",
            "#663399",
        )
        with Center():
            with Middle():
                yield ProgressBar(total=100, gradient=gradient)

    def on_mount(self) -> None:
        self.query_one(ProgressBar).update(progress=70)


if __name__ == "__main__":
    ProgressApp().run()
```
### Custom Styling

This shows a progress bar with custom styling.
Refer to the [section below](#styling-the-progress-bar) for more information.

**progress_bar_styled.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Center, Middle
from textual.timer import Timer
from textual.widgets import Footer, ProgressBar


class StyledProgressBar(App[None]):
    BINDINGS = [("s", "start", "Start")]
    CSS_PATH = "progress_bar_styled.tcss"

    progress_timer: Timer
    """Timer to simulate progress happening."""

    def compose(self) -> ComposeResult:
        with Center():
            with Middle():
                yield ProgressBar()
        yield Footer()

    def on_mount(self) -> None:
        """Set up a timer to simulate progress happening."""
        self.progress_timer = self.set_interval(1 / 10, self.make_progress, pause=True)

    def make_progress(self) -> None:
        """Called automatically to advance the progress bar."""
        self.query_one(ProgressBar).advance(1)

    def action_start(self) -> None:
        """Start the progress tracking."""
        self.query_one(ProgressBar).update(total=100)
        self.progress_timer.resume()


if __name__ == "__main__":
    StyledProgressBar().run()
```

**progress_bar_styled.tcss**


```css
Bar > .bar--indeterminate {
    color: $primary;
    background: $secondary;
}

Bar > .bar--bar {
    color: $primary;
    background: $primary 30%;
}

Bar > .bar--complete {
    color: $error;
}

PercentageStatus {
    text-style: reverse;
    color: $secondary;
}

ETAStatus {
    text-style: underline;
}
```
## Styling the Progress Bar

The progress bar is composed of three sub-widgets that can be styled independently:

| Widget name        | ID            | Description                                                      |
|--------------------|---------------|------------------------------------------------------------------|
| `Bar`              | `#bar`        | The bar that visually represents the progress made.              |
| `PercentageStatus` | `#percentage` | [Label](./label.md) that shows the percentage of completion.     |
| `ETAStatus`        | `#eta`        | [Label](./label.md) that shows the estimated time to completion. |

### Bar Component Classes

*API reference: `textual.widgets._progress_bar.Bar.COMPONENT_CLASSES`*


## Reactive Attributes

| Name         | Type    | Default | Description                                                                                             |
| ------------ | ------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `percentage` | `float  | None`   | The read-only percentage of progress that has been made. This is `None` if the `total` hasn't been set. |
| `progress`   | `float` | `0`     | The number of steps of progress already made.                                                           |
| `total`      | `float  | None`   | The total number of steps that we are keeping track of.                                                 |

## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.

## See also

- [LoadingIndicator](./loading_indicator.md) - An indeterminate loading animation
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---

*API reference: `textual.widgets.ProgressBar`*
