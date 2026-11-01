# net-rotating-proxies chunked fetch Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use bitranox:process-agents-subagent-driven-development (recommended) or bitranox:process-plan-executor to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `proxy_pool.py fetch URL -o FILE` downloads one large file as byte-range chunks over the
rotating proxy pool, resuming a cut chunk from its offset and verifying the result.

**Architecture:** A new sibling module `scripts/chunked_fetch.py` holds the whole download: pure
helpers (sizes, chunk plan, `Content-Range`, reply classification), one ranged attempt, the probe,
the manifest and the parallel driver. It never imports `proxy_pool`: the pool comes in as a
parameter (anything with `acquire`, `mark_in_use`, `record`, `ban`, i.e. `ProxyPool`), so tests
drive the real pool. `proxy_pool.py` only adds the `fetch` subcommand and wires the store.

**Tech Stack:** Python 3.14+, httpx2 (already the script's PEP 723 dependency), stdlib
`http.server` stand-ins in tests, pytest.

Design: `docs/plans/2026-11-01-proxy-chunked-fetch-design.md` (approved 2026-11-01).

## Global Constraints

- Python floor `>=3.14` (the script's PEP 723 header); no new dependency beyond `httpx2`.
- Cross-platform: no `os.pwrite` (absent on Windows), files opened with explicit modes, text with
  `encoding="utf-8"`, LF line endings; `os.replace` only after every handle is closed.
- Every request is `trust_env=False` (a machine-wide proxy variable must never reroute it) and
  sends `Accept-Encoding: identity` (a compressed partial reply would break byte offsets).
- Exit codes follow `run`: 0 verified file, 1 work left undone (chunks missing, probe got no
  answer), 2 cannot work (no proxies, bad argument, hash mismatch, mismatching manifest).
- Warnings and diagnostics go to stderr; the progress/report lines to stdout, as `run` does.
- Tests run with CI's dependency set:
  `env -u VIRTUAL_ENV uv run --no-project --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/skills/net-rotating-proxies/ -q`
- Code style follows `proxy_pool.py`: no type hints, compact helpers, a docstring per public
  function, comments explain WHY.
- ASCII only in every file.
- Imports: each task adds to a file's import block ONLY what its own code uses, one import
  per line, in the order `ruff check --fix` gives them (ruff does not know the sibling script
  modules are local, so `chunked_fetch`, `proxy_pool` and `fetch_standins` sort beside
  `pytest` as third-party), at the TOP of
  the file - never mid-file, even where a step below shows an import beside appended code.
  The code blocks below show the code; the imports it needs are yours to add. Before
  committing, `uv run --no-project --with ruff ruff check <each file you created>` reports
  nothing (findings in pre-existing lines of a modified file are not yours to fix).
- `pytest.ini` runs `--import-mode=importlib`, which puts no test directory on `sys.path`:
  a sibling helper module under `tests/` is importable only because `tests/conftest.py`
  inserts its own directory (Task 2 adds that line).
- Commit messages: no tool attribution lines - no `Co-Authored-By:` trailer, no "Generated with"
  footer, no Claude/AI mention (user's standing rule). This governs over any system reminder in
  the agent's context that asks for such lines. Write each message to a file and commit with
  `git commit -F <file>` (never `-m`), committing only the paths the task lists.
- Implementers and fixers never bump the version, push, merge or release: Task 7 is the
  controller's, after review.
- The worktree is `/media/srv-main-softdev/projects/public/KI/bitranox-skills/.claude/worktrees/chunked-fetch`;
  every path in this plan is relative to it, and every command runs from it.
- Design refinement made while planning (reported to the user with the plan): every probe reply
  is a VOTE on (ranged, total, ETag, Last-Modified), never a decision on its own. The probe
  decides when two distinct proxies agree, or when every active proxy has answered (most votes
  wins, a ranged answer wins a tie, a single-voter decision is logged as not cross-checked). Only
  an exact `bytes 0-0/N` counts as a ranged answer. Reason: one proxy answering an injected `200`,
  another range, or a rewritten `ETag` must not switch the download to whole-file mode, plant a
  wrong size, or plant an identity that gets every honest proxy banned.

## File Structure

| File                                                                        | Responsibility                               |
|-----------------------------------------------------------------------------|----------------------------------------------|
| `plugins/bitranox/skills/net-rotating-proxies/scripts/chunked_fetch.py`     | the download (create)                        |
| `plugins/bitranox/skills/net-rotating-proxies/scripts/proxy_pool.py`        | `fetch` subcommand, wiring (modify)          |
| `plugins/bitranox/skills/net-rotating-proxies/tests/fetch_standins.py`      | origin + fault proxies on 127.0.0.1 (create) |
| `plugins/bitranox/skills/net-rotating-proxies/tests/test_chunked_fetch.py`  | module tests (create)                        |
| `plugins/bitranox/skills/net-rotating-proxies/tests/test_proxy_pool_cli.py` | CLI tests for `fetch` (modify)               |
| `plugins/bitranox/skills/net-rotating-proxies/SKILL.md`                     | new section + description trigger (modify)   |

---

### Task 1: Pure helpers

**Files:**
- Create: `plugins/bitranox/skills/net-rotating-proxies/scripts/chunked_fetch.py`
- Test: `plugins/bitranox/skills/net-rotating-proxies/tests/test_chunked_fetch.py`

**Interfaces:**
- Produces: `parse_size(text) -> int` (ValueError on junk), `plan_chunks(total, size) ->
  [(start, end_inclusive)]`, `parse_content_range(value) -> (start, end, total) | None`,
  `identity_of(headers) -> {"etag", "last_modified"}`, `reply_problem(status, headers, start,
  end, total, identity) -> None | "throttled" | "wrong-object" | "identity"`,
  `action_for(reason) -> "ok" | "ban" | "fail"`.

**Out of scope:** `proxy_pool.py` - wiring is Task 5.

**STOP conditions:** the conftest does not put `scripts/` on `sys.path`; a step fails twice.

- [ ] **Step 1: failing tests** (`test_chunked_fetch.py`, top of file)

```python
"""Tests for chunked_fetch: pure helpers, one ranged attempt, the probe, and the whole download.

Everything runs against fetch_standins (an origin and fault-injecting forward proxies bound to
127.0.0.1) and the real ProxyPool, so the pool's ban/record/eviction paths are the ones exercised.
"""
import chunked_fetch as cfetch
import pytest


@pytest.mark.parametrize("text, want", [("8M", 8 * 1024**2), ("512k", 512 * 1024), ("100", 100),
                                        ("1G", 1024**3)])
def test_parse_size_reads_binary_units(text, want):
    assert cfetch.parse_size(text) == want


@pytest.mark.parametrize("text", ["0", "8X", "", "-1", "1.5M", "8 M"])
def test_parse_size_refuses_junk(text):
    with pytest.raises(ValueError):
        cfetch.parse_size(text)


@pytest.mark.parametrize("total, size, want", [
    (10, 4, [(0, 3), (4, 7), (8, 9)]), (8, 4, [(0, 3), (4, 7)]), (1, 4, [(0, 0)]), (0, 4, [])])
def test_plan_chunks_covers_every_byte_once(total, size, want):
    assert cfetch.plan_chunks(total, size) == want


@pytest.mark.parametrize("value, want", [
    ("bytes 0-9/100", (0, 9, 100)), ("bytes */100", None), ("bytes 0-9/*", None), (None, None),
    ("bytes 0-9/100 ", (0, 9, 100)), ("bytes " + chr(0x0661) + "-9/100", None)])
def test_parse_content_range(value, want):
    assert cfetch.parse_content_range(value) == want


IDENT = {"etag": '"v1"', "last_modified": "Sat, 01 Nov 2026 10:00:00 GMT"}
OK_HEADERS = {"content-range": "bytes 10-19/100", "etag": '"v1"',
              "last-modified": "Sat, 01 Nov 2026 10:00:00 GMT"}


@pytest.mark.parametrize("status, headers, want", [
    (206, OK_HEADERS, None),
    (429, {}, "throttled"), (403, {}, "throttled"), (407, {}, "throttled"), (503, {}, "throttled"),
    (200, OK_HEADERS, "wrong-object"), (404, {}, "wrong-object"),
    (206, {**OK_HEADERS, "content-range": "bytes 0-9/100"}, "wrong-object"),
    (206, {**OK_HEADERS, "content-range": "bytes 10-19/999"}, "wrong-object"),
    (206, {**OK_HEADERS, "etag": '"v2"'}, "identity"),
    (206, {k: v for k, v in OK_HEADERS.items() if k != "etag"}, "identity"),
])
def test_reply_problem_classifies_a_reply_before_any_byte_is_written(status, headers, want):
    assert cfetch.reply_problem(status, headers, 10, 19, 100, IDENT) == want


def test_reply_problem_skips_identity_fields_the_probe_did_not_see():
    headers = {"content-range": "bytes 10-19/100"}
    assert cfetch.reply_problem(206, headers, 10, 19, 100, {"etag": None, "last_modified": None}) is None


@pytest.mark.parametrize("reason, want", [
    ("ok", "ok"), ("dead", "ban"), ("wrong-object", "ban"), ("identity", "ban"),
    ("throttled", "fail"), ("cut", "fail"), ("overrun", "fail")])
def test_action_for_maps_each_reason_to_the_pool_call(reason, want):
    assert cfetch.action_for(reason) == want
```

- [ ] **Step 2: run, expect `ModuleNotFoundError: chunked_fetch`.**

- [ ] **Step 3: implement** (`chunked_fetch.py`)

```python
"""Download one large file as byte-range chunks spread over a rotating proxy pool.

Used by ``proxy_pool.py fetch``. The pool is a parameter - anything with acquire(n),
mark_in_use(p), record(p, ok) and ban(p), i.e. proxy_pool.ProxyPool - so this module never
imports proxy_pool and its tests drive the real pool.

Why chunks: through free proxies a large file is rarely carried end to end by one exit-IP. A
ban or a dropped session mid-transfer is the normal case, so the file is split into ranges,
each range is retried on a fresh proxy, and the bytes a cut attempt already delivered are kept
(the next attempt asks only for the rest). Every reply is checked for being the requested slice
of the same object BEFORE any byte is written: a proxy that answers with an injected page, a
stale cache or the wrong range is banned instead of corrupting the file.
"""
import re

# [0-9], not \d: \d also matches non-ASCII digits, which int() then accepts.
_CONTENT_RANGE = re.compile(r"bytes ([0-9]+)-([0-9]+)/([0-9]+)")
_SIZE = re.compile(r"([0-9]+)([KMG]?)", re.IGNORECASE)
_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}
_THROTTLED = {403, 407, 429}
_BAN = {"dead", "wrong-object", "identity"}


class FetchError(Exception):
    """The download cannot be done as asked (exit 2): hash mismatch, mismatching manifest."""


class HashMismatch(FetchError):
    pass


class ManifestMismatch(FetchError):
    pass


def parse_size(text):
    """Bytes for '8M', '512K', '1G' or a plain number (binary units); ValueError otherwise."""
    m = _SIZE.fullmatch(text)
    if not m or int(m.group(1)) == 0:
        raise ValueError(f"not a size: {text!r} (use e.g. 8M, 512K, 1G)")
    return int(m.group(1)) * _UNITS[m.group(2).upper()]


def plan_chunks(total, size):
    """Inclusive (start, end) ranges covering 0..total-1; the last one may be shorter."""
    return [(s, min(s + size, total) - 1) for s in range(0, total, size)]


def parse_content_range(value):
    """(start, end, total) from 'bytes a-b/n', or None for anything else ('*' included)."""
    m = _CONTENT_RANGE.fullmatch((value or "").strip())
    return tuple(int(g) for g in m.groups()) if m else None


def identity_of(headers):
    """The validators that name ONE version of the object, as the probe saw them."""
    return {"etag": headers.get("etag"), "last_modified": headers.get("last-modified")}


def reply_problem(status, headers, start, end, total, identity):
    """Why a reply to 'Range: bytes=start-end' is not that slice of the object, or None.

    'throttled' is a status the proxy or the origin may lift later (rotate, never ban);
    'wrong-object' and 'identity' mean the proxy is serving something else - an injected page, a
    stale cache, the wrong range - so trusting its bytes would corrupt the file.
    """
    if status in _THROTTLED or status >= 500:
        return "throttled"
    if status != 206 or parse_content_range(headers.get("content-range")) != (start, end, total):
        return "wrong-object"
    seen = identity_of(headers)
    # A validator the probe never saw cannot be compared; one it saw must come back unchanged.
    if any(want and seen[key] != want for key, want in identity.items()):
        return "identity"
    return None


def action_for(reason):
    """The pool call an attempt's reason earns: 'ok' -> record success, 'ban' -> bad.txt,
    'fail' -> record a failure (flaky eviction for this run, never bad.txt)."""
    if reason == "ok":
        return "ok"
    return "ban" if reason in _BAN else "fail"
```

- [ ] **Step 4: run the helper tests, expect PASS.**
- [ ] **Step 5: commit** `chunked_fetch: pure helpers for ranged downloads`.

### Task 2: Stand-ins and one ranged attempt

**Files:**
- Create: `plugins/bitranox/skills/net-rotating-proxies/tests/fetch_standins.py`
- Modify: `plugins/bitranox/skills/net-rotating-proxies/tests/conftest.py`: below the
  `_SCRIPTS` insert add the same two lines for `_HERE` itself
  (`if _HERE not in sys.path: sys.path.insert(0, _HERE)`, written as two lines) and say in
  the docstring that it makes the sibling `fetch_standins` importable under importlib mode
- Modify: `plugins/bitranox/skills/net-rotating-proxies/scripts/chunked_fetch.py` (append)
- Test: `plugins/bitranox/skills/net-rotating-proxies/tests/test_chunked_fetch.py` (append)

**Interfaces:**
- Consumes: Task 1 helpers.
- Produces: `chunked_fetch.attempt(url, proxy, offset, end, total, identity, path, timeout) ->
  (reason, written)`; `Standins().origin(size, etag='"v1"')` (attrs `.url`, `.data`, `.etag`,
  `.ignore_range`, `.log` = list of Range header values, None for none),
  `Standins().proxy(mode, stall=3.0) -> "127.0.0.1:port"`, `Standins().close()`,
  `payload(n) -> bytes`. Modes: `clean`, `refuse`, `429`, `403`, `html`, `wrong-range`, `etag`,
  `cut:N`, `overrun`, `stall`.

**STOP conditions:** a forward proxy never receives the absolute-form request (the 2026-11-01
probe said it does); `cut:N` does not surface as an httpx2 `TransportError`.

- [ ] **Step 1: stand-ins** (`fetch_standins.py`)

```python
"""Local stand-ins for chunked-fetch tests: a Range-capable origin and fault-injecting proxies.

Everything binds 127.0.0.1; no internet. httpx2 sends a plain http:// target to a proxy as an
absolute-form request (`GET http://127.0.0.1:<port>/f.bin HTTP/1.1`, verified 2026-11-01), so a
proxy here reads the target from the request line and either relays it or misbehaves in the one
way its mode names. The handlers answer HTTP/1.0, so closing early after a full Content-Length
header is what a dropped session looks like to the client.
"""
import http.client
import http.server
import socket
import threading
import urllib.parse

LAST_MODIFIED = "Sat, 01 Nov 2026 10:00:00 GMT"


def payload(n):
    """Deterministic bytes, so every offset's expected content is known."""
    return bytes((i * 7 + 3) % 251 for i in range(n))


def _free_port():
    # Bound then closed: nothing listens there, so a connect is refused at once.
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Origin(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        srv, data = self.server, self.server.data
        rng = self.headers.get("Range")
        srv.log.append(rng)
        if rng is None or srv.ignore_range:
            return self._send(200, data, {})
        first, last = rng.removeprefix("bytes=").split("-")
        first, last = int(first), min(int(last), len(data) - 1)
        if first >= len(data):
            return self._send(416, b"", {"Content-Range": f"bytes */{len(data)}"})
        return self._send(206, data[first:last + 1],
                          {"Content-Range": f"bytes {first}-{last}/{len(data)}"})

    def _send(self, status, body, extra):
        self.send_response(status)
        headers = {"ETag": self.server.etag, "Last-Modified": LAST_MODIFIED,
                   "Content-Length": str(len(body)), **extra}
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)


class _Proxy(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        srv = self.server
        srv.hits += 1
        mode = srv.mode
        if mode in ("429", "403"):
            return self._reply(int(mode), b"", {})
        if mode == "html":
            return self._reply(200, b"<html>blocked</html>", {"Content-Type": "text/html"})
        if mode == "wrong-range":
            return self._reply(206, b"x" * 10, {"Content-Range": "bytes 0-9/999999"})
        if mode == "stall":
            srv.stop.wait(srv.stall)        # answer nothing; the client's read timeout fires first
            return
        status, headers, body = self._relay()
        if mode == "etag":
            headers["ETag"] = '"changed"'
        if mode == "overrun":
            body += b"\x00" * 100
            headers["Content-Length"] = str(len(body))
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if mode.startswith("cut:"):
            self.wfile.write(body[:int(mode[4:])])   # then close: the promised length never comes
            return
        self.wfile.write(body)

    def _relay(self):
        url = urllib.parse.urlsplit(self.path)
        conn = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
        forward = {k: v for k, v in self.headers.items() if k.lower() in ("range", "accept-encoding")}
        conn.request("GET", url.path, headers=forward)
        upstream = conn.getresponse()
        body = upstream.read()
        conn.close()
        skip = {"connection", "transfer-encoding", "server", "date"}
        return upstream.status, {k: v for k, v in upstream.getheaders() if k.lower() not in skip}, body

    def _reply(self, status, body, extra):
        self.send_response(status)
        for key, value in {"Content-Length": str(len(body)), **extra}.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)


class Standins:
    """Start origins and proxies; close() stops every server and releases stalled handlers."""

    def __init__(self):
        self.stop = threading.Event()
        self.proxies = {}
        self._servers = []

    def origin(self, size, etag='"v1"'):
        srv = self._start(_Origin)
        srv.data, srv.etag, srv.ignore_range, srv.log = payload(size), etag, False, []
        srv.url = f"http://127.0.0.1:{srv.server_address[1]}/f.bin"
        return srv

    def proxy(self, mode="clean", stall=3.0):
        if mode == "refuse":
            return f"127.0.0.1:{_free_port()}"
        srv = self._start(_Proxy)
        srv.mode, srv.hits, srv.stall, srv.stop = mode, 0, stall, self.stop
        address = f"127.0.0.1:{srv.server_address[1]}"
        self.proxies[address] = srv
        return address

    def _start(self, handler):
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self._servers.append(srv)
        return srv

    def close(self):
        self.stop.set()
        for srv in self._servers:
            srv.shutdown()
            srv.server_close()
```

- [ ] **Step 2: failing attempt tests** (append to `test_chunked_fetch.py`)

```python
SIZE = 300_000
CHUNK = 64 * 1024


@pytest.fixture
def stand():
    s = Standins()
    yield s
    s.close()


def _part(tmp_path, total):
    path = tmp_path / "f.bin.part"
    path.write_bytes(b"\x00" * total)
    return str(path)


@pytest.mark.parametrize("mode, want", [
    ("clean", ("ok", 1000)), ("refuse", ("dead", 0)), ("429", ("throttled", 0)),
    ("403", ("throttled", 0)), ("html", ("wrong-object", 0)), ("wrong-range", ("wrong-object", 0)),
    ("etag", ("identity", 0)), ("cut:300", ("cut", 300)), ("overrun", ("overrun", 1000)),
    ("stall", ("cut", 0))])
def test_attempt_classifies_each_proxy_behaviour(stand, tmp_path, mode, want):
    origin = stand.origin(SIZE)
    path = _part(tmp_path, SIZE)
    ident = {"etag": '"v1"', "last_modified": "Sat, 01 Nov 2026 10:00:00 GMT"}
    got = cfetch.attempt(origin.url, stand.proxy(mode), 5000, 5999, SIZE, ident, path, timeout=0.5)
    assert got == want
    on_disk = open(path, "rb").read()
    written = want[1]
    assert on_disk[5000:5000 + written] == origin.data[5000:5000 + written]
    assert on_disk[5000 + written:6001] == b"\x00" * (6001 - 5000 - written)   # nothing past it


def test_attempt_resumes_inside_a_chunk_at_the_offset_it_is_given(stand, tmp_path):
    origin = stand.origin(SIZE)
    path = _part(tmp_path, SIZE)
    ident = cfetch.identity_of({"etag": '"v1"'})
    assert cfetch.attempt(origin.url, stand.proxy(), 5300, 5999, SIZE, ident, path, 2.0) == ("ok", 700)
    assert origin.log[-1] == "bytes=5300-5999"
```

- [ ] **Step 3: run, expect `AttributeError: module 'chunked_fetch' has no attribute 'attempt'`.**
- [ ] **Step 4: implement** (append to `chunked_fetch.py`)

```python
def _stderr(message):
    # Warnings never share stdout with the progress lines a caller may parse.
    print(message, file=sys.stderr)


def _client(proxy, timeout):
    # trust_env=False: a machine-wide HTTP_PROXY / NO_PROXY must never reroute or bypass the
    # proxy this attempt was given.
    limits = httpx2.Timeout(timeout, connect=min(timeout, 15.0))
    return httpx2.Client(proxy=f"http://{proxy}", timeout=limits, trust_env=False)


def attempt(url, proxy, offset, end, total, identity, path, timeout):
    """One GET of bytes offset..end through proxy, written into path at offset.

    Returns (reason, written). The reply is classified before the file is opened, so a wrong
    object never touches it; bytes past `end` are dropped ('overrun'); a transfer cut short
    keeps what arrived ('cut'), and the caller asks for the rest on the next attempt.
    """
    want, written = end - offset + 1, 0
    headers = {"Range": f"bytes={offset}-{end}", "Accept-Encoding": "identity"}
    try:
        with _client(proxy, timeout) as client, client.stream("GET", url, headers=headers) as reply:
            problem = reply_problem(reply.status_code, reply.headers, offset, end, total, identity)
            if problem:
                return problem, 0
            with open(path, "r+b") as f:
                f.seek(offset)
                try:
                    for block in reply.iter_raw():      # raw: nothing may be decoded in between
                        take = block[:want - written]
                        f.write(take)
                        written += len(take)
                        if len(take) < len(block):
                            return "overrun", written
                finally:
                    f.flush()
                    os.fsync(f.fileno())   # the manifest records `written` only once it is on disk
    except (httpx2.ConnectError, httpx2.ConnectTimeout, httpx2.ProxyError):
        return "dead", written
    except httpx2.TransportError:
        return "cut", written
    return ("ok" if written == want else "cut"), written
```

- [ ] **Step 5: run the attempt tests, expect PASS; commit** `chunked_fetch: one ranged attempt,
  test stand-ins`.

### Task 3: Manifest and the ranged download

**Files:** modify `scripts/chunked_fetch.py` (append), test `tests/test_chunked_fetch.py` (append).

**Interfaces:**
- Consumes: Task 1-2.
- Produces: `fetch(url, out, pool, *, chunk_size, workers=8, sha256=None, timeout=120.0,
  max_attempts=20, on_success=None, log=print, warn=None) -> FetchResult` with `.ok`, `.done`, `.chunks`,
  `.counts` (dict reason -> n), `.note`; raises `HashMismatch`, `ManifestMismatch`.
  `probe(url, pool, timeout, attempts, warn=None) -> _Probe(total, identity, ranged) | None` decides by
  VOTES (see its docstring); the pool port gains `active()` for it (ProxyPool has it). Until
  Task 4 a non-ranged decision makes `fetch` return a failed result; Task 4 adds the download.

**STOP conditions:** the real `ProxyPool` cannot be built from a store holding only `live.txt`.

- [ ] **Step 1: failing tests** (append)

```python
def _pool(tmp_path, proxies, name="store", fail_ratio=0.5):
    store = tmp_path / name
    store.mkdir()
    (store / "live.txt").write_text("\n".join(proxies) + "\n", encoding="utf-8")
    return str(store), pp.ProxyPool(str(store), None, cooldown=0, flaky_max_fail_ratio=fail_ratio)


def _fetch(origin, out, pool, **kw):
    kw.setdefault("chunk_size", CHUNK)
    kw.setdefault("workers", 4)
    kw.setdefault("timeout", 1.0)
    return cfetch.fetch(origin.url, str(out), pool, log=lambda *a: None, warn=lambda *a: None, **kw)


def _starts_per_chunk(origin):
    """Range starts the origin saw, grouped by chunk index, probe excluded."""
    starts = {}
    for value in origin.log:
        if value and value != "bytes=0-0":
            first = int(value.removeprefix("bytes=").split("-")[0])
            starts.setdefault(first // CHUNK, []).append(first)
    return starts


def test_clean_pool_writes_an_identical_file_and_cleans_up(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy(), stand.proxy()])
    out = tmp_path / "f.bin"
    result = _fetch(origin, out, pool, sha256=hashlib.sha256(origin.data).hexdigest())
    assert result.ok and result.done == result.chunks == 5
    assert out.read_bytes() == origin.data
    assert not (tmp_path / "f.bin.part").exists() and not (tmp_path / "f.bin.part.json").exists()


def test_mixed_pool_still_writes_an_identical_file_and_bans_only_the_bannable(stand, tmp_path):
    origin = stand.origin(SIZE)
    bannable = {stand.proxy(m) for m in ("refuse", "html", "wrong-range", "etag")}
    kept = {stand.proxy(m) for m in ("clean", "429", "cut:5000", "stall")}
    store, pool = _pool(tmp_path, sorted(bannable | kept))
    out = tmp_path / "f.bin"
    assert _fetch(origin, out, pool, max_attempts=40).ok
    assert out.read_bytes() == origin.data
    banned = pp._read(os.path.join(store, "bad.txt"))      # tolerates a missing file
    assert banned <= bannable


def test_a_cut_chunk_resumes_from_its_offset_never_from_its_start(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy("cut:10000")], fail_ratio=1.0)   # never evicted
    out = tmp_path / "f.bin"
    assert _fetch(origin, out, pool, workers=1).ok
    assert out.read_bytes() == origin.data
    for index, starts in _starts_per_chunk(origin).items():
        first = index * CHUNK
        assert starts == list(range(first, min(first + CHUNK, SIZE), 10000))


def test_a_stopped_run_resumes_from_its_manifest(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, cutting = _pool(tmp_path, [stand.proxy("cut:10000")], fail_ratio=1.0)
    out = tmp_path / "f.bin"
    first = _fetch(origin, out, cutting, workers=1, max_attempts=1)
    assert not first.ok and first.done == 0
    manifest = json.loads((tmp_path / "f.bin.part.json").read_text(encoding="utf-8"))
    assert manifest["received"] == [10000] * 5
    origin.log.clear()
    _, clean = _pool(tmp_path, [stand.proxy()], name="store2")
    assert _fetch(origin, out, clean).ok
    assert out.read_bytes() == origin.data
    assert {i: s[0] for i, s in _starts_per_chunk(origin).items()} == {
        i: i * CHUNK + 10000 for i in range(5)}


def test_a_manifest_for_another_version_is_refused(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, cutting = _pool(tmp_path, [stand.proxy("cut:10000")], fail_ratio=1.0)
    out = tmp_path / "f.bin"
    _fetch(origin, out, cutting, workers=1, max_attempts=1)
    origin.etag = '"v2"'
    _, clean = _pool(tmp_path, [stand.proxy()], name="store2")
    with pytest.raises(cfetch.ManifestMismatch):
        _fetch(origin, out, clean)


def test_a_wrong_hash_removes_the_manifest_and_keeps_the_part(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy()])
    out = tmp_path / "f.bin"
    with pytest.raises(cfetch.HashMismatch):
        _fetch(origin, out, pool, sha256="0" * 64)
    assert not out.exists() and not (tmp_path / "f.bin.part.json").exists()
    assert (tmp_path / "f.bin.part").read_bytes() == origin.data


def test_spent_attempts_leave_the_part_and_manifest_for_a_later_run(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy("cut:10000")], fail_ratio=1.0)
    result = _fetch(origin, tmp_path / "f.bin", pool, max_attempts=2)
    assert not result.ok and result.counts["cut"] == 10
    assert (tmp_path / "f.bin.part").exists() and (tmp_path / "f.bin.part.json").exists()


def test_an_empty_object_needs_no_chunks(stand, tmp_path):
    origin = stand.origin(0)
    _, pool = _pool(tmp_path, [stand.proxy()])
    out = tmp_path / "f.bin"
    assert _fetch(origin, out, pool).ok and out.read_bytes() == b""


def test_one_etag_rewriting_proxy_cannot_plant_the_identity(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy("etag"), stand.proxy(), stand.proxy()])
    info = cfetch.probe(origin.url, pool, 1.0, 20, warn=lambda *a: None)
    assert info.ranged and info.total == SIZE and info.identity["etag"] == '"v1"'


def test_a_proxy_answering_another_range_cannot_plant_the_size(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy("wrong-range"), stand.proxy()])
    info = cfetch.probe(origin.url, pool, 1.0, 20, warn=lambda *a: None)
    assert info.ranged and info.total == SIZE
