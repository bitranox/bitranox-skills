# API Reference

## Serialization: Brine and Vinegar

> Module: `rpyc.core.brine`, `rpyc.core.vinegar`

**Brine** -- simple, fast serialization for immutable data (numbers, strings, tuples, `None`, booleans, frozensets). This is the "over-the-wire" encoding format.

**Vinegar** -- configurable serializer for exceptions. Extracts exception details and stores them in brine-friendly format. Custom exceptions can be registered:
```python
rpyc.core.vinegar._generic_exceptions_cache["urllib.error.URLError"] = urllib.error.URLError
```

---

## IO Layer: Streams and Channel

> Module: `rpyc.core.stream`, `rpyc.core.channel`

**Streams** -- byte-oriented, platform-agnostic stream layer. Implementations:
- `SocketStream` -- TCP socket stream
- `PipeStream` -- pipe-based stream (Windows requires `pywin32`)
- `NamedPipeStream` -- named pipes

**Channel** -- framing and compression layer on top of streams. Adds message framing (length-prefixed) and optional compression.

---

## Protocol: Connection

> Module: `rpyc.core.protocol`

The `Connection` class implements the RPyC protocol. Key aspects:
- Manages request/response multiplexing
- Handles boxing/unboxing of objects
- Dispatches incoming requests to appropriate handlers
- Configurable via `protocol_config` dict

Key methods on connection objects:
- `conn.root` -- access the remote service's root object
- `conn.close()` -- close the connection
- `conn.serve()` -- serve a single incoming request
- `conn.serve_all()` -- serve requests until connection closes
- `conn.poll()` -- serve pending requests (non-blocking)
- `conn.poll_all()` -- serve all pending requests
- `conn.fileno()` -- file descriptor for reactor integration
- `conn.ping()` -- ping the remote end

---

## Service Model

> Module: `rpyc.core.service`

**`rpyc.Service`** -- base class for all services.

Key class-level attributes:
- `ALIASES` -- list of service name aliases
- `exposed_*` -- any attribute/method with this prefix is accessible remotely

Key methods:
- `on_connect(self, conn)` -- called on new connection
- `on_disconnect(self, conn)` -- called after connection closes
- `get_service_name()` -- returns the formal service name
- `get_service_aliases()` -- returns all aliases

**Built-in services:**
- `rpyc.Service` / `rpyc.VoidService` -- base/empty service
- `rpyc.SlaveService` -- classic mode (full remote access)

**Decorators:**
- `@rpyc.service` -- class decorator (alternative to `exposed_` prefix on class)
- `@rpyc.exposed` -- method/attribute decorator (alternative to `exposed_` prefix)

---

## Netref and Async Proxies

> Module: `rpyc.core.netref`, `rpyc.core.async_`

**Netrefs** -- transparent object proxies. All attribute access, method calls, and operations are forwarded to the remote object.

**`AsyncResult`** -- returned by async-wrapped functions:
- `.ready` -- bool, whether result arrived
- `.error` -- bool, whether result is an exception
- `.expired` -- bool, whether timeout elapsed
- `.value` -- the value (blocks if pending; raises if error/expired)
- `.wait()` -- block until ready or expired
- `.add_callback(func)` -- register completion callback
- `.set_expiry(seconds)` -- set timeout

---

## Server Utilities

> Module: `rpyc.utils.server`

**`rpyc.utils.server.Server`** -- base server class.

Constructor parameters:
- `service` -- the service class or instance
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

Key methods: `start()`, `close()`

**Concrete server classes:**
- `ThreadedServer` -- thread per connection
- `ForkingServer` -- fork per connection (POSIX)
- `ThreadPoolServer` -- fixed thread pool
- `OneShotServer` -- serves one connection then exits

---

## Client Factories

> Module: `rpyc.utils.factory`

