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


def test_check_on_a_project_dir_resolves_refs_against_its_ancestors(tmp_path):
    """D - `--check <project-dir>` must not report an UPWARD ref as an orphan.

    `[[refs]]` are upward-only by spec, so a project-level fact citing a fact whose pointer lives at
    an ANCESTOR level is the correct shape, not a defect. Resolving only against the dirs passed in
    reported every such ref as an orphan: measured 5 false orphans from a project dir against 0 from
    the anchor on the same data. A verifier that cries wolf teaches the reader to ignore it, so a
    genuinely dangling ref then reads exactly like the noise.
    """
    import self_improve_signals as sig            # reconcile puts hooks/ on sys.path at import

    top = tmp_path / "top"
    top.mkdir()
    (top / "CLAUDE.md").write_text("top\n", encoding="utf-8")
    sub = top / "sub"
    sub.mkdir()
    (sub / "CLAUDE.md").write_text("sub\n", encoding="utf-8")

    general = E.add_or_update_entry(str(top), "General rule", "the general rule", body="b",
                                    scope_default="top")
    E.add_or_update_entry(str(sub), "Local delta", "cites [[%s]] plus a delta" % general, body="b",
                          scope_default="sub")

    # Precondition, not decoration: if an ambient CLAUDE.md above tmp_path hijacked the walk, the
    # chain would not reach `top` and this test could pass for entirely the wrong reason.
    chain = [str(Path(d).resolve()) for d in sig.altitude_chain(str(sub))]
    assert str(top.resolve()) in chain, "fixture did not build a real two-level chain: %s" % chain

    refs = R.check_references([str(sub)])
    assert refs["checked"] >= 1, "no ref was examined, so an empty orphan list proves nothing"
    assert refs["orphans"] == [], "upward ref to an ancestor level reported as an orphan"


def test_explicit_chain_still_flags_a_downward_ref(tmp_path):
    """The ancestor expansion must not blind the DOWNWARD check when a full chain is passed.

    Ancestors are added as target providers only when the caller did not already pass them; adding
    a level twice would give its slug a broader position too, and `max(where) < pos` would then
    never fire.
    """
    top = tmp_path / "top"
    top.mkdir()
    (top / "CLAUDE.md").write_text("top\n", encoding="utf-8")
    sub = top / "sub"
    sub.mkdir()
    (sub / "CLAUDE.md").write_text("sub\n", encoding="utf-8")

    low = E.add_or_update_entry(str(sub), "Low fact", "narrow", body="b", scope_default="sub")
    E.add_or_update_entry(str(top), "High fact", "points [[%s]] down" % low, body="b",
                          scope_default="top")

    refs = R.check_references([str(sub), str(top)])
    assert ("high-fact", low) in refs["downward"]


def test_cli_relative_dir_matches_absolute(tmp_path, monkeypatch, capsys):
    """E - a RELATIVE dir argument must produce the same verdict as its absolute form.

    Relative input reached level/anchor resolution in several downstream paths and produced
    confident nonsense instead of an error: on the real store `--check .` examined 0 refs and
    printed success, while `--check-tree .` invented 33 problems and labelled every level "[.]".
    Absolutizing the dirs once at the CLI boundary makes every path agree.
    """
    top = tmp_path / "top"
    (top / "proj").mkdir(parents=True)
    (top / "CLAUDE.md").write_text("top\n", encoding="utf-8")

    general = E.add_or_update_entry(str(top), "General rule", "the general rule", body="b",
                                    scope_default="top")
    E.add_or_update_entry(str(top / "proj"), "Local delta", "cites [[%s]]" % general, body="b",
                          scope_default="proj")

    R.main(["--check", str(top / "proj")])
    absolute = capsys.readouterr().out

    monkeypatch.chdir(top / "proj")
    R.main(["--check", "."])
    relative = capsys.readouterr().out

    assert "ref(s) checked" in absolute, "fixture produced no reference report to compare"
    assert relative == absolute
