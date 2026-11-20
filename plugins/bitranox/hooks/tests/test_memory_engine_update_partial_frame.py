"""Tests that an UPDATE add whose body carries its own, partial frontmatter keeps every stored key
that frame does not set. A body framed with `name:` and `topics:` only replaced the stored frame
whole: `description:` and `metadata:` were dropped, so the body no longer yielded a line and the
fact stopped being placed by topic. The new frame's own keys still win, `description:` still
follows the hook, and the stored `topics:` line still wins over the frame's. All content ASCII.
"""

import pytest
import yaml

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
    _head, m = E.split_frontmatter(text)
    assert m is not None
    return m.group(1)


def test_an_update_with_a_partial_frame_keeps_the_stored_keys_it_does_not_set(fact):
    anchor, proj, slug = fact
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=PARTIAL, slug=slug)
    stored = _stored(anchor, slug)
    assert E.body_description(stored) == HOOK
    assert E.body_type(stored) == "feedback"
    assert E._body_skill(stored) == "bitranox:compuse-git"
    assert E._body_topics(stored) == ("python",)          # the stored line wins over the frame's
    assert E.body_title(stored) == "T"
    assert "name: %s" % slug in _frame(stored)
    assert stored.endswith("new prose\n") and "first prose" not in stored
    head = E.read_body_head(us.body_path(anchor, slug))
    assert E.managed_topics(slug, head, ()) == ("python",)   # still placed by topic


def test_the_description_still_follows_a_new_hook(fact):
    anchor, proj, slug = fact
    E.add_or_update_entry(proj, title="T", hook="When the hook changes, follow it.",
                          body=PARTIAL, slug=slug)
    assert E.body_description(_stored(anchor, slug)) == "When the hook changes, follow it."


def test_keys_the_new_frame_sets_still_win(fact):
    anchor, proj, slug = fact
    body = "---\nname: x\nmetadata:\n  type: reference\n---\n\nnew prose\n"
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=body, slug=slug)
    stored = _stored(anchor, slug)
    assert E.body_type(stored) == "reference"                # the frame's kind
    assert E._body_skill(stored) == "bitranox:compuse-git"    # a metadata key it did not set
    assert E.body_description(stored) == HOOK


def test_a_full_frame_update_is_unchanged_by_the_merge(fact):
    anchor, proj, slug = fact
    full = _stored(anchor, slug).replace("first prose", "rewritten prose")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=full, slug=slug)
    assert _stored(anchor, slug) == full


# ---- removing a frame key the engine does not manage -------------------------------------------
# A frame says what it sets, never what it drops, so leaving a key out keeps the stored one. The
# one way to remove a key is to name it with no value; the store-edit-guard denies a hand edit.

def _with_extra_key(anchor, slug, line):
    stored = _stored(anchor, slug)
    us.put_body(str(anchor), slug, stored.replace("\n---\n", "\n%s\n---\n" % line, 1))
    return _stored(anchor, slug)


def test_a_frame_that_leaves_out_an_unknown_key_keeps_it(fact):
    anchor, proj, slug = fact
    full = _stored(anchor, slug).replace("first prose", "second prose")
    _with_extra_key(anchor, slug, "stale: old")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=full, slug=slug)
    assert _yaml_frame(_stored(anchor, slug))["stale"] == "old"


def test_a_frame_that_names_an_unknown_key_with_no_value_removes_it(fact):
    anchor, proj, slug = fact
    stored = _with_extra_key(anchor, slug, "stale: old\nkept: here")
    emptied = stored.replace("stale: old", "stale:").replace("first prose", "second prose")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=emptied, slug=slug)
    frame = _yaml_frame(_stored(anchor, slug))
    assert "stale" not in frame
    assert frame["kept"] == "here"
    assert frame["metadata"] == {"type": "feedback", "skill": "bitranox:compuse-git"}
    assert _stored(anchor, slug).endswith("second prose\n")


def test_a_stored_key_with_no_value_survives_an_unedited_round_trip(fact):
    anchor, proj, slug = fact
    stored = _with_extra_key(anchor, slug, "marker:")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=stored, slug=slug)
    assert _stored(anchor, slug) == stored


def test_a_bare_metadata_line_still_keeps_the_stored_sub_keys(fact):
    anchor, proj, slug = fact
    body = "---\nname: x\nmetadata:\n---\n\nnew prose\n"
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=body, slug=slug)
    assert _yaml_frame(_stored(anchor, slug))["metadata"] == {
        "type": "feedback", "skill": "bitranox:compuse-git"}


