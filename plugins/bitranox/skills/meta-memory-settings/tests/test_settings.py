"""Tests for the meta-memory-settings CLI. All content ASCII."""

import pytest

import settings as ST
import self_improve_signals as sig


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def test_view_shows_defaults(capsys):
    assert ST.main(["view"]) == 0
    out = capsys.readouterr().out
    assert "dream_mode = propose" in out
    assert "promotion = corroborated" in out


def test_set_string_knob(capsys):
    assert ST.main(["set", "privacy", "walled"]) == 0
    assert sig.load_config()["privacy"] == "walled"


def test_set_bool_and_int_coercion(capsys):
    ST.main(["set", "nudges", "off"])
    ST.main(["set", "forget_idle_dreams", "5"])
    cfg = sig.load_config()
    assert cfg["nudges"] is False and cfg["forget_idle_dreams"] == 5


def test_set_rejects_unknown_key(capsys):
    assert ST.main(["set", "bogus", "x"]) == 2
    assert "unknown key" in capsys.readouterr().err


def test_set_rejects_bad_int(capsys):
    assert ST.main(["set", "forget_idle_dreams", "notanint"]) == 2


def test_reset_restores_defaults(capsys):
    ST.main(["set", "dream_mode", "off"])
    ST.main(["set", "privacy", "walled"])
    assert ST.main(["reset"]) == 0
    cfg = sig.load_config()
    assert cfg["dream_mode"] == "propose" and cfg["privacy"] == "open"