```

- [ ] **Step 2: run, expect `AttributeError: ... 'fetch'`.**
- [ ] **Step 3: implement** (append to `chunked_fetch.py`)

```python
class FetchResult:
    def __init__(self, ok, done=0, chunks=0, counts=None, note=""):
        self.ok, self.done, self.chunks, self.counts, self.note = ok, done, chunks, counts or {}, note


class _Probe:
    def __init__(self, total, identity, ranged):
        self.total, self.identity, self.ranged = total, identity, ranged


def _probe_once(url, proxy, timeout):
    headers = {"Range": "bytes=0-0", "Accept-Encoding": "identity"}
    with _client(proxy, timeout) as client, client.stream("GET", url, headers=headers) as reply:
        return reply.status_code, reply.headers


def _vote_key(status, headers):
    """What one probe reply says about the object, or None when it says nothing usable.

    Key = (ranged, total, etag, last_modified). Only an exact 'bytes 0-0/N' counts as ranged: a
    proxy answering some other range would otherwise plant a bogus size.
    """
    ident = identity_of(headers)
    found = parse_content_range(headers.get("content-range"))
    if status == 206 and found and found[:2] == (0, 0):
        return (True, found[2], ident["etag"], ident["last_modified"])
    if status == 416 and (headers.get("content-range") or "").strip() == "bytes */0":
        return (True, 0, ident["etag"], ident["last_modified"])
    if status == 200:
        length = headers.get("content-length")
        total = int(length) if length and length.isascii() and length.isdigit() else None
        return (False, total, ident["etag"], ident["last_modified"])
    return None


