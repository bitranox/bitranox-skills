"""Tests for the meta-memory-settings CLI.

The source is ASCII only; the non-ASCII test data (CJK, umlauts, undecodable bytes) is spelled
as escapes.
"""

import os
import subprocess
import sys

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


# ---- a write that did not happen is never reported as saved -----------------------------------

def _claude_dir_is_a_file(home):
    """Make ~/.claude a plain FILE, so the config's parent dir cannot be created."""
    d = home / ".claude"
    d.rmdir()
    d.write_text("not a dir", encoding="utf-8")


def test_set_reports_a_failed_write_and_exits_1(home, capsys):
    _claude_dir_is_a_file(home)
    rc = ST.main(["set", "dream_mode", "off"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "not saved" in err


def test_reset_reports_a_failed_write_and_exits_1(home, capsys):
    _claude_dir_is_a_file(home)
    assert ST.main(["reset"]) == 1
    assert "not saved" in capsys.readouterr().err


def test_save_config_is_still_best_effort_by_default(home):
    """The hooks' contract: save_config never raises unless the caller asks for strict."""
    _claude_dir_is_a_file(home)
    assert sig.save_config({"dream_mode": "off"})["dream_mode"] == "off"


def test_save_config_strict_raises_on_a_failed_write(home):
    _claude_dir_is_a_file(home)
    with pytest.raises(OSError):
        sig.save_config({"dream_mode": "off"}, strict=True)


# ---- a corrupt config file is refused, never shown as defaults nor overwritten ----------------

CORRUPT = '{"dream_mode":"off","privacy":"walled","nudges":false,}'   # trailing comma


@pytest.mark.parametrize("argv", [["view"], ["set", "promotion", "eager"], ["reset"]])
def test_a_corrupt_config_is_refused_and_left_untouched(home, capsys, argv):
    cfg = home / ".claude" / ".bitranox-memory.json"
    cfg.write_text(CORRUPT, encoding="utf-8")
    rc = ST.main(argv)
    err = capsys.readouterr().err
    assert rc == 2
    assert "not a valid" in err and str(cfg) in err
    assert cfg.read_text(encoding="utf-8") == CORRUPT


def test_a_config_holding_a_json_list_is_refused(home, capsys):
    cfg = home / ".claude" / ".bitranox-memory.json"
    cfg.write_text("[1, 2]", encoding="utf-8")
    assert ST.main(["set", "promotion", "eager"]) == 2
    assert cfg.read_text(encoding="utf-8") == "[1, 2]"


def test_a_valid_config_keeps_the_users_choices_on_set(home, capsys):
    """Control for the corrupt case: the same JSON without the trailing comma."""
    cfg = home / ".claude" / ".bitranox-memory.json"
    cfg.write_text(CORRUPT.replace(",}", "}"), encoding="utf-8")
    assert ST.main(["set", "promotion", "eager"]) == 0
    got = sig.load_config()
    assert (got["dream_mode"], got["privacy"], got["nudges"], got["promotion"]) == \
        ("off", "walled", False, "eager")


def test_a_config_with_a_utf8_bom_is_read(home, capsys):
    """Notepad on Windows writes a BOM; json.loads refuses one, which read as 'corrupt'."""
    cfg = home / ".claude" / ".bitranox-memory.json"
    cfg.write_bytes(b"\xef\xbb\xbf" + b'{"dream_mode": "off"}')
    assert sig.load_config()["dream_mode"] == "off"
    assert ST.main(["view"]) == 0
    assert "dream_mode = off" in capsys.readouterr().out


# ---- a config that is not UTF-8 text is refused like a corrupt one ----------------------------
# A lone byte a UTF-8 decoder rejects raised UnicodeDecodeError out of every verb (a traceback,
# exit 1) where a refusal with exit 2 was promised. load_config reads the same file as defaults,
# so without the refusal a `set` would also have written those defaults over every choice in it.

NOT_UTF8 = [
    b'{"dream_mode":"off","note":"\xff"}',                                  # a lone 0xff byte
    b'{"dream_mode":"off","discovery_roots":["C:\\\\M\xfcller"]}',          # cp1252 u-umlaut
    b"\xff\xfe" + '{"dream_mode":"off"}'.encode("utf-16-le"),               # PowerShell UTF-16
]


@pytest.mark.parametrize("raw", NOT_UTF8)
@pytest.mark.parametrize("argv", [["view"], ["set", "promotion", "eager"], ["reset"]])
def test_a_non_utf8_config_is_refused_with_exit_2_and_left_untouched(home, capsys, argv, raw):
    cfg = home / ".claude" / ".bitranox-memory.json"
    cfg.write_bytes(raw)
    rc = ST.main(argv)
    err = capsys.readouterr().err
    assert rc == 2
    assert str(cfg) in err and "UTF-8" in err
    assert cfg.read_bytes() == raw


def test_a_non_utf8_config_gives_no_traceback_from_the_cli(home):
    """The refusal reaches the user as one line, not as a UnicodeDecodeError traceback."""
    cfg = home / ".claude" / ".bitranox-memory.json"
    cfg.write_bytes(NOT_UTF8[0])
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), PYTHONUTF8="1")
    r = subprocess.run([sys.executable, str(ST.__file__), "view"], env=env,
                       capture_output=True, encoding="utf-8", errors="replace")
    assert r.returncode == 2, r.stderr
    assert "Traceback" not in r.stderr and str(cfg) in r.stderr


