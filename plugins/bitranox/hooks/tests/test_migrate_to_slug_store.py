"""Tests for migrate_to_slug_store.py (uuid-sharded -> slug-named store migration). ASCII."""
import os
import stat
from pathlib import Path, PureWindowsPath

import pytest

import uuid_store as us
import migrate_to_slug_store as MS


@pytest.fixture(autouse=True)
def _scratch_home(tmp_path, monkeypatch):
    """Every tree here lives under a scratch HOME: the walk prunes the machine-local audit dir by
    resolving it from HOME, and nothing may reach the real ~/.claude."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


def _legacy_tree(tmp_path, extra_level_same_slug=False):
    """A tree with OLD-format blocks (old fence, uuid: lines, sharded bodies)."""
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (proj / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()

    def plant(level, slug, body):
        u = us.fact_uuid(str(level), slug)
        bp = us.legacy_body_path(str(anchor), u)
        bp.parent.mkdir(parents=True, exist_ok=True)
        bp.write_text(body + "\n", encoding="utf-8")
        return "- [%s](uuid:%s) - a hook <!-- bx:src=x bx:slug=%s -->" % (slug.title(), u, slug)

    lines_proj = [plant(proj, "proj-fact", "PROJ BODY")]
    lines_anchor = [plant(anchor, "anchor-fact", "ANCHOR BODY")]
    if extra_level_same_slug:
        lines_anchor.append(plant(anchor, "proj-fact", "DIFFERENT BODY SAME SLUG"))
    for level, lines in ((proj, lines_proj), (anchor, lines_anchor)):
        block = ("%s\n<!-- bitranox:self-learning -->\nlvl scope\n<!-- /bitranox:self-learning -->\n\n"
                 "# Memory index\n\n%s\n%s\n") % (us.LEGACY_INDEX_BEGIN, "\n".join(lines),
                                                  us.LEGACY_INDEX_END)
        (level / "CLAUDE.local.md").write_text(block, encoding="utf-8")
    return anchor, proj


def test_dry_run_reports_and_writes_nothing(tmp_path):
    anchor, proj = _legacy_tree(tmp_path)
    before = (proj / "CLAUDE.local.md").read_text(encoding="utf-8")
    rep = MS.migrate([str(tmp_path)], apply=False)
    assert rep["legacy_lines"] == 2 and rep["moved"] == 0 and rep["collisions"] == 0
    assert (proj / "CLAUDE.local.md").read_text(encoding="utf-8") == before
    assert not us.body_path(anchor, "proj-fact").exists()


def test_apply_moves_bodies_flips_lines_and_adds_recipe(tmp_path):
    anchor, proj = _legacy_tree(tmp_path)
    rep = MS.migrate([str(tmp_path)], apply=True)
    assert rep["moved"] == 2 and rep["missing"] == 0
    # bodies at slug paths; old sharded files gone
    assert us.body_path(anchor, "proj-fact").read_text(encoding="utf-8") == "PROJ BODY\n"
    assert us.body_path(anchor, "anchor-fact").read_text(encoding="utf-8") == "ANCHOR BODY\n"
    assert not any(us.central_facts_dir(anchor).glob("*/*.md"))
    # blocks rewritten: new fence, mem: lines, recipe, no legacy remnants
    local = (proj / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert us.INDEX_BEGIN in local and us.LEGACY_INDEX_BEGIN not in local
    assert "(mem:proj-fact)" in local and "uuid:" not in local and "walk UP" in local
    # resolve roundtrip
    got = {r.slug: r.body for r in us.resolve(str(proj))}
    assert got == {"proj-fact": "PROJ BODY", "anchor-fact": "ANCHOR BODY"}
    # backup exists
    assert rep["backups"] and Path(rep["backups"][0]).is_dir()


def test_apply_is_idempotent(tmp_path):
    anchor, proj = _legacy_tree(tmp_path)
    MS.migrate([str(tmp_path)], apply=True)
    rep2 = MS.migrate([str(tmp_path)], apply=True)
    assert rep2["legacy_lines"] == 0 and rep2["moved"] == 0


def test_cross_level_slug_collision_gets_suffixed_and_reported(tmp_path):
    anchor, proj = _legacy_tree(tmp_path, extra_level_same_slug=True)
    rep = MS.migrate([str(tmp_path)], apply=True)
    assert rep["collisions"] == 1
    bodies = {p.stem: p.read_text(encoding="utf-8").strip()
              for p in us.central_facts_dir(anchor).glob("*.md")}
    assert bodies["proj-fact"] in ("PROJ BODY", "DIFFERENT BODY SAME SLUG")
    assert bodies["proj-fact-2"] != bodies["proj-fact"]   # both facts survive under distinct slugs
    got = {r.slug for r in us.resolve(str(proj))}
    assert {"proj-fact", "proj-fact-2", "anchor-fact"} <= got


def test_missing_old_body_leaves_line_legacy_and_reports(tmp_path):
    anchor, proj = _legacy_tree(tmp_path)
    # delete one old body before migrating
    u = us.fact_uuid(str(proj), "proj-fact")
    us.legacy_body_path(str(anchor), u).unlink()
    rep = MS.migrate([str(tmp_path)], apply=True)
    assert rep["missing"] == 1 and rep["moved"] == 1
    local = (proj / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "uuid:%s" % u in local                     # NOT flipped (body unmovable), still visible


# ---- a legacy fact must never be pointed at a body another fact already owns -------------------

def _legacy_line(anchor, level, slug, body):
    """Plant a pre-pivot body at its sharded path and return its `uuid:` pointer line."""
    u = us.fact_uuid(str(level), slug)
    bp = us.legacy_body_path(str(anchor), u)
    bp.parent.mkdir(parents=True, exist_ok=True)
    bp.write_text(body + "\n", encoding="utf-8")
    return "- [%s](uuid:%s) - a hook <!-- bx:src=x bx:slug=%s -->" % (slug.title(), u, slug)


def _legacy_block(lines):
    return ("%s\n<!-- bitranox:self-learning -->\nlvl scope\n<!-- /bitranox:self-learning -->\n\n"
            "# Memory index\n\n%s\n%s\n") % (us.LEGACY_INDEX_BEGIN, "\n".join(lines),
                                             us.LEGACY_INDEX_END)


def _tree(root, name="tree"):
    anchor = root / name
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (proj / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return anchor, proj


def _mixed_tree(tmp_path):
    """The ANCHOR holds a legacy `foo`; the PROJ level already holds a migrated `foo` with its own
    body. The walk reaches the anchor's file first, before the migrated pointer is seen."""
    anchor, proj = _tree(tmp_path)
    (anchor / "CLAUDE.local.md").write_text(
        _legacy_block([_legacy_line(anchor, anchor, "foo", "ANCHOR LEGACY BODY")]), encoding="utf-8")
    us.put_body(anchor, "foo", "PROJ MIGRATED BODY")
    (proj / "CLAUDE.local.md").write_text(
        us.upsert_pointer_block("", "proj scope", [us.Pointer(slug="foo", title="Foo", hook="h")]),
        encoding="utf-8")
    return anchor, proj


