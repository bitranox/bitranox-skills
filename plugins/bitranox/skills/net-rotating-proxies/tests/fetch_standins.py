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
        srv.ae_log.append(self.headers.get("Accept-Encoding"))
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
        srv.log.append(self.headers.get("Range"))
        mode = srv.mode
        if mode == "probe-only" and self.headers.get("Range") != "bytes=0-0":
            # Honest for the probe, then a page for every chunk: banned on first download contact.
            return self._reply(200, b"<html>blocked</html>", {"Content-Type": "text/html"})
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
        if mode.startswith("trickle:"):
            return self._trickle(body, float(mode[8:]))
        self.wfile.write(body)

    def _trickle(self, body, pause):
        # One byte per pause: every read completes inside the client's read timeout, so only a
        # wall-time budget on the whole attempt ends it. close() releases it through `stop`.
        try:
            for i in range(len(body)):
                self.wfile.write(body[i:i + 1])
                if self.server.stop.wait(pause):
                    return
        except OSError:          # the client gave up and closed the connection
            return

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
        srv.data, srv.etag, srv.ignore_range, srv.log, srv.ae_log = payload(size), etag, False, [], []
        srv.url = f"http://127.0.0.1:{srv.server_address[1]}/f.bin"
        return srv

    def proxy(self, mode="clean", stall=3.0):
        if mode == "refuse":
            return f"127.0.0.1:{_free_port()}"
        srv = self._start(_Proxy)
        srv.mode, srv.hits, srv.stall, srv.stop, srv.log = mode, 0, stall, self.stop, []
        address = f"127.0.0.1:{srv.server_address[1]}"
        self.proxies[address] = srv
        return address

    def _start(self, handler):
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        srv.daemon_threads = True
        # A short poll: shutdown() waits up to one poll interval per server, and the default
        # 0.5 s made every test teardown cost a second.
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05},
                         daemon=True).start()
        self._servers.append(srv)
        return srv

    def close(self):
        self.stop.set()
        for srv in self._servers:
            srv.shutdown()
            srv.server_close()
