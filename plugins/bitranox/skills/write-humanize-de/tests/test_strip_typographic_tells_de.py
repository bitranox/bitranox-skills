"""Tests for strip_typographic_tells.py.

All literal source here is pure ASCII. Non-ASCII test inputs are built from
code points with chr(0xXXXX), never pasted as glyphs, because a write-blocking
hook rejects literal non-ASCII characters in the test file itself.
"""

import os
import subprocess
import sys

import pytest

import strip_typographic_tells as mod

SCRIPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
SCRIPT_PATH = os.path.join(SCRIPT_DIR, "strip_typographic_tells.py")

# Code points used throughout the tests.
NBSP = chr(0x00A0)
NNBSP = chr(0x202F)
SHY = chr(0x00AD)            # soft hyphen (removable)
ZWSP = chr(0x200B)
ZWNJ = chr(0x200C)
ZWJ = chr(0x200D)
BOM = chr(0xFEFF)
WORD_JOINER = chr(0x2060)
NEL = chr(0x0085)            # next line -> newline
LINE_SEP = chr(0x2028)
PARA_SEP = chr(0x2029)
HYPHEN = chr(0x2010)
NB_HYPHEN = chr(0x2011)
FIG_DASH = chr(0x2012)
EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)
HORIZ_BAR = chr(0x2015)
MINUS = chr(0x2212)
LSQUO = chr(0x2018)
RSQUO = chr(0x2019)
LDQUO = chr(0x201C)
RDQUO = chr(0x201D)
LAQUO = chr(0x00AB)
RAQUO = chr(0x00BB)
ONE_DOT = chr(0x2024)
TWO_DOT = chr(0x2025)
ELLIPSIS = chr(0x2026)

# Symbols the spec deliberately leaves untouched.
ARROW = chr(0x2192)
CHECK = chr(0x2713)
MULTIPLY = chr(0x00D7)
BULLET = chr(0x2022)
GTE = chr(0x2265)
LTE = chr(0x2264)
NE = chr(0x2260)


# ---- normalize(): the public function --------------------------------------

def test_normalize_returns_str():
    assert isinstance(mod.normalize("plain"), str)


@pytest.mark.parametrize(
    "src, expected",
    [
        (EM_DASH, " - "),
        (EN_DASH, "-"),
        (HYPHEN, "-"),
        (NB_HYPHEN, "-"),
        (FIG_DASH, "-"),
        (HORIZ_BAR, "-"),
        (MINUS, "-"),
        (LSQUO, "'"),
        (RSQUO, "'"),
        (LDQUO, '"'),
        (RDQUO, '"'),
        (LAQUO, '"'),
        (RAQUO, '"'),
        (ONE_DOT, "."),
        (TWO_DOT, ".."),
        (ELLIPSIS, "..."),
        (NBSP, " "),
        (NNBSP, " "),
        (ZWSP, ""),
        (ZWNJ, ""),
        (ZWJ, ""),
        (BOM, ""),
        (SHY, ""),
        (WORD_JOINER, ""),
        (NEL, "\n"),
        (LINE_SEP, "\n"),
        (PARA_SEP, "\n"),
    ],
)
def test_each_tell_maps_to_ascii(src, expected):
    assert mod.normalize(src) == expected


def test_combined_input_becomes_pure_ascii():
    src = (
        BOM
        + "em" + EM_DASH + "dash "
        + LDQUO + "curly" + RDQUO
        + " ellipsis" + ELLIPSIS
        + " nbsp" + NBSP + "x"
        + " zwsp" + ZWSP + "y"
    )
    out = mod.normalize(src)
    assert all(ord(ch) < 0x80 for ch in out), repr(out)
    assert out == 'em - dash "curly" ellipsis... nbsp x zwspy'


def test_idempotent():
    src = (
        EM_DASH + EN_DASH + LDQUO + RDQUO + LSQUO + RSQUO
        + ELLIPSIS + NBSP + ZWSP + BOM + "text"
    )
    once = mod.normalize(src)
    twice = mod.normalize(once)
    assert once == twice


def test_plain_ascii_untouched():
    src = "Plain ASCII: a-b, \"quote\", 'apostrophe', dots... and -- dashes.\n"
    assert mod.normalize(src) == src


@pytest.mark.parametrize("sym", [ARROW, CHECK, MULTIPLY, BULLET, GTE, LTE, NE])
def test_allowed_symbols_preserved(sym):
    # Per the script's spec these intentional symbols stay as-is.
    assert mod.normalize("x" + sym + "y") == "x" + sym + "y"


