# Configuration and CLI Tools

## Configuration Reference

Protocol configuration is passed as a dict via `protocol_config` (server) or `config` (client connect functions).

**Key configuration parameters (`DEFAULT_CONFIG`):**

| Parameter                             | Default      | Description                                                     |
|---------------------------------------|--------------|-----------------------------------------------------------------|
| `allow_safe_attrs`                    | `True`       | Allow access to "safe" attributes (those in `SAFE_ATTRS`)       |
| `allow_exposed_attrs`                 | `True`       | Allow access to `exposed_` prefixed attributes                  |
| `allow_public_attrs`                  | `False`      | Allow access to public (non-underscore) attributes              |
| `allow_all_attrs`                     | `False`      | Allow access to ALL attributes (including private/special)      |
| `safe_attrs`                          | `set(...)`   | Set of attribute names considered safe                          |
| `exposed_prefix`                      | `"exposed_"` | Prefix for exposed attributes                                   |
| `allow_getattr`                       | `True`       | Allow `getattr` on remote objects                               |
| `allow_setattr`                       | `False`      | Allow `setattr` on remote objects                               |
| `allow_delattr`                       | `False`      | Allow `delattr` on remote objects                               |
| `allow_pickle`                        | `False`      | Allow pickling of remote objects                                |
| `import_custom_exceptions`            | `False`      | Allow importing of custom exception classes                     |
| `instantiate_custom_exceptions`       | `False`      | Allow instantiating custom exception classes                    |
| `instantiate_oldstyle_exceptions`     | `False`      | Allow old-style exception instantiation                         |
| `propagate_SystemExit_locally`        | `False`      | Propagate `SystemExit` locally                                  |
| `propagate_KeyboardInterrupt_locally` | `False`      | Propagate `KeyboardInterrupt` locally                           |
| `logger`                              | `None`       | Logger instance for protocol debugging                          |
| `connid`                              | `None`       | Connection ID string                                            |
| `credentials`                         | `None`       | Credentials dict                                                |
| `endpoints`                           | `None`       | Tuple of `(local_addr, remote_addr)`                            |
| `sync_request_timeout`                | `30`         | Timeout in seconds for synchronous requests (`None` = infinite) |

**Usage examples:**
```python
# Server-side
ThreadedServer(MyService, port=12345, protocol_config={
    'allow_public_attrs': True,
    'allow_setattr': True,
    'sync_request_timeout': None,
})

# Client-side
rpyc.connect("localhost", 12345, config={
    'allow_all_attrs': True,
    'sync_request_timeout': None,
})
```

---

## rpyc_classic.py

Classic-mode server. Installed to Python scripts directory.

```bash
rpyc_classic.py [options]
```

**General switches:**

| Switch               | Description                                  | Default                |
|----------------------|----------------------------------------------|------------------------|
| `-m`, `--mode=MODE`  | Serving mode: `threaded`, `forking`, `stdio` | `threaded`             |
| `-p`, `--port=PORT`  | TCP port                                     | `18812` (SSL: `18821`) |
| `--host=HOSTNAME`    | Bind address                                 | `0.0.0.0`              |
| `--ipv6`             | Bind IPv6 socket                             | IPv4                   |
| `--logfile=FILENAME` | Log file                                     | `stderr`               |
| `-q`, `--quiet`      | Quiet mode (no logging)                      | off                    |

**Registry switches:**

| Switch                    | Description                   | Default                 |
|---------------------------|-------------------------------|-------------------------|
| `--register`              | Register with registry server | off                     |
| `--registry-type=REGTYPE` | `UDP` or `TCP`                | `UDP`                   |
| `--registry-port=REGPORT` | Registry port                 | `18811`                 |
| `--registry-host=REGHOST` | Registry host                 | `255.255.255.255` (UDP) |

**SSL switches (enables SSL authenticator):**

