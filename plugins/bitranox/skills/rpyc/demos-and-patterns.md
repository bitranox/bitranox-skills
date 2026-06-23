# Demo Catalog

## 1. Echo -- Simple One-Shot Echo

> Source: `demos/echo/`

Pattern: `OneShotServer` with a basic request/response service.

**Server (`server.py`):**
```python
import rpyc

class EchoService(rpyc.Service):
    def on_connect(self, conn):
        msg = f"on connect: {conn._channel.stream.sock.getpeername()}"
        conn._config["logger"].debug(msg)

    def on_disconnect(self, conn):
        pass

    def exposed_echo(self, message):
        if message == "Echo":
            return "Echo Reply"
        else:
            return "Parameter Problem"

rpyc.OneShotServer(service=EchoService, port=18861,
                    protocol_config={'allow_all_attrs': True}).start()
```

**Client (`client.py`):**
```python
import rpyc
conn = rpyc.connect("localhost", 18861)
conn.root.echo("Echo")   # => "Echo Reply"
conn.close()
```

---

## 2. Boilerplate -- Generic Service with Events

> Source: `demos/boilerplate/`

Pattern: File monitor service factory with async callbacks, `BgServingThread`, and client object lifecycle.

**Service (`rpyc_service.py`):**
```python
import rpyc, os, time
from threading import Thread

class MyServiceFactory(rpyc.Service):
    class exposed_MyService(object):
        def __init__(self, filename, callback, interval=1):
            self.filename = filename
            self.interval = interval
            self.last_stat = None
            self.callback = rpyc.async_(callback)
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

**Server (`rpyc_server.py`):**
```python
from rpyc.utils.server import ThreadedServer
from rpyc_service import MyServiceFactory
ThreadedServer(MyServiceFactory, port=18000).start()
```

**Client (`rpyc_client.py`):**
```python
import rpyc
from time import sleep

class MyClient(object):
    def __init__(self):
        self.conn = rpyc.connect("localhost", 18000)
        self.bgsrv = rpyc.BgServingThread(self.conn)
        self.service = self.conn.root.MyService("/tmp/test.txt", self.on_event)

    def on_event(self, oldstat, newstat):
        print(f"file changed: {oldstat} -> {newstat}")

    def close(self):
        self.service.stop()
        self.bgsrv.stop()
        self.conn.close()

client = MyClient()
sleep(10)
client.close()
```

---

## 3. Time -- Service Discovery with Registry

> Source: `demos/time/`

Pattern: Service with `auto_register=True`, client discovers via `connect_by_service`.

**Service (`time_service.py`):**
```python
import time
from rpyc import Service

class TimeService(Service):
    def exposed_get_utc(self):
        return time.time()
    def exposed_get_time(self):
        return time.ctime()
