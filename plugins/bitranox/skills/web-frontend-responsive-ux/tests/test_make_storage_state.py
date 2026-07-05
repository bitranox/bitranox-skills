"""Tests for make_storage_state pure helpers (no browser)."""
import make_storage_state as mss


def test_parse_args_defaults():
    args = mss.parse_args(["https://x/login"])
    assert args.login_url == "https://x/login"
    assert args.out == "state.json"


def test_parse_args_custom_out():
    args = mss.parse_args(["https://x/login", "--out", "s.json"])
    assert args.out == "s.json"


def test_module_is_import_safe():
    assert callable(mss.capture) and callable(mss.main)
