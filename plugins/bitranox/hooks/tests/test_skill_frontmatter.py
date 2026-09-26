"""Tests for skill_frontmatter.py - the ONE reader of a SKILL.md's `name:` and `description:`.

The same value used to be parsed by five readers (the commit gate, the trigger-map builder, the
mirror audit, the listing-budget hook, the Jev router catalogue) with four different rules, so the
gate could lint one
string while the router shipped another. The agreement test at the bottom pins every consumer to
this reader. ASCII only.
"""
import pytest

import build_skill_triggers as B
import classifier as cl
import harness_checks as hc
import repo_gate as RG
import skill_frontmatter as F
import skill_listing_budget as budget

GOOD = "Use when parsing gitignore files, filtering paths, or reaching for pathspec"


def _md(tmp_path, text, name="SKILL.md", bom=False, crlf=False):
    if crlf:
        text = text.replace("\n", "\r\n")
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_reads_a_plain_name_and_description(tmp_path):
    md = _md(tmp_path, "---\nname: demo\ndescription: %s\n---\n\n# demo\n" % GOOD)
    assert F.name(md) == "demo" and F.description(md) == GOOD


def test_a_bom_does_not_hide_the_front_matter(tmp_path):
    """Windows editors write a BOM, and it made both fields read as absent."""
    md = _md(tmp_path, "---\nname: demo\ndescription: %s\n---\n" % GOOD, bom=True)
    assert F.name(md) == "demo" and F.description(md) == GOOD


def test_crlf_line_endings_read_the_same(tmp_path):
    md = _md(tmp_path, "---\nname: demo\ndescription: %s\n  wrapped on\n---\n" % GOOD, crlf=True)
    assert F.name(md) == "demo" and F.description(md) == GOOD + " wrapped on"


def test_an_empty_name_does_not_capture_the_next_line(tmp_path):
    md = _md(tmp_path, "---\nname:\ndescription: %s\n---\n" % GOOD)
    assert F.name(md) is None
    assert F.description(md) == GOOD


def test_an_empty_name_with_trailing_blanks_does_not_capture_the_next_line(tmp_path):
    md = _md(tmp_path, "---\nname:   \t\ndescription: %s\n---\n" % GOOD)
    assert F.name(md) is None


def test_an_empty_description_does_not_capture_the_next_key(tmp_path):
    md = _md(tmp_path, "---\ndescription:\nname: my-skill\n---\n")
    assert F.description(md) is None
    assert F.name(md) == "my-skill"


def test_a_value_starting_on_the_next_indented_line_is_still_read(tmp_path):
    """Control: a plain scalar may begin on an indented continuation line - that is valid YAML
    and must keep reading, not collapse to "absent" with the fix above."""
    md = _md(tmp_path, "---\nname: demo\ndescription:\n  %s\n---\n" % GOOD)
    assert F.description(md) == GOOD


def test_a_following_comment_line_is_not_part_of_the_description(tmp_path):
    """Its words became router keywords and catalog text, and no gate noticed."""
    md = _md(tmp_path, "---\nname: demo\ndescription: %s\n# todo reword before release\n---\n"
             % GOOD)
    assert F.description(md) == GOOD


@pytest.mark.parametrize("key", ["version2: 3", "a.b: c", "x-y_z9: w"])
def test_a_following_key_of_any_shape_ends_the_description(tmp_path, key):
    md = _md(tmp_path, "---\nname: demo\ndescription: %s\n%s\n---\n" % (GOOD, key))
    assert F.description(md) == GOOD


def test_an_indented_continuation_is_joined(tmp_path):
    """Control for the two tests above: the continuation that IS part of the value stays."""
    md = _md(tmp_path, "---\nname: demo\ndescription: Use when\n  wrapped\n\tand tabbed\n---\n")
    assert F.description(md) == "Use when wrapped and tabbed"


def test_a_trailing_inline_comment_on_a_plain_value_is_dropped(tmp_path):
    """YAML: a `#` preceded by whitespace on a plain scalar starts a comment. It used to be read
    as text and leaked into the router's keywords and the catalog."""
    md = _md(tmp_path, "---\nname: demo\ndescription: Use when a # tail\n---\n")
    assert F.description(md) == "Use when a"


def test_an_indented_comment_only_continuation_line_is_dropped(tmp_path):
    """A plain scalar's continuation line that is ONLY a comment once un-indented must not join
    the value at all - unlike the block-scalar case below, where the same line is literal text."""
    md = _md(tmp_path, "---\nname: demo\ndescription: Use when a\n  # not a comment in plain scalar\n"
             "---\n")
    assert F.description(md) == "Use when a"


def test_an_inline_and_an_indented_comment_both_drop_together(tmp_path):
    md = _md(tmp_path, "---\nname: demo-skill\ndescription: Use when rotating widgets "
             "# zebrafrobnicate\n  # quokkaflux\n---\n")
    assert F.description(md) == "Use when rotating widgets"


def test_a_hash_with_no_preceding_whitespace_is_not_a_comment(tmp_path):
    """YAML only starts a comment at `#` preceded by whitespace or at the start of the scalar; a
    hash glued to a word (a C# example, a hashtag) is plain text."""
    md = _md(tmp_path, "---\nname: demo\ndescription: Use when writing C#code\n---\n")
    assert F.description(md) == "Use when writing C#code"