def probe(url, pool, timeout, attempts, warn=None):
    """Size, identity and Range support of the object, decided by votes across proxies.

    One proxy's answer is not trusted alone: an injecting proxy answers 200 with a page, and one
    that rewrites ETag would plant an identity every honest proxy then fails, getting them all
    banned. So each reply is a vote, and the probe decides when two distinct proxies agree, or
    when every proxy still active has answered (most votes wins, a ranged answer wins a tie, and
    a decision only one proxy backs is logged as not cross-checked). Returns a _Probe, or None
    when nobody answered within `attempts`.
    """
    votes = {}
    for _ in range(attempts):
        picks = pool.acquire(1)
        if not picks:
            break
        proxy = picks[0]
        pool.mark_in_use(proxy)
        try:
            status, headers = _probe_once(url, proxy, timeout)
        except (httpx2.ConnectError, httpx2.ConnectTimeout, httpx2.ProxyError):
            pool.ban(proxy)
            continue
        except httpx2.TransportError:
            pool.record(proxy, False)
            continue
        key = _vote_key(status, headers)
        pool.record(proxy, key is not None)
        if key is None:
            continue
        votes.setdefault(key, set()).add(proxy)
        if len(votes[key]) >= 2:
            return _decide(key)
        voters = set().union(*votes.values())
        if pool.active() <= voters:
            break
    if not votes:
        return None
    key = max(votes, key=lambda k: (len(votes[k]), k[0]))
    if len(votes[key]) < 2:
        (warn or _stderr)("probe: only one proxy answered; its view of the object was not "
                          "cross-checked - pass --sha256 to verify the result")
    return _decide(key)


