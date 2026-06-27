# LoadingIndicator

> **Tip: Added in version 0.15.0**


Displays pulsating dots to indicate when data is being loaded.

- [ ] Focusable
- [ ] Container


> **Tip**
>
>
> Widgets have a ``loading`` reactive which
> you can use to temporarily replace your widget with a `LoadingIndicator`.
> See the [Loading Indicator](../guide/widgets.md#loading-indicator) section
> in the Widgets guide for details.


## Example

Simple usage example:

**loading_indicator.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import LoadingIndicator


class LoadingApp(App):
    def compose(self) -> ComposeResult:
        yield LoadingIndicator()


if __name__ == "__main__":
    app = LoadingApp()
    app.run()
```
## Changing Indicator Color

You can set the color of the loading indicator by setting its `color` style.

Here's how you would do that with CSS:

```css
LoadingIndicator {
    color: red;
}
```

## Reactive Attributes

This widget has no reactive attributes.

## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.

## See also

- [ProgressBar](./progress_bar.md) - Display determinate progress
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.LoadingIndicator`*
