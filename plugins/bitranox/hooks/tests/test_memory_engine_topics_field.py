"""Tests for the body frontmatter `topics:` line - the topics a fact is bound to, kept as data.

A fact with topics is read only where its topics are; the list lives in the body's frontmatter
and changes only through `set-topics`. `topics: []` means tagged and bound to no topic; no line
means never tagged. An ordinary write to the fact keeps the stored line. All content ASCII.
"""

from pathlib import Path

import pytest

import memory_engine as E
import uuid_store as us

HOOK = "When a fact carries topics, keep them through every ordinary write."
FRAME = "---\nname: s\ndescription: d\ntitle: T\nmetadata:\n  type: feedback\n---\n\nprose\n"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path):
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return str(anchor), str(proj)


def _stored(anchor, slug):
    return us.body_path(anchor, slug).read_text(encoding="utf-8")


def test_body_topics_tells_never_tagged_from_bound_to_none():
    assert E._body_topics(FRAME) is None
    assert E._body_topics(E._with_topics(FRAME, ())) == ()
    assert E._body_topics(E._with_topics(FRAME, ("uv", "python"))) == ("python", "uv")


def test_with_topics_adds_the_line_after_the_title_and_touches_nothing_else():
    tagged = E._with_topics(FRAME, ("python",))
    assert tagged.split("\n")[3:5] == ["title: T", "topics: [python]"]
    assert tagged.replace("topics: [python]\n", "") == FRAME


def test_with_topics_replaces_in_place_and_none_removes_the_line():
    tagged = E._with_topics(E._with_topics(FRAME, ("python",)), ("rust",))
    assert tagged.count("topics:") == 1 and "topics: [rust]" in tagged
    assert E._with_topics(tagged, None) == FRAME


def test_with_topics_falls_back_to_description_then_name_when_there_is_no_title():
    no_title = FRAME.replace("title: T\n", "")
    assert E._with_topics(no_title, ("a",)).split("\n")[2:4] == ["description: d", "topics: [a]"]
    bare = "---\nname: s\n---\n\nprose\n"
    assert E._with_topics(bare, ("a",)).split("\n")[1:3] == ["name: s", "topics: [a]"]


def test_a_topics_line_in_the_prose_or_an_unframed_body_is_not_the_field():
    assert E._body_topics("topics: [python]\n\nprose") is None
    assert E._body_topics(FRAME + "topics: [python]\n") is None
    assert E._with_topics("just prose", ("a",)) == "just prose"


def test_a_line_that_is_no_topic_list_reads_as_never_tagged():
    assert E._body_topics(FRAME.replace("title: T\n", "title: T\ntopics: [Not A Tag]\n")) is None


def test_an_update_with_an_unframed_body_keeps_the_stored_topics(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, title="T", hook=HOOK, body="first", type_="feedback")
    us.put_body(anchor, slug, E._with_topics(_stored(anchor, slug), ("python",)))
    E.add_or_update_entry(proj, title="T", hook=HOOK, body="second, unframed", slug=slug)
    stored = _stored(anchor, slug)
    assert "second, unframed" in stored and E._body_topics(stored) == ("python",)


def test_an_update_whose_framed_body_carries_other_topics_keeps_the_stored_ones(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, title="T", hook=HOOK, body="first", type_="feedback")
    us.put_body(anchor, slug, E._with_topics(_stored(anchor, slug), ("python",)))
    edited = E._with_topics(_stored(anchor, slug), ("rust",)).replace("first", "edited")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=edited, slug=slug)
    stored = _stored(anchor, slug)
    assert "edited" in stored and E._body_topics(stored) == ("python",)


def test_an_update_of_a_fact_never_tagged_does_not_gain_a_topics_line(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, title="T", hook=HOOK, body="first", type_="feedback")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body="second", slug=slug)
    assert "topics:" not in _stored(anchor, slug)


