"""Tests for the pure placement rules: which levels a topic-bound fact's pointer lines go to."""

import pytest

import topic_placement as tp

A_PY, B_PY, C_RUST, D_MACH = ("a", "python"), ("b", "python"), ("c", "rust"), ("d", "machines")


def _design_tree(**extra):
    """The design's example: /a/python/{x1,x2}, /b/python/{y1,y2}, /c/rust, /d/machines."""
    levels = {
        tp.TOP: [], ("a",): [], ("b",): [], ("c",): [], ("d",): [],
        A_PY: ["python"], A_PY + ("x1",): [], A_PY + ("x2",): [],
        B_PY: ["python"], B_PY + ("y1",): [], B_PY + ("y2",): [],
        C_RUST: ["rust"], D_MACH: ["machines"],
    }
    levels.update(extra)
    return tp.LevelMap(levels)


def test_a_python_rule_is_placed_at_both_python_dirs_and_nowhere_else():
    assert _design_tree().placements(["python"]) == (A_PY, B_PY)


def test_a_level_below_one_that_has_the_topic_gets_no_second_copy():
    tree = tp.LevelMap({tp.TOP: [], ("a",): ["python"], ("a", "x"): ["python"], ("b",): []})
    assert tree.placements(["python"]) == (("a",),)


def test_a_single_child_does_not_roll_up():
    tree = _design_tree()
    assert tree.topics(("a",)) == frozenset()
    assert tree.topics(A_PY) == frozenset({"python"})


def test_a_topic_every_child_has_rolls_up_to_the_parent():
    rolled = tp.LevelMap({tp.TOP: [], ("p",): [], ("p", "one"): ["python", "ci"], ("p", "two"): ["python"]})
    assert rolled.topics(("p",)) == frozenset({"python"})
    assert rolled.placements(["python"]) == (("p",),)
    assert rolled.placements(["ci"]) == (("p", "one"),)


def test_a_roll_up_carries_on_to_the_grandparent():
    tree = tp.LevelMap({tp.TOP: [], ("g",): [], ("g", "p"): [], ("g", "q"): ["python"],
                        ("g", "p", "one"): ["python"], ("g", "p", "two"): ["python"]})
    assert tree.placements(["python"]) == (("g",),)


def test_one_child_without_the_topic_stops_the_roll_up():
    tree = tp.LevelMap({tp.TOP: [], ("p",): [], ("p", "one"): ["python"], ("p", "two"): ["rust"]})
    assert tree.topics(("p",)) == frozenset()
    assert tree.placements(["python"]) == (("p", "one"),)


def test_a_topic_every_child_has_does_not_roll_up_into_the_top():
    tree = tp.LevelMap({tp.TOP: [], ("one",): ["python"], ("two",): ["python"]})
    assert tree.topics(tp.TOP) == frozenset()
    assert tree.placements(["python"]) == (("one",), ("two",))


def test_a_topic_the_top_declares_is_placed_at_the_top_only():
    tree = tp.LevelMap({tp.TOP: ["git"], ("one",): ["git", "python"]})
    assert tree.placements(["git"]) == (tp.TOP,)
    assert tree.placements(["git", "python"]) == (tp.TOP,)


def test_a_fact_whose_topic_no_level_has_falls_back_to_the_top():
    assert _design_tree().placements(["cobol"]) == (tp.TOP,)


def test_two_topics_place_the_fact_at_the_topmost_level_of_each_branch():
    assert _design_tree().placements(["python", "rust"]) == (A_PY, B_PY, C_RUST)
    tree = tp.LevelMap({tp.TOP: [], ("a",): ["ci"], ("a", "x"): ["python"], ("b",): ["python"]})
    assert tree.placements(["python", "ci"]) == (("a",), ("b",))


def test_a_gap_dir_that_is_no_level_is_skipped_when_finding_the_parent():
    tree = tp.LevelMap({tp.TOP: [], ("a",): ["python"], ("a", "gap", "deep"): ["python"]})
    assert tree.parent(("a", "gap", "deep")) == ("a",)
    assert tree.placements(["python"]) == (("a",),)


