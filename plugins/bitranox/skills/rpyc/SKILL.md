---
name: rpyc
description: >
  Use when building transparent remote procedure calls, distributed computing,
  or remote object proxying in Python with RPyC. Use when asked about rpyc.connect,
  rpyc.Service, netref proxies, async_(), BgServingThread, SSLAuthenticator,
  DeployedServer, or rpyc_classic.py.
---

# RPyC -- Remote Python Call

RPyC is a transparent, symmetric Python library for remote procedure calls,
clustering, and distributed computing. Object-proxying makes remote objects
behave like local ones.

Use the Read tool to load referenced files identified as relevant for full details.

**Install:** `pip install rpyc`
**Default ports:** Classic `18812`, SSL `18821`, Registry `18811`
**Python:** CPython 3.7+ (no Python 2<->3 crossing)
**Dependencies:** None for core; `plumbum` for zero-deploy; `pywin32` for `PipeStream` on Windows
**Repository:** https://github.com/tomerfiliba-org/rpyc

## When to Use

- Remote testing -- run tests centrally, operations happen on remote machines
- Administration -- control heterogeneous machines from one place using Python
- Remote hardware -- access `ctypes`, `/dev` files, drivers on remote machines transparently
- Parallel execution -- overcome GIL by distributing work across RPyC processes
- Distributed computation -- platform-agnostic foundation for clustering
- Remote services -- implement secure RPC services without heavyweight frameworks
- Monkey-patching -- replace local modules with remote ones to cross network boundaries

## When NOT to Use

- Need a REST/HTTP API (use Flask, FastAPI)
- Need language-agnostic RPC (use gRPC, Thrift)
- Need message queuing (use Celery, RabbitMQ)
- Untrusted clients over the Internet without SSL/SSH wrapping

---

## Which File Do I Need?

**Reference files** (distilled, code-rich summaries):

| I need to...                                                                                    | Read                          |
|-------------------------------------------------------------------------------------------------|-------------------------------|
| Classic mode -- `rpyc.classic.connect()`, `conn.modules`, `conn.teleport()`, tutorials 1/2/4    | `classic-and-tutorials.md`    |
| Services -- `rpyc.Service`, `exposed_`, `ThreadedServer`, `rpyc.discover()`, tutorial 3         | `services-and-servers.md`     |
| Async -- `rpyc.async_()`, `AsyncResult`, `rpyc.timed()`, `BgServingThread`, tutorial 5          | `async-and-events.md`         |
| Security -- `SSLAuthenticator`, `rpyc.ssl_connect()`, `restricted()`, `DeployedServer`          | `security-and-connections.md` |
| API -- `rpyc.connect()`, `Connection`, `Service`, `Netref`, factory functions, `classpartial()` | `api-reference.md`            |
| Demos -- echo, chat, filemon, sharing, async_client, boilerplate patterns                       | `demos-and-patterns.md`       |
| Config -- `protocol_config`, `rpyc_classic.py`, `rpyc_registry.py`, Wireshark debugging         | `config-and-cli.md`           |

Try distilled references (above) first. Use upstream docs below only when more detail is needed.

**Original upstream docs** (for additional detail beyond the reference files):

