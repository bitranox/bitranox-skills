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

# the script now lives in hooks/ - one copy shared by write-humanize-en and -de, so a test in one
# language's skill can no longer silently exercise the other's copy
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
        (EM_DASH, "-"),             # both sides are line edges; mid-line spacing is tested below
        (EN_DASH, "-"),
        (HYPHEN, "-"),
        (NB_HYPHEN, "-"),
        (FIG_DASH, "-"),
        (HORIZ_BAR, "-"),
        (MINUS, "-"),
        # LSQUO, LDQUO, LAQUO and RAQUO are German punctuation and are deliberately absent:
        # `test_german_punctuation_survives_the_strip` asserts the script leaves them alone.
        (RSQUO, "'"),
        (RDQUO, '"'),
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
        + "it" + RSQUO + "s "
        + RDQUO + "curly" + RDQUO
        + " ellipsis" + ELLIPSIS
        + " nbsp" + NBSP + "x"
        + " zwsp" + ZWSP + "y"
    )
    out = mod.normalize(src)
    assert all(ord(ch) < 0x80 for ch in out), repr(out)
    assert out == 'em - dash it\'s "curly" ellipsis... nbsp x zwspy'


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
    # newline="" keeps the \n we wrote as a literal \n. Text mode translates it to CRLF on
    # Windows, which shifts every byte offset and breaks a byte-identical comparison, while
    # the real artifact this stands in for (a Claude transcript, a markdown file) is LF.
    p.write_text(text, encoding="utf-8", newline="")
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
    res = _run(["-"], stdin="q" + RDQUO + "z" + RDQUO + "\n")
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

    monkeypatch.setattr("sys.stdin", io.StringIO("q" + RDQUO + "z" + RDQUO))
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


# ---- code is left alone, matching the tell-sweep hook ---------------------------------------

EM_DASH = chr(0x2014)
CURLY = chr(0x201D) + "quoted" + chr(0x201D)   # both halves must still BE tells


def test_normalize_leaves_an_inline_code_span_untouched():
    out = mod.normalize("prose em%sand `code em%s` end\n" % (EM_DASH, EM_DASH))
    assert out == "prose em - and `code em%s` end\n" % EM_DASH


def test_normalize_leaves_a_fenced_block_untouched():
    src = "before %s\n```\nfenced %s\n```\n" % (CURLY, CURLY)
    out = mod.normalize(src)
    assert "fenced %s" % CURLY in out          # the example survives
    assert '"quoted"' in out                    # the prose above it does not


def test_normalize_still_rewrites_ordinary_prose():
    assert mod.normalize("plain em%sdash\n" % EM_DASH) == "plain em - dash\n"


def test_normalize_agrees_with_the_hook_about_what_is_code():
    """A file the sweep hook passes must survive the script unchanged - that is the whole point.

    One codepoint cannot show this. The em dash alone kept passing while U+2028 inside a span was
    rewritten, because that one also ends a line for `str.splitlines()` - so the pair is only
    honestly tested with a sample from every CLASS in RANGES: dash, space, quote, ellipsis,
    invisible format, line separator, verdict emoji, BOM.
    """
    import sys as _sys, pathlib as _pathlib
    _sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[3] / "hooks"))
    import tell_chars as TC
    classes = {
        "dash": EM_DASH, "space": chr(0x00A0), "quote": chr(0x201C), "ellipsis": chr(0x2026),
        "invisible": chr(0x200B), "line separator": chr(0x2028), "verdict": chr(0x2705),
        "bom": chr(0xFEFF),
    }
    for name, ch in classes.items():
        src = "clean prose here\n```\nfenced %s\n```\nand `inline %s` too\n" % (ch, ch)
        assert TC.find_tell_lines(src) == [], name       # the hook says clean
        assert mod.normalize(src) == src, name           # so the script must not touch it


# ---- em dash: one space per side, and never whitespace at a line edge ------------------------
#
# A SPACED em dash used to leave the doubled-space residue "a  -  b": the original spaces stayed
# and the fixed replacement " - " contributed its own, so every caller tidied it by hand. The
# collapse has to stay local to the dash - a blanket whitespace collapse joins lines, destroys a
# markdown hard line break (two trailing spaces), and fights the table-alignment hook.

TWO_EM = chr(0x2E3A)
THREE_EM = chr(0x2E3B)


