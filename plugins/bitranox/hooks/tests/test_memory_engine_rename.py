"""Tests for `memory_engine rename`: correcting a fact's SLUG without orphaning it.

A slug is the fact's identity - the body filename, the pointer's `mem:` target, and the target of
every `[[ref]]` aimed at it. `move`/`relocate` change a fact's LEVEL and never its NAME, so before
this verb a slug whose WORDS had gone wrong (one naming a premise that turned out false) had no
correction path: capturing under a better slug leaves the stale fact live beside the new one, and
hand-editing the store is what the store-edit guard exists to stop.

The load-bearing part is the citation rewrite. A rename that broke inbound `[[refs]]` would be no
better than the capture-and-orphan it replaces. All content ASCII.
"""

from pathlib import Path

import pytest

import memory_engine as E
import uuid_store as us


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _three_levels(tmp_path):
    """anchor -> mid -> proj, each a CLAUDE.md-bearing rung; central store at the anchor."""
    anchor = tmp_path / "tree"
    mid = anchor / "mid"
    proj = mid / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, mid, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return str(anchor), str(mid), str(proj)


def _slugs_at(level):
    _scope, pointers = us.parse_pointer_index((Path(level) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    return {p.slug for p in pointers}


def test_rename_moves_the_pointer_and_the_body_keeping_content(tmp_path):
    """The name changes; the fact does not."""
    anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Wrong name", "hook text", body="the body", source=["cap"], pin=True)

    rep = E.rename_entry(proj, "wrong-name", "right-name")

    assert rep["renamed"] is True and rep["refused"] is None
    assert _slugs_at(proj) == {"right-name"}
    assert "the body" in us.body_path(anchor, "right-name").read_text(encoding="utf-8")
    assert not us.body_path(anchor, "wrong-name").is_file(), "the old body must not stay live"
    _scope, pointers = us.parse_pointer_index((Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    kept = next(p for p in pointers if p.slug == "right-name")
    assert kept.title == "Wrong name" and kept.hook == "hook text" and kept.pin
    assert "cap" in kept.source, "provenance must survive a rename"


def test_the_body_frontmatter_name_follows_the_slug(tmp_path):
    """Otherwise the body asserts one identity and the pointer another."""
    anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Old", "h", body="B")

    E.rename_entry(proj, "old", "new")

    text = us.body_path(anchor, "new").read_text(encoding="utf-8")
    assert "name: new\n" in text and "name: old\n" not in text


def test_inbound_refs_are_repointed_not_broken(tmp_path):
    """The reason rename exists: a citation must survive it.

    Capturing a new fact and orphaning the old one leaves every citer pointing at a slug that no
    longer resolves, which is exactly the outcome this verb is meant to avoid.
    """
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Target", "the renamed one", body="B")
    E.add_or_update_entry(mid, "Citer", "see [[target]] for detail", body="body cites [[target]] too")

    rep = E.rename_entry(proj, "target", "better-target")

    assert rep["renamed"] is True
    _scope, pointers = us.parse_pointer_index((Path(mid) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    citer = next(p for p in pointers if p.slug == "citer")
    assert "[[better-target]]" in citer.hook and "[[target]]" not in citer.hook
    body = us.body_path(anchor, "citer").read_text(encoding="utf-8")
    assert "[[better-target]]" in body and "[[target]]" not in body
    assert {(lvl, s, where) for lvl, s, where in rep["refs_rewritten"]} >= {
        (mid, "citer", "hook"), (mid, "citer", "body")
    }


def test_a_refs_prefix_and_label_belong_to_the_citer_and_survive(tmp_path):
    """`[[reference:x|see here]]` keeps its prefix and label; only the target name changes.

    Those are the citer's wording, not the target's identity, so flattening them to a bare
    `[[y]]` would silently rewrite someone else's sentence.
    """
    _anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Target", "t", body="B")
    E.add_or_update_entry(mid, "Citer", "as [[reference:target|see here]] explains", body="B")

    E.rename_entry(proj, "target", "renamed")

    _scope, pointers = us.parse_pointer_index((Path(mid) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    citer = next(p for p in pointers if p.slug == "citer")
    assert "[[reference:renamed|see here]]" in citer.hook


def test_an_unrelated_ref_is_left_alone(tmp_path):
    """Only the renamed slug is repointed."""
    _anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Target", "t", body="B")
    E.add_or_update_entry(mid, "Citer", "cites [[something-else]] only", body="B")

    E.rename_entry(proj, "target", "renamed")

    _scope, pointers = us.parse_pointer_index((Path(mid) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    citer = next(p for p in pointers if p.slug == "citer")
    assert "[[something-else]]" in citer.hook


def test_rename_onto_a_live_slug_is_refused_no_silent_overwrite(tmp_path):
    """Slugs are tree-unique, so the target name already belongs to a DIFFERENT fact.

    Landing on it would destroy that fact silently. Deduping is a decision, never a side effect.
    """
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "One", "first", body="ONE")
    E.add_or_update_entry(mid, "Two", "second", body="TWO")

    rep = E.rename_entry(proj, "one", "two")

    assert rep["renamed"] is False and "already exists" in rep["refused"]
    assert _slugs_at(proj) == {"one"} and _slugs_at(mid) == {"two"}
    assert "TWO" in us.body_path(anchor, "two").read_text(encoding="utf-8"), "the victim survives intact"


def test_unknown_slug_and_no_op_rename_are_refused(tmp_path):
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Here", "h", body="B")

    assert "not found" in E.rename_entry(proj, "absent", "whatever")["refused"]
    assert "same as the old one" in E.rename_entry(proj, "here", "here")["refused"]


def test_a_non_canonical_new_slug_is_normalised_with_a_warning(tmp_path):
    """The store's identity is the canonical form, so accept sloppy input but say what was stored."""
    anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Old", "h", body="B")

    rep = E.rename_entry(proj, "old", "New Slug_Here")

    assert rep["renamed"] is True and rep["to_slug"] == "new-slug-here"
    assert any("normalised" in w for w in rep["warnings"])
    assert us.body_path(anchor, "new-slug-here").is_file()


def test_the_old_body_is_archived_and_stays_recoverable(tmp_path):
    """Same contract as relocate: the previous copy is recoverable, not deleted."""
    anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Old", "h", body="RECOVER ME")

    E.rename_entry(proj, "old", "new")

    archived = us.central_facts_dir(anchor).parent / ".archive" / "old.md"
    assert archived.is_file() and "RECOVER ME" in archived.read_text(encoding="utf-8")


def test_the_fact_still_resolves_from_below_after_a_rename(tmp_path):
    """Cascade visibility is the point of the pointer index; a rename must not drop out of it."""
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Old", "h", body="B")

    E.rename_entry(proj, "old", "new")

    assert {r.slug for r in us.resolve(proj)} == {"new"}


def test_cli_rename_reports_the_repointed_citers(tmp_path, capsys):
    _anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Target", "t", body="B")
    E.add_or_update_entry(mid, "Citer", "see [[target]]", body="B")

    rc = E.main(["rename", "--level", proj, "--slug", "target", "--to-slug", "renamed"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "renamed target -> renamed" in out
    assert "ref repointed: citer (hook)" in out


def test_cli_rename_refusal_exits_nonzero(tmp_path, capsys):
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Here", "h", body="B")

    rc = E.main(["rename", "--level", proj, "--slug", "absent", "--to-slug", "x"])

    assert rc == 1 and "! refused:" in capsys.readouterr().out
