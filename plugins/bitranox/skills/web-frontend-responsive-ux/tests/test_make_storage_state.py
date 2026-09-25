"""Tests for make_storage_state: argument parsing, and capture()/main() with a scripted browser."""

import json
import os
import stat
import sys

import pytest

import make_storage_state as mss
from responsive_fake_browser import MISSING_EXECUTABLE, MISSING_HOST_DEPS, Script, fake_launcher

POSIX_MODES = pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits do not exist on Windows")


def test_parse_args_defaults():
    args = mss.parse_args(["https://x/login"])
    assert args.login_url == "https://x/login"
    assert args.out == "state.json"


def test_parse_args_custom_out():
    args = mss.parse_args(["https://x/login", "--out", "s.json"])
    assert args.out == "s.json"


def test_module_is_import_safe():
    assert callable(mss.capture) and callable(mss.main)


def _capture(tmp_path, out_name="state.json", script=None):
    out = tmp_path / "sub" / out_name
    launch = fake_launcher(script)
    mss.capture("http://127.0.0.1:9/login", out, prompt=lambda _msg: "", launch=launch)
    return out, launch.browser


def test_capture_saves_the_session_state(tmp_path):
    out, browser = _capture(tmp_path)
    assert json.loads(out.read_text(encoding="utf-8")) == {"cookies": [{"name": "sid", "value": "SECRET"}]}
    assert browser.pages[0].url == "http://127.0.0.1:9/login"


@POSIX_MODES
def test_session_file_is_owner_only_whatever_the_umask(tmp_path):
    old = os.umask(0o022)
    try:
        out, _ = _capture(tmp_path)
    finally:
        os.umask(old)
    assert stat.S_IMODE(out.stat().st_mode) == 0o600


@POSIX_MODES
def test_an_existing_world_readable_file_is_tightened(tmp_path):
    out = tmp_path / "sub" / "state.json"
    out.parent.mkdir()
    out.write_text("{}", encoding="utf-8")
    out.chmod(0o644)
    _capture(tmp_path)
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    assert "SECRET" in out.read_text(encoding="utf-8")


def test_main_exit_0_names_the_saved_file(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _msg="": "")
    out = tmp_path / "state.json"
    assert mss.main(["http://127.0.0.1:9/login", "--out", str(out)], launch=fake_launcher()) == 0
    assert str(out) in capsys.readouterr().out
    assert out.exists()


def test_main_missing_browser_exits_3(tmp_path, capsys):
    rc = mss.main(["http://x/", "--out", str(tmp_path / "s.json")],
                  launch=fake_launcher(error=RuntimeError(MISSING_EXECUTABLE)))
    assert rc == 3
    assert "playwright install chromium" in capsys.readouterr().err


def test_main_missing_host_libraries_exit_3_naming_install_deps(tmp_path, capsys):
    rc = mss.main(["http://x/", "--out", str(tmp_path / "s.json")],
                  launch=fake_launcher(error=RuntimeError(MISSING_HOST_DEPS)))
    err = capsys.readouterr().err
    assert rc == 3
    assert "install-deps" in err and "Chromium not installed" not in err


def test_main_other_failure_exits_1(tmp_path, capsys):
    script = Script(goto_error=RuntimeError("net::ERR_NAME_NOT_RESOLVED"))
    rc = mss.main(["http://x/", "--out", str(tmp_path / "s.json")], launch=fake_launcher(script))
    assert rc == 1
    assert "ERR_NAME_NOT_RESOLVED" in capsys.readouterr().err
    assert not (tmp_path / "s.json").exists()
