"""Tests for tell_chars.py (shared tell codepoints + scanner). All source ASCII; tells via chr()."""

import tell_chars as TC

EM_DASH = chr(0x2014)
NBSP = chr(0x00A0)
CURLY_OPEN = chr(0x201C)
ARROW = chr(0x2192)   # allowed on purpose, must NOT trip


def test_clean_text_no_hits():
    assert TC.find_tell_lines("Plain ASCII, no tells.\nSecond line -.\n") == []


def test_em_dash_and_nbsp_caught():
    assert len(TC.find_tell_lines("a real %s dash\nand a%sNBSP\n" % (EM_DASH, NBSP))) == 2


def test_curly_quote_caught():
    assert TC.find_tell_lines("He said %shi\n" % CURLY_OPEN)[0].startswith("1: ")


def test_inline_code_span_ignored():
    assert TC.find_tell_lines("use `%s` only in code\n" % EM_DASH) == []


def test_fenced_block_ignored():
    assert TC.find_tell_lines("```\n%s\n```\n" % EM_DASH) == []


def test_allowed_symbols_not_flagged():
    assert TC.find_tell_lines("a %s b, ok\n" % ARROW) == []


def test_empty_and_none_safe():
    assert TC.find_tell_lines("") == [] and TC.find_tell_lines(None) == []


def test_ranges_are_canonical_ascii_source():
    # the module must stay pure ASCII (codepoints as hex), and cover the key tells
    import pathlib
    src = pathlib.Path(TC.__file__).read_text(encoding="utf-8")
    assert all(ord(c) < 128 for c in src)
    assert TC._TELL.search(EM_DASH) and not TC._TELL.search(ARROW)


def test_verdict_emoji_flagged_plain_check_allowed():
    heavy_check, cross, warn, sel = chr(0x2705), chr(0x274C), chr(0x26A0), chr(0xFE0F)
    plain_check = chr(0x2713)
    assert TC.find_tell_lines("verdict: %s pass\n" % heavy_check)
    assert TC.find_tell_lines("verdict: %s fail\n" % cross)
    assert TC.find_tell_lines("note: %s%s risky\n" % (warn, sel))
    assert TC.find_tell_lines("verdict: %s pass\n" % plain_check) == []