```

**Server (`server.py`):**
```python
from rpyc.utils.server import ThreadedServer
from time_service import TimeService
ThreadedServer(TimeService, auto_register=True).start()
```

**Client (`client.py`):**
```python
import rpyc
c = rpyc.connect_by_service("TIME")
print("server's time is", c.root.get_time())
```

---

## 4. Sharing -- Thread-Safe Shared State

> Source: `demos/sharing/`

Pattern: `ThreadedServer` with shared state between connections, synchronized with `threading.Lock`.

**Synchronize decorator:**
```python
def synchronize(lock):
    def sync_func(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            lock.acquire()
            res = func(*args, **kwargs)
            lock.release()
            return res
        return wrapper
    return sync_func
```

**Class-level shared state:**
```python
class SharingComponent(object):
    lock = threading.Lock()

    def __init__(self):
        self.sequence_id = 0

    @synchronize(lock)
    def get_sequence_id(self):
        return self.sleepy_sequence_id()

class SharingService(rpyc.Service):
    __shared__ = SharingComponent()  # shared across all connection instances

    @property
    def shared(self):
        return SharingService.__shared__

    def exposed_echo(self, message):
        seq_id = self.shared.get_sequence_id()  # thread-safe access
        return f"Echo Reply {seq_id}"
```

---

## 5. Async Client -- Blocking Server Functions

> Source: `demos/async_client/`

Pattern: Handling blocking server-side functions with async proxies and `BgServingThread`.

**Server (`server.py`):**
```python
class Service(rpyc.Service):
    def exposed_fetch_value(self):
        return self._value

    def exposed_function(self, client_event, block_server_thread=False):
        if block_server_thread:
            def _wait(): return getattr(client_event, 'wait')()
            def _set(): return getattr(client_event, 'set')()
        else:
            _wait = rpyc.async_(client_event.wait)
            _set = rpyc.async_(client_event.set)
        _wait()
        for i in (1, 2):
            time.sleep(0.2)
        self._value = 6465616462656566
        _set()
```

**Client (`client.py`):**
```python
def async_example(connection, event):
    _async_function = rpyc.async_(connection.root.function)
    bgsrv = rpyc.BgServingThread(connection)
    ares = _async_function(event, block_server_thread=False)
    value = ares.value
    event.clear()
    bgsrv.stop()
```

---

## 6. Chat -- Multi-User Chat with Callbacks

> Source: `demos/chat/`

Pattern: User tokens as capabilities, async broadcast callbacks, GTK reactor integration.

**Server (`server.py`):**
```python
class UserToken(object):
    def __init__(self, name, callback):
        self.name = name
        self.callback = callback
        self.broadcast(f"* Hello {self.name} *")
        tokens.add(self)

    def exposed_say(self, message):
        self.broadcast(f"[{self.name}] {message}")

    def exposed_logout(self):
        self.stale = True
        tokens.discard(self)
        self.broadcast(f"* Goodbye {self.name} *")

    def broadcast(self, text):
        with broadcast_lock:
            for tok in tokens:
                tok.callback(text)

class ChatService(Service):
    def exposed_login(self, username, password, callback):
        if username in USERS_DB and password == USERS_DB[username]:
            self.token = UserToken(username, async_(callback))
            return self.token
```

**Client usage:**
```python
conn = rpyc.connect("localhost", 19912)
user_token = conn.root.login("foo", "bar", on_message)
user_token.say("hello world")
```

**GTK reactor integration:**
```python
gobject.io_add_watch(self.conn, gobject.IO_IN, self.bg_server)

def bg_server(self, source=None, cond=None):
    if self.conn:
        self.conn.poll_all()
        return True
    return False
```

---

## 7. File Monitor -- Event-Driven File Watching

> Source: `demos/filemon/`

Pattern: Server-side thread monitors file changes, notifies client via async callbacks. Same as tutorial Part 5 FileMonitorService.

**Client (`client.py`):**
```python
import rpyc, time, os

f = open("/tmp/floop.bloop", "w")
conn = rpyc.connect("localhost", 18871)
bgsrv = rpyc.BgServingThread(conn)

def on_file_changed(oldstat, newstat):
    print(f"file changed: {oldstat} -> {newstat}")

mon = conn.root.FileMonitor("/tmp/floop.bloop", on_file_changed)
time.sleep(2)
f.write("shmoop"); f.flush()
time.sleep(2)
mon.stop()
bgsrv.stop()
conn.close()
```

---

## 8. Web8 -- Remote GUI via RPyC

> Source: `demos/web8/`

Pattern: Server constructs GTK widgets on the client via passed proxy objects. Demonstrates bidirectional capability passing and reactor integration.

**Server builds UI using client's GTK:**
```python
class Web8Service(rpyc.Service):
    def exposed_get_page(self, gtk, content, page):
        lbl = gtk.Label("Hello mate")
        lbl.show()
        content.pack_start(lbl)
```

**Client passes SafeGTK capability:**
```python
from safegtk import SafeGTK
conn = rpyc.connect(host, port, service=BrowserServiceFactory(self))
conn.root.get_page(SafeGTK, self.box_content, page)
```

**SafeGTK -- restricted capability object:**
```python
safe_gtk_classes = {"Box", "VBox", "HBox", "Frame", "Entry", "Button",
                    "ScrolledWindow", "TextView", "Label"}

class SafeGTK(object):
    for _name in dir(gtk):
        if _name in safe_gtk_classes or _name.isupper():
            exec(f"exposed_{_name} = gtk.{_name}")
```
