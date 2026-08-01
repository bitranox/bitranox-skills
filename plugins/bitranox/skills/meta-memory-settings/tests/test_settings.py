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


# ---- enum knobs reject an unknown value instead of storing it -------------------------------

@pytest.mark.parametrize("key,bad", [
    ("dream_mode", "notarealvalue"),
    ("dream_mode", "of"),               # the realistic typo for "off"
    ("privacy", "public"),
    ("promotion", "always"),
    ("mcp_search", "on"),
])
def test_set_refuses_an_unknown_enum_value(capsys, key, bad):
    rc = ST.main(["set", key, bad])
    out = capsys.readouterr()
    assert rc != 0, "an unknown %s value must not be accepted" % key
    assert bad not in sig.load_config().get(key, ""), "the bogus value must not be stored"
    assert key in (out.out + out.err)


def test_set_still_accepts_every_documented_enum_value():
    for key, values in ST.ENUM_CHOICES.items():
        for v in values:
            assert ST.main(["set", key, v]) == 0
            assert sig.load_config()[key] == v


def test_bool_knob_refuses_a_non_boolean_word(capsys):
    rc = ST.main(["set", "nudges", "banana"])
    assert rc != 0                       # silently coercing to False is the bug
    assert sig.load_config()["nudges"] is True


def test_bool_knob_accepts_the_usual_spellings():
    for word, expected in (("true", True), ("1", True), ("on", True),
                           ("false", False), ("0", False), ("off", False)):
        assert ST.main(["set", "nudges", word]) == 0
        assert sig.load_config()["nudges"] is expected