| Topic                 | Key API / search terms                                                                                                                                                                      | Read                           |
|-----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------|
| Theory of operation   | boxing by-value/by-reference, netref proxying, address space unification, symmetry                                                                                                          | `docs/theory.md`               |
| Classic mode          | `rpyc.classic.connect()`, `conn.modules`, `conn.execute()`, `conn.builtins`, `rpyc_classic.py`                                                                                               | `docs/classic.md`              |
| Services              | `rpyc.Service`, `exposed_` prefix, `@rpyc.exposed`, `@rpyc.service`, `conn.root`, `on_connect()`, `on_disconnect()`, `ALIASES`, `VoidService`                                               | `docs/services.md`             |
| Servers & registry    | `ThreadedServer`, `ForkingServer`, `ClassicService`, `rpyc_classic.py` flags (`-m`, `-p`, `--register`), `rpyc_registry.py`                                                                 | `docs/servers.md`              |
| Async & background    | `rpyc.async_()`, `AsyncResult` (`.ready`, `.value`, `.wait()`, `.set_expiry()`, `.add_callback()`), `rpyc.timed()`, `BgServingThread`                                                       | `docs/async.md`                |
| Security model        | `restricted()`, `allow_public_attrs`, `_rpyc_getattr`, `_rpyc_setattr`, `_rpyc_delattr`, capability-based security                                                                          | `docs/security.md`             |
| SSL/TLS               | `SSLAuthenticator`, `rpyc.ssl_connect()`, `keyfile`, `certfile`, certificate/key setup                                                                                                      | `docs/secure-connection.md`    |
| Zero-deploy (SSH)     | `DeployedServer`, `MultiServerDeployment`, `SshMachine`, `.classic_connect()`, `.classic_connect_all()`, plumbum                                                                            | `docs/zerodeploy.md`           |
| How-to recipes        | `redirected_stdio()`, `rpyc.classic.pm()`, stdio redirection, tunneling over bridges, monkey-patching                                                                                       | `docs/howto.md`                |
| Advanced debugging    | pyenv multi-version testing, Docker testing, Wireshark capture, `rpyc_classic.py --host`                                                                                                    | `docs/advanced-debugging.md`   |
| Tutorial 1: Classic   | `rpyc.classic.connect()`, `conn.modules`, `conn.builtins`, `conn.namespace`, `conn.teleport()`, `conn.eval()`, `conn.execute()`                                                             | `tutorial/tut1.md`             |
| Tutorial 2: Netrefs   | netref, `isinstance()`, exception propagation, `import_custom_exceptions`, `OneShotServer`, `protocol_config=`                                                                              | `tutorial/tut2.md`             |
| Tutorial 3: Services  | `rpyc.Service`, `ThreadedServer`, `OneShotServer`, `rpyc.discover()`, `rpyc.list_services()`, `rpyc.connect_by_service()`, `classpartial`                                                   | `tutorial/tut3.md`             |
| Tutorial 4: Callbacks | callbacks as first-class objects, passing local functions to remote, symmetric protocol                                                                                                     | `tutorial/tut4.md`             |
| Tutorial 5: Async     | `rpyc.async_()`, `AsyncResult` (`.error`), `BgServingThread`, `conn.poll_all()`, `conn.serve`, event producer/consumer                                                                      | `tutorial/tut5.md`             |
| Use cases             | remote testing, administration, hardware access, GIL workaround, distributed computation, clustering                                                                                        | `docs/usecases.md`             |
| Release process       | `hatch build`, `hatch publish`, git tagging, PyPI, semantic versioning, CHANGELOG                                                                                                           | `docs/rpyc-release-process.md` |
| Per-module API        | `core.brine`, `core.protocol`, `core.netref`, `core.service`, `core.stream`, `utils.server`, `utils.registry`, `utils.authenticators`, `utils.factory`, `utils.classic`, `utils.zerodeploy` | `api/*.md` (11 files)          |

---

## Quick Reference

### Connect (Classic Mode)

```python
import rpyc
conn = rpyc.classic.connect("hostname")       # port 18812
conn.modules.os.listdir("/tmp")                # remote module access
conn.builtins.open("/etc/hostname").read()      # remote builtins
```

### Create a Service

```python
import rpyc
from rpyc.utils.server import ThreadedServer

class MyService(rpyc.Service):
    def on_connect(self, conn): pass
    def on_disconnect(self, conn): pass
    def exposed_add(self, a, b):
        return a + b

ThreadedServer(MyService, port=18861).start()
```

### Connect to a Service

```python
conn = rpyc.connect("hostname", 18861)
conn.root.add(3, 4)  # => 7
```

For async, timed calls, BgServingThread examples see `async-and-events.md`.
For SSL, zero-deploy, service discovery examples see `security-and-connections.md` and `services-and-servers.md`.

---

## Common Mistakes

| Mistake                                            | Fix                                                                                  |
|----------------------------------------------------|--------------------------------------------------------------------------------------|
| `rpyc.async_(conn.root.fn)(args)` -- weak-ref lost | Store wrapper: `afn = rpyc.async_(conn.root.fn); afn(args)`                          |
| Expecting async execution order                    | No order guarantee for multiple async requests                                       |
| `allow_all_attrs` on public server                 | Use `allow_exposed_attrs` (default) + capability-based access                        |
| No `BgServingThread` when using callbacks          | Server callbacks won't process unless client serves requests                         |
| Overriding `__init__` on Service class             | Use `on_connect(self, conn)` instead                                                 |
| Passing class instance vs class to ThreadedServer  | `ThreadedServer(MyService)` = per-connection; `ThreadedServer(MyService())` = shared |
| Exposing objects with `sys` references             | Attacker can traverse to `sys.modules`; use `restricted()` wrapper                   |
| Cross-Python-version connections (2<->3)           | Not supported; 3.x<->3.y works if shared types/modules used                          |
| Not closing connections (resource leak)            | Use `with rpyc.connect(...) as conn:` or try/finally with `conn.close()`             |

---

## Key Concepts

**Transparent** (remote objects behave local) | **Symmetric** (both ends serve requests) | **Boxing** (immutables by value, rest by reference as netrefs) | **Capability-based security** (pass specific objects, not broad access)