def test_placed_at_answers_for_one_level():
    tree = _design_tree()
    assert tree.placed_at(A_PY, ["python"]) is True
    assert tree.placed_at(C_RUST, ["python"]) is False
    assert tree.placed_at(tp.TOP, ["cobol"]) is True


def test_normalise_sorts_dedups_and_refuses_a_bad_tag():
    assert tp.normalise_topics(["uv", "python", "uv"]) == ("python", "uv")
    for bad in ("Python", "has space", "", "-lead", "x" * 33, "a,b", "new\nline"):
        with pytest.raises(tp.InvalidTopic):
            tp.normalise_topics([bad])
    with pytest.raises(tp.InvalidTopic):
        tp.normalise_topics("t%d" % i for i in range(tp.MAX_TOPICS + 1))


def test_parse_and_format_round_trip_including_the_empty_list():
    assert tp.parse_topics("[python, uv]") == ("python", "uv")
    assert tp.parse_topics("uv,python") == ("python", "uv")
    assert tp.parse_topics("[]") == () and tp.parse_topics("") == ()
    assert tp.format_topics(["uv", "python"]) == "[python, uv]"
    assert tp.format_topics([]) == "[]"


def test_descriptor_topics_tells_never_tagged_from_tagged_with_none():
    assert tp.descriptor_topics("WHAT: x\nSTACK: y") is None
    assert tp.descriptor_topics("WHAT: x\nTOPICS:\nPLACE-HERE: z") == ()
    assert tp.descriptor_topics("WHAT: x\nTOPICS: uv, python") == ("python", "uv")
    assert tp.descriptor_topics("WHAT: about TOPICS: nothing") is None


def test_with_descriptor_topics_inserts_after_stack_and_replaces_in_place():
    scope = "WHAT: x\nSTACK: y\nCHILDREN:\n- a/: b\nPLACE-HERE: z"
    tagged = tp.with_descriptor_topics(scope, ["uv", "python"])
    assert tagged.split("\n")[2] == "TOPICS: python, uv"
    assert tagged.replace("TOPICS: python, uv\n", "") == scope
    again = tp.with_descriptor_topics(tagged, ["rust"])
    assert again.split("\n")[2] == "TOPICS: rust" and again.count("TOPICS:") == 1
    assert tp.with_descriptor_topics("WHAT: x", []) == "WHAT: x\nTOPICS: "
    assert tp.with_descriptor_topics("", ["a"]) == "TOPICS: a"


def test_descriptor_digest_ignores_the_topics_line_and_sees_every_other_change():
    scope = "WHAT: x\nSTACK: y"
    assert tp.descriptor_digest(scope) == tp.descriptor_digest(tp.with_descriptor_topics(scope, ["a"]))
    assert tp.descriptor_digest(scope) == tp.descriptor_digest("WHAT: x\r\n\nSTACK: y\n")
    assert tp.descriptor_digest(scope) != tp.descriptor_digest("WHAT: x\nSTACK: z")


def _small_tree():
    return tp.LevelMap({tp.TOP: [], ("a",): ["python"], ("b",): ["rust"]})


def test_normalise_refuses_a_bare_string_for_a_topic_list():
    with pytest.raises(tp.InvalidTopic):
        tp.normalise_topics("python")


def test_format_refuses_a_bare_string_for_a_topic_list():
    with pytest.raises(tp.InvalidTopic):
        tp.format_topics("uv")


def test_a_level_map_refuses_a_string_level_key():
    with pytest.raises(TypeError):
        tp.LevelMap({tp.TOP: [], "ab": ["x"]})


def test_placements_refuses_a_bare_string_and_an_invalid_tag():
    with pytest.raises(tp.InvalidTopic):
        _small_tree().placements("python")
    with pytest.raises(tp.InvalidTopic):
        _small_tree().placements(["Python"])


def test_placements_treats_an_unnormalised_tag_as_its_normalised_form():
    assert _small_tree().placements([" python", "python "]) == (("a",),)


def test_placed_at_normalises_its_topics_and_refuses_a_string_level():
    tree = _small_tree()
    assert tree.placed_at(("a",), [" python"]) is True
    with pytest.raises(tp.InvalidTopic):
        tree.placed_at(("a",), "python")
    with pytest.raises(TypeError):
        tree.placed_at("a", ["python"])