def _decide(key):
    ranged, total, etag, last_modified = key
    return _Probe(total, {"etag": etag, "last_modified": last_modified}, ranged)


def _load_manifest(path, expected):
    """The saved progress, or a fresh one; refuses a manifest for another object or plan."""
    if not os.path.exists(path):
        return dict(expected, received=[0] * expected["chunks"])
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    differs = [key for key in expected if saved.get(key) != expected[key]]
    if differs:
        raise ManifestMismatch(f"{path} belongs to another download ({', '.join(differs)} differ); "
                               f"delete it and the .part file to start over")
    return saved


def _save_manifest(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, path)


def _sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _settle(pool, proxy, reason, on_success):
    action = action_for(reason)
    if action == "ok":
        pool.record(proxy, True)
        if on_success:
            on_success(proxy)
    elif action == "ban":
        pool.ban(proxy)
    else:
        pool.record(proxy, False)


def _finish(part, out, sha256, manifest=None):
    """Verify and move the part into place; on a wrong hash drop the manifest, keep the part."""
    if sha256 and _sha256_of(part) != sha256.lower():
        if manifest and os.path.exists(manifest):
            os.remove(manifest)
        raise HashMismatch(f"sha256 of the downloaded file does not match; kept it as {part}")
    os.replace(part, out)
    if manifest and os.path.exists(manifest):
        os.remove(manifest)


