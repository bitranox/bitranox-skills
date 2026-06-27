# Classic Mode and Tutorials

## Core Concepts

> Source: `docs/theory.md`

### Transparency and Symmetry

RPyC is **transparent**: remote objects can be plugged into existing code with virtually no cost. No definition files, name servers, HTTP servers, or special invocation syntax needed — duck-typing to the extreme. A function that works on a local file object works seamlessly on a remote file object.

**Symmetry** follows from transparency: there is no strict server vs. client distinction. Both parties may serve requests and dispatch replies. The server is simply the party that accepts incoming connections. Both client and server are identical in capability.

Two RPyC-connected processes can be thought of as a **single process** with a unified address space. Classic RPyC unifies the full address space; service-based RPyC unifies selected parts.

### Boxing (Serialization)

Objects are transferred between endpoints via "boxing":

- **By Value** — simple, immutable Python objects (strings, integers, tuples, `None`, booleans, frozensets) are serialized and sent. The encoding format is called **Brine**.
- **By Reference** — all other objects are passed as references. On the other side, these become **netrefs** (network references / transparent object proxies).

**Unboxing**: by-value data is deserialized to local objects; by-reference data becomes proxy objects (netrefs).

### Object Proxying (Netrefs)

A **netref** is a proxy object that delegates all operations to the remote target object transparently. Most operations are synchronous by default; invocation of remote functions can be made asynchronous by wrapping with `async_()`.

Netrefs fool Python's introspection:
```python
>>> isinstance(conn.modules.sys.path, list)
True
>>> import inspect
>>> inspect.isbuiltin(conn.modules.os.listdir)
True
```

Internal attributes: `____conn__` (which connection to resolve over) and `____id_pack__` (server-side object lookup identifier).

### Services

RPyC 3.0+ is **service-oriented**. RPyC itself is a "sophisticated transport layer" (mechanism); services define policy. Each end of a connection exposes a service that determines what operations are available. Classic RPyC is implemented as `SlaveService` — one specific service that grants full access.

---

## Classic Mode

> Source: `docs/classic.md`

Classic mode (pre-v3 "slave mode") gives the client full, unrestricted control over the server. Now implemented as `SlaveService`.

**Start classic server:** `rpyc_classic.py` (installed to Python scripts directory)

**Connect and use:**
```python
conn = rpyc.classic.connect("hostname")  # default port 18812

proc = conn.modules.subprocess.Popen("ls", stdout=-1, stderr=-1)
stdout, stderr = proc.communicate()

remote_list = conn.builtins.range(7)
conn.execute("print('foo')")
```

---

## Tutorial Part 1: Introduction to Classic RPyC

> Source: `tutorial/tut1.md`

**Start a classic server:**
```bash
python bin/rpyc_classic.py
# INFO:SLAVE/18812:server started on [127.0.0.1]:18812
```

**Connect from client:**
```python
import rpyc
conn = rpyc.classic.connect("localhost")  # default port 18812
```

**The `modules` namespace** — access any remote module:
```python
rsys = conn.modules.sys              # top-level: dot notation
minidom = conn.modules["xml.dom.minidom"]  # nested: bracket notation
rsys.argv                            # => ['bin/rpyc_classic.py']
conn.modules.os.chdir('..')          # change server's cwd
print("Hello!", file=conn.modules.sys.stdout)  # print on server console
```

**The `builtins` namespace:**
```python
f = conn.builtins.open('/etc/hostname')
f.read()
```

**`eval` and `execute`:**
```python
conn.execute('import math')
conn.eval('2*math.pi')       # => 6.283185307179586
conn.namespace                # => {'__builtins__': ..., 'math': ...}
```

**`teleport` — send functions to remote side:**
```python
def square(x):
    return x**2

fn = conn.teleport(square)
fn(2)                          # computed remotely
conn.eval('square(3)')         # => 9 (auto-added to remote namespace)
```

Note: teleporting closures over non-trivial objects may not work. Consider `dill` for complex cases.

---

## Tutorial Part 2: Netrefs and Exceptions

> Source: `tutorial/tut2.md`

**Netrefs are transparent proxies:**
```python
type(conn.modules.sys)           # => <netref class 'builtins.module'>
type(conn.modules.sys.path)      # => <netref class 'builtins.list'>
```

**Exception propagation** — remote exceptions propagate transparently with dual tracebacks (remote + local):
```python
conn.modules.sys.path[300]  # IndexError with both remote and local tracebacks
```

**Custom exception handling:**

Server:
```python
class HelloService(rpyc.Service):
    def exposed_foobar(self, remote_str):
        raise urllib.error.URLError("test")

server = OneShotServer(
    HelloService, port=12345,
    protocol_config={'import_custom_exceptions': True}
)
server.start()
```

Client:
```python
import rpyc
import urllib.error
rpyc.core.vinegar._generic_exceptions_cache["urllib.error.URLError"] = urllib.error.URLError

conn = rpyc.connect("localhost", 12345)
try:
    conn.root.foobar('hello')
except urllib.error.URLError:
    print('caught a URLError')
```

---

## Tutorial Part 4: Callbacks and Symmetry

> Source: `tutorial/tut4.md`

Functions are objects, and RPyC is symmetric — local functions can be passed as arguments to remote objects:

```python
c = rpyc.classic.connect("localhost")
rlist = c.modules.builtins.list(range(10))  # remote list

def f(x):
    return x**3

# Remote map calls local function f for each element:
list(c.modules.builtins.map(f, rlist))
# => [0, 1, 8, 27, 64, 125, 216, 343, 512, 729]
```

While the client waits for the result (synchronous request), it serves all incoming requests — so the server can invoke the callback it received on the client.

---

## How-To Patterns

> Source: `docs/howto.md`

**Redirect stdin/stdout between hosts:**
```python
import rpyc, sys
c = rpyc.classic.connect("localhost")
c.modules.sys.stdout = sys.stdout        # redirect server stdout to client
c.execute("print('hi here')")            # now prints on client
```

**Context manager for redirected stdio:**
```python
with rpyc.classic.redirected_stdio(c):
    c.execute("print('hi here')")         # printed on client
# After context: printed on server again
```

**Remote debugging with pdb:**
```python
c = rpyc.classic.connect("localhost")
c.modules["xml.dom.minidom"].parseString("<<invalid>>")  # raises ExpatError
rpyc.classic.pm(c)  # start post-mortem pdb on server's last exception
```

**Network tunneling** — use remote machine as bridge:
```python
# Machine A connects to machine B through machine C
machine_c = rpyc.classic.connect("machine-c")
sock = machine_c.modules.socket.socket()
sock.connect(("machine-b", 12345))
sock.send(...)
sock.recv(...)
```

**Monkey-patching** — replace local modules with remote ones:
```python
import rpyc, telnetlib
machine_c = rpyc.classic.connect("machine-c")
telnetlib.socket = machine_c.modules.socket  # telnetlib now uses remote socket

# General pattern:
import mymodule
mymodule.os = conn.modules.os
mymodule.open = conn.builtins.open
mymodule.Telnet = conn.modules.telnetlib.Telnet
```
