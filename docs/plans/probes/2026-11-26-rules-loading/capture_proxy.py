"""Forwarding proxy for ANTHROPIC_BASE_URL: saves each request BODY (never headers) to a dir.

Usage: python3 capture_proxy.py <port> <outdir>
Each POST body is written to <outdir>/<n>.json, then forwarded to api.anthropic.com unchanged;
the upstream reply is buffered and returned whole (SSE included), which the CLI accepts.
"""

import http.client
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UPSTREAM = "api.anthropic.com"
DROP = {"host", "accept-encoding", "content-length", "connection"}
_lock = threading.Lock()
_count = [0]


class Handler(BaseHTTPRequestHandler):
    def _forward(self, method: str) -> None:
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else b""
        if method == "POST":
            with _lock:
                _count[0] += 1
                n = _count[0]
            (OUT / f"{n:03d}.json").write_bytes(body)
            (OUT / f"{n:03d}.path").write_text(self.path, encoding="utf-8")
        headers = {k: v for k, v in self.headers.items() if k.lower() not in DROP}
        conn = http.client.HTTPSConnection(UPSTREAM, timeout=300)
        conn.request(method, self.path, body=body or None, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() not in {"transfer-encoding", "content-length", "connection", "content-encoding"}:
                self.send_header(k, v)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        self._forward("POST")

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        self._forward("GET")

    def log_message(self, *args: object) -> None:
        pass


if __name__ == "__main__":
    OUT = Path(sys.argv[2])
    OUT.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
