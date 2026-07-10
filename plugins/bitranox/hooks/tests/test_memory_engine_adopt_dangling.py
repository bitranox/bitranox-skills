"""Tests for the dangling-body recovery on the add path: the hard hook cap, and `add` re-adopting an
orphaned central body instead of refusing (the fix for stuck 'stale' entries). All content ASCII."""

from pathlib import Path

import pytest

import self_improve_signals as sig
import memory_engine as E
import uuid_store as us


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return str(p)


def _drop_pointer(proj, slug):
    """Orphan a fact: strip its pointer line from CLAUDE.local.md, leave the central body in place
    (mimics a formatter mangling the line and a heal round-trip then dropping it)."""
    path = sig.claude_local_md_path(proj)
    text = path.read_text(encoding="utf-8")
    kept = [ln for ln in text.splitlines() if ("mem:%s)" % slug) not in ln]
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")


# ---- C1: hard hook cap --------------------------------------------------------------------------

def test_cap_hook_leaves_short_and_truncates_long_at_word_boundary():
    assert us.cap_hook("a short hook") == "a short hook"
    capped = us.cap_hook("When something happens " * 40)   # ~920 chars
    assert len(capped) <= us.HOOK_HARD_MAX
    assert capped == capped.rstrip() and " " in capped     # word boundary, no trailing space


def test_add_hard_caps_an_over_long_hook(proj):
    E.add_or_update_entry(proj, "Title", "When x, " + "yy " * 400, body="B", type_="reference")
    assert len(E.read_store(proj)[1][0].hook) <= us.HOOK_HARD_MAX


# ---- A: add re-adopts a dangling body -----------------------------------------------------------

def test_add_readopts_a_dangling_body_instead_of_refusing(proj):
    slug = E.add_or_update_entry(proj, "Reusable Fact", "When x, do y.", body="Original body.",
                                 type_="reference")
    _drop_pointer(proj, slug)
    assert all(e.slug != slug for e in E.read_store(proj)[1])   # orphaned: no pointer
    assert us.body_path(proj, slug).is_file()                   # body still registers the slug

    slug2 = E.add_or_update_entry(proj, "Reusable Fact", "When x, do y sharpened.", body="",
                                  type_="reference")            # re-capture: must re-adopt
    assert slug2 == slug
    entries = E.read_store(proj)[1]
    assert any(e.slug == slug for e in entries)                 # pointer restored
    assert entries[0].hook == "When x, do y sharpened."         # hook updated
    assert "Original body." in E.read_store(proj)[2][slug]      # empty body arg preserves the body


def test_add_refuses_when_an_ancestor_owns_the_slug(proj):
    # a CLAUDE.md makes `proj` the anchor, so `child` shares its store and altitude chain
    (Path(proj) / "CLAUDE.md").write_text("# proj\n", encoding="utf-8")
    E.add_or_update_entry(proj, "Owned Fact", "When x.", body="B", type_="reference")
    child = str(Path(proj) / "child")
    Path(child).mkdir()
    with pytest.raises(E.SlugCollision):                        # an ancestor owns it -> real collision
        E.add_or_update_entry(child, "Owned Fact", "When x.", body="B2", type_="reference")