| Switch                    | Description                                   |
|---------------------------|-----------------------------------------------|
| `--ssl-keyfile=FILENAME`  | Server SSL key file (required)                |
| `--ssl-certfile=FILENAME` | Server SSL certificate file (required)        |
| `--ssl-cafile=FILENAME`   | CA chain file (optional; enables client auth) |

**Examples:**
```bash
rpyc_classic.py -m threaded -p 12333
rpyc_classic.py --host 0.0.0.0 --ssl-keyfile=server.key --ssl-certfile=server.cert
rpyc_classic.py -m stdio  # for inetd integration
```

---

## rpyc_registry.py

Service registry server (bonjour-like discovery).

```bash
rpyc_registry.py [options]
```

| Switch                    | Description                                        | Default       |
|---------------------------|----------------------------------------------------|---------------|
| `-m`, `--mode=MODE`       | Registry mode: `UDP` or `TCP`                      | `UDP`         |
| `-p`, `--port=PORT`       | Bind port                                          | `18811`       |
| `-f`, `--file=FILE`       | Log file                                           | `stderr`      |
| `-q`, `--quiet`           | Quiet mode                                         | off           |
| `-t`, `--timeout=SECONDS` | Pruning timeout (time to keep stale registrations) | `240` (4 min) |
| `-l`, `--listing`         | Allow listing all known services                   | `False`       |

**Example:**
```bash
rpyc_registry.py --listing
rpyc_registry.py -m TCP -p 18811 -t 120
```

---

## Advanced Debugging

> Source: `docs/advanced-debugging.md`

**Testing with pyenv:**
```bash
versions=( 3.10 3.11 3.12 3.13 3.14.0rc1 3.15-dev )
for ver in ${versions[@]}; do
    pyenv install --force ${ver}
    pyenv global ${ver}
    pyenv exec pip install --upgrade pip setuptools wheel
    pyenv exec pip install --upgrade --pre plumbum
    site="$(pyenv exec python -c 'import site; print(site.getsitepackages()[0])')"
    printf "${PWD}\n" > "${site}/rpyc.pth"
done

PYENV_VERSION=3.10 pyenv exec python ./bin/rpyc_classic.py --host 127.0.0.1
```

**Testing with Docker:**
```bash
docker-compose -f ./docker/docker-compose.yml create
docker-compose -f ./docker/docker-compose.yml start rpyc-python-3.7
docker exec rpyc-3.8 /opt/rpyc/bin/rpyc_registry.py
docker exec rpyc-3.7 /opt/rpyc/bin/rpyc_classic.py --host 0.0.0.0 &
docker exec -it rpyc-3.10 python -c "import rpyc;conn = rpyc.utils.classic.connect('rpyc-3.7'); conn.modules.sys.stderr.write('hello world\n')"
```

**Unit tests:**
```bash
python -m unittest discover -v -k test_affinity
python -m unittest discover
```

**Wireshark display filters:**
```
tcp.port == 18878 || tcp.port == 18879
(tcp.port == 18878 || tcp.port == 18879) && tcp.segment_data contains "rpyc.core.service.SlaveService"
```

---

## Source File Index

### Root Files

| File          | Description                                                                |
|---------------|----------------------------------------------------------------------------|
| `index.md`    | Main project page: features, use cases, getting started                    |
| `install.md`  | Installation instructions, platform compatibility, cross-interpreter notes |
| `api.md`      | API reference index (links to all api/ docs)                               |
| `docs.md`     | Documentation index (links to all docs/ pages)                             |
| `tutorial.md` | Tutorial index (links to 5 tutorial parts)                                 |

### Documentation (`docs/`)

