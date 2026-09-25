"""CLI-level tests for proxy_pool.py: main(), run(), discover, and the background loops.

No real proxy and no internet: the worklist command is a small Python fake that never touches the
proxy it is handed, and discovery reads from an http.server bound to 127.0.0.1. Proxy environment
variables are cleared so httpx2 cannot route the local fetch through a machine-wide proxy.
"""
import http.server
import os
import socket
import subprocess
import sys
import threading

import pytest

import proxy_pool as pp

FAKE_TOOL = r'''
import pathlib, sys, time
proxy, item, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
if item.startswith("ok"):
    pathlib.Path(outdir, item + ".vtt").write_text(proxy, encoding="utf-8")
    sys.exit(0)
if item.startswith("rl"):
    sys.stderr.write("ERROR: HTTP Error 429: Too Many Requests\n")
    sys.exit(1)
if item.startswith("dead"):
    sys.stderr.write("connection refused\n")
    sys.exit(1)
if item.startswith("slow"):
    time.sleep(30)
if item.startswith("bytes"):
    sys.stdout.buffer.write(b"\xff\xfe not utf-8 \x81\n")
    sys.stdout.flush()
    sys.exit(1)
sys.exit(1)
'''


@pytest.fixture(autouse=True)
def _no_proxy_env(monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")


@pytest.fixture
def tool(tmp_path):
    script = tmp_path / "fake_tool.py"
    script.write_text(FAKE_TOOL, encoding="utf-8")
    outdir = tmp_path / "out"
    outdir.mkdir()
    # Double quotes, not shlex.quote: the template is split by Windows rules on Windows, where a
    # single quote is an ordinary character.
    cmd = f'"{sys.executable}" "{script}" {{proxy}} {{item}} "{outdir}"'
    return cmd, outdir


def _store(tmp_path, live=("1.2.3.4:80",)):
    store = tmp_path / "store"
    store.mkdir()
    if live:
        (store / "live.txt").write_text("\n".join(live) + "\n", encoding="utf-8")
    return str(store)


def _worklist(tmp_path, *items, bom=False):
    path = tmp_path / "items.txt"
    data = "\n".join(items).encode("utf-8") + b"\n"
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)
    return str(path)


def _run(store, worklist, cmd, *extra):
    return pp.main(["--store", store, "run", "--worklist", worklist, "--cmd", cmd,
                    "--workers", "2", "--per-item-proxies", "1", "--cooldown", "0", *extra])


# ---- run exit codes -----------------------------------------------------------------------------
def test_run_exits_0_when_every_item_succeeds(tmp_path, tool):
    cmd, _ = tool
    assert _run(_store(tmp_path), _worklist(tmp_path, "ok1", "ok2"), cmd) == 0


def test_run_exits_1_when_an_item_fails(tmp_path, tool):
    cmd, _ = tool
    assert _run(_store(tmp_path), _worklist(tmp_path, "ok1", "rl1"), cmd) == 1


def test_run_exits_1_when_no_item_succeeds(tmp_path, tool):
    cmd, _ = tool
    assert _run(_store(tmp_path), _worklist(tmp_path, "rl1", "rl2"), cmd) == 1


def test_run_with_an_empty_pool_is_an_error(tmp_path, tool, capsys):
    cmd, _ = tool
    assert _run(_store(tmp_path, live=()), _worklist(tmp_path, "ok1"), cmd) == 2
    assert "no usable proxies" in capsys.readouterr().err


def test_run_with_a_missing_command_aborts_with_exit_2(tmp_path, capsys):
    rc = _run(_store(tmp_path), _worklist(tmp_path, "a", "b", "c"),
              "no-such-binary-xyz {proxy} {item}")
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_run_counts_a_timed_out_attempt_as_a_failure_not_a_crash(tmp_path, tool):
    cmd, _ = tool
    assert _run(_store(tmp_path), _worklist(tmp_path, "slow1"), cmd, "--item-timeout", "1") == 1


def test_run_survives_output_that_is_not_utf8(tmp_path, tool):
    """Text-mode capture with the locale codec raised UnicodeDecodeError past every handler."""
    cmd, _ = tool
    assert _run(_store(tmp_path), _worklist(tmp_path, "bytes1"), cmd) == 1


def test_a_worklist_saved_with_a_bom_does_not_corrupt_the_first_item(tmp_path, tool):
    cmd, outdir = tool
    assert _run(_store(tmp_path), _worklist(tmp_path, "ok1", bom=True), cmd) == 0
    assert (outdir / "ok1.vtt").exists()


# ---- success glob -------------------------------------------------------------------------------
def test_success_glob_matches_an_item_with_glob_metacharacters(tmp_path, tool):
    """{item} goes into the glob escaped; 'ok[1]' used to be read as a character class."""
    cmd, outdir = tool
    glob_arg = str(outdir / "{item}*.vtt")
    rc = _run(_store(tmp_path), _worklist(tmp_path, "ok[1]"), cmd, "--success-glob", glob_arg)
    assert rc == 0
    assert (outdir / "ok[1].vtt").exists()


