"""Local stand-ins for chunked-fetch tests: a Range-capable origin and fault-injecting proxies.

Everything binds 127.0.0.1; no internet. httpx2 sends a plain http:// target to a proxy as an
absolute-form request (`GET http://127.0.0.1:<port>/f.bin HTTP/1.1`, verified 2026-11-01), so a
proxy here reads the target from the request line and either relays it or misbehaves in the one
way its mode names. An https:// target arrives as a CONNECT instead: mode 'tunnel' opens it and
pipes bytes both ways (so the TLS handshake is the client's with the origin, as through a real
proxy), mode 'connect:STATUS' refuses it. A TLS origin presents a certificate from tls_certs. The
handlers answer HTTP/1.0, so closing early after a full Content-Length header is what a dropped
session looks like to the client.
"""
import http.client
import http.server
import selectors
import socket
import ssl
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
        if srv.redirect_to:
            return self._send(302, b"", {"Location": srv.redirect_to})
        if srv.status:                      # every request, the probe's included: a URL that 404s
            return self._send(srv.status, b"", {})
        # Anything but the probe's byte 0 is a download request: chunk_status / chunk_etag model
        # an origin that changes between the probe and the download (replaced file, removed URL).
        download = rng != "bytes=0-0"
        etag = srv.chunk_etag if download and srv.chunk_etag else srv.etag
        if download and srv.chunk_status:
            return self._send(srv.chunk_status, b"", {}, etag)
        if rng is None or srv.ignore_range:
            return self._send(200, data, {}, etag)
        first, last = rng.removeprefix("bytes=").split("-")
        first, last = int(first), min(int(last), len(data) - 1)
        if first >= len(data):
            return self._send(416, b"", {"Content-Range": f"bytes */{len(data)}"}, etag)
        return self._send(206, data[first:last + 1],
                          {"Content-Range": f"bytes {first}-{last}/{len(data)}"}, etag)

    def _send(self, status, body, extra, etag=None):
        self.send_response(status)
        headers = {"ETag": etag or self.server.etag, "Last-Modified": LAST_MODIFIED,
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
        if mode.isdigit():                  # "429", "403", "404": that status, no body
            return self._reply(int(mode), b"", {})
        if mode == "html":
            return self._reply(200, b"<html>blocked</html>", {"Content-Type": "text/html"})
        if mode == "wrong-range":
            return self._reply(206, b"x" * 10, {"Content-Range": "bytes 0-9/999999"})
        if mode == "stall":
            srv.stop.wait(srv.stall)        # answer nothing; the client's read timeout fires first
            return
        status, headers, body = self._relay()
        if mode.startswith("trickle-head:"):
            # The status line and headers one byte per pause: the reply never starts, yet every
            # read completes inside the read timeout.
            head = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
            raw = f"HTTP/1.0 {status} Relayed\r\n{head}\r\n".encode("latin-1") + body
            return self._trickle(raw, float(mode[13:]))
        if mode == "etag":
            headers["ETag"] = '"changed"'
        if mode == "overrun":
            body += b"\x00" * 100
            headers["Content-Length"] = str(len(body))
        if mode.startswith("unsized"):
            # No length: an HTTP/1.0 body then ends where the connection closes, so a short or
            # long one arrives as a clean end of stream, never as a transport error.
            headers.pop("Content-Length", None)
            if mode == "unsized-overrun":
                body += b"\x00" * 100
            elif mode.startswith("unsized-cut:"):
                body = body[:int(mode[12:])]
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if mode.startswith("cut:"):
            self.wfile.write(body[:int(mode[4:])])   # then close: the promised length never comes
            return
        if mode.startswith("trickle:"):
            return self._trickle(body, float(mode[8:]))
        if mode.startswith("trickle-stall:"):
            # 'trickle-stall:PAUSE:N': N body bytes one per PAUSE, then silence.
            pause, count = mode[14:].split(":")
            if not self._trickle(body[:int(count)], float(pause)):
                srv.stop.wait(srv.stall)
            return
        self.wfile.write(body)

    def do_CONNECT(self):
        # 'tunnel': open it and pipe. 'connect:STATUS': refuse it with that status, as a proxy does
        # that cannot reach the origin (502) or will not tunnel to it (403, 405). Any other mode
        # refuses with 501, as an http-only proxy does.
        srv = self.server
        srv.hits += 1
        srv.log.append("CONNECT")
        if srv.mode == "tunnel":
            return self._tunnel()
        status = int(srv.mode[8:]) if srv.mode.startswith("connect:") else 501
        self._reply(status, b"", {})

    def _tunnel(self):
        host, _, port = self.path.rpartition(":")
        try:
            upstream = socket.create_connection((host, int(port)), timeout=10)
        except OSError:
            return self._reply(502, b"", {})
        self.send_response(200, "Connection established")
        self.end_headers()
        self.wfile.flush()
        with upstream, selectors.DefaultSelector() as sel:
            sel.register(self.connection, selectors.EVENT_READ, upstream)
            sel.register(upstream, selectors.EVENT_READ, self.connection)
            # Polled, so close() ends a tunnel that both ends keep open.
            while not self.server.stop.is_set():
                for key, _ in sel.select(timeout=0.05):
                    try:
                        data = key.fileobj.recv(65536)
                        if not data:
                            return
                        key.data.sendall(data)
                    except OSError:
                        return

    def _trickle(self, body, pause):
        # One byte per pause: every read completes inside the client's read timeout, so only a
        # wall-time budget on the whole attempt ends it. close() releases it through `stop`.
        # Returns True when it stopped early (closed, or the client went away).
        try:
            for i in range(len(body)):
                self.wfile.write(body[i:i + 1])
                if self.server.stop.wait(pause):
                    return True
        except OSError:          # the client gave up and closed the connection
            return True
        return False

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


class _TLSServer(http.server.ThreadingHTTPServer):
    """The handshake runs in the request's own thread, not in the accept loop: a client that
    rejects the certificate, or one that never finishes, must not hold up every other one."""

    def finish_request(self, request, client_address):
        try:
            request.do_handshake()
        except OSError:              # the client refused the certificate, or went away
            return
        super().finish_request(request, client_address)


class Standins:
    """Start origins and proxies; close() stops every server and releases stalled handlers."""

    def __init__(self):
        self.stop = threading.Event()
        self.proxies = {}
        self._servers = []
        self._sockets = []

    def origin(self, size, etag='"v1"', tls=None):
        """A Range-capable origin; tls=(certfile, keyfile) serves it over https."""
        srv = self._start(_Origin, _TLSServer if tls else http.server.ThreadingHTTPServer)
        if tls:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(*tls)
            srv.socket = ctx.wrap_socket(srv.socket, server_side=True,
                                         do_handshake_on_connect=False)
        srv.data, srv.etag, srv.ignore_range, srv.log, srv.ae_log = payload(size), etag, False, [], []
        srv.chunk_status = srv.chunk_etag = srv.redirect_to = srv.status = None
        scheme = "https" if tls else "http"
        srv.url = f"{scheme}://127.0.0.1:{srv.server_address[1]}/f.bin"
        return srv

    def silent(self):
        """An https URL whose server accepts the connection and never answers: the kernel
        completes the TCP handshake for a listening socket nobody accepts on, so a TLS handshake
        through a tunnel waits out its timeout."""
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(16)
        self._sockets.append(s)
        return f"https://127.0.0.1:{s.getsockname()[1]}/f.bin"

    def proxy(self, mode="clean", stall=3.0):
        if mode == "refuse":
            return f"127.0.0.1:{_free_port()}"
        srv = self._start(_Proxy)
        srv.mode, srv.hits, srv.stall, srv.stop, srv.log = mode, 0, stall, self.stop, []
        address = f"127.0.0.1:{srv.server_address[1]}"
        self.proxies[address] = srv
        return address

    def _start(self, handler, server=http.server.ThreadingHTTPServer):
        srv = server(("127.0.0.1", 0), handler)
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
        for s in self._sockets:
            s.close()
