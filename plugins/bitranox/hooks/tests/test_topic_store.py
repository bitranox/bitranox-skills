"""Tests for the topic file: a tree's closed topic list and the per-level descriptor digests."""

import json

import pytest

import self_improve_signals as sig
import topic_placement as tp
import topic_store
import uuid_store as us


def _anchor(tmp_path):
    anchor = tmp_path / "tree"
    (anchor / us.STORE_DIRNAME).mkdir(parents=True)
    return anchor


def test_no_file_means_no_list(tmp_path):
    assert topic_store.load(_anchor(tmp_path)) is None


def test_save_then_load_round_trips_and_the_file_is_sorted_json(tmp_path):
    anchor = _anchor(tmp_path)
    assert topic_store.save_list(anchor, {"uv": "uv projects", "python": "Python code"}, "jev") is True
    data = topic_store.load(anchor)
    assert data["topics"] == {"python": "Python code", "uv": "uv projects"} and data["tagger"] == "jev"
    raw = topic_store.store_path(anchor).read_text(encoding="utf-8")
    assert json.loads(raw) == data and raw.index('"python"') < raw.index('"uv"')
    assert topic_store.save_list(anchor, {"uv": "uv projects", "python": "Python code"}, "jev") is False


def test_a_new_list_keeps_the_recorded_levels(tmp_path):
    anchor = _anchor(tmp_path)
    topic_store.save_list(anchor, {"python": "Python code"}, "opus")
    (anchor / "a" / "b").mkdir(parents=True)
    topic_store.record_level(anchor, anchor / "a" / "b", "d1")
    topic_store.record_level(anchor, anchor, "d0")
    topic_store.save_list(anchor, {"rust": "Rust code"}, "opus")
    assert topic_store.load(anchor)["levels"] == {"": "d0", "a/b": "d1"}


@pytest.mark.parametrize("topics, tagger", [
    ({"python": "ok"}, "gpt"),
    ({"python": ""}, "jev"),
    ({"python": "   "}, "jev"),
    ({"python": "two\nlines"}, "jev"),
    ({"python": "x" * (topic_store.MAX_MEANING + 1)}, "jev"),
    ({"python": 7}, "jev"),
    ({"t%d" % i: "m" for i in range(topic_store.MAX_LIST + 1)}, "jev"),
])
def test_an_unacceptable_list_is_refused_and_nothing_is_written(tmp_path, topics, tagger):
    anchor = _anchor(tmp_path)
    with pytest.raises((topic_store.TopicStoreError, tp.InvalidTopic)):
        topic_store.save_list(anchor, topics, tagger)
    assert not topic_store.store_path(anchor).exists()


def test_a_bad_tag_name_is_refused(tmp_path):
    with pytest.raises(tp.InvalidTopic):
        topic_store.save_list(_anchor(tmp_path), {"Not A Tag": "m"}, "jev")


def test_a_damaged_file_is_an_error_never_an_absent_list(tmp_path):
    anchor = _anchor(tmp_path)
    topic_store.store_path(anchor).write_text("{not json", encoding="utf-8")
    with pytest.raises(topic_store.TopicStoreError):
        topic_store.load(anchor)
    topic_store.store_path(anchor).write_text('["a list"]', encoding="utf-8")
    with pytest.raises(topic_store.TopicStoreError):
        topic_store.load(anchor)


def test_recording_a_level_needs_a_list(tmp_path):
    anchor = _anchor(tmp_path)
    with pytest.raises(topic_store.TopicStoreError):
        topic_store.record_level(anchor, anchor, "d")


def test_writes_are_refused_when_memory_writes_are_off(tmp_path, monkeypatch):
    anchor = _anchor(tmp_path)
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff):
        topic_store.save_list(anchor, {"python": "m"}, "jev")
    assert not topic_store.store_path(anchor).exists()


def test_level_key_is_posix_relative_and_keeps_a_leading_dot_name(tmp_path):
    anchor = _anchor(tmp_path)
    (anchor / ".cfg" / "x").mkdir(parents=True)
    assert topic_store.level_key(anchor, anchor) == ""
    assert topic_store.level_key(anchor, anchor / ".cfg" / "x") == ".cfg/x"


@pytest.mark.parametrize("size", [tp.MAX_TOPICS + 1, topic_store.MAX_LIST])
def test_a_tree_list_may_hold_more_topics_than_one_fact(tmp_path, size):
    # The tree's list is capped by MAX_LIST, not by the per-fact tp.MAX_TOPICS.
    anchor = _anchor(tmp_path)
    topics = {"t%d" % i: "meaning %d" % i for i in range(size)}
    assert topic_store.save_list(anchor, topics, "jev") is True
    assert len(topic_store.load(anchor)["topics"]) == size


def test_a_padded_name_is_stored_trimmed_and_a_collision_is_refused(tmp_path):
    anchor = _anchor(tmp_path)
    topic_store.save_list(anchor, {" python ": "Python code"}, "jev")
    assert topic_store.load(anchor)["topics"] == {"python": "Python code"}
    with pytest.raises(topic_store.TopicStoreError):
        topic_store.save_list(anchor, {"python": "a", " python": "b"}, "jev")
    assert topic_store.load(anchor)["topics"] == {"python": "Python code"}


def test_recording_a_level_keeps_the_list_and_the_tagger(tmp_path):
    anchor = _anchor(tmp_path)
    topic_store.save_list(anchor, {"python": "Python code", "rust": "Rust code"}, "jev")
    topic_store.record_level(anchor, anchor, "d0")
    data = topic_store.load(anchor)
    assert data["topics"] == {"python": "Python code", "rust": "Rust code"}
    assert data["tagger"] == "jev" and data["levels"] == {"": "d0"}
