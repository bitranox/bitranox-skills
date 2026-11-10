"""Tests for the body frontmatter `title:` - a fact's title kept as data beside its pointer line.

The title lives in the always-loaded pointer line `- [Title](mem:slug) - hook`, and otherwise
nowhere. Kept in the body's frontmatter as well, a pointer line can be rebuilt from the body
alone: every write through the engine copies the title there and keeps it equal to the pointer,
and `heal --backfill-titles` fills it into bodies written before. Pointer lines are unchanged by
all of this. All content ASCII.
"""

from pathlib import Path

import pytest

import memory_engine as E
import uuid_store as us


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path):
    """anchor -> proj, each a CLAUDE.md-bearing rung; central store at the anchor."""
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return str(anchor), str(proj)


def _body(anchor, slug):
    return us.body_path(anchor, slug).read_text(encoding="utf-8")


def _pointer_title(level, slug):
    text = (Path(level) / "CLAUDE.local.md").read_text(encoding="utf-8")
    return next(p.title for p in us.parse_pointer_index(text)[1] if p.slug == slug)


# ---- every write keeps the body's title equal to the pointer's ------------------------------

def test_add_writes_the_title_into_the_frontmatter_after_the_description(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Use the jig", "When counting, use the jig.", body="B")
    body = _body(anchor, slug)
    assert body.startswith("---\nname: %s\ndescription: When counting, use the jig.\n"
                           "title: Use the jig\nmetadata:\n" % slug), body
    assert _pointer_title(proj, slug) == "Use the jig"


def test_an_update_with_a_new_title_rewrites_the_body_title(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Old title", "When x, do y.", body="B")
    E.add_or_update_entry(proj, "New title", "When x, do y.", slug=slug)
    assert E._body_title(_body(anchor, slug)) == "New title"


def test_an_amend_that_passes_no_title_keeps_it(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Iron rule", "When x, do y.", body="B", pin=True)
    assert E.main(["amend-pinned", "--proj", proj, "--slug", slug, "--hook", "When x, do z."]) == 0
    capsys.readouterr()
    assert E._body_title(_body(anchor, slug)) == "Iron rule"


def test_a_body_handed_back_with_a_stale_title_takes_the_pointer_title(tmp_path):
    """A body read with `show --body` before a retitle carries the old `title:`; writing it back
    must not resurrect it, as the description already does not."""
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Old title", "When x, do y.", body="B")
    stale = _body(anchor, slug)
    E.add_or_update_entry(proj, "New title", "When x, do y.", body=stale, slug=slug)
    assert E._body_title(_body(anchor, slug)) == "New title"


def test_a_title_with_a_backslash_and_a_colon_is_stored_literally(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, r"Paths: C:\temp\x", "When x, do y.", body="B",
                                 slug="paths-fact")
    assert E._body_title(_body(anchor, slug)) == r"Paths: C:\temp\x"


def test_a_retitle_changes_the_body_title_and_nothing_else_in_the_body(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Stale title", "When x, do y.", body="the body")
    before = _body(anchor, slug)
    assert E.retitle_entry(proj, slug, "Accurate title")["retitled"] is True
    after = _body(anchor, slug)
    assert E._body_title(after) == "Accurate title"
    assert after == before.replace("title: Stale title", "title: Accurate title")


def test_a_retitle_of_a_fact_whose_body_is_missing_creates_no_body_file(tmp_path):
    """A dangling pointer reads as an empty body; the retitle must leave it dangling. Writing the
    unchanged empty text back created a one-newline body file, which the empty-body refusal in
    `add` (keyed on the file existing) then took for a stored fact."""
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Old title", "When x, do y.", body="B")
    us.body_path(anchor, slug).unlink()
    assert E.retitle_entry(proj, slug, "New title")["retitled"] is True
    assert not us.body_path(anchor, slug).exists()


def test_a_move_leaves_the_body_and_its_title_byte_identical(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Moving fact", "When x, do y.", body="B")
    before = us.body_path(anchor, slug).read_bytes()
    assert E.move_entry(proj, anchor, slug)["moved"] is True
    assert us.body_path(anchor, slug).read_bytes() == before
    assert E._body_title(before.decode("utf-8")) == "Moving fact"


def test_the_pointer_line_is_unchanged_by_the_title_field(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Use the jig", "When counting, use the jig.", body="B")
    text = (Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "- [Use the jig](mem:%s) - When counting, use the jig.\n" % slug in text
