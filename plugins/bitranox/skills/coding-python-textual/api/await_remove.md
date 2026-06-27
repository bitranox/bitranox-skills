This module contains the `AwaitRemove` class.
An `AwaitRemove` object is returned by ``Widget.remove()`` and other methods which remove widgets.
You can await the return value if you need to know exactly when the widget(s) have been removed.
Or you can ignore it and Textual will wait for the widgets to be removed before handling the next message.

> **Note**
>
>
> You are unlikely to need to explicitly create these objects yourself.


*API reference: `textual.await_remove`*
