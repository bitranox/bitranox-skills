"""Tests for memory_engine.dangling_wikilinks - write-time [[ref]] validation. ASCII only."""
import memory_engine as ME


def test_flags_missing_target_and_suggests_closest():
    out = ME.dangling_wikilinks("see [[foo-bar]] and [[real-slug]] here", {"real-slug", "foo-baz"})
    assert ("foo-bar", "foo-baz") in out            # missing slug + closest existing suggestion
    assert all(t != "real-slug" for t, _ in out)    # an EXISTING slug is not flagged


def test_none_when_all_targets_exist():
    assert ME.dangling_wikilinks("[[a]] and [[b]]", {"a", "b"}) == []


def test_no_suggestion_when_nothing_close():
    assert ME.dangling_wikilinks("[[zzz-nothing-like-it]]", {"a", "b"}) == [("zzz-nothing-like-it", None)]


def test_deduplicates_repeated_missing_target():
    assert ME.dangling_wikilinks("[[gone]] ... [[gone]] again", set()) == [("gone", None)]
