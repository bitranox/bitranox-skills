"""Tests that an UPDATE add whose body carries its own, partial frontmatter keeps every stored key
that frame does not set. A body framed with `name:` and `topics:` only replaced the stored frame
whole: `description:` and `metadata:` were dropped, so the body no longer yielded a line and the
fact stopped being placed by topic. The new frame's own keys still win, `description:` still
follows the hook, and the stored `topics:` line still wins over the frame's. All content ASCII.
"""

import pytest

import memory_engine as E
import uuid_store as us

HOOK = "When a fact is updated with a partial frame, keep the keys it does not set."
PARTIAL = "---\nname: whatever\ntopics: [rust]\n---\n\nnew prose\n"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


@pytest.fixture
def fact(tmp_path):
    """(anchor, proj, slug): a fact with a skill, tagged with topics the way set-topics stores them."""
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    slug = E.add_or_update_entry(str(proj), title="T", hook=HOOK, body="first prose",
                                 type_="feedback", skill="bitranox:compuse-git")
    us.put_body(str(anchor), slug, E._with_topics(_stored(anchor, slug), ("python",)))
    return str(anchor), str(proj), slug


def _stored(anchor, slug):
    return us.body_path(str(anchor), slug).read_text(encoding="utf-8")


def _frame(text):
    _head, m = E._frontmatter(text)
    return m.group(1)


def test_an_update_with_a_partial_frame_keeps_the_stored_keys_it_does_not_set(fact):
    anchor, proj, slug = fact
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=PARTIAL, slug=slug)
    stored = _stored(anchor, slug)
    assert E._body_description(stored) == HOOK
    assert E._body_type(stored) == "feedback"
    assert E._body_skill(stored) == "bitranox:compuse-git"
    assert E._body_topics(stored) == ("python",)          # the stored line wins over the frame's
    assert E._body_title(stored) == "T"
    assert "name: %s" % slug in _frame(stored)
    assert stored.endswith("new prose\n") and "first prose" not in stored
    head = E._read_body_head(us.body_path(anchor, slug))
    assert E._managed_topics(slug, head, ()) == ("python",)   # still placed by topic


def test_the_description_still_follows_a_new_hook(fact):
    anchor, proj, slug = fact
    E.add_or_update_entry(proj, title="T", hook="When the hook changes, follow it.",
                          body=PARTIAL, slug=slug)
    assert E._body_description(_stored(anchor, slug)) == "When the hook changes, follow it."


def test_keys_the_new_frame_sets_still_win(fact):
    anchor, proj, slug = fact
    body = "---\nname: x\nmetadata:\n  type: reference\n---\n\nnew prose\n"
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=body, slug=slug)
    stored = _stored(anchor, slug)
    assert E._body_type(stored) == "reference"                # the frame's kind
    assert E._body_skill(stored) == "bitranox:compuse-git"    # a metadata key it did not set
    assert E._body_description(stored) == HOOK


def test_a_full_frame_update_is_unchanged_by_the_merge(fact):
    anchor, proj, slug = fact
    full = _stored(anchor, slug).replace("first prose", "rewritten prose")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=full, slug=slug)
    assert _stored(anchor, slug) == full
