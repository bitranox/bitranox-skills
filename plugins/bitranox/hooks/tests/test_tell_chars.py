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


# --- extraction line-continuation artifacts (U+2190) -------------------------------------------

LARR = chr(0x2190)
RARR = chr(0x2192)


def test_continuation_flags_a_wrapped_token():
    """The shape that splits a command: ' <-token' with no space after the arrow."""
    hits = TC.find_continuation_lines("wget https://example.com/keyring- %strixie.gpg" % LARR)
    assert len(hits) == 1 and hits[0].startswith("1: ")


def test_continuation_flags_a_lone_marker_line():
    assert TC.find_continuation_lines("a\n%s-\nb" % LARR) == ["2: %s-" % LARR]
    assert TC.find_continuation_lines("a\n%s\nb" % LARR) == ["2: %s" % LARR]


def test_continuation_ignores_prose_where_the_arrow_is_followed_by_a_space():
    """'runs in process.cwd() <- empty parameter' is an annotation, not an artifact."""
    assert TC.find_continuation_lines("runs in cwd() %s empty parameter" % LARR) == []


def test_continuation_ignores_the_allowed_right_arrow():
    assert TC.find_continuation_lines("Datacenter %s Cluster %s Join" % (RARR, RARR)) == []


def test_continuation_looks_INSIDE_fenced_blocks():
    """The whole point: a split command lives in the blind spot find_tell_lines exempts."""
    src = "prose\n```bash\nmv /a/b/ %sc/d\n```\n" % LARR
    assert TC.find_continuation_lines(src) == ["3: mv /a/b/ %sc/d" % LARR]


def test_find_tell_lines_does_NOT_see_it_which_is_why_the_second_scanner_exists():
    """Control: the two scanners must disagree here, or the new one is redundant."""
    src = "prose\n```bash\nmv /a/b/ %sc/d\n```\n" % LARR
    assert TC.find_tell_lines(src) == []
    assert TC.find_continuation_lines(src) != []


def test_continuation_of_empty_and_none_is_empty():
    assert TC.find_continuation_lines("") == [] and TC.find_continuation_lines(None) == []


# ---- the three separators that are tells AND break str.splitlines() ---------------------------

LINE_SEP = chr(0x2028)
PARA_SEP = chr(0x2029)
NEL = chr(0x0085)


def test_a_separator_outside_code_is_a_tell_not_a_line_break():
    """U+2028/U+2029/U+0085 are in RANGES, and str.splitlines() breaks on all three.

    Splitting there hands the scanner two clean lines and the tell is in NEITHER, so the file
    passes while carrying it. One shared splitter that breaks only on real newlines is what makes
    the detector able to see them at all.
    """
    for sep in (LINE_SEP, PARA_SEP, NEL):
        hits = TC.find_tell_lines("prose%smore prose\n" % sep)
        assert hits, "separator %04X is invisible to the scanner" % ord(sep)
        assert hits[0].startswith("1: "), hits


def test_a_separator_does_not_advance_the_reported_line_number():
    hits = TC.find_tell_lines("first\nsecond%stail\n" % LINE_SEP)
    assert [h.split(":")[0] for h in hits] == ["2"], hits


def test_a_separator_inside_a_code_span_is_left_alone_by_both_halves():
    """The detector and the rewriter must agree, and here they did not.

    find_tell_lines split AT the separator, so the span looked like two lines and the tell was in
    neither - clean. transform_outside_code splits with keepends=True, so it KEPT the separator,
    saw an unterminated span, and rewrote through it. A file the hook passes could therefore still
    be rewritten, splitting the span in two.
    """
    src = "text `code%sspan` tail\n" % LINE_SEP
    assert TC.find_tell_lines(src) == []
    assert TC.transform_outside_code(src, lambda s: s.replace(LINE_SEP, "!")) == src


def test_the_shared_splitter_matches_splitlines_on_ordinary_text():
    for src in ("", "a", "a\n", "a\nb", "a\r\nb\r\n", "a\n\nb", "\n"):
        assert TC.split_lines(src) == src.splitlines(), repr(src)
        assert TC.split_lines(src, keepends=True) == src.splitlines(keepends=True), repr(src)
    assert TC.split_lines(None) == []
