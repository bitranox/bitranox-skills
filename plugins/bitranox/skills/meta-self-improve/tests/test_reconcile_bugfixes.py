"""Bug-fix regression tests for reconcile_memory_index (found during the 2026-07-19 deep dream).

A - `--dry-run --archive` must write NOTHING (it wrote for real).
B - `--archive` at a HIGH level must NOT archive the body when a DESCENDANT level still points at
    the slug (the guard only walked the altitude chain, so descendants were invisible -> orphan pointer).
C - `check_tree` must report a dangling `[[ref]]` (regression guard; C was a concurrent-store
    artifact in the field, not a code defect - this proves the detection itself is correct).
All content ASCII.
"""
import shutil
from pathlib import Path

import reconcile_memory_index as R
import memory_engine as E


def _two_level_tree(tmp_path):
    """top (anchor, CLAUDE.md + store) with a nested sub level (CLAUDE.md), both pointing at ONE slug.

    `add` refuses to create a second pointer for a tree-unique slug (SlugCollision), so the duplicate
    is built the way it arises in the field: a promotion/copy leaves a lower pointer behind. We copy
    top's pointer file down to sub so both levels point at the one central body.
    """
    top = tmp_path / "top"
    top.mkdir()
    (top / "CLAUDE.md").write_text("top\n", encoding="utf-8")
    sub = top / "sub"
    sub.mkdir()
    (sub / "CLAUDE.md").write_text("sub\n", encoding="utf-8")
    slug = E.add_or_update_entry(str(top), "Shared Fact", "When x, do y.", body="Keep me.",
                                 type_="reference")
    shutil.copy(top / "CLAUDE.local.md", sub / "CLAUDE.local.md")   # leave a duplicate lower pointer
    return top, sub, slug


def _central_body(top, slug):
    return top / ".claude-memory" / "facts" / (slug + ".md")


# ---- Bug A: --dry-run --archive writes nothing -------------------------------------------------
def test_archive_dry_run_writes_nothing(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    slug = E.add_or_update_entry(str(proj), "Fact", "When x.", body="B", type_="reference")
    body = _central_body(proj, slug)
    assert body.is_file()
    rc = R.main(["--dry-run", "--archive", slug, str(proj)])
    assert rc == 0
    assert body.is_file(), "dry-run must NOT move the body to .archive"
    assert any(e.slug == slug for e in E.read_store(str(proj))[1]), "dry-run must NOT drop the pointer"


def test_archive_entry_dry_run_kwarg(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    slug = E.add_or_update_entry(str(proj), "Fact", "When x.", body="B", type_="reference")
    R.archive_entry(str(proj), slug, dry_run=True)
    assert _central_body(proj, slug).is_file()
    assert any(e.slug == slug for e in E.read_store(str(proj))[1])


# ---- Bug B: descendant level still pointing must block body archival ---------------------------
def test_archive_at_top_keeps_body_when_descendant_still_points(tmp_path):
    top, sub, slug = _two_level_tree(tmp_path)
    # sanity: the fixture really is a two-level duplicate under one anchor
    assert slug in R.check_tree(str(top))["duplicates"]
    R.archive_entry(str(top), slug)                       # drop the TOP pointer only
    assert _central_body(top, slug).is_file(), "body must survive: the sub level still points at it"
    # and the sub pointer must still resolve (no orphan pointer)
    rep = R.check_tree(str(top))
    assert rep["orphan_pointers"] == [], "sub pointer must still resolve to a live body"
    assert slug not in rep["duplicates"], "the duplicate is resolved (only sub points now)"


# ---- Bug C: check_tree DOES report a dangling ref (regression guard) ---------------------------
def test_check_tree_reports_a_dangling_ref(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    E.add_or_update_entry(str(proj), "Citing Fact", "When x.",
                          body="See [[totally-nonexistent-slug]].", type_="reference")
    refs = [r for (_lvl, _src, r) in R.check_tree(str(proj))["orphan_refs"]]
    assert "totally-nonexistent-slug" in refs