def test_a_bare_managed_key_is_not_removed(fact):
    """`description:` and `title:` are the engine's: a bare one keeps them, set from this write."""
    anchor, proj, slug = fact
    body = "---\nname: x\ndescription:\ntitle:\n---\n\nnew prose\n"
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=body, slug=slug)
    frame = _yaml_frame(_stored(anchor, slug))
    assert (frame["description"], frame["title"]) == (HOOK, "T")


# ---- removing a `metadata:` sub-key -------------------------------------------------------------
# The same rule one level down: a sub-key named with no value removes the stored one. `type:` is
# the fact's kind, which --type changes and the lint requires, so a bare `type:` keeps it.

def test_a_bare_skill_sub_key_removes_the_stored_skill(fact):
    anchor, proj, slug = fact
    stored = _stored(anchor, slug)
    emptied = stored.replace("skill: bitranox:compuse-git", "skill:").replace("first", "second")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=emptied, slug=slug)
    after = _stored(anchor, slug)
    assert E._body_skill(after) == ""
    assert _yaml_frame(after)["metadata"] == {"type": "feedback"}
    assert after.endswith("second prose\n")


def test_a_bare_skill_sub_key_beside_a_four_space_frame_removes_it(fact):
    anchor, proj, slug = fact
    body = "---\nname: x\nmetadata:\n    type: reference\n    skill:\n---\n\nnew prose\n"
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=body, slug=slug)
    assert _yaml_frame(_stored(anchor, slug))["metadata"] == {"type": "reference"}


def test_an_explicit_skill_wins_over_a_bare_skill_sub_key(fact):
    anchor, proj, slug = fact
    emptied = _stored(anchor, slug).replace("skill: bitranox:compuse-git", "skill:")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=emptied, slug=slug,
                          skill="bitranox:compuse-bash")
    assert E._body_skill(_stored(anchor, slug)) == "bitranox:compuse-bash"


def test_a_bare_type_sub_key_keeps_the_stored_kind(fact):
    anchor, proj, slug = fact
    emptied = _stored(anchor, slug).replace("type: feedback", "type:")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=emptied, slug=slug)
    assert _yaml_frame(_stored(anchor, slug))["metadata"] == {
        "type": "feedback", "skill": "bitranox:compuse-git"}


def test_a_stored_bare_sub_key_survives_an_unedited_round_trip(fact):
    anchor, proj, slug = fact
    stored = _stored(anchor, slug).replace("  skill: bitranox:compuse-git\n",
                                           "  skill: bitranox:compuse-git\n  marker:\n")
    us.put_body(str(anchor), slug, stored)
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=stored, slug=slug)
    assert _stored(anchor, slug) == stored


# ---- a frame whose `metadata:` sub-keys are indented differently from the stored frame ---------
# A stored frame indents its sub-keys by two spaces; a body handed in may use four. Lines carried
# over, or inserted, at the other indent made the frontmatter invalid YAML.

FOUR_SPACE = "---\nname: x\nmetadata:\n    type: reference\n---\n\nnew prose\n"


def _yaml_frame(text):
    return yaml.safe_load(_frame(text))


def test_a_four_space_metadata_frame_merged_with_a_two_space_stored_one_stays_valid_yaml(fact):
    anchor, proj, slug = fact
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=FOUR_SPACE, slug=slug)
    meta = _yaml_frame(_stored(anchor, slug))["metadata"]
    assert meta == {"type": "reference", "skill": "bitranox:compuse-git"}


def test_a_skill_added_under_a_four_space_metadata_frame_stays_valid_yaml(tmp_path):
    anchor = tmp_path / "tree2"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    slug = E.add_or_update_entry(str(proj), title="T", hook=HOOK, body="first prose",
                                 type_="feedback")
    E.add_or_update_entry(str(proj), title="T", hook=HOOK, body=FOUR_SPACE, slug=slug,
                          skill="bitranox:compuse-git")
    meta = _yaml_frame(_stored(anchor, slug))["metadata"]
    assert meta == {"type": "reference", "skill": "bitranox:compuse-git"}


@pytest.mark.parametrize("sub", ["other: kept", "skill: bitranox:compuse-git"])
def test_a_type_inserted_under_a_four_space_metadata_follows_its_indent(sub):
    frame = "---\nname: x\nmetadata:\n    %s\n---\n\nprose\n" % sub
    assert _yaml_frame(E._retype_body("x", HOOK, "reference", frame))["metadata"]["type"] \
        == "reference"


@pytest.mark.parametrize("sub", ["other: kept", "type: reference"])
def test_a_skill_inserted_under_a_four_space_metadata_follows_its_indent(sub):
    frame = "---\nname: x\nmetadata:\n    %s\n---\n\nprose\n" % sub
    assert _yaml_frame(E._with_skill(frame, "bitranox:compuse-git"))["metadata"]["skill"] \
        == "bitranox:compuse-git"
