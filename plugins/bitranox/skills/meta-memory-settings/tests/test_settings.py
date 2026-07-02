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


def test_set_bool_coercion(capsys):
    ST.main(["set", "nudges", "off"])
    assert sig.load_config()["nudges"] is False


def test_set_rejects_unknown_key(capsys):
    assert ST.main(["set", "bogus", "x"]) == 2
    assert "unknown key" in capsys.readouterr().err


def test_reset_restores_defaults(capsys):
    ST.main(["set", "dream_mode", "off"])
    ST.main(["set", "privacy", "walled"])
    assert ST.main(["reset"]) == 0
    cfg = sig.load_config()
    assert cfg["dream_mode"] == "propose" and cfg["privacy"] == "open"


def test_set_list_knob_json(capsys):
    assert ST.main(["set", "discovery_roots", '["/a", "/b"]']) == 0
    assert sig.load_config()["discovery_roots"] == ["/a", "/b"]


def test_set_list_knob_csv(capsys):
    assert ST.main(["set", "discovery_roots", "/x, /y"]) == 0
    assert sig.load_config()["discovery_roots"] == ["/x", "/y"]


def test_set_track_private_bool(capsys):
    assert ST.main(["set", "track_private", "yes"]) == 0
    assert sig.load_config()["track_private"] is True
