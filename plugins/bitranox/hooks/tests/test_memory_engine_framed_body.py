"""A body is passed through unframed only when it really carries frontmatter. ASCII only.

`_framed_body` used to pass through any body that merely STARTED with `---`, so a body opening with
a markdown horizontal rule was stored as-is: no name, no description, no type. Every later reader
of the frame then found none, and reconcile reported the fact as frame-only.
"""
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


def _stored(level, slug):
    return us.body_path(ME._anchor(str(level)), slug).read_text(encoding="utf-8")


def test_a_body_opening_with_a_rule_is_framed(tmp_path):
    level = tmp_path / "proj"
    level.mkdir()
    slug = ME.add_or_update_entry(str(level), "Rule", "When x, do y.",
                                  body="---\nAlways do X because Y.", type_="reference")
    text = _stored(level, slug)
    assert text.startswith("---\nname: %s\ndescription: When x, do y.\n" % slug)
    assert "type: reference" in text
    assert text.rstrip("\n").endswith("---\nAlways do X because Y.")


def test_a_body_with_rules_but_no_name_key_is_framed():
    framed = ME._framed_body("s", "h", "project", "---\nnot frontmatter\n---\nprose")
    assert framed.startswith("---\nname: s\n")
    assert framed.endswith("---\nnot frontmatter\n---\nprose")


def test_a_body_that_already_carries_frontmatter_passes_through_unchanged():
    body = "---\nname: s\ndescription: own\nmetadata:\n  type: user\n---\n\nprose\n"
    assert ME._framed_body("s", "h", "project", body) == body


def test_a_crlf_frontmatter_body_passes_through_unchanged():
    body = "---\r\nname: s\r\ndescription: own\r\n---\r\nprose\r\n"
    assert ME._framed_body("s", "h", "project", body) == body


def test_a_plain_body_is_framed_as_before():
    framed = ME._framed_body("s", "the hook", None, "plain prose")
    assert framed == ("---\nname: s\ndescription: the hook\nmetadata:\n  type: project\n---\n\n"
                      "plain prose")


# ---- the frame READERS and REWRITERS use the same detection as the writer ---------------------
#
# `_framed_body` does not treat a leading horizontal rule as frontmatter, and neither may the three
# helpers that read or rewrite an EXISTING body. Asking only `startswith("---")`, a body stored as
# "---\nprose" was re-typed by APPENDING a `metadata:` block to its prose.

RULE_BODY = "---\nAlways do X because Y."


def test_retyping_a_body_that_opens_with_a_rule_frames_it_and_keeps_the_prose(tmp_path):
    level = tmp_path / "proj"
    level.mkdir()
    slug = ME.add_or_update_entry(str(level), "Rule", "When x, do y.", body="placeholder",
                                  type_="project")
    us.body_path(ME._anchor(str(level)), slug).write_text(RULE_BODY + "\n", encoding="utf-8")
    ME.add_or_update_entry(str(level), "Rule", "When x, do y.", type_="feedback", slug=slug)
    text = _stored(level, slug)
    assert text.startswith(f"---\nname: {slug}\n"), text
    assert ME._body_type(text) == "feedback"
    assert text.rstrip("\n").endswith(RULE_BODY), text
    assert "because Y.\nmetadata:" not in text


def test_a_type_line_in_prose_under_a_rule_is_not_the_body_type():
    assert ME._body_type("---\nSome text\n  type: feedback\n") == ""


def test_the_description_of_a_body_opening_with_a_rule_is_left_alone():
    body = "---\nprose\ndescription: keep me\n"
    assert ME._reframe_description(body, "new hook") == body


def test_a_description_line_in_the_prose_is_never_rewritten():
    body = "---\nname: s\nmetadata:\n  type: user\n---\n\ndescription: keep me\n"
    assert ME._reframe_description(body, "new hook") == body


def test_a_real_frame_still_has_its_description_and_type_rewritten():
    """Control: the narrowing must not stop the helpers working on a genuine frame."""
    body = "---\nname: s\ndescription: old\nmetadata:\n  type: user\n---\n\nprose\n"
    assert "description: new hook\n" in ME._reframe_description(body, "new hook")
    retyped = ME._retype_body("s", "h", "feedback", body)
    assert ME._body_type(retyped) == "feedback" and retyped.endswith("---\n\nprose\n")


def test_a_real_frame_with_no_type_line_gains_one_inside_the_frame():
    body = "---\nname: s\ndescription: d\n---\n\nprose\n"
    retyped = ME._retype_body("s", "h", "reference", body)
    assert ME._body_type(retyped) == "reference"
    assert retyped.endswith("---\n\nprose\n"), retyped


def test_a_crlf_frame_is_retyped_inside_the_frame():
    body = "---\r\nname: s\r\ndescription: d\r\nmetadata:\r\n  type: user\r\n---\r\n\r\nprose\r\n"
    retyped = ME._retype_body("s", "h", "feedback", body)
    assert ME._body_type(retyped) == "feedback"
    assert retyped.endswith("---\r\n\r\nprose\r\n"), retyped
