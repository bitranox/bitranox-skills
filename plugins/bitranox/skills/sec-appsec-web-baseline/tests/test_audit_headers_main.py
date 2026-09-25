"""End-to-end tests for audit_headers.main()/fetch(): exit codes, redirects, the HEAD probe.

No test reaches the internet. HTTPS sites are simulated with an httpx MockTransport (the
network edge, injected through fetch's ``transport`` seam); the plain-HTTP tests use a real
http.server on 127.0.0.1. Hosts are IP literals, so the internal-target check never asks DNS.
"""

import functools
import http.server
import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path

import httpx2 as httpx
import pytest

import audit_headers as a

SCRIPT = Path(a.__file__).resolve()
SITE = "203.0.113.10"  # TEST-NET-3 literal: never resolved, never routed

CLEAN_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; object-src 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Type": "text/html; charset=utf-8",
}


class FakeSite:
    """A MockTransport handler: plain HTTP 301s to https, https serves ``headers`` + ``html``."""

    def __init__(self, headers, html="<p>hi</p>", cookies=()):
        self.headers = headers
        self.html = html
        self.cookies = list(cookies)
        self.requests = []

    def __call__(self, request):
        self.requests.append((request.method, str(request.url)))
        if request.url.scheme == "http":
            target = str(request.url.copy_with(scheme="https", port=None))
            return httpx.Response(301, headers={"Location": target})
        headers = list(self.headers.items()) + [("Set-Cookie", c) for c in self.cookies]
        return httpx.Response(200, headers=headers, text=self.html)


def run_main(argv, site, capsys):
    fetcher = functools.partial(a.fetch, transport=httpx.MockTransport(site))
    rc = a.main(argv, fetcher=fetcher)
    return rc, capsys.readouterr()


def test_clean_https_site_exits_0(capsys):
    rc, out = run_main([f"https://{SITE}/"], FakeSite(CLEAN_HEADERS), capsys)
    assert rc == 0, out.out
    assert "SEVERE=0 MEDIUM=0" in out.out


def test_medium_finding_exits_1(capsys):
    headers = dict(CLEAN_HEADERS)
    del headers["X-Content-Type-Options"]
    rc, out = run_main([f"https://{SITE}/"], FakeSite(headers), capsys)
    assert rc == 1
    assert "[MEDIUM] x-content-type-options" in out.out


def test_json_output_keys(capsys):
    rc, out = run_main([f"https://{SITE}/", "--json"], FakeSite(CLEAN_HEADERS), capsys)
    doc = json.loads(out.out)
    assert rc == 0
    assert doc["url"] == f"https://{SITE}/"
    assert set(doc["counts"]) == {"SEVERE", "MEDIUM", "MINOR", "OK"}
    assert all({"check", "severity", "detail", "fix"} <= set(f) for f in doc["findings"])


def test_http_url_redirected_to_https_is_graded_as_https(capsys):
    # the site behind the redirect has no HSTS, an insecure cookie and an http:// script
    headers = {k: v for k, v in CLEAN_HEADERS.items() if k != "Strict-Transport-Security"}
    site = FakeSite(headers, html='<script src="http://cdn.example/a.js"></script>',
                    cookies=["sid=abc; HttpOnly; SameSite=Lax"])
    rc, out = run_main([f"http://{SITE}/", "--json"], site, capsys)
    by = {f["check"]: f["severity"] for f in json.loads(out.out)["findings"]}
    assert rc == 1
    assert by["hsts"] == "SEVERE"
    assert by["cookie:sid"] == "SEVERE"
    assert by["mixed-content"] == "SEVERE"
    assert by["https-redirect"] == "OK"


def test_https_url_with_port_probes_plain_http_on_the_default_port(capsys):
    site = FakeSite(CLEAN_HEADERS)
    run_main([f"https://{SITE}:8443/app?x=1"], site, capsys)
    heads = [url for method, url in site.requests if method == "HEAD"]
    assert heads == [f"http://{SITE}/app?x=1"]


def test_http_url_with_port_probes_that_same_port(capsys):
    site = FakeSite(CLEAN_HEADERS)
    run_main([f"http://{SITE}:8080/"], site, capsys)
    heads = [url for method, url in site.requests if method == "HEAD"]
    assert heads == [f"http://{SITE}:8080/"]


def test_fetch_failure_exits_2_not_the_gate_code(capsys):
    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)

    rc = a.main([f"https://{SITE}/"], fetcher=functools.partial(a.fetch, transport=httpx.MockTransport(refuse)))
    err = capsys.readouterr().err
    assert rc == 2
    assert "could not fetch" in err


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_refused_real_port_exits_2(capsys):
    assert a.main([f"http://127.0.0.1:{_free_port()}/"]) == 2


def test_internal_target_warning():
    assert "INTERNAL address (127.0.0.1)" in a.internal_target_warning("http://127.0.0.1:8080/x", None)
    assert a.internal_target_warning("http://127.0.0.1/", "http://proxy:3128") is None
    assert a.internal_target_warning("https://8.8.8.8/", None) is None


class _Handler(http.server.BaseHTTPRequestHandler):
    def _reply(self, body=b""):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        return body

    def do_GET(self):  # noqa: N802 - http.server naming
        self.wfile.write(self._reply(b"<p>hi</p>"))

    def do_HEAD(self):  # noqa: N802
        self._reply()

    def log_message(self, *args):
        pass


@pytest.fixture
def local_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_cp1252_stdout_does_not_crash_on_a_non_cp1252_url(local_server):
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    url = local_server + "/π.html"
    proc = subprocess.run([sys.executable, str(SCRIPT), url], capture_output=True, env=env,
                          timeout=60)
    stdout = proc.stdout.decode("cp1252")
    assert b"UnicodeEncodeError" not in proc.stderr, proc.stderr
    assert proc.returncode == 1  # the gate (plain HTTP, no CSP), not a crash
    assert "SEVERE=" in stdout