@pytest.mark.parametrize("dash", [EM_DASH, TWO_EM, THREE_EM])
@pytest.mark.parametrize(
    "template",
    [
        "a%sb",         # unspaced: the already-correct case, must not gain a second space
        "a %sb",
        "a%s b",
        "a %s b",       # the spaced em dash that produced "a  -  b"
        "a\t%s\tb",
    ],
)
def test_em_dash_yields_exactly_one_space_per_side(dash, template):
    assert mod.normalize(template % dash) == "a - b"


@pytest.mark.parametrize(
    "template, expected",
    [
        ("a  %s  b", "a  -  b"),             # a wider run is padding, not the script's residue
        ("a   %s b", "a   - b"),
        ("a %s   b", "a -   b"),
        ("| x |  %s   |", "| x |  -   |"),   # a padded table cell keeps its width
        ("cmd %s  # aligned comment", "cmd -  # aligned comment"),
    ],
)
def test_padding_wider_than_one_space_beside_the_dash_is_preserved(template, expected):
    # Only the single space that pairs with the emitted one is reused: collapsing a wider run
    # would rewrite whatever it aligned (a table column, a trailing comment).
    src = template % EM_DASH
    out = mod.normalize(src)
    assert out == expected
    assert len(out) == len(src)              # one character in, one character out


def test_em_dash_padded_with_non_breaking_spaces_collapses_too():
    # NBSP becomes a plain space before the dash pass runs, so this real-world form collapses too.
    assert mod.normalize("a" + NBSP + EM_DASH + NBSP + "b") == "a - b"


def test_em_dash_at_end_of_line_neither_joins_the_lines_nor_leaves_a_trailing_space():
    src = "one" + EM_DASH + "\ntwo\n"
    out = mod.normalize(src)
    assert out == "one -\ntwo\n"
    assert out.count("\n") == src.count("\n")


def test_a_dash_alone_on_its_line_does_not_absorb_either_newline():
    src = "a\n" + EM_DASH + "\nb\n"
    out = mod.normalize(src)
    assert out.count("\n") == src.count("\n")
    assert out == "a\n-\nb\n"


def test_em_dash_before_a_markdown_hard_line_break_keeps_both_trailing_spaces():
    src = "text" + EM_DASH + "  \nnext\n"
    out = mod.normalize(src)
    assert out == "text -  \nnext\n"
    # two trailing spaces are a markdown hard break; three would still break but the bytes must
    # not drift, and one would silently drop the break
    assert out.splitlines(keepends=True)[0].endswith("-  \n")


def test_spaced_em_dash_mid_line_keeps_a_trailing_hard_break():
    assert mod.normalize("a " + EM_DASH + " b  \nc\n") == "a - b  \nc\n"


def test_em_dash_after_indentation_keeps_the_indentation():
    # the leading run belongs to the line, not to the dash: eating it would re-nest a list item
    assert mod.normalize("    " + EM_DASH + " item\n") == "    - item\n"


def test_whitespace_only_line_around_the_dash_is_preserved():
    assert mod.normalize("  " + EM_DASH + "  \n") == "  -  \n"


def test_a_markdown_list_item_is_not_altered():
    src = "- item one\n- item two " + EM_DASH + " tail\n"
    assert mod.normalize(src) == "- item one\n- item two - tail\n"


def test_spaced_em_dash_in_a_table_cell_keeps_every_column_width():
    src = (
        "| col | note    |\n"
        "| --- | ------- |\n"
        "| a   | x " + EM_DASH + " y   |\n"
    )
    out = mod.normalize(src)
    assert [len(ln) for ln in out.splitlines()] == [len(ln) for ln in src.splitlines()]
    assert "| a   | x - y   |" in out


def test_spaced_em_dash_inside_an_inline_code_span_survives():
    src = "prose " + EM_DASH + " and `code " + EM_DASH + " span` end\n"
    assert mod.normalize(src) == "prose - and `code " + EM_DASH + " span` end\n"


@pytest.mark.parametrize("dash", [HYPHEN, NB_HYPHEN, FIG_DASH, EN_DASH, HORIZ_BAR, MINUS])
def test_other_dashes_stay_a_bare_hyphen_and_keep_the_original_spacing(dash):
    # only the em-dash family gains spaces; these must not be pulled into that pass
    assert mod.normalize("a" + dash + "b") == "a-b"
    assert mod.normalize("a " + dash + " b") == "a - b"
    assert mod.normalize("a  " + dash + "  b") == "a  -  b"


