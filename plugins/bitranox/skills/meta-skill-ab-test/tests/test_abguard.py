"""abguard: the manifest snapshot and the out-of-band login check, through their real seams."""
import http.server
import inspect
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



def test_the_fake_keys_its_behaviours_on_the_chain_dir_name_not_the_path(tmp_path):
    # A parent dir (or pytest's tmp_path, named after the test) holding "nostore" must not turn
    # an ordinary chain into a no-store one.
    chain = tmp_path / "nostore-parent" / "workpiece"
    chain.mkdir(parents=True)
    assert G.snapshot(chain, tmp_path / "guard", manifest=FAKE)["taken"] is True


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



@pytest.mark.parametrize("token", [TOKEN + "\n", TOKEN + "\r\nx-injected: 1", TOKEN + "\x00", TOKEN + "\u00e9"])
def test_check_login_refuses_a_token_that_cannot_be_a_header_value(tmp_path, token):
    creds = tmp_path / "c.json"
    creds.write_text(json.dumps({"claudeAiOauth": {"accessToken": token}}), encoding="utf-8")
    called = []

    def fake_post(*args):
        called.append(args)
        return 200, ""

    assert G.check_login(creds, post=fake_post) == "login"
    assert called == [], "a malformed token is never sent"


def test_the_docstrings_state_the_429_and_missing_manifest_caveats():
    login_doc = " ".join((inspect.getdoc(G.check_login) or "").split())
    module_doc = " ".join((G.__doc__ or "").split())
    for doc in (login_doc, module_doc):
        assert "rate limited" in doc and "request shape" in doc, doc
    verify_doc = " ".join((inspect.getdoc(G.verify) or "").split())
    assert "taken=True" in verify_doc and "no change" in verify_doc, verify_doc

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


def test_post_with_a_header_value_holding_a_newline_is_status_zero_and_never_echoes_it():
    # http.client refuses the header with a ValueError whose message quotes the value.
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    status, detail = G._post(f"http://127.0.0.1:{port}/v1/messages",
                             {"authorization": "Bearer " + TOKEN + "\nx"}, b"{}")
    assert status == 0 and TOKEN not in detail, detail


def test_post_with_a_malformed_status_line_is_status_zero():
    # A non-HTTP answer makes http.client raise BadStatusLine, an HTTPException and not an OSError.
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        def answer():
            conn, _ = srv.accept()
            with conn:
                conn.recv(65536)
                conn.sendall(b"not http at all\r\n\r\n")

        thread = threading.Thread(target=answer, daemon=True)
        thread.start()
        status, detail = G._post(f"http://127.0.0.1:{port}/v1/messages",
                                 {"authorization": "Bearer " + TOKEN}, b"{}")
        thread.join(timeout=5)
    assert status == 0 and TOKEN not in detail, detail