def test_the_hooks_still_read_a_non_utf8_config_as_the_defaults_without_raising(home):
    """The hook side of the same file stays fail-open and silent: only the CLI refuses."""
    (home / ".claude" / ".bitranox-memory.json").write_bytes(NOT_UTF8[0])
    assert sig.load_config()["dream_mode"] == "propose"


def test_a_utf8_config_holding_non_ascii_text_is_still_read(home, capsys):
    """Control for the refusal: real UTF-8 (with a BOM and a non-ASCII path) passes."""
    cfg = home / ".claude" / ".bitranox-memory.json"
    cfg.write_bytes(b"\xef\xbb\xbf" + '{"dream_mode":"off","discovery_roots":["/data/M\u00fcller"]}'
                    .encode("utf-8"))
    assert ST.main(["set", "promotion", "eager"]) == 0
    got = sig.load_config()
    assert (got["dream_mode"], got["promotion"], got["discovery_roots"]) == \
        ("off", "eager", ["/data/M\u00fcller"])


# ---- leftover arguments are refused, never silently ignored ------------------------------------

@pytest.mark.parametrize("argv", [
    ["reset", "--dry-run"],
    ["view", "extra"],
    ["set", "classifier_model", "jev", "2025"],
    ["set", "dream_mode"],
    ["set"],
    ["frobnicate"],
])
def test_wrong_argument_count_is_refused_with_exit_2(home, capsys, argv):
    ST.main(["set", "dream_mode", "off"])
    capsys.readouterr()
    assert ST.main(argv) == 2
    assert "usage" in capsys.readouterr().err
    assert sig.load_config()["dream_mode"] == "off", "a refused command must not write"


# ---- int knobs are bounded ---------------------------------------------------------------------

@pytest.mark.parametrize("key,bad", [
    ("context_handover_pct", "-5"),
    ("context_handover_pct", "0"),
    ("context_handover_pct", "101"),
    ("context_window", "-1"),
    ("context_window", "500"),
    ("context_handover_cap", "0"),
    ("context_handover_cap", "-3"),
    ("context_handover_pct", "abc"),
])
def test_an_out_of_range_int_knob_is_refused(home, capsys, key, bad):
    before = sig.load_config()[key]
    assert ST.main(["set", key, bad]) == 2
    assert key in capsys.readouterr().err
    assert sig.load_config()[key] == before


@pytest.mark.parametrize("key,good,expected", [
    ("context_handover_pct", "1", 1),
    ("context_handover_pct", "100", 100),
    ("context_window", "0", 0),
    ("context_window", "1000", 1000),
    ("context_window", "1000000", 1000000),
    ("context_handover_cap", "1", 1),
])
def test_an_in_range_int_knob_is_stored(home, capsys, key, good, expected):
    assert ST.main(["set", key, good]) == 0
    assert sig.load_config()[key] == expected


# ---- list knobs hold only non-empty, rooted strings --------------------------------------------

@pytest.mark.parametrize("bad", ['[null, "/a"]', '[5]', '[""]', '["  "]', '["relative/dir"]',
                                 '{"a": 1}', "[not json", "relative, /b"])
def test_a_bad_discovery_roots_value_is_refused(home, capsys, bad):
    assert ST.main(["set", "discovery_roots", bad]) == 2
    assert "discovery_roots" in capsys.readouterr().err
    assert sig.load_config()["discovery_roots"] == []


def test_discovery_roots_csv_drops_empty_entries(home, capsys):
    assert ST.main(["set", "discovery_roots", "/a,,/b"]) == 0
    assert sig.load_config()["discovery_roots"] == ["/a", "/b"]


def test_discovery_roots_accepts_a_home_relative_root(home, capsys):
    assert ST.main(["set", "discovery_roots", '["~/projects"]']) == 0
    assert sig.load_config()["discovery_roots"] == ["~/projects"]


# ---- a console that cannot encode a value does not crash after the write ----------------------

def _run_cli(home, *args):
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    env.update(HOME=str(home), USERPROFILE=str(home), PYTHONIOENCODING="cp1252")
    return subprocess.run([sys.executable, str(ST.__file__), *args], env=env,
                          capture_output=True, encoding="utf-8", errors="replace")


def test_a_cp1252_console_survives_a_value_it_cannot_encode(home):
    r = _run_cli(home, "set", "discovery_roots", "/data/\u65e5\u672c")
    assert r.returncode == 0, r.stderr
    assert "discovery_roots" in r.stdout
    assert "UnicodeEncodeError" not in r.stderr
    r = _run_cli(home, "view")
    assert r.returncode == 0, r.stderr