def test_empty_string():
    assert mod.normalize("") == ""


# ---- CLI behaviour: --check ------------------------------------------------

def _run(args, stdin=None):
    return subprocess.run(
        [sys.executable, SCRIPT_PATH] + args,
        input=stdin,
        capture_output=True,
        text=True,
    )


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_check_nonzero_when_tells_present(tmp_path):
    p = _write(tmp_path, "dirty.txt", "a" + EM_DASH + "b\n")
    res = _run(["--check", str(p)])
    assert res.returncode == 1
    # --check must not modify the file.
    assert p.read_text(encoding="utf-8") == "a" + EM_DASH + "b\n"


def test_check_zero_when_clean(tmp_path):
    p = _write(tmp_path, "clean.txt", "all ascii here\n")
    res = _run(["--check", str(p)])
    assert res.returncode == 0


def test_inplace_rewrite(tmp_path):
    p = _write(tmp_path, "f.txt", "x" + ELLIPSIS + NBSP + "y\n")
    res = _run([str(p)])
    assert res.returncode == 0
    assert p.read_text(encoding="utf-8") == "x... y\n"
    # After rewrite, --check passes.
    assert _run(["--check", str(p)]).returncode == 0


def test_clean_file_left_byte_identical(tmp_path):
    text = "nothing to change\n"
    p = _write(tmp_path, "ok.txt", text)
    before = p.read_bytes()
    assert _run([str(p)]).returncode == 0
    assert p.read_bytes() == before


def test_stdin_mode_writes_normalized_stdout():
    res = _run(["-"], stdin="q" + LDQUO + "z" + RDQUO + "\n")
    assert res.returncode == 0
    assert res.stdout == 'q"z"\n'


def test_stdin_check_nonzero(tmp_path):
    res = _run(["--check", "-"], stdin="a" + EM_DASH + "b")
    assert res.returncode == 1


def test_multiple_files(tmp_path):
    a = _write(tmp_path, "a.txt", "a" + EM_DASH + "b")
    b = _write(tmp_path, "b.txt", "c" + ELLIPSIS + "d")
    res = _run([str(a), str(b)])
    assert res.returncode == 0
    assert a.read_text(encoding="utf-8") == "a - b"
    assert b.read_text(encoding="utf-8") == "c...d"


# ---- _main(): in-process, for direct coverage of the CLI dispatcher --------

def test_main_inplace(tmp_path):
    p = _write(tmp_path, "m.txt", "a" + EM_DASH + "b")
    rc = mod._main(["prog", str(p)])
    assert rc == 0
    assert p.read_text(encoding="utf-8") == "a - b"


def test_main_check_returns_one(tmp_path):
    p = _write(tmp_path, "m.txt", "a" + EM_DASH + "b")
    assert mod._main(["prog", "--check", str(p)]) == 1
    # unchanged by --check
    assert p.read_text(encoding="utf-8") == "a" + EM_DASH + "b"


def test_main_check_clean_returns_zero(tmp_path):
    p = _write(tmp_path, "m.txt", "clean ascii")
    assert mod._main(["prog", "--check", str(p)]) == 0


def test_main_stdin_normalizes(monkeypatch, capsys):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("q" + LDQUO + "z" + RDQUO))
    rc = mod._main(["prog"])
    assert rc == 0
    assert capsys.readouterr().out == 'q"z"'


def test_main_stdin_dash_normalizes(monkeypatch, capsys):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("x" + ELLIPSIS))
    rc = mod._main(["prog", "-"])
    assert rc == 0
    assert capsys.readouterr().out == "x..."


def test_main_stdin_check_returns_one(monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("a" + EM_DASH + "b"))
    assert mod._main(["prog", "--check"]) == 1


def test_main_stdin_check_clean_returns_zero(monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("clean"))
    assert mod._main(["prog", "--check"]) == 0


def test_verdict_emoji_normalized_to_ascii_markers():
    heavy_check, cross, warn, sel = chr(0x2705), chr(0x274C), chr(0x26A0), chr(0xFE0F)
    src = "%s done %s broken %s%s risky" % (heavy_check, cross, warn, sel)
    assert mod.normalize(src) == "OK done NO broken WARN risky"
    plain_check = chr(0x2713)
    assert mod.normalize("keep %s and ->" % plain_check) == "keep %s and ->" % plain_check