def test_a_hash_inside_a_block_scalar_stays_literal(tmp_path):
    """Control: comments are a PLAIN-scalar rule only - inside `|`/`>` the same line is content."""
    md = _md(tmp_path, "---\nname: demo\ndescription: >-\n  Use when a\n  # literal, not a comment\n"
             "---\n")
    assert F.description(md) == ">- Use when a # literal, not a comment"
    assert F.scalar_text(F.description(md)) == "Use when a # literal, not a comment"


@pytest.mark.parametrize("crlf", [False, True])
@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_a_blank_line_inside_a_value_does_not_end_it(tmp_path, crlf, blank):
    """A blank line inside a block scalar (or between two indented lines of a plain scalar) is
    part of the value in YAML. It ended the value, dropping every paragraph after the first."""
    md = _md(tmp_path, "---\nname: demo\ndescription: >-\n  Use when one.\n%s\n  Also two.\n"
             "---\n" % blank, crlf=crlf)
    assert F.description(md) == ">- Use when one. Also two."
    assert F.scalar_text(F.description(md)) == "Use when one. Also two."


def test_a_blank_line_before_a_column_zero_key_still_ends_the_value(tmp_path):
    """Control: a blank line followed by the next key is the end of the value, not a bridge."""
    md = _md(tmp_path, "---\ndescription: %s\n\nname: demo\n\n---\n" % GOOD)
    assert F.description(md) == GOOD and F.name(md) == "demo"


def test_no_front_matter_and_missing_file_read_as_none(tmp_path):
    md = _md(tmp_path, "# heading only\n")
    assert F.name(md) is None and F.description(md) is None
    assert F.description(tmp_path / "absent.md") is None


def test_undecodable_bytes_do_not_raise(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_bytes(b"---\nname: demo\ndescription: Use when \xff bytes\n---\n")
    assert F.name(path) == "demo" and F.description(path).startswith("Use when")


# ---- the scalar's text, for a consumer that is not the lint ------------------------------------
# `field` returns the value as written, because the gate rejects a quoted or block-scalar
# description by its first character. Third-party skills use both forms, and a consumer that
# offers their text (the Jev roster) needs what YAML means by it.

@pytest.mark.parametrize("raw, want", [
    (GOOD, GOOD),
    ('"Cancel active Ralph Loop"', "Cancel active Ralph Loop"),
    ("'it''s quoted'", "it's quoted"),
    ('"say \\"hi\\""', 'say "hi"'),
    (">- Use when one thing or another.", "Use when one thing or another."),
    ("| literal block", "literal block"),
    (">2- indented block", "indented block"),
    (">", None),
    ('"unbalanced', '"unbalanced'),
    ("> not a quote: x > y", "not a quote: x > y"),
    (None, None),
])
def test_scalar_text_decodes_quotes_and_block_indicators(raw, want):
    assert F.scalar_text(raw) == want


def test_the_raw_field_still_shows_the_form_the_gate_lints():
    block = "\nname: demo\ndescription: >-\n  Use when folded.\n"
    assert F.field(block, "description") == ">- Use when folded."
    assert F.scalar_text(F.field(block, "description")) == "Use when folded."


@pytest.mark.parametrize("text, block, body", [
    ("---\nname: d\n---\nBody.\n", "\nname: d\n", "\nBody.\n"),
    ("\ufeff---\nname: d\n---\nBody.\n", "\nname: d\n", "\nBody.\n"),
    ("# no front matter\n", None, "# no front matter\n"),
    ("---\nname: unclosed\n", "\nname: unclosed\n", ""),
])
def test_split_frontmatter_returns_the_block_and_the_body(text, block, body):
    assert F.split_frontmatter(text) == (block, body)
    assert F.frontmatter_block(text) == block


def test_read_text_decodes_like_the_front_matter_reader(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_bytes(b"\xef\xbb\xbf---\ndescription: \xff\n---\n")
    assert F.read_text(path) == "---\ndescription: \ufffd\n---\n"
    assert F.read_text(tmp_path / "absent.md") is None


# ---- every consumer reads through this one function ------------------------------------------

FIXTURES = {
    "plain": "---\nname: demo\ndescription: %s\n---\n" % GOOD,
    "comment": "---\nname: demo\ndescription: %s\n# todo reword before release\n---\n" % GOOD,
    "digitkey": "---\nname: demo\ndescription: %s\nversion2: tokenleaks intoprose\n---\n" % GOOD,
    "wrapped": "---\nname: demo\ndescription: %s\n  continued here\n---\n" % GOOD,
    "nextline": "---\nname: demo\ndescription:\n  %s\n---\n" % GOOD,
    "empty": "---\ndescription:\nname: demo\n---\n",
}


@pytest.mark.parametrize("case", sorted(FIXTURES))
@pytest.mark.parametrize("bom", [False, True])
def test_the_gate_the_builders_and_the_budget_read_the_same_description(tmp_path, case, bom):
    skills = tmp_path / "skills"
    (skills / "demo").mkdir(parents=True)
    md = _md(skills / "demo", FIXTURES[case], bom=bom)
    want = F.description(md)
    assert hc.frontmatter_description(md) == want
    assert (RG._description(md) or None) == want
    assert budget.read_description(md) == want
    assert cl.load_skill_descriptions(skills).get("demo") == want
    built = B.build(skills).get("demo")
    if want is None:
        assert built is None
    else:
        assert built == B.select(B.distill(want), {t: 1 for t in B.distill(want)})
