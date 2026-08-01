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


# ---- transform_outside_code: the primitive the strip script and the hook must share -----------

EM = chr(0x2014)


def _to_dash(s):
    return s.replace(EM, "-")


def test_transform_leaves_an_inline_code_span_untouched():
    out = TC.transform_outside_code("prose em%sdash and `code em%sdash` here\n" % (EM, EM), _to_dash)
    assert out == "prose em-dash and `code em%sdash` here\n" % EM


def test_transform_leaves_a_fenced_block_untouched():
    src = "before em%s\n```\nfenced em%s\n```\nafter em%s\n" % (EM, EM, EM)
    out = TC.transform_outside_code(src, _to_dash)
    assert out == "before em-\n```\nfenced em%s\n```\nafter em-\n" % EM


def test_transform_handles_tilde_fences():
    src = "~~~\ntilde em%s\n~~~\nprose em%s\n" % (EM, EM)
    out = TC.transform_outside_code(src, _to_dash)
    assert "tilde em%s" % EM in out and "prose em-" in out


def test_transform_handles_several_spans_on_one_line():
    src = "a em%s `x em%s` b em%s `y em%s` c em%s\n" % (EM, EM, EM, EM, EM)
    out = TC.transform_outside_code(src, _to_dash)
    assert out.count(EM) == 2                      # only the two spans keep it
    assert "`x em%s`" % EM in out and "`y em%s`" % EM in out


def test_transform_preserves_text_with_no_trailing_newline():
    assert TC.transform_outside_code("em%s" % EM, _to_dash) == "em-"


def test_transform_of_empty_and_none_is_empty():
    assert TC.transform_outside_code("", _to_dash) == ""
    assert TC.transform_outside_code(None, _to_dash) == ""