| File                           | Description                                                                    |
|--------------------------------|--------------------------------------------------------------------------------|
| `docs/about.md`                | Project history, contributors, logo                                            |
| `docs/theory.md`               | Theory of operation: transparency, symmetry, boxing, proxying, services        |
| `docs/usecases.md`             | Use cases: remote services, admin, hardware, parallel, distributed, testing    |
| `docs/howto.md`                | How-to recipes: stdio redirect, pdb debugging, tunneling, monkey-patching      |
| `docs/servers.md`              | Server types, classic server CLI, custom servers, registry server CLI          |
| `docs/classic.md`              | Classic mode usage (SlaveService)                                              |
| `docs/services.md`             | Service definition, exposed members, decorators, callbacks, decoupled services |
| `docs/async.md`                | async_(), timed(), BgServingThread                                             |
| `docs/security.md`             | Security model, wrapping, attribute access protocol, configuration parameters  |
| `docs/secure-connection.md`    | SSL/TLS setup (server and client)                                              |
| `docs/zerodeploy.md`           | Zero-deploy via SSH: DeployedServer, MultiServerDeployment                     |
| `docs/advanced-debugging.md`   | pyenv testing, Docker testing, Wireshark debugging                             |
| `docs/rpyc-release-process.md` | Release process: versioning, changelog generation, hatch build/publish         |

### Tutorials (`tutorial/`)

| File               | Description                                                                                   |
|--------------------|-----------------------------------------------------------------------------------------------|
| `tutorial/tut1.md` | Part 1: Classic RPyC -- modules, builtins, eval, execute, teleport                            |
| `tutorial/tut2.md` | Part 2: Netrefs and exceptions -- proxy objects, dual tracebacks, custom exceptions           |
| `tutorial/tut3.md` | Part 3: Services -- exposed methods, access policy, shared instances, classpartial, discovery |
| `tutorial/tut4.md` | Part 4: Callbacks and symmetry -- passing functions across connections                        |
| `tutorial/tut5.md` | Part 5: Async and events -- async_(), AsyncResult, BgServingThread, event pattern             |

### API Reference (`api/`)

| File                          | Description                                                               |
|-------------------------------|---------------------------------------------------------------------------|
| `api/core_brine.md`           | Brine serialization and Vinegar exception serialization                   |
| `api/core_stream.md`          | Stream (byte transport) and Channel (framing/compression) layers          |
| `api/core_protocol.md`        | Connection/Protocol class                                                 |
| `api/core_service.md`         | Service base class                                                        |
| `api/core_netref.md`          | Netref (proxy) and Async (AsyncResult) classes                            |
| `api/utils_server.md`         | Server classes (Threaded, Forking, ThreadPool, OneShot)                   |
| `api/utils_registry.md`       | Registry server and client classes                                        |
| `api/utils_authenticators.md` | SSL and TLSlite authenticators                                            |
| `api/utils_factory.md`        | Connection factory functions (connect, ssl_connect, ssh_connect, etc.)    |
| `api/utils_classic.md`        | Classic mode utilities and helpers (async_, timed, BgServingThread, etc.) |
| `api/utils_zerodeploy.md`     | DeployedServer and MultiServerDeployment                                  |

### Demos (`demos/`)

| Directory             | Description                                  | Key Pattern                                                                |
|-----------------------|----------------------------------------------|----------------------------------------------------------------------------|
| `demos/echo/`         | Simple one-shot echo server/client           | `OneShotServer`, basic service                                             |
| `demos/boilerplate/`  | Generic service with file monitor events     | Async callbacks, `BgServingThread`, client lifecycle                       |
| `demos/time/`         | Time service with registry discovery         | `auto_register=True`, `connect_by_service()`                               |
| `demos/sharing/`      | Thread-safe shared state between connections | Class-level shared objects, `threading.Lock`, synchronize decorator        |
| `demos/async_client/` | Blocking server function with async handling | `async_()` proxy, `BgServingThread`, event coordination                    |
| `demos/chat/`         | Multi-user chat with user tokens             | Capability tokens, async broadcast, GTK reactor                            |
| `demos/filemon/`      | File change monitor with events              | Server-side thread, `os.stat`, async callback notification                 |
| `demos/web8/`         | Remote GUI construction via RPyC             | Server builds client UI widgets, SafeGTK capability, bidirectional proxies |
