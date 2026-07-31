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


# ---- C1: the hard hook cap REFUSES, it does not truncate ----------------------------------------

OVER_CAP_HOOK = "When x, " + "yy " * 400        # ~1200 chars


def test_hook_over_hard_cap_predicate():
    assert not us.hook_over_hard_cap(None) and not us.hook_over_hard_cap("a short hook")
    assert not us.hook_over_hard_cap("x" * us.HOOK_HARD_MAX)          # the cap itself is allowed
    assert us.hook_over_hard_cap("x" * (us.HOOK_HARD_MAX + 1))
    assert not us.hook_over_hard_cap(" " + "x" * us.HOOK_HARD_MAX + " ")   # measured after strip


def test_add_refuses_an_over_cap_hook_and_writes_nothing(proj):
    with pytest.raises(E.HookTooLong):
        E.add_or_update_entry(proj, "Title", OVER_CAP_HOOK, body="B", type_="reference")
    assert E.read_store(proj)[1] == []                          # no pointer
    assert not us.body_path(proj, "reference-title").is_file()   # and no body


def test_add_refusal_leaves_an_existing_entry_untouched(proj):
    slug = E.add_or_update_entry(proj, "Title", "When x, do y.", body="B", type_="reference")
    with pytest.raises(E.HookTooLong):
        E.add_or_update_entry(proj, "Title", OVER_CAP_HOOK, type_="reference")
    entry = E.read_store(proj)[1][0]
    assert entry.slug == slug and entry.hook == "When x, do y."


def test_a_mover_may_carry_an_already_stored_over_cap_hook_verbatim(proj):
    """rehome/migrate MOVE text that is already in a store; refusing there would strand the fact."""
    E.add_or_update_entry(proj, "Title", OVER_CAP_HOOK, body="B", type_="reference",
                          allow_over_cap_hook=True)
    assert E.read_store(proj)[1][0].hook == OVER_CAP_HOOK.strip()


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


def test_bracketed_title_round_trips_and_does_not_orphan(proj):
    # a `[dev]` in the title used to make the pointer line unparseable (`_PTR_RX` title is `[^\]]*`),
    # so it was silently DROPPED on the next block round-trip, orphaning the body. It must survive now.
    slug = E.add_or_update_entry(proj, "bmk make test gets [dev] via bmk 3.1.7", "When x, do y.",
                                 body="Body.", type_="reference")
    assert any(e.slug == slug for e in E.read_store(proj)[1])          # parses back, does not vanish
    # survives a re-serialization (a heal-like read -> commit -> read cycle):
    E.add_or_update_entry(proj, "bmk make test gets [dev] via bmk 3.1.7", "When x, do y sharper.",
                          body="", type_="reference")
    assert any(e.slug == slug for e in E.read_store(proj)[1])
    local = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    assert "(dev)" in local                                            # brackets sanitized in the line


def test_add_refuses_when_an_ancestor_owns_the_slug(proj):
    # a CLAUDE.md makes `proj` the anchor, so `child` shares its store and altitude chain
    (Path(proj) / "CLAUDE.md").write_text("# proj\n", encoding="utf-8")
    E.add_or_update_entry(proj, "Owned Fact", "When x.", body="B", type_="reference")
    child = str(Path(proj) / "child")
    Path(child).mkdir()
    with pytest.raises(E.SlugCollision):                        # an ancestor owns it -> real collision
        E.add_or_update_entry(child, "Owned Fact", "When x.", body="B2", type_="reference")