def test_spaced_em_dash_is_idempotent():
    src = "a " + EM_DASH + " b\nc" + EM_DASH + "\n  " + EM_DASH + "  \nd" + EM_DASH + "  \n"
    once = mod.normalize(src)
    assert mod.normalize(once) == once


def test_cli_second_run_leaves_the_file_byte_identical(tmp_path):
    doc = (
        "a " + EM_DASH + " b\n"
        "\n"
        "| a | b     |\n"
        "| - | ----- |\n"
        "| x | y " + EM_DASH + " z |\n"
    )
    p = _write(tmp_path, "doc.md", doc)
    assert _run([str(p)]).returncode == 0
    first = p.read_bytes()
    assert b"a - b\n" in first
    assert b"| x | y - z |\n" in first
    assert _run([str(p)]).returncode == 0
    assert p.read_bytes() == first
    assert _run(["--check", str(p)]).returncode == 0


# --------------------------------------------------------------------------
# Rewriting a file must not silently change its line endings. open() defaults to
# universal newlines on read and os.linesep on write, so on Windows every file
# this tool touched came back CRLF - in a repo whose gate REQUIRES LF for .py,
# .sh and .json, and whose hooks run this over markdown.
# --------------------------------------------------------------------------


def test_rewriting_preserves_lf_line_endings(tmp_path):
    p = tmp_path / "lf.md"
    p.write_bytes(("a " + EM_DASH + " b\nsecond\n").encode("utf-8"))
    assert _run([str(p)]).returncode == 0
    assert p.read_bytes() == b"a - b\nsecond\n"


def test_rewriting_preserves_crlf_line_endings(tmp_path):
    """A file that arrived CRLF stays CRLF: the job is to strip tells, not to renormalize."""
    p = tmp_path / "crlf.md"
    p.write_bytes(("a " + EM_DASH + " b\r\nsecond\r\n").encode("utf-8"))
    assert _run([str(p)]).returncode == 0
    assert p.read_bytes() == b"a - b\r\nsecond\r\n"


# ---- the strip script may never flatten what the hook now permits ----------------------------
#
# The script calls itself "the exact inverse of the tell-sweep detector". Once German punctuation
# left RANGES, a table entry for it would make the sanctioned repair tool destroy exactly the
# characters the hook allows - and a German page run through it would come back with ASCII quotes
# and no complaint from anything.

GERMAN_PUNCTUATION = [chr(cp) for cp in (0x00AB, 0x00BB, 0x2018, 0x201A, 0x201C, 0x201E, 0x2039, 0x203A)]


def test_german_punctuation_survives_the_strip():
    for ch in GERMAN_PUNCTUATION:
        src = "ein Satz mit %s Zeichen\n" % ch
        assert mod.normalize(src) == src, "U+%04X" % ord(ch)


def test_the_table_rewrites_nothing_the_hook_permits():
    """A wider oracle than the table's own list: every rewritten codepoint must BE a tell.

    Checked against RANGES rather than against a second copy of the table, so a codepoint dropped
    from one side and not the other fails here whichever side moved.
    """
    import sys as _sys, pathlib as _pathlib
    _sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
    import tell_chars as TC
    permitted = [cp for cp in mod.TABLE if not TC._TELL.search(chr(cp))]
    assert permitted == [], ["U+%04X" % cp for cp in permitted]


def test_an_english_curly_apostrophe_is_still_normalized():
    assert mod.normalize("it%ss here\n" % chr(0x2019)) == "it's here\n"


# ---- the shipped skills must not promise a rewrite the script does not do --------------------
#
# Both humanize skills describe this script's coverage in one sentence. That sentence is the only
# thing most readers ever consult about it, and it went false the moment German quotation marks
# left RANGES: it still said the script replaces curly quotes and guillemets, so a German writer
# reading it would believe their correct typography gets flattened. Prose cannot be kept honest by
# review, so the claim is tied to TABLE here.

import re as _re

from pathlib import Path as _Path

SKILLS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "skills")
UML_U = chr(0x00FC)   # the file under test is German; this module stays ASCII

# term named in the sentence -> a codepoint that term would have to cover
CLAIMED_TERMS = {
    "guillemets": 0x00AB,
    "curly quotes": 0x201C,
    "typografische Anf%shrungszeichen" % UML_U: 0x201C,
}

COVERAGE_SENTENCE = {
    "write-humanize-en": (r"It replaces", r"untouched\."),
    "write-humanize-de": (r"Es ersetzt", r"unangetastet\."),
}


