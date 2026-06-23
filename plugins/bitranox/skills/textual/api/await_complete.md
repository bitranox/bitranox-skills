This module contains the `AwaitComplete` class.
An `AwaitComplete` object is returned by methods that do work in the *background*.
You can await this object if you need to know when that work has completed.
Or you can ignore it, and Textual will automatically await the work before handling the next message.

> **Note**
>
>
> You are unlikely to need to explicitly create these objects yourself.


*API reference: `textual.await_complete`*