@pytest.mark.parametrize("raw", ["topics: [Python]", "topics: [a b]", "topics: python, Rust"])
def test_a_prose_update_keeps_a_stored_topics_line_that_does_not_parse_verbatim(tmp_path, raw):
    # A line no parser accepts is still the author's data: an ordinary write must neither refuse
    # (one bad body would wedge every write to the fact) nor drop it (silent data loss).
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, title="T", hook=HOOK, body="first", type_="feedback")
    stored = _stored(anchor, slug)
    assert stored.count("\ntitle: T\n") == 1
    us.put_body(anchor, slug, stored.replace("\ntitle: T\n", "\ntitle: T\n%s\n" % raw))
    assert E._body_topics(_stored(anchor, slug)) is None
    E.add_or_update_entry(proj, title="T", hook=HOOK, body="second prose", slug=slug)
    lines = _stored(anchor, slug).split("\n")
    assert "second prose" in lines
    assert [row for row in lines if row.startswith("topics:")] == [raw]
    assert lines[lines.index(raw) - 1] == "title: T"


def test_a_framed_update_does_not_replace_a_stored_line_that_does_not_parse(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, title="T", hook=HOOK, body="first", type_="feedback")
    tagged = _stored(anchor, slug).replace("\ntitle: T\n", "\ntitle: T\ntopics: [Python]\n")
    us.put_body(anchor, slug, tagged)
    edited = E._with_topics(_stored(anchor, slug), ("rust",)).replace("first", "edited")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=edited, slug=slug)
    stored = _stored(anchor, slug)
    assert "edited" in stored and stored.count("topics:") == 1 and "topics: [Python]\n" in stored


@pytest.mark.parametrize("line", ["topics: [python]", "topics: []", "topics: [Not A Tag]"])
def test_add_refuses_a_new_fact_whose_frame_carries_a_topics_line(tmp_path, capsys, line):
    # Only set-topics changes a fact's topics: a create handed a frame with the line would store a
    # tagging nobody checked against the tree's list. Refused before anything is written.
    anchor, proj = _tree(tmp_path)
    body_file = tmp_path / "body.md"
    body_file.write_text(FRAME.replace("title: T\n", "title: T\n%s\n" % line), encoding="utf-8")
    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook", HOOK, "--slug", "s",
                 "--body-file", str(body_file)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "! refused" in out and "set-topics" in out
    assert not us.body_path(anchor, "s").exists()
    assert not (Path(proj) / "CLAUDE.local.md").exists()


def test_the_library_create_raises_and_a_topics_line_in_the_prose_is_no_frame(tmp_path):
    anchor, proj = _tree(tmp_path)
    with pytest.raises(E.TopicsOnCreate):
        E.add_or_update_entry(proj, title="T", hook=HOOK, slug="s",
                              body=FRAME.replace("title: T\n", "title: T\ntopics: [python]\n"))
    assert not us.body_path(anchor, "s").exists()
    slug = E.add_or_update_entry(proj, title="T", hook=HOOK, slug="s",
                                 body=FRAME + "topics: [python]\n")
    assert E._body_topics(_stored(anchor, slug)) is None


# ---- a topics: line in the prose is no data ----------------------------------------------------

PROSE_LINE = "topics: [rust]"


def _with_prose_line(tmp_path):
    anchor, proj = _tree(tmp_path)
    (Path(anchor) / us.STORE_DIRNAME / "topics.json").write_text(
        '{"version": 1, "tagger": "jev", "topics": {"python": "P", "rust": "R"}, "levels": {}}\n',
        encoding="utf-8")
    slug = E.add_or_update_entry(proj, title="T", hook=HOOK, body="first\n\n%s\n" % PROSE_LINE,
                                 type_="feedback")
    return anchor, proj, slug


def test_set_topics_and_clear_touch_only_the_frame_never_a_prose_topics_line(tmp_path):
    anchor, proj, slug = _with_prose_line(tmp_path)
    assert E._body_topics(_stored(anchor, slug)) is None
    E.set_fact_topics(proj, {slug: ("python",)})
    stored = _stored(anchor, slug)
    assert E._body_topics(stored) == ("python",) and stored.count(PROSE_LINE) == 1
    E.set_fact_topics(proj, {slug: None})
    stored = _stored(anchor, slug)
    assert E._body_topics(stored) is None and stored.count("topics:") == 1
    assert stored.count(PROSE_LINE) == 1