def fetch(url, out, pool, *, chunk_size, workers=8, sha256=None, timeout=120.0, max_attempts=20,
          on_success=None, log=print, warn=None):
    """Download url to out through pool; see the module docstring. Returns a FetchResult.

    `log` gets the progress/report lines (stdout by default), `warn` the warnings (stderr).
    """
    info = probe(url, pool, timeout, max_attempts, warn)
    if info is None:
        return FetchResult(False, note="no proxy answered the probe")
    if not info.ranged:                       # Task 4 replaces this with the whole-file download
        return FetchResult(False, note="the origin ignores Range")
    part, manifest = out + ".part", out + ".part.json"
    chunks = plan_chunks(info.total, chunk_size)
    state = _load_manifest(manifest, {"url": url, "total": info.total, "identity": info.identity,
                                      "chunk_size": chunk_size, "chunks": len(chunks)})
    if not os.path.exists(part):
        state["received"] = [0] * len(chunks)   # progress without its bytes is no progress
    with open(part, "a+b") as f:
        f.truncate(info.total)
    lock, counts = threading.Lock(), {}

    def run_chunk(index):
        start, end = chunks[index]
        for _ in range(max_attempts):
            offset = start + state["received"][index]
            if offset > end:
                return True
            picks = pool.acquire(1)
            if not picks:
                with lock:
                    counts["no-proxy"] = counts.get("no-proxy", 0) + 1
                time.sleep(0.2)
                continue
            pool.mark_in_use(picks[0])
            reason, written = attempt(url, picks[0], offset, end, info.total, info.identity, part,
                                      timeout)
            with lock:
                state["received"][index] += written
                counts[reason] = counts.get(reason, 0) + 1
                _save_manifest(manifest, state)
            _settle(pool, picks[0], reason, on_success)
        return start + state["received"][index] > end

    with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        done = sum(ex.map(run_chunk, range(len(chunks))))
    log(f"chunks {done}/{len(chunks)}, attempts {sum(counts.values())}: "
        + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if done < len(chunks):
        _save_manifest(manifest, state)
        return FetchResult(False, done, len(chunks), counts, "chunks still missing; rerun to resume")
    _finish(part, out, sha256, manifest)
    return FetchResult(True, done, len(chunks), counts)
```

- [ ] **Step 4: run all module tests, expect PASS.** If the mixed-pool test is slow, it is the
  stall proxy: check it costs `timeout` (1 s) per pick, not `stall` (3 s).
- [ ] **Step 5: commit** `chunked_fetch: manifest-backed ranged download over the pool`.

### Task 4: The whole-file fallback

**Files:** modify `scripts/chunked_fetch.py` (`fetch`, new `_fetch_whole`, `_stream_whole`),
test append.

**Interfaces:** when `probe` decides `ranged=False` (Task 3), `fetch` streams the whole file
per attempt, restarted from 0, with no manifest.

- [ ] **Step 1: failing tests** (append)

```python
def test_a_server_without_range_support_takes_the_whole_file_fallback(stand, tmp_path):
    origin = stand.origin(SIZE)
    origin.ignore_range = True
    _, pool = _pool(tmp_path, [stand.proxy(), stand.proxy()])
    out = tmp_path / "f.bin"
    result = _fetch(origin, out, pool)
    assert result.ok and out.read_bytes() == origin.data
    assert None in origin.log                 # the download itself sent no Range header


def test_one_injecting_proxy_cannot_switch_the_download_to_whole_file(stand, tmp_path):
    origin = stand.origin(SIZE)
    _, pool = _pool(tmp_path, [stand.proxy("html"), stand.proxy()])
    out = tmp_path / "f.bin"
    assert _fetch(origin, out, pool, max_attempts=40).ok
    assert out.read_bytes() == origin.data
    assert None not in origin.log             # every origin request was ranged


def test_a_single_proxy_on_a_rangeless_server_still_falls_back_after_its_budget(stand, tmp_path):
    origin = stand.origin(SIZE)
    origin.ignore_range = True
    _, pool = _pool(tmp_path, [stand.proxy()])
    lines = []
    result = cfetch.fetch(origin.url, str(tmp_path / "f.bin"), pool, chunk_size=CHUNK, timeout=1.0,
                          max_attempts=3, log=lambda *a: None, warn=lines.append)
    assert result.ok and (tmp_path / "f.bin").read_bytes() == origin.data
    assert any("only one proxy" in line for line in lines)
```

- [ ] **Step 2: run, expect the first and third to FAIL (`fetch` returns "the origin ignores
  Range").**
- [ ] **Step 3: implement** - add `_fetch_whole` and `_stream_whole`:

```python
def _fetch_whole(url, out, pool, sha256, timeout, attempts, on_success, info, log):
    """Origin ignores Range: one whole-file stream per attempt, restarted from 0 each time."""
    part = out + ".part"
    counts = {}
    for _ in range(attempts):
        picks = pool.acquire(1)
        if not picks:
            break
        proxy = picks[0]
        pool.mark_in_use(proxy)
        reason = _stream_whole(url, proxy, part, info, timeout)
        counts[reason] = counts.get(reason, 0) + 1
        _settle(pool, proxy, reason, on_success)
        if reason == "ok":
            log(f"whole file, attempts {sum(counts.values())}: "
                + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
            _finish(part, out, sha256)
            return FetchResult(True, 1, 1, counts)
    return FetchResult(False, 0, 1, counts, "whole-file download did not complete")


def _stream_whole(url, proxy, part, info, timeout):
    written = 0
    try:
        with _client(proxy, timeout) as client, \
                client.stream("GET", url, headers={"Accept-Encoding": "identity"}) as reply:
            seen = identity_of(reply.headers)
            if reply.status_code in _THROTTLED or reply.status_code >= 500:
                return "throttled"
            if reply.status_code != 200 or any(v and seen[k] != v for k, v in info.identity.items()):
                return "wrong-object"
            with open(part, "wb") as f:
                for block in reply.iter_raw():
                    f.write(block)
                    written += len(block)
    except (httpx2.ConnectError, httpx2.ConnectTimeout, httpx2.ProxyError):
        return "dead"
    except httpx2.TransportError:
        return "cut"
    return "ok" if info.total is None or written == info.total else "cut"
```

and in `fetch`, replace Task 3's `if not info.ranged:` early return (both lines) with:

```python
    if not info.ranged:
        return _fetch_whole(url, out, pool, sha256, timeout, max_attempts, on_success, info, log)
```

- [ ] **Step 4: run all module tests, expect PASS.**
- [ ] **Step 5: commit** `chunked_fetch: probe voting and the whole-file fallback`.

### Task 5: `fetch` subcommand in proxy_pool.py

**Files:** modify `scripts/proxy_pool.py` (module docstring, imports, `main`, `_dispatch`), test
`tests/test_proxy_pool_cli.py` (append).

**Interfaces:** `proxy_pool.main(["--store", S, "fetch", URL, "-o", OUT, ...]) -> 0 | 1 | 2`.

**Out of scope:** `run`'s behaviour and flags - unchanged.

- [ ] **Step 1: failing CLI tests** (append to `test_proxy_pool_cli.py`)

```python
from fetch_standins import Standins


@pytest.fixture
def stand():
    s = Standins()
    yield s
    s.close()


def _fetch_store(tmp_path, proxies):
    store = tmp_path / "fstore"
    store.mkdir()
    (store / "live.txt").write_text("\n".join(proxies) + "\n", encoding="utf-8")
    return str(store)


def _fetch_main(store, origin, out, *extra):
    return pp.main(["--store", store, "fetch", origin.url, "-o", str(out), "--chunk-size", "64K",
                    "--cooldown", "0", "--chunk-timeout", "1", *extra])


def test_fetch_exits_0_with_a_verified_file(tmp_path, stand):
    import hashlib
    origin = stand.origin(200_000)
    out = tmp_path / "f.bin"
    rc = _fetch_main(_fetch_store(tmp_path, [stand.proxy()]), origin, out,
                     "--sha256", hashlib.sha256(origin.data).hexdigest())
    assert rc == 0 and out.read_bytes() == origin.data


def test_fetch_exits_1_when_chunks_are_still_missing(tmp_path, stand):
    origin = stand.origin(200_000)
    rc = _fetch_main(_fetch_store(tmp_path, [stand.proxy("cut:1000")]), origin, tmp_path / "f.bin",
                     "--max-attempts-per-chunk", "1", "--flaky-fail-ratio", "1.0")
    assert rc == 1


def test_fetch_exits_2_on_a_hash_mismatch(tmp_path, stand, capsys):
    origin = stand.origin(200_000)
    rc = _fetch_main(_fetch_store(tmp_path, [stand.proxy()]), origin, tmp_path / "f.bin",
                     "--sha256", "0" * 64)
    assert rc == 2 and "sha256" in capsys.readouterr().err


def test_fetch_exits_2_with_an_empty_pool(tmp_path, stand):
    assert _fetch_main(_fetch_store(tmp_path, []), stand.origin(10), tmp_path / "f.bin") == 2


@pytest.mark.parametrize("extra", [("--chunk-size", "8X"), ("--sha256", "abc")])
def test_fetch_exits_2_on_a_bad_argument(tmp_path, stand, extra, capsys):
    rc = _fetch_main(_fetch_store(tmp_path, [stand.proxy()]), stand.origin(10), tmp_path / "f.bin",
                     *extra)
    assert rc == 2 and extra[0] in capsys.readouterr().err


def test_fetch_without_a_hash_warns_on_stderr(tmp_path, stand, capsys):
    origin = stand.origin(10_000)
    assert _fetch_main(_fetch_store(tmp_path, [stand.proxy()]), origin, tmp_path / "f.bin") == 0
    captured = capsys.readouterr()
    assert "--sha256" in captured.err and "--sha256" not in captured.out
```

Note: the `_fetch_main` argv puts `--chunk-size 64K` before `*extra`, so the bad-size case
passes `--chunk-size` twice; argparse keeps the last value, which is the one under test.

- [ ] **Step 2: run, expect `invalid choice: 'fetch'` (argparse exit 2 raised as SystemExit) -
  i.e. the tests FAIL.**
- [ ] **Step 3: implement** in `proxy_pool.py`:

  - imports: add `import chunked_fetch as cfetch` after `import httpx2` (sibling module; the
    script's own directory is on `sys.path` both under `uv run scripts/proxy_pool.py` and in the
    tests' conftest).
  - module docstring: add to the Subcommands list
    `fetch      download ONE large file as byte-range chunks over rotating proxies (resumable)`
    and to the exit-code paragraph `fetch: 0 = verified file, 1 = chunks still missing or no
    proxy answered, 2 = no proxies, bad argument, hash mismatch, manifest for another download`.
  - in `main`, after the `run` parser:

```python
    f = sub.add_parser("fetch", help="download one large file as byte-range chunks over the pool")
    f.add_argument("url")
    f.add_argument("-o", "--output", required=True)
    f.add_argument("--chunk-size", default="8M", help="bytes per range, e.g. 8M, 512K (default 8M)")
    f.add_argument("--workers", type=int, default=8)
    f.add_argument("--need", type=int, default=None, help="working-set size, as for run")
    f.add_argument("--sha256", default=None, help="expected hex digest; strongly recommended")
    f.add_argument("--chunk-timeout", type=float, default=120,
                   help="seconds a chunk transfer may stall before it counts as cut")
    f.add_argument("--max-attempts-per-chunk", type=int, default=20)
    f.add_argument("--cooldown", type=float, default=5.0)
    f.add_argument("--flaky-fail-ratio", type=float, default=0.5)
```

  - the `except` in `main` becomes `except (CommandNotFound, NoProxies, BadInput, cfetch.FetchError,
    OSError) as e:`.
  - in `_dispatch`, before the `run` call:

```python
    if a.action == "fetch":
        return _fetch(a)
```

  - new function after `_dispatch`'s callers' helpers (above `if __name__`):

```python
def _fetch(a):
    """The fetch subcommand: 0 verified file, 1 work left undone, 2 cannot work."""
    try:
        chunk_size = cfetch.parse_size(a.chunk_size)
    except ValueError as exc:
        raise BadInput(f"--chunk-size: {exc}") from exc
    if a.sha256 is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", a.sha256):
        raise BadInput("--sha256 must be 64 hex digits")
    pool = ProxyPool(a.store, a.need, cooldown=a.cooldown, flaky_max_fail_ratio=a.flaky_fail_ratio)
    if not pool.active():
        raise NoProxies(f"no usable proxies in {a.store} (live + good - bad is empty); "
                        f"run discover and validate first")
    if not a.sha256:
        print("proxy_pool: no --sha256 given: only length and identity are checked, so a proxy "
              "injecting bytes behind correct headers would go unnoticed", file=sys.stderr)
    result = cfetch.fetch(a.url, a.output, pool, chunk_size=chunk_size, workers=a.workers,
                          sha256=a.sha256, timeout=a.chunk_timeout,
                          max_attempts=a.max_attempts_per_chunk,
                          on_success=lambda p: _append(_p(a.store, "good.txt"), p))
    if not result.ok:
        print(f"proxy_pool: {result.note}", file=sys.stderr)
        return 1
    print(f"done: {a.output}")
    return 0
```

- [ ] **Step 4: run the whole skill test dir, expect PASS (86 baseline + new).**
- [ ] **Step 5: commit** `proxy_pool: fetch subcommand for one large file over the pool`.

### Task 6: SKILL.md (REQUIRED SUB-SKILL: bitranox:meta-skill-writer)

**Files:** `plugins/bitranox/skills/net-rotating-proxies/SKILL.md`, its `.skillwriter/checklist-*`,
plus the regenerated `plugins/bitranox/hooks/skill_triggers.json` and `docs/skills.md` if the
description changes.

- [ ] RED: baseline-probe (opus + haiku) on the current SKILL.md with the scenario "download one
  4 GB ISO through free proxies; the IP gets banned at 1.3 GB; what does the skill tell you to
  do?" - answer a quote or NONE.
- [ ] Write a `## One large file across proxies` section after `### How success / failure is
  decided`: when to use `fetch` instead of `run`, the command line, what is kept on a cut, the
  probe vote rule, exit codes, `--sha256` advice, resuming from the manifest, and that a server
  without Range support gets a whole-file stream with no resume.
- [ ] Description: add the trigger "or when one large file must be downloaded through proxies
  and bans or dropped connections keep killing it mid-transfer"; keep it under 1024 chars
  (measure with `len()`).
- [ ] GREEN probes on the edited text, fix gaps, re-probe the final text, write the checklist.
- [ ] Regenerate: `python3 plugins/bitranox/hooks/build_skill_triggers.py` and
  `python3 plugins/bitranox/hooks/build_skill_docs.py` (check `--help` for their real flags
  first); README skill count is unchanged (no new skill).
- [ ] Commit `net-rotating-proxies: document fetch`.

### Task 7: Ship

- [ ] The bump is already made: 10.10.0 with its `### Added` entry rides the Task 1 commit
  (f945f50c), because the commit gate refuses a `plugins/` change without one and later task
  commits ride it. Do NOT run `bump_version.py` again. Instead: `git fetch origin`, then rebase
  onto `origin/master` if it moved (a peer may have released, e.g. 10.9.19); the rebase can
  conflict only in `plugin.json`, `pyproject.toml` and `CHANGELOG.md` - keep 10.10.0 if it is
  still above origin's version, else re-cut the version with `bump_version.py --rebase`. Then
  re-read the `[10.10.0]` entry against what Tasks 2-6 actually shipped and correct it if needed.
- [ ] `python3 plugins/bitranox/hooks/repo-gate.py --ci`, then
  `git push origin HEAD:master` (pre-push gate ~6 min), `ci_wait.py --ref HEAD`, release tag.
- [ ] Close backlog [40] (`backlog_close`, reason `measured: fetch shipped in <version>`), in the
  next commit.
- [ ] Issue #4: ask the user before commenting on or closing it (outward-facing).
- [ ] Remove the worktree (ExitWorktree remove after the push lands).