def test_success_glob_still_fails_when_no_file_was_written(tmp_path, tool):
    cmd, outdir = tool
    rc = _run(_store(tmp_path), _worklist(tmp_path, "rl1"), cmd,
              "--success-glob", str(outdir / "{item}*.vtt"))
    assert rc == 1


# ---- flaky proxies are rotated, never banned for good -------------------------------------------
def test_repeated_rate_limits_never_write_the_proxy_to_bad_txt(tmp_path, tool):
    """429 is the TARGET throttling, not a dead proxy: it must not be banned permanently."""
    cmd, _ = tool
    store = _store(tmp_path)
    rc = _run(store, _worklist(tmp_path, "rl1", "rl2", "rl3", "rl4", "rl5"), cmd)
    assert rc == 1
    assert pp._read(pp._p(store, "bad.txt")) == set()


def test_a_connection_level_failure_is_still_banned(tmp_path, tool):
    cmd, _ = tool
    store = _store(tmp_path)
    _run(store, _worklist(tmp_path, "dead1"), cmd)
    assert pp._read(pp._p(store, "bad.txt")) == {"1.2.3.4:80"}


# ---- Windows command lines ----------------------------------------------------------------------
def test_a_windows_cmd_keeps_the_backslashes_in_its_paths():
    tpl = r"C:\tools\yt-dlp.exe --proxy http://{proxy} -o out\{item}.%(ext)s"
    assert pp.split_command(tpl, windows=True) == [
        r"C:\tools\yt-dlp.exe", "--proxy", "http://{proxy}", "-o", r"out\{item}.%(ext)s"]


def test_windows_rules_keep_a_quoted_path_with_spaces_whole():
    assert pp.split_command(r'"C:\Program Files\x.exe" {item}', windows=True) == [
        r"C:\Program Files\x.exe", "{item}"]


def test_posix_rules_are_unchanged():
    assert pp.split_command("a 'b c' {item}", windows=False) == ["a", "b c", "{item}"]


# ---- discover -----------------------------------------------------------------------------------
@pytest.fixture
def list_server(tmp_path):
    root = tmp_path / "www"
    root.mkdir()
    (root / "list.txt").write_text("192.0.2.1:8080\n192.0.2.2:3128\n", encoding="utf-8")

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _closed_port_url():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}/list.txt"


def test_discover_merges_a_reachable_source(tmp_path, list_server):
    store = _store(tmp_path, live=())
    assert pp.main(["--store", store, "discover", "--sources", list_server + "/list.txt"]) == 0
    assert pp._read(pp._p(store, "pool.txt")) == {"192.0.2.1:8080", "192.0.2.2:3128"}


def test_discover_with_every_source_failing_is_an_error(tmp_path):
    store = _store(tmp_path, live=())
    assert pp.main(["--store", store, "discover", "--sources", _closed_port_url(), _closed_port_url()]) == 2


def test_discover_counts_an_http_error_page_as_a_failed_source(tmp_path, list_server):
    """A 404 body parses to zero entries; counting it as an answer would hide a dead list URL."""
    store = _store(tmp_path, live=())
    assert pp.main(["--store", store, "discover", "--sources", list_server + "/missing.txt"]) == 2


def test_discover_with_one_source_failing_still_succeeds(tmp_path, list_server):
    store = _store(tmp_path, live=())
    assert pp.main(["--store", store, "discover", "--sources", _closed_port_url(),
                    list_server + "/list.txt"]) == 0


# ---- background loops ---------------------------------------------------------------------------
def test_bg_refresh_tops_the_pool_up_from_its_sources(tmp_path, list_server, monkeypatch):
    store = _store(tmp_path, live=())
    monkeypatch.setattr(pp, "_reachable", lambda p, u, t: (True, 0.1))
    stop = threading.Event()
    thread = threading.Thread(target=pp._bg_refresh, daemon=True,
                              args=(store, "http://127.0.0.1/", 4, 1, stop),
                              kwargs={"need": 1, "interval": 0.05,
                                      "sources": [list_server + "/list.txt"]})
    thread.start()
    deadline = threading.Event()
    for _ in range(200):
        if pp._read(pp._p(store, "live.txt")):
            break
        deadline.wait(0.05)
    stop.set()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert len(pp._read(pp._p(store, "live.txt"))) >= 1


def test_benchmark_loop_stops_when_told(tmp_path):
    pool = pp.ProxyPool(_store(tmp_path), need=1)
    stop = threading.Event()
    stop.set()
    pool.benchmark_loop(stop, interval=0.01)


# ---- output on a cp1252 console -----------------------------------------------------------------
def test_a_non_cp1252_item_name_does_not_crash_the_report(tmp_path, tool):
    cmd, _ = tool
    script = os.path.join(os.path.dirname(pp.__file__), "proxy_pool.py")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    proc = subprocess.run(
        [sys.executable, script, "--store", _store(tmp_path), "run",
         "--worklist", _worklist(tmp_path, "ok\u0141"), "--cmd", cmd, "--cooldown", "0"],
        capture_output=True, env=env, check=False, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert b"OK ok?" in proc.stdout