def test_an_update_neither_lifts_a_prose_topics_line_into_the_frame_nor_drops_it(tmp_path):
    anchor, proj, slug = _with_prose_line(tmp_path)
    E.add_or_update_entry(proj, title="T", hook=HOOK, slug=slug,
                          body="second\n\n%s\n" % PROSE_LINE)
    stored = _stored(anchor, slug)
    assert E._body_topics_line(stored) is None and stored.count(PROSE_LINE) == 1


# ---- a fact leaving its tree leaves its topics behind ------------------------------------------

def _tag_raw(anchor, slug, line):
    stored = _stored(anchor, slug)
    assert stored.count("\ntitle: T\n") == 1
    us.put_body(anchor, slug, stored.replace("\ntitle: T\n", "\ntitle: T\n%s\n" % line))


@pytest.mark.parametrize("line", ["topics: []", "topics: [Not A Tag]"])
def test_a_cross_tree_relocate_drops_the_topics_line_and_says_so(two_trees, capsys, line):
    src, dst = str(two_trees.proj_a), str(two_trees.proj_b)
    slug = E.add_or_update_entry(src, title="T", hook=HOOK, body="prose\n\n%s\n" % PROSE_LINE,
                                 type_="feedback", slug="feedback-moving")
    _tag_raw(us.resolve_anchor(src), slug, line)
    untagged = _stored(us.resolve_anchor(src), slug).replace(line + "\n", "")
    assert E.main(["relocate", "--from-level", src, "--to-level", dst, "--slug", slug]) == 0
    out = capsys.readouterr().out
    assert "topics" in out and "dropped" in out
    moved = _stored(us.resolve_anchor(dst), slug)
    assert moved == untagged and moved.count(PROSE_LINE) == 1


def test_a_cross_tree_relocate_of_an_untagged_fact_copies_it_verbatim_and_says_nothing(two_trees, capsys):
    src, dst = str(two_trees.proj_a), str(two_trees.proj_b)
    slug = E.add_or_update_entry(src, title="T", hook=HOOK, body="prose\n\n%s\n" % PROSE_LINE,
                                 type_="feedback", slug="feedback-moving")
    before = us.body_path(us.resolve_anchor(src), slug).read_bytes()
    assert E.main(["relocate", "--from-level", src, "--to-level", dst, "--slug", slug]) == 0
    assert "dropped" not in capsys.readouterr().out
    assert us.body_path(us.resolve_anchor(dst), slug).read_bytes() == before


def test_a_cross_tree_relocate_keeps_crlf_line_endings_when_it_drops_the_line(two_trees):
    src, dst = str(two_trees.proj_a), str(two_trees.proj_b)
    slug = E.add_or_update_entry(src, title="T", hook=HOOK, body="prose", type_="feedback",
                                 slug="feedback-moving")
    path = us.body_path(us.resolve_anchor(src), slug)
    tagged = E._with_topics(path.read_text(encoding="utf-8"), ())
    path.write_bytes(tagged.replace("\n", "\r\n").encode("utf-8"))
    E.relocate_entry(src, dst, slug)
    moved = us.body_path(us.resolve_anchor(dst), slug).read_bytes()
    assert b"topics:" not in moved and moved == E._with_topics(tagged, None).replace("\n", "\r\n").encode("utf-8")


def test_a_same_tree_move_keeps_the_topics_line(tmp_path):
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    slug = E.add_or_update_entry(str(proj), title="T", hook=HOOK, body="prose", type_="feedback",
                                 slug="feedback-staying")
    _tag_raw(str(anchor), slug, "topics: []")
    before = us.body_path(anchor, slug).read_bytes()
    rep = E.relocate_entry(str(proj), str(anchor), slug)
    assert rep["relocated"] and not rep["cross_tree"]
    assert us.body_path(anchor, slug).read_bytes() == before