def _coverage_sentence(skill):
    start, end = COVERAGE_SENTENCE[skill]
    body = _Path(os.path.join(SKILLS_DIR, skill, "SKILL.md")).read_text(encoding="utf-8")
    m = _re.search(start + r".*?" + end, body, _re.S)
    assert m, "%s: coverage sentence not found - the anchors moved" % skill
    return m.group(0)


@pytest.mark.parametrize("skill", sorted(COVERAGE_SENTENCE))
def test_the_skill_claims_no_rewrite_the_table_does_not_perform(skill):
    sentence = _coverage_sentence(skill)
    broken = [
        term for term, cp in CLAIMED_TERMS.items()
        if term.lower() in sentence.lower() and cp not in mod.TABLE
    ]
    assert broken == [], "%s promises a rewrite the script no longer does: %s" % (skill, broken)


@pytest.mark.parametrize("skill", sorted(COVERAGE_SENTENCE))
def test_the_coverage_sentence_still_names_something_the_table_does(skill):
    """A control: the sentence must not pass by naming nothing at all."""
    sentence = _coverage_sentence(skill).lower()
    assert "ascii" in sentence and ("bom" in sentence or "zero" in sentence or "null" in sentence)


# ---- a line edge is not a code-span edge -----------------------------------------------------
#
# The spacing pass saw a stretch with nothing beyond it and could not tell whether that was the
# edge of an inline-code span (where a space keeps the hyphen off the code) or the edge of the
# LINE, where a space is new indentation or new trailing whitespace.


def test_an_em_dash_at_column_zero_gets_no_leading_space():
    assert mod.normalize("Intro\n%s a quoted aside\n" % EM_DASH) == "Intro\n- a quoted aside\n"


def test_an_em_dash_ending_the_file_gets_no_trailing_space():
    assert mod.normalize("foo %s" % EM_DASH) == "foo -"


def test_an_em_dash_before_crlf_gets_no_trailing_space():
    assert mod.normalize("a %s\r\nb\r\n" % EM_DASH) == "a -\r\nb\r\n"


def test_an_em_dash_at_column_zero_after_crlf_gets_no_leading_space():
    assert mod.normalize("a\r\n%sb\r\n" % EM_DASH) == "a\r\n- b\r\n"


def test_control_an_em_dash_beside_a_code_span_still_gets_its_space():
    assert mod.normalize("`x`%sy\n" % EM_DASH) == "`x` - y\n"
    assert mod.normalize("y%s`x`\n" % EM_DASH) == "y - `x`\n"


def test_control_a_mid_line_and_an_lf_line_end_em_dash_are_unchanged():
    assert mod.normalize("x %s a\n" % EM_DASH) == "x - a\n"
    assert mod.normalize("foo %s\n" % EM_DASH) == "foo -\n"


# ---- a line separator must not manufacture a fence ------------------------------------------


def test_a_separator_before_a_fence_marker_does_not_open_a_block():
    """U+2028 became a newline, and a newline in front of ``` opened a block the original never had,
    so a second run rewrote the example that the first run had treated as code."""
    src = "p%s```\ntext\n```\nexample %s\n```\n" % (LINE_SEP, RDQUO)
    once = mod.normalize(src)
    assert mod.normalize(once) == once
    assert "example %s" % RDQUO in once
    assert TC_find(once) == []


def test_control_a_separator_in_prose_still_becomes_a_newline():
    for sep in (LINE_SEP, PARA_SEP, NEL):
        assert mod.normalize("a%sb\n" % sep) == "a\nb\n"


def test_a_separator_in_a_code_span_or_fence_is_left_alone():
    src = "`a%sb` and\n```\nc%sd\n```\n" % (LINE_SEP, LINE_SEP)
    assert mod.normalize(src) == src


def TC_find(text):
    import tell_chars
    return tell_chars.find_tell_lines(text)


# ---- stdin is UTF-8 whatever the locale says ------------------------------------------------


def test_stdin_mode_reads_and_writes_utf8_under_a_legacy_locale():
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    res = subprocess.run(
        [sys.executable, SCRIPT_PATH, "-"],
        input=("a %s b\r\nc %s\n" % (EM_DASH, RDQUO)).encode("utf-8"),
        capture_output=True, env=env,
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout == b'a - b\r\nc "\n'


def test_stdin_check_mode_under_a_legacy_locale():
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    res = subprocess.run([sys.executable, SCRIPT_PATH, "--check", "-"],
                         input="clean\r\n".encode("utf-8"), capture_output=True, env=env)
    assert res.returncode == 0, res.stderr
