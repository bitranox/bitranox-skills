"""Tests for skill_decisions: the per-skill decision ledger."""
import copy

import pytest

import skill_decisions as SD

LINE_SEPARATOR = chr(0x2028)  # built with chr(): a typed escape would land as the raw character


def _rule(**over):
    entry = {"v": 1, "date": "2026-11-05", "kind": "rule", "topic": "env-model",
             "decision": "bmk installs alone as a shared uv tool.",
             "why": "The per-project env was the inverse of what bmk 3.8.0 does.",
             "evidence": {"tier": "measured", "text": "bmk 3.8.0 release behaviour"},
             "reopen_if": "bmk changes its env model again.",
             "anchors": ["bmk alone, shared across projects"],
             "supersedes": [], "refs": [], "origin": "authored"}
    entry.update(over)
    entry["id"] = SD.entry_id(entry)
    return entry


# ---- matcher (the M0-measured rules) ----

def test_a_rewrap_and_a_repad_do_not_break_an_anchor():
    assert SD.anchor_occurs("Do **not** add `--with .` to the install line",
                            "Do **not** add\n   `--with .`   to the\ninstall line")


def test_a_blockquote_rewrap_does_not_break_an_anchor():
    assert SD.anchor_occurs("never restore the per-project env", "> never restore the\n> per-project env")
    assert SD.anchor_occurs("never restore the per-project env", ">never restore the\n>per-project env")


def test_an_anchor_spanning_two_list_items_survives_renumbering():
    anchor = "commit the plan. 2. push the plan"
    assert SD.anchor_occurs(anchor, "1. commit the plan.\n2. push the plan")
    assert SD.anchor_occurs(anchor, "3. commit the plan.\n4. push the plan")


def test_a_reworded_sentence_breaks_the_anchor():
    assert not SD.anchor_occurs("bmk installs as a persistent uv tool",
                                "bmk installs into a per-project .venv-bmk")


def test_unusual_line_separators_count_as_whitespace():
    assert SD.anchor_occurs("first half second half", "first half" + LINE_SEPARATOR + "second half")


def test_case_matters():
    assert not SD.anchor_occurs("Never push", "never push")


# ---- entry model ----

def test_a_complete_rule_entry_validates():
    assert SD.validate_entry(_rule()) == []


def test_the_id_is_the_date_plus_a_hash_of_the_whole_entry():
    a, b = _rule(), _rule(why="Another reason, same day.")
    assert a["id"].startswith("d-20261105-") and len(a["id"]) == len("d-20261105-") + 8
    assert a["id"] != b["id"]


def test_an_entry_edited_after_its_id_was_computed_is_refused():
    entry = _rule()
    entry["why"] = "rewritten in place"
    assert any(p.startswith("id:") for p in SD.validate_entry(entry))


@pytest.mark.parametrize("field", ["why", "reopen_if", "decision", "topic"])
def test_a_rule_without_a_mandatory_field_is_refused(field):
    entry = _rule(**{field: ""})
    assert any(p.startswith(field + ":") for p in SD.validate_entry(entry))


def test_a_void_entry_needs_why_and_a_target_but_no_reopen_if():
    void = _rule(kind="void", anchors=[], reopen_if="", supersedes=["d-20261101-0123abcd"])
    assert SD.validate_entry(void) == []
    no_target = _rule(kind="void", anchors=[], reopen_if="", supersedes=[])
    assert any(p.startswith("supersedes:") for p in SD.validate_entry(no_target))


def test_only_a_rule_carries_anchors_and_a_rule_needs_one():
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(anchors=[])))
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(kind="rejected")))


@pytest.mark.parametrize("anchor", ["too short to anchor", "x" * 201])
def test_an_anchor_outside_20_to_200_characters_is_refused(anchor):
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(anchors=[anchor])))


def test_the_length_is_measured_after_normalising():
    padded = "- " + "a b c d e f g h i"    # 17 characters once the list marker is gone
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(anchors=[padded])))


@pytest.mark.parametrize("field,value", [("kind", "note"), ("origin", "copied"),
                                         ("evidence", {"tier": "felt", "text": "x"}),
                                         ("evidence", {"tier": "argued", "text": ""}),
                                         ("topic", "Env Model")])
def test_a_value_outside_its_vocabulary_is_refused(field, value):
    assert SD.validate_entry(_rule(**{field: value}))


def test_an_unknown_field_is_refused_so_a_typo_cannot_hide_a_reason():
    entry = copy.deepcopy(_rule())
    entry["reopen-if"] = entry.pop("reopen_if")
    problems = SD.validate_entry(entry)
    assert any("reopen-if" in p for p in problems) and any(p.startswith("reopen_if:") for p in problems)
