# Security, SSL/SSH, and Zero-Deploy

## Security Model

> Source: `docs/security.md`

RPyC 3+ uses a **capability-based security model**. Default configuration is restrictive (only `exposed_` attributes accessible). Key principles:

- **Don't expose RPyC openly over the Internet** -- use on secure local networks or over secure connections
- Exposing objects that reference `sys` can allow traversal to `sys.modules` and all imports
- Default configs mitigate access to dangerous objects, but enabling `allow_public_attrs` or overriding `_rpyc_getattr` can expose vulnerabilities

**CVE-2019-16328** -- affected versions 4.1.0 and 4.1.1; fixed in 4.1.2.

### Wrapping -- Restrict Exposed Attributes

```python
from rpyc.utils.helpers import restricted

class MyService(rpyc.Service):
    def exposed_open(self, filename):
        f = open(filename, "r")
        return restricted(f, ["read", "close"], [])  # only allow read and close
```

### RPyC Attribute Protocol -- Fine-Grained Access Control

```python
class MyObject(object):
    def __init__(self):
        self._secret = 18

    def _rpyc_getattr(self, name):
        if name.startswith("__"):
            raise AttributeError("cannot access private/special names")
        return getattr(self, name)

    # Also: _rpyc_setattr(self, name, value), _rpyc_delattr(self, name)
```

**Classic mode (`SlaveService`) is intentionally insecure** -- only use on secure local networks.

---

## SSL/TLS Connections

> Source: `docs/secure-connection.md`

**SSL server:**
```python
from rpyc.utils.authenticators import SSLAuthenticator
from rpyc.utils.server import ThreadedServer

authenticator = SSLAuthenticator("myserver.key", "myserver.cert")
server = ThreadedServer(SlaveService, port=12345, authenticator=authenticator)
server.start()
```

**SSL client:**
```python
conn = rpyc.ssl_connect("hostname", port=12345,
                         keyfile="client.key", certfile="client.cert")
```

### Authenticators

- `SSLAuthenticator(keyfile, certfile, ca_certs=None, ...)` -- SSL/TLS authenticator
- `TlsliteVdbAuthenticator` -- TLSlite-based authenticator (if tlslite available)

---

## Zero-Deploy

> Source: `docs/zerodeploy.md`

Deploy RPyC servers on remote machines that don't have RPyC installed. Requirements: `plumbum` on client, SSH access + Python on remote.

**How it works:**
1. Creates temp directory on remote machine
2. Copies RPyC distribution to temp dir
3. Starts server in temp dir (binds to localhost on arbitrary port)
4. Sets up SSH tunnel from local port to remote port
5. Client connects to `localhost:local_port` (forwarded by SSH)
6. On close: removes temp directory, shuts down server -- no trace left

### Usage

```python
from rpyc.utils.zerodeploy import DeployedServer
from plumbum import SshMachine

mach = SshMachine("somehost", user="someuser", keyfile="/path/to/keyfile")
server = DeployedServer(mach)

conn1 = server.classic_connect()
print(conn1.modules.sys.platform)

conn2 = server.classic_connect()
print(conn2.modules.os.getpid())

server.close()
```

### Context Manager

```python
with DeployedServer(mach) as server:
    conn = server.classic_connect()
    # ...
```

### Multi-Server Deployment

```python
from rpyc.utils.zerodeploy import MultiServerDeployment

m1, m2, m3 = SshMachine("host1"), SshMachine("host2"), SshMachine("host3")
dep = MultiServerDeployment([m1, m2, m3])
conn1, conn2, conn3 = dep.classic_connect_all()
# ...
dep.close()
```

**Timeout:** `server.close(timeout=30)` -- raises `TimeoutExpired` if cleanup exceeds timeout.
