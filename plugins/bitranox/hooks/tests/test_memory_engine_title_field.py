"""Tests for the body frontmatter `title:` - a fact's title kept as data beside its pointer line.

The title lives in the always-loaded pointer line `- [Title](mem:slug) - hook`, and otherwise
nowhere. Kept in the body's frontmatter as well, a pointer line can be rebuilt from the body
alone: every write through the engine copies the title there and keeps it equal to the pointer,
and `heal --backfill-titles` fills it into bodies written before. Pointer lines are unchanged by
all of this. All content ASCII.
"""

import os
from pathlib import Path

import pytest

import memory_engine as E
import self_improve_signals as sig
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
    _, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Use the jig", "When counting, use the jig.", body="B")
    text = (Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "- [Use the jig](mem:%s) - When counting, use the jig.\n" % slug in text


# ---- the back-fill: bodies written before titles were kept ---------------------------------

def _pre_title_fact(level, title, slug, extra=""):
    """A fact as every engine before this change left it: written through the engine, then its
    body reset to the frame those engines wrote, which has no `title:` (or `extra` in its place)."""
    E.add_or_update_entry(level, title, "When x, do y.", body="P.", slug=slug, type_="feedback")
    anchor = E._anchor(level)
    us.body_path(anchor, slug).write_text(
        "---\nname: %s\ndescription: When x, do y.\n%smetadata:\n  type: feedback\n---\n\nP.\n"
        % (slug, extra), encoding="utf-8")
    return us.body_path(anchor, slug)


def test_backfill_copies_the_pointer_title_into_a_body_without_one(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    _pre_title_fact(proj, "Old fact title", "old-fact")
    assert E.main(["heal", "--proj", proj, "--backfill-titles"]) == 0
    assert "back-filled 1 title(s)" in capsys.readouterr().out
    assert E._body_title(_body(anchor, "old-fact")) == "Old fact title"
    assert _body(anchor, "old-fact").endswith("---\n\nP.\n")


def test_backfill_never_rewrites_a_body_that_already_has_a_title(tmp_path):
    _, proj = _tree(tmp_path)
    path = _pre_title_fact(proj, "A different pointer title", "kept-fact",
                           extra="title: Its own title\n")
    os.utime(path, (1_000_000, 1_000_000))
    before = path.read_bytes()
    rep = E.backfill_titles(proj)
    assert rep["filled"] == [] and rep["kept"] == 1
    assert path.read_bytes() == before and path.stat().st_mtime == 1_000_000


def test_backfill_covers_every_level_of_the_tree_not_only_the_chain(tmp_path):
    anchor, proj = _tree(tmp_path)
    sibling = Path(anchor) / "sibling"
    sibling.mkdir()
    (sibling / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    _pre_title_fact(str(sibling), "Sibling fact", "sib-fact")
    assert E.backfill_titles(proj)["filled"] == ["sib-fact"]


def test_backfill_leaves_an_unframed_body_and_reports_a_missing_one(tmp_path):
    anchor, proj = _tree(tmp_path)
    bare = _pre_title_fact(proj, "Bare", "bare")
    bare.write_text("just prose\n", encoding="utf-8")
    _pre_title_fact(proj, "Gone", "gone").unlink()
    rep = E.backfill_titles(proj)
    assert rep["unframed"] == ["bare"] and rep["missing"] == ["gone"]
    assert _body(anchor, "bare") == "just prose\n"


def test_plain_heal_still_never_opens_a_body(tmp_path):
    """SessionStart runs `heal` on every start; the back-fill must not ride along with it."""
    _, proj = _tree(tmp_path)
    path = _pre_title_fact(proj, "Old fact title", "old-fact")
    before = path.read_bytes()
    E.heal(proj)
    assert path.read_bytes() == before


def test_backfill_is_refused_under_memory_writes_off(tmp_path, monkeypatch, capsys):
    anchor, proj = _tree(tmp_path)
    _pre_title_fact(proj, "Old fact title", "old-fact")
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    assert E.main(["heal", "--proj", proj, "--backfill-titles"]) == 2
    capsys.readouterr()
    # The CLI refuses every `heal` before parsing, so call the function too: it refuses on its own.
    with pytest.raises(sig.MemoryWritesOff):
        E.backfill_titles(proj)
    assert E._body_title(_body(anchor, "old-fact")) == ""


def test_backfill_reports_a_pointer_with_no_title_apart_from_an_unframed_body(tmp_path, capsys):
    """An empty link text gives nothing to copy; the body is framed, so 'no frontmatter' is false."""
    _, proj = _tree(tmp_path)
    path = _pre_title_fact(proj, "Untitled", "untitled")
    local = Path(proj) / "CLAUDE.local.md"
    text = local.read_text(encoding="utf-8")
    assert text.count("- [Untitled](mem:untitled)") == 1
    local.write_text(text.replace("- [Untitled](mem:untitled)", "- [](mem:untitled)"),
                     encoding="utf-8")
    before = path.read_bytes()
    rep = E.backfill_titles(proj)
    assert rep["unframed"] == [] and rep["untitled"] == ["untitled"] and rep["filled"] == []
    assert path.read_bytes() == before
    assert E.main(["heal", "--proj", proj, "--backfill-titles"]) == 0
    out = capsys.readouterr().out
    assert "pointer has no title to copy, body left as it is: untitled" in out
    assert "no frontmatter" not in out


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0,
                    reason="POSIX permission bits; root reads through them")
def test_backfill_refuses_when_the_bodies_cannot_be_reached(tmp_path, capsys):
    """A facts dir that can be LISTED but not SEARCHED (r without x): the tree walk still lists it,
    while every body stat fails EACCES - which `Path.is_file()` answers False for, so a pre-check
    reported every body missing, back-filled 0 and exited 0 over a tree it never read. Mode 000
    would not show it: the walk itself cannot list the dir and raises first."""
    anchor, proj = _tree(tmp_path)
    _pre_title_fact(proj, "Old fact title", "old-fact")
    facts = us.body_path(anchor, "old-fact").parent
    facts.chmod(0o444)
    try:
        with pytest.raises(E.TreeWalkError):
            E.backfill_titles(proj)
        assert E.main(["heal", "--proj", proj, "--backfill-titles"]) == 2
        assert "missing central body" not in capsys.readouterr().out
    finally:
        facts.chmod(0o755)
    assert E._body_title(_body(anchor, "old-fact")) == ""