def _only_pointer(level):
    _scope, pointers = us.parse_pointer_index((level / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert len(pointers) == 1
    return pointers[0]


def test_a_legacy_fact_sharing_a_migrated_slug_keeps_its_own_body(tmp_path):
    anchor, proj = _mixed_tree(tmp_path)
    rep = MS.migrate([str(tmp_path)], apply=True)
    migrated = _only_pointer(anchor)
    assert not migrated.legacy
    assert migrated.slug != "foo"
    assert us.body_path(anchor, migrated.slug).read_text(encoding="utf-8") == "ANCHOR LEGACY BODY\n"
    assert us.body_path(anchor, "foo").read_text(encoding="utf-8") == "PROJ MIGRATED BODY\n"
    assert not any(us.central_facts_dir(anchor).glob("*/*.md"))      # nothing left orphaned
    assert rep["collisions"] == 1


def test_a_migrated_pointer_whose_body_is_missing_still_owns_its_slug(tmp_path):
    """The registry, not the disk: a migrated `foo` with no body file is an orphan pointer, and a
    legacy fact moved onto `foo` would silently become what that pointer resolves to."""
    anchor, proj = _mixed_tree(tmp_path)
    us.body_path(anchor, "foo").unlink()
    rep = MS.migrate([str(tmp_path)], apply=True)
    assert _only_pointer(anchor).slug == "foo-2" and rep["collisions"] == 1
    assert not us.body_path(anchor, "foo").exists()


def test_a_dangling_body_at_the_slug_path_is_a_collision_too(tmp_path):
    """A body file nobody points at still belongs to some fact; moving onto it is not allowed."""
    anchor, _proj = _tree(tmp_path)
    (anchor / "CLAUDE.local.md").write_text(
        _legacy_block([_legacy_line(anchor, anchor, "foo", "LEGACY BODY")]), encoding="utf-8")
    us.put_body(anchor, "foo", "DANGLING BODY")
    rep = MS.migrate([str(tmp_path)], apply=True)
    migrated = _only_pointer(anchor)
    assert migrated.slug == "foo-2" and rep["collisions"] == 1
    assert us.body_path(anchor, "foo-2").read_text(encoding="utf-8") == "LEGACY BODY\n"
    assert us.body_path(anchor, "foo").read_text(encoding="utf-8") == "DANGLING BODY\n"


def test_the_same_slug_in_two_independent_trees_is_not_a_collision(tmp_path):
    """Control for the registry: slugs are unique per TREE, so a migrated `foo` in one tree says
    nothing about a legacy `foo` in another under the same --root."""
    a1, _p1 = _tree(tmp_path, "t1")
    a2, _p2 = _tree(tmp_path, "t2")
    us.put_body(a1, "foo", "T1 BODY")
    (a1 / "CLAUDE.local.md").write_text(
        us.upsert_pointer_block("", "t1", [us.Pointer(slug="foo", title="Foo", hook="h")]),
        encoding="utf-8")
    (a2 / "CLAUDE.local.md").write_text(
        _legacy_block([_legacy_line(a2, a2, "foo", "T2 BODY")]), encoding="utf-8")
    rep = MS.migrate([str(tmp_path)], apply=True)
    assert rep["collisions"] == 0
    assert _only_pointer(a2).slug == "foo"
    assert us.body_path(a2, "foo").read_text(encoding="utf-8") == "T2 BODY\n"


# ---- an undecodable CLAUDE.local.md is reported, not fatal -------------------------------------

def test_a_non_utf8_pointer_file_is_reported_and_the_rest_still_migrates(tmp_path, capsys):
    _legacy_tree(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    (other / "CLAUDE.local.md").write_bytes(b"caf\xe9 " + us.LEGACY_INDEX_BEGIN.encode("ascii"))
    rep = MS.migrate([str(tmp_path)], apply=False)
    assert rep["legacy_lines"] == 2
    assert rep["unreadable"] == [str(other / "CLAUDE.local.md")]
    assert MS.main(["--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "UNREADABLE" in out and str(other / "CLAUDE.local.md") in out


# ---- a failed backup stops the apply -----------------------------------------------------------

def test_a_failed_backup_aborts_the_apply_with_a_non_zero_exit(tmp_path, capsys):
    if os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0):
        pytest.skip("needs a POSIX permission bit that the current user cannot override")
    anchor, proj = _tree(tmp_path)
    (proj / "CLAUDE.local.md").write_text(
        _legacy_block([_legacy_line(anchor, proj, "proj-fact", "PROJ BODY")]), encoding="utf-8")
    before = (proj / "CLAUDE.local.md").read_text(encoding="utf-8")
    mode = anchor.stat().st_mode
    # The backup dir goes under the anchor, so it cannot be created; the store and the level's own
    # file stay writable, so nothing else would stop the apply.
    anchor.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        rc = MS.main(["--root", str(tmp_path), "--apply"])
    finally:
        anchor.chmod(mode)
    assert (proj / "CLAUDE.local.md").read_text(encoding="utf-8") == before
    assert not us.body_path(anchor, "proj-fact").exists()
    assert rc != 0
    assert "backup" in capsys.readouterr().err.lower()


def test_a_successful_backup_holds_every_touched_pointer_file(tmp_path):
    """Control: with a writable anchor the apply proceeds and each file is recoverable."""
    anchor, proj = _legacy_tree(tmp_path)
    before = (proj / "CLAUDE.local.md").read_text(encoding="utf-8")
    rep = MS.migrate([str(tmp_path)], apply=True)
    bdir = Path(rep["backups"][0])
    manifest = (bdir / "manifest.txt").read_text(encoding="utf-8").splitlines()
    saved = {line.split("\t")[1]: bdir / line.split("\t")[0] for line in manifest}
    assert saved[str(proj / "CLAUDE.local.md")].read_text(encoding="utf-8") == before
    assert bdir in saved[str(proj / "CLAUDE.local.md")].parents


# ---- the backup path stays inside the backup dir on Windows ------------------------------------

def test_backup_rel_of_a_windows_path_lands_inside_the_backup_dir():
    local = PureWindowsPath(r"C:\Users\me\proj\CLAUDE.local.md")
    anchor = PureWindowsPath(r"C:\Users\me")
    bdir = PureWindowsPath(r"C:\Users\me\.claude-memory-migration-backup-1")
    target = bdir / MS.backup_rel(local, anchor)
    assert target != local
    assert bdir in target.parents


def test_backup_rel_of_a_path_outside_the_anchor_is_flattened_not_absolute():
    rel = MS.backup_rel(PureWindowsPath(r"D:\elsewhere\CLAUDE.local.md"),
                        PureWindowsPath(r"C:\Users\me"))
    assert not rel.is_absolute() and not rel.drive
    assert len(rel.parts) == 1


# ---- trees under a hidden directory are walked -------------------------------------------------

def test_a_tree_under_a_hidden_dir_is_found(tmp_path):
    """A checkout under `.claude/worktrees/` is a tree like any other; pruning every dot-dir gave a
    false "0 legacy" there."""
    anchor, _proj = _tree(tmp_path / "repo" / ".claude" / "worktrees", "wt")
    (anchor / "CLAUDE.local.md").write_text(
        _legacy_block([_legacy_line(anchor, anchor, "foo", "WT BODY")]), encoding="utf-8")
    assert MS.find_pointer_files(str(tmp_path)) == [anchor / "CLAUDE.local.md"]


def test_stores_backups_and_the_audit_dir_are_still_not_walked(tmp_path, _scratch_home):
    """Control: a copy of a pointer block inside a store, a migration backup or the dream's audit
    dir is a snapshot, not a live level."""
    block = _legacy_block(["- [X](uuid:00000000-0000-0000-0000-000000000000) - h <!-- bx:slug=x -->"])
    for d in (tmp_path / "t" / ".claude-memory" / "sub",
              tmp_path / "t" / ".claude-memory-migration-backup-20260101-000000" / "levels",
              tmp_path / "t" / "old.bak",
              _scratch_home / ".claude" / "self-improve-audit" / "dream-backup" / "lvl"):
        d.mkdir(parents=True)
        (d / "CLAUDE.local.md").write_text(block, encoding="utf-8")
    assert MS.find_pointer_files(str(tmp_path)) == []
