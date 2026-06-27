*API reference: `textual.events.Click`*


## Double & triple clicks

The `chain` attribute on the `Click` event can be used to determine the number of clicks that occurred in quick succession.
A value of `1` indicates a single click, `2` indicates a double click, and so on.

By default, clicks must occur within 500ms of each other for them to be considered a chain.
You can change this value by setting the `CLICK_CHAIN_TIME_THRESHOLD` class variable on your `App` subclass.

See `MouseEvent` for the list of properties and methods on the parent class.

## See also

- [MouseDown](mouse_down.md) - Sent when a mouse button is pressed down
- [MouseUp](mouse_up.md) - Sent when a mouse button is released
- [Enter](enter.md) - Sent when the mouse enters a widget
- [Leave](leave.md) - Sent when the mouse leaves a widget
- [MouseMove](mouse_move.md) - Sent when the mouse moves over a widget
- [Button widget](../widgets/button.md) - A clickable button widget
- [Events guide](../guide/events.md) - Introduction to Textual's event system
