# Toast

> **Tip: Added in version 0.30.0**


A widget which displays a notification message.

- [ ] Focusable
- [ ] Container

> **Warning: Note that `Toast` isn't designed to be used directly in your applications, but it is instead used by ``notify`` to display a message when using Textual's built-in notification system.**


## Styling

You can customize the style of Toasts by targeting the `Toast` [CSS type](../guide/CSS.md#type-selector).
For example:

```scss
Toast {
    padding: 3;
}
```

If you wish to change the location of Toasts, it is possible by targeting the `ToastRack` CSS type.
For example:

```scss
ToastRack {
        align: right top;
}
```

The three severity levels also have corresponding
[classes](../guide/CSS.md#class-name-selector), allowing you to target the
different styles of notification. They are:

- `-information`
- `-warning`
- `-error`

If you wish to tailor the notifications for your application you can add
rules to your CSS like this:

```scss
Toast.-information {
    /* Styling here. */
}

Toast.-warning {
    /* Styling here. */
}

Toast.-error {
    /* Styling here. */
}
```

You can customize just the title wih the `toast--title` class.
The following would make the title italic for an information toast:

```scss
Toast.-information .toast--title {
    text-style: italic;
}

```

## Example

**toast.py**


```python
from textual.app import App


class ToastApp(App[None]):
    def on_mount(self) -> None:
        # Show an information notification.
        self.notify("It's an older code, sir, but it checks out.")

        # Show a warning. Note that Textual's notification system allows
        # for the use of Rich console markup.
        self.notify(
            "Now witness the firepower of this fully "
            "[b]ARMED[/b] and [i][b]OPERATIONAL[/b][/i] battle station!",
            title="Possible trap detected",
            severity="warning",
        )

        # Show an error. Set a longer timeout so it's noticed.
        self.notify("It's a trap!", severity="error", timeout=10)

        # Show an information notification, but without any sort of title.
        self.notify("It's against my programming to impersonate a deity.", title="")


if __name__ == "__main__":
    ToastApp().run()
```
## Reactive Attributes

This widget has no reactive attributes.

## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

The toast widget provides the following component classes:

*API reference: `textual.widgets._toast.Toast.COMPONENT_CLASSES`*


## See also

- [Widgets guide](../guide/widgets.md) - How to build and use widgets
- [CSS guide](../guide/CSS.md) - How to style widgets with CSS

---

*API reference: `textual.widgets._toast.Toast`*
