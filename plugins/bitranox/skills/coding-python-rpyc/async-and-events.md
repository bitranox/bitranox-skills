# Asynchronous Operations and Events

## Tutorial Part 5: Asynchronous Operation

> Source: `tutorial/tut5.md`, `docs/async.md`

### `async_()` -- Make Remote Calls Asynchronous

```python
import rpyc
c = rpyc.classic.connect("localhost")

# Wrap a remote function
asleep = rpyc.async_(c.modules.time.sleep)

# Returns AsyncResult immediately (non-blocking)
res = asleep(15)
res.ready        # => False (not done yet)
# ... after 15 seconds ...
res.ready        # => True
res.value        # => None

# With exceptions
aint = rpyc.async_(c.builtins.int)
x = aint("not a number")
x.error          # => True
x.value          # raises ValueError
```

### AsyncResult Properties and Methods

- `ready` -- whether result has arrived
- `error` -- whether result is an exception
- `expired` -- whether the object's time-to-wait has elapsed
- `value` -- the value (blocks if not ready; raises if error/expired)
- `wait()` -- wait for completion or expiry
- `add_callback(func)` -- callback when value arrives
- `set_expiry(seconds)` -- set timeout

### Important: Hold Strong References

Async proxies are cached by weak-reference. Hold a strong reference:
```python
# WRONG:
res = rpyc.async_(conn.root.myfunc)(1, 2, 3)

# CORRECT:
myfunc_async = rpyc.async_(conn.root.myfunc)
res = myfunc_async(1, 2, 3)
```

**No execution order guarantee** for multiple async requests.

---

## `timed()` -- Synchronous Call with Timeout

```python
timed_sleep = rpyc.timed(conn.modules.time.sleep, 6)

async_res = timed_sleep(3)
async_res.value              # returns after 3 seconds

async_res = timed_sleep(10)
async_res.value              # raises AsyncResultTimeout
```

---

## `BgServingThread` -- Background Request Processing

```python
bgsrv = rpyc.BgServingThread(conn)
# ... do blocking stuff while incoming requests are handled in background ...
bgsrv.stop()
```

Allows client-side code to perform blocking calls while still processing incoming requests (e.g., server callbacks). Alternative: use `conn.poll_all()` to explicitly serve pending requests, or integrate with a reactor (e.g., `gobject.io_add_watch`).

---

## Events -- Async Callbacks

Combining `async_` and callbacks yields events: async callbacks where the return value is ignored.

### FileMonitor Example (Server)

```python
import rpyc, os, time
from threading import Thread

class FileMonitorService(rpyc.Service):
    class exposed_FileMonitor(object):
        def __init__(self, filename, callback, interval=1):
            self.filename = filename
            self.interval = interval
            self.last_stat = None
            self.callback = rpyc.async_(callback)  # async callback
            self.active = True
            self.thread = Thread(target=self.work)
            self.thread.start()

        def exposed_stop(self):
            self.active = False
            self.thread.join()

        def work(self):
            while self.active:
                stat = os.stat(self.filename)
                if self.last_stat is not None and self.last_stat != stat:
                    self.callback(self.last_stat, stat)
                self.last_stat = stat
                time.sleep(self.interval)
```

### FileMonitor Example (Client)

```python
conn = rpyc.connect("localhost", 18871)
bgsrv = rpyc.BgServingThread(conn)

def on_file_changed(oldstat, newstat):
    print(f"file changed: {oldstat} -> {newstat}")

mon = conn.root.FileMonitor("/tmp/floop.bloop", on_file_changed)
# ... file changes are reported via callback ...

mon.stop()
bgsrv.stop()
conn.close()
```

### Without BgServingThread

```python
conn = rpyc.connect("localhost", 18871)
mon = conn.root.FileMonitor("/tmp/floop.bloop", on_file_changed)
# Notifications are NOT processed until you interact with the connection
conn.poll_all()  # explicitly serve all pending requests
```
