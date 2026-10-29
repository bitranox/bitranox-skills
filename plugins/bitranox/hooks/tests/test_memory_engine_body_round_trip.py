"""A body handed back to the engine is stored as given, framed once and in sync with the hook.

Three ways a write used to store something other than what the caller meant:

* `_framed_body` joined `---\\n\\n` and the body verbatim, so a body file that opened with a blank
  line got a doubled blank under the frontmatter.
* A body that already CARRIED a frame (the text `factedit.py show --body` prints, or a body read
  back from the store) passed through untouched, so its `description:` kept the OLD hook while the
  pointer got the new one, and an explicit `--type` was ignored.
* The add-time recurrence lint read "Recurrence 2026-10-24" as a count of 2026.

ASCII only.
"""
from pathlib import Path

import pytest

import memory_engine as ME
import uuid_store as us


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


@pytest.fixture
def level(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return p


def _stored(level, slug):
    return us.body_path(ME._anchor(str(level)), slug).read_text(encoding="utf-8")


# ---- leading blank lines --------------------------------------------------------------------------

def test_a_body_opening_with_blank_lines_gets_exactly_one_blank_under_the_frame():
    framed = ME._framed_body("s", "h", "project", "\n\nprose\n")
    assert framed == "---\nname: s\ndescription: h\nmetadata:\n  type: project\n---\n\nprose\n"


def test_stripping_leading_blank_lines_keeps_the_first_content_line_s_indentation():
    framed = ME._framed_body("s", "h", "project", "\n    code block\n")
    assert framed.endswith("---\n\n    code block\n")


def test_reading_a_body_back_and_writing_it_again_is_byte_identical(level):
    slug = ME.add_or_update_entry(str(level), "Rule", "When x, do y.",
                                  body="\nFirst line.\n\nSecond paragraph.\n", type_="feedback")
    first = _stored(level, slug)
    assert "---\n\nFirst line." in first and "---\n\n\nFirst line." not in first
    ME.add_or_update_entry(str(level), "Rule", "When x, do y.", body=first, slug=slug)
    assert _stored(level, slug) == first


# ---- a framed body handed back with a new hook ----------------------------------------------------

def test_a_framed_body_sent_with_a_new_hook_stores_the_new_hook_as_its_description(level):
    slug = ME.add_or_update_entry(str(level), "Rule", "When x, do y.", body="Prose.",
                                  type_="feedback")
    old_text = _stored(level, slug)
    ME.add_or_update_entry(str(level), "Rule", "When x happens, do z.", body=old_text, slug=slug)
    text = _stored(level, slug)
    assert "description: When x happens, do z.\n" in text, text
    assert "do y." not in text
    assert ME._body_type(text) == "feedback"


def test_a_framed_body_on_create_takes_the_hook_as_its_description(level):
    body = "---\nname: whatever\ndescription: stale words\nmetadata:\n  type: reference\n---\n\nP.\n"
    slug = ME.add_or_update_entry(str(level), "Fresh", "When a, do b.", body=body)
    text = _stored(level, slug)
    assert "description: When a, do b.\n" in text and "stale words" not in text
    assert ME._body_type(text) == "reference"
    assert text.startswith("---\nname: %s\n" % slug), text


def test_an_explicit_type_wins_over_the_type_a_framed_body_carries(level):
    slug = ME.add_or_update_entry(str(level), "Rule", "When x, do y.", body="Prose.",
                                  type_="feedback")
    old_text = _stored(level, slug)
    ME.add_or_update_entry(str(level), "Rule", "When x, do y.", body=old_text, slug=slug,
                           type_="reference")
    assert ME._body_type(_stored(level, slug)) == "reference"


def test_a_framed_body_keeps_its_prose_byte_for_byte(level):
    slug = ME.add_or_update_entry(str(level), "Rule", "When x, do y.",
                                  body="Line one.\n  indented\n\ndescription: in prose\n")
    old_text = _stored(level, slug)
    ME.add_or_update_entry(str(level), "Rule", "When x, do z.", body=old_text, slug=slug)
    new_text = _stored(level, slug)
    assert new_text.split("---\n", 2)[2] == old_text.split("---\n", 2)[2]


# ---- recurrence: a date is not a count ------------------------------------------------------------

def test_a_dated_recurrence_heading_is_not_read_as_a_count():
    assert us.recurrence_count("Recurrence 2026-10-24 (the cut came back).") is None


def test_a_dated_recurrence_heading_does_not_hide_a_real_count_beside_it():
    assert us.recurrence_count("Recurrence 2026-10-24 (third). recurrence: 3") == 3


def test_control_a_plain_count_still_reads():
    assert us.recurrence_count("recurrence 2.") == 2
    assert us.recurrence_count("recurrence: 7 (last 2026-10-24)") == 7


# ---- a sideways move names the two-leg route ------------------------------------------------------

def test_a_sibling_move_refusal_names_the_common_ancestor_route(tmp_path):
    anchor = tmp_path / "tree"
    a = anchor / "dept" / "a"
    b = anchor / "dept" / "b"
    for d in (a, b):
        d.mkdir(parents=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    ME.add_or_update_entry(str(a), "F", "When f, do g.", body="B", scope_default="a")
    rep = ME.move_entry(str(a), str(b), "f")
    assert rep["moved"] is False
    refused = rep["refused"] or ""
    assert "sibling" in refused
    # dept carries no CLAUDE.local.md, so the nearest LEVEL above both is the anchor.
    assert str(anchor.resolve()) in refused, refused
    assert "two moves" in refused


def test_the_route_names_a_nearer_common_level_when_one_exists(tmp_path):
    anchor = tmp_path / "tree"
    dept = anchor / "dept"
    a, b = dept / "a", dept / "b"
    for d in (a, b):
        d.mkdir(parents=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (dept / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    ME.ensure_level(str(dept), scope_default="dept")
    ME.add_or_update_entry(str(a), "F", "When f, do g.", body="B", scope_default="a")
    refused = ME.move_entry(str(a), str(b), "f")["refused"] or ""
    assert "--to-level %s" % Path(dept).resolve() in refused, refused
