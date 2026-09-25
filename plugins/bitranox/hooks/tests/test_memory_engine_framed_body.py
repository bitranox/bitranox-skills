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