| Function                                               | Description                                |
|--------------------------------------------------------|--------------------------------------------|
| `rpyc.connect(host, port, ...)`                        | Connect over TCP                           |
| `rpyc.ssl_connect(host, port, keyfile, certfile, ...)` | Connect over SSL                           |
| `rpyc.ssh_connect(remote_machine, remote_port, ...)`   | Connect over SSH tunnel (requires plumbum) |
| `rpyc.connect_by_service(service_name, ...)`           | Discover and connect via registry          |
| `rpyc.connect_subproc(args, ...)`                      | Connect to a subprocess                    |
| `rpyc.connect_pipes(input_pipe, output_pipe, ...)`     | Connect over pipes                         |
| `rpyc.connect_channel(channel, ...)`                   | Connect over existing channel              |
| `rpyc.connect_stream(stream, ...)`                     | Connect over existing stream               |
| `rpyc.discover(service_name)`                          | Query registry for service endpoints       |
| `rpyc.list_services()`                                 | List all registered services               |

Common parameters for connect functions:
- `service` -- client-side service class (default `VoidService`)
- `config` -- protocol configuration dict
- `keepalive` -- enable keepalive

---

## Classic Utilities and Helpers

> Module: `rpyc.utils.classic`, `rpyc.utils.helpers`

**Classic utilities (`rpyc.classic`):**
- `rpyc.classic.connect(host, port=18812)` -- connect in classic mode (both sides expose `SlaveService`)
- `rpyc.classic.connect_subproc()` -- classic connection to subprocess
- `rpyc.classic.connect_channel(channel)` -- classic connection over channel
- `rpyc.classic.connect_stream(stream)` -- classic connection over stream
- `rpyc.classic.redirected_stdio(conn)` -- context manager to redirect server stdio to client
- `rpyc.classic.pm(conn)` -- post-mortem pdb on server's last exception
- `rpyc.classic.teleport_function(conn, func)` -- transfer function to remote

**Helpers (`rpyc.utils.helpers`):**
- `rpyc.async_(proxy)` -- create async wrapper for callable proxy
- `rpyc.timed(proxy, timeout)` -- create timed (timeout) wrapper
- `rpyc.BgServingThread(conn)` -- background thread serving incoming requests
- `rpyc.restricted(obj, attrs, setter_attrs)` -- create restricted view of an object
- `classpartial(cls, *args, **kwargs)` -- partial application for class constructors
- `buffiter(proxy_iterator, chunk_size)` -- buffered iteration over remote iterators

---

## Registry

> Module: `rpyc.utils.registry`

The registry is a bonjour-like discovery agent. Servers register themselves; clients query by service name.

**Registry types:**
- `UDPRegistryServer` -- listens on UDP broadcast socket
- `TCPRegistryServer` -- listens on TCP socket

**Registrar clients (used by servers to register):**
- `UDPRegistryClient`
- `TCPRegistryClient`

---

## Authenticators

> Module: `rpyc.utils.authenticators`

- `SSLAuthenticator(keyfile, certfile, ca_certs=None, ...)` -- SSL/TLS authenticator
- `TlsliteVdbAuthenticator` -- TLSlite-based authenticator (if tlslite available)

Usage:
```python
from rpyc.utils.authenticators import SSLAuthenticator
auth = SSLAuthenticator("server.key", "server.cert")
server = ThreadedServer(MyService, port=12345, authenticator=auth)
```

---

## Zero-Deploy Utilities

> Module: `rpyc.utils.zerodeploy`

- `DeployedServer(remote_machine, ...)` -- deploy single RPyC server via SSH
  - `.classic_connect()` -- create classic connection to deployed server
  - `.connect(service, ...)` -- create service connection
  - `.close(timeout=None)` -- shut down and clean up
  - Can be used as context manager
- `MultiServerDeployment(machines, ...)` -- deploy to multiple machines
  - `.classic_connect_all()` -- connect to all deployed servers
  - `.close()` -- shut down all
