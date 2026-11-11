"""Tests for the body frontmatter `topics:` line - the topics a fact is bound to, kept as data.

A fact with topics is read only where its topics are; the list lives in the body's frontmatter
and changes only through `set-topics`. `topics: []` means tagged and bound to no topic; no line
means never tagged. An ordinary write to the fact keeps the stored line. All content ASCII.
"""

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
