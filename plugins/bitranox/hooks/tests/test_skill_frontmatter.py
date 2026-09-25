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


def test_no_front_matter_and_missing_file_read_as_none(tmp_path):
    md = _md(tmp_path, "# heading only\n")
    assert F.name(md) is None and F.description(md) is None
    assert F.description(tmp_path / "absent.md") is None


def test_undecodable_bytes_do_not_raise(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_bytes(b"---\nname: demo\ndescription: Use when \xff bytes\n---\n")
    assert F.name(path) == "demo" and F.description(path).startswith("Use when")


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
