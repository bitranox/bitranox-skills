"""Tests for the parts `render-topics` is built from: the streamed body heads, a level as path
parts, the line a body renders, the tree's level map, and the set-topics guard that keeps a
fact's stored line equal to what its body renders before the fact is bound. All content ASCII.
"""

import os
import tracemalloc
from pathlib import Path

import pytest

import memory_engine as E
import self_improve_signals as sig
import topic_placement as tp
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python"
LIST = {"python": "Python code and its tooling", "rust": "Rust code", "git": "git and GitHub"}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top\nSTACK: none"]) == 0
    return str(anchor)


def _level(anchor, rel, topics=None, scope=SCOPE):
    level = Path(anchor, *rel.split("/"))
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    if scope:
        assert E.main(["set-scope", "--proj", str(level), "--scope", scope]) == 0
    if topics is not None:
        E.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, pin=False):
    return E.add_or_update_entry(level, title="T " + slug, hook=HOOK, body="body of " + slug,
                                 type_="feedback", slug=slug, pin=pin)


def _plant_scope(level, scope):
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    local.write_text(us.upsert_pointer_block(text, scope, us.parse_pointer_index(text)[1]),
                     encoding="utf-8")


def _plant_bodies(anchor, count):
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    prose = "x" * 200_000
    for i in range(count):
        (facts / ("feedback-n%05d.md" % i)).write_text(
            "---\nname: feedback-n%05d\ndescription: d\ntitle: T\ntopics: [python]\nmetadata:\n"
            "  type: feedback\n---\n\n%s\n" % (i, prose), encoding="utf-8")


def _heads_peak(anchor):
    tracemalloc.start()
    try:
        longest = max(len(head) for _slug, head in E._iter_body_heads(anchor))
        return longest, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_body_heads_are_streamed_one_at_a_time_and_capped(tmp_path):
    small, large = tmp_path / "small", tmp_path / "large"
    _plant_bodies(small, 20)
    _plant_bodies(large, 200)
    (us.central_facts_dir(large) / "notes.txt").write_text("x", encoding="utf-8")
    longest, peak_small = _heads_peak(small)
    _longest, peak_large = _heads_peak(large)
    assert longest == E.FRONTMATTER_HEAD_BYTES
    assert sum(1 for _ in E._iter_body_heads(large)) == 200
    assert peak_large < 200_000 and peak_large < peak_small * 2 + 50_000
    assert list(E._iter_body_heads(tmp_path / "nothing")) == []


def test_a_level_is_its_path_parts_below_the_anchor(tmp_path):
    anchor = _tree(tmp_path)
    assert E._level_parts(anchor, anchor) == tp.TOP == ()
    assert E._level_parts(anchor, os.path.join(anchor, "a", "py")) == ("a", "py")
    with pytest.raises(topic_store.TopicStoreError):
        E._level_parts(anchor, str(tmp_path / "elsewhere"))


def test_a_line_is_built_from_the_body_alone(tmp_path):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    head = us.body_path(anchor, "feedback-a").read_text(encoding="utf-8")
    line = E._line_from_head("feedback-a", head)
    stored = us.parse_pointer_index(sig.claude_local_md_path(anchor).read_text(encoding="utf-8"))[1][0]
    assert line.index_line() == stored.index_line() and line.pin is False
    assert E._line_from_head("feedback-a", head.replace("title: T feedback-a\n", "")) is None
    assert E._line_from_head("feedback-a", head.replace("description: " + HOOK + "\n", "")) is None


def test_the_level_map_holds_described_levels_with_their_topics(tmp_path):
    anchor = _tree(tmp_path)
    _level(anchor, "a/py", ("python",))
    _level(anchor, "c", ())
    _level(anchor, "d")                                   # a descriptor, never tagged
    bare = _level(anchor, "e", scope=None)
    _fact(bare, "feedback-at-bare")                       # a pointer block with no descriptor
    level_map, dirs = E.topic_level_map(anchor)
    assert level_map.levels() == [(), ("c",), ("d",), ("a", "py")]
    assert level_map.topics(("a", "py")) == {"python"} and level_map.topics(("d",)) == frozenset()
    assert dirs[("a", "py")] == os.path.join(anchor, "a", "py") and dirs[()] == anchor


def test_a_level_without_a_descriptor_does_not_block_a_roll_up(tmp_path):
    anchor = _tree(tmp_path)
    _level(anchor, "a", ())
    _level(anchor, "a/x1", ("python",))
    _level(anchor, "a/x2", ("python",))
    _fact(_level(anchor, "a/x3", scope=None), "feedback-at-bare")
    level_map, _dirs = E.topic_level_map(anchor)
    assert level_map.placements(("python",)) == (("a",),)


def test_a_topics_line_that_does_not_parse_refuses_the_map_and_names_the_level(tmp_path):
    anchor = _tree(tmp_path)
    level = _level(anchor, "a", ("python",))
    _plant_scope(level, SCOPE + "\nTOPICS: Not A Tag")
    with pytest.raises(E.TopicRefusal) as exc:
        E.topic_level_map(anchor)
    assert level in str(exc.value) and "does not parse" in str(exc.value)


def test_pinned_slugs_are_found_at_any_level(tmp_path):
    anchor = _tree(tmp_path)
    level = _level(anchor, "a")
    _fact(level, "feedback-pinned", pin=True)
    _fact(anchor, "feedback-free")
    assert E._pinned_slugs(E.curated_levels_under(anchor)) == {"feedback-pinned"}


# ---- set-topics: a fact is bound only when its line equals what its body renders ---------------

def _replant_pointer(level, slug, hook):
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    for p in pointers:
        if p.slug == slug:
            p.hook = hook
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")


def test_binding_a_fact_whose_line_differs_from_its_body_is_refused(tmp_path, capsys):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    _replant_pointer(anchor, "feedback-a", "When the line was edited by hand, it says this.")
    body = us.body_path(anchor, "feedback-a").read_bytes()
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--topics", "python"]) == 2
    out = capsys.readouterr().out
    assert "! refused" in out and "differs from what its body would render" in out
    assert us.body_path(anchor, "feedback-a").read_bytes() == body
    # un-binding hands nothing to the renderer, so it stays allowed
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--universal"]) == 0


def test_binding_a_fact_whose_body_has_no_title_is_refused(tmp_path, capsys):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    path = us.body_path(anchor, "feedback-a")
    path.write_text(path.read_text(encoding="utf-8").replace("title: T feedback-a\n", ""),
                    encoding="utf-8")
    before = path.read_bytes()
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--topics", "python"]) == 2
    assert "lacks title: or description:" in capsys.readouterr().out
    assert path.read_bytes() == before


def test_binding_a_fact_whose_line_equals_its_body_goes_through(tmp_path):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--topics", "python"]) == 0
    assert E.read_body_topics(us.body_path(anchor, "feedback-a")) == ("python",)
    assert list(E.iter_fact_topics(anchor)) == [("feedback-a", ("python",))]
