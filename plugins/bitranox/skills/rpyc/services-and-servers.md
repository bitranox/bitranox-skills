# Services and Servers

## Tutorial Part 3: Services and New-Style RPyC

> Source: `tutorial/tut3.md`, `docs/services.md`

### Service Boilerplate

```python
import rpyc

class MyService(rpyc.Service):
    def on_connect(self, conn):
        pass  # called when connection is created

    def on_disconnect(self, conn):
        pass  # called after connection closes

    def exposed_get_answer(self):  # accessible remotely
        return 42

    exposed_the_real_answer_though = 43  # exposed attribute

    def get_question(self):  # NOT accessible remotely
        return "what is the airspeed velocity of an unladen swallow?"
```

Note: `on_connect(self, conn)` signature with `conn` parameter added in rpyc 4.0.

### Starting a Server

```python
if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    t = ThreadedServer(MyService, port=18861)
    t.start()
```

### Client Usage

```python
import rpyc
c = rpyc.connect("localhost", 18861)
c.root.get_answer()                 # => 42
c.root.the_real_answer_though       # => 43
c.root.get_question()               # => AttributeError: cannot access 'get_question'
```

### Decorator Style (alternative to `exposed_` prefix)

```python
@rpyc.service
class CalculatorService(rpyc.Service):
    @rpyc.exposed
    def add(self, a, b):
        return a + b
    @rpyc.exposed
    def sub(self, a, b):
        return a - b
```

### Exposed Classes

```python
class MyService(rpyc.Service):
    class exposed_MyClass(object):
        def __init__(self, a, b):
            self.a, self.b = a, b
        def exposed_foo(self):
            return self.a + self.b
```

### Access Policy Configuration

```python
server = ThreadedServer(MyService, port=18861, protocol_config={
    'allow_public_attrs': True,
})
```

### Shared vs. Per-Connection Service Instances

```python
# Per-connection (class passed): each connection gets its own instance
t = ThreadedServer(MyService, port=18861)

# Shared (instance passed): all connections share one instance
t = ThreadedServer(MyService(), port=18861)  # note the parentheses!
```

### Passing Arguments with `classpartial`

```python
from rpyc.utils.helpers import classpartial
service = classpartial(MyService, 1, 2, pi=3)
t = ThreadedServer(service, port=18861)
```

### Service Naming and Aliases

```python
class MyService(rpyc.Service):
    ALIASES = ["floop", "bloop"]
```

Default name: class name minus `"Service"` suffix (e.g., `MyService` -> `"MY"`). Names are case-insensitive.

### Lifecycle Hooks

- `on_connect(self, conn)` -- invoked when connection established
- `on_disconnect(self, conn)` -- invoked after connection closes (cannot access remote objects here)

Avoid overriding `__init__` -- use `on_connect` instead.

### Built-in Services

- `VoidService` -- empty "do-nothing" service; used as default client-side service
- `SlaveService` -- implements classic mode (full access)

---

## Service Discovery with Registry

> Source: `tutorial/tut3.md`

```python
# Server with auto-registration
svc = rpyc.OneShotServer(service=MyService, port=18861, auto_register=True)
svc.start()

# Client discovery
rpyc.list_services()
rpyc.discover("MY")                  # => (('192.168.1.101', 18861),)
c = rpyc.connect_by_service("MY")
c.root.get_answer()                   # => 42
```

---

## Decoupled Services

> Source: `docs/services.md`

Client and server expose different services. By default, clients expose `VoidService` (no functionality to server). In classic mode, both sides expose `SlaveService`.

**Server calls back into client service:**
```python
# Server
class ServerService(rpyc.Service):
    def on_connect(self, conn):
        self._conn = conn
    def exposed_bar(self):
        return self._conn.root.foo() + "bar"

# Client
class ClientService(rpyc.Service):
    def exposed_foo(self):
        return "foo"
conn = rpyc.connect("hostname", 12345, service=ClientService)
conn.root.bar()  # => "foobar"
```

**Callback approach (no client service needed):**
```python
# Server
class ServerService(rpyc.Service):
    def exposed_bar(self, func):
        return func() + "bar"

# Client
def foofunc():
    return "foo"
conn = rpyc.connect("hostname", 12345)
conn.root.bar(foofunc)  # => "foobar"
```

---

## Server Types

> Source: `docs/servers.md`

| Server             | Description                                        | Platform        |
|--------------------|----------------------------------------------------|-----------------|
| `ForkingServer`    | Forks child process per connection                 | POSIX only      |
| `ThreadedServer`   | Spawns thread per connection                       | POSIX + Windows |
| `ThreadPoolServer` | Thread pool; drops connections when pool exhausted | POSIX + Windows |
| `OneShotServer`    | Handles one connection then exits                  | All             |

**Custom server** -- derive from `rpyc.utils.server.Server`, implement `_accept_method()`.

**Server constructor parameters:**
- `service` -- service class or instance
- `hostname` -- bind address (default `"0.0.0.0"`)
- `port` -- TCP port
- `reuse_addr` -- reuse address (default `True`)
- `ipv6` -- use IPv6 (default `False`)
- `authenticator` -- authenticator object (default `None`)
- `registrar` -- registrar object for service discovery
- `auto_register` -- auto-register with registry (default `False`)
- `protocol_config` -- dict of protocol configuration options
- `logger` -- logger instance
- `listener_timeout` -- timeout for accept loop

**Key methods:** `start()`, `close()`
