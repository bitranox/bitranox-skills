"""abguard: the manifest snapshot and the out-of-band login check, through their real seams."""
import http.server
import json
import socket
import threading
from pathlib import Path

import abguard as G
import pytest

FAKE = Path(__file__).resolve().parent / "fakes" / "store_manifest_fake.py"
TOKEN = "tok-not-real"


def test_snapshot_and_verify_through_the_cli(tmp_path):
    out = tmp_path / "guard"
    assert G.snapshot(tmp_path, out, manifest=FAKE) == {"taken": True, "entries": 3, "skipped": None}
    assert G.verify(out, manifest=FAKE) == []
    (out / "CHANGED").write_text("", encoding="utf-8")
    assert G.verify(out, manifest=FAKE) == ["changed: {'slug': 'x', 'what': 'hook'}"]


def test_snapshot_skips_a_chain_without_a_store(tmp_path):
    chain = tmp_path / "nostore"
    chain.mkdir()
    res = G.snapshot(chain, tmp_path / "guard", manifest=FAKE)
    assert res["taken"] is False and "no .claude-memory" in res["skipped"]
    assert G.verify(tmp_path / "guard", manifest=FAKE) == [], "nothing taken, nothing to compare"


def test_the_real_manifest_script_reports_no_store_as_a_skip(tmp_path):
    # The shipped store_manifest.py, not the fake: its no-store wording is what NO_STORE_MARK keys on.
    chain = tmp_path / "workpiece"
    chain.mkdir()
    res = G.snapshot(chain, tmp_path / "guard")
    assert res["taken"] is False and G.NO_STORE_MARK in res["skipped"], res


def test_a_backup_refusal_other_than_no_store_is_a_guard_error(tmp_path):
    chain = tmp_path / "refuse"
    chain.mkdir()
    with pytest.raises(G.GuardError, match="rc=2"):
        G.snapshot(chain, tmp_path / "guard", manifest=FAKE)


def test_a_manifest_that_cannot_start_is_a_guard_error(tmp_path):
    with pytest.raises(G.GuardError):
        G.snapshot(tmp_path, tmp_path / "guard", manifest=tmp_path / "missing.py")


def test_a_manifest_that_times_out_is_a_guard_error(tmp_path):
    with pytest.raises(G.GuardError, match="timed out"):
        G._manifest(["backup", "--from", str(tmp_path / "slow"), "--out", str(tmp_path / "g")], FAKE,
                    timeout=0.5)


def test_verify_that_cannot_run_is_a_guard_error(tmp_path):
    out = tmp_path / "guard"
    G.snapshot(tmp_path, out, manifest=FAKE)
    (out / "UNREADABLE").write_text("", encoding="utf-8")
    with pytest.raises(G.GuardError, match="could not run"):
        G.verify(out, manifest=FAKE)


def test_the_shipped_manifest_script_exists_and_has_the_cli():
    assert G.MANIFEST.is_file(), G.MANIFEST
    text = G.MANIFEST.read_text(encoding="utf-8")
    assert '"--out"' in text and '"--scope"' in text and '"verify"' in text


def _creds(tmp_path):
    creds = tmp_path / "c.json"
    creds.write_text(json.dumps({"claudeAiOauth": {"accessToken": TOKEN}}), encoding="utf-8")
    return creds


@pytest.mark.parametrize("status, expected", [(200, "ok"), (401, "login"), (429, "quota"), (500, "unknown:500"), (0, "unknown:0")])
def test_check_login_classifies_the_status(tmp_path, status, expected):
    seen = {}

    def fake_post(url, headers, body):
        seen["url"], seen["auth"] = url, headers.get("authorization")
        return status, "{}"

    result = G.check_login(_creds(tmp_path), post=fake_post)
    assert result == expected
    assert TOKEN not in result
    assert seen["url"].endswith("/v1/messages") and seen["auth"] == "Bearer " + TOKEN


def test_check_login_without_a_token_is_login(tmp_path):
    creds = tmp_path / "c.json"
    creds.write_text("{}", encoding="utf-8")
    assert G.check_login(creds, post=lambda *a: (200, "")) == "login"


def test_check_login_with_an_unreadable_file_is_login(tmp_path):
    assert G.check_login(tmp_path / "absent.json", post=lambda *a: (200, "")) == "login"
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert G.check_login(bad, post=lambda *a: (200, "")) == "login"


class _Handler(http.server.BaseHTTPRequestHandler):
    status = 200

    def do_POST(self):
        self.rfile.read(int(self.headers.get("content-length") or 0))
        self.send_response(type(self).status)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"answer": 1}')

    def log_message(self, *args):
        pass


@pytest.mark.parametrize("status", [200, 429])
def test_post_returns_status_and_body_from_a_real_server(status):
    handler = type("H", (_Handler,), {"status": status})
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/v1/messages"
        assert G._post(url, {"content-type": "application/json"}, b"{}") == (status, '{"answer": 1}')
    finally:
        server.shutdown()
        server.server_close()


def test_post_without_a_listener_is_status_zero():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    status, detail = G._post(f"http://127.0.0.1:{port}/v1/messages", {"authorization": "Bearer " + TOKEN}, b"{}")
    assert status == 0 and TOKEN not in detail
