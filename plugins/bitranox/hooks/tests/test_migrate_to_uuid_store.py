"""Tests for migrate_to_uuid_store.py - copy the legacy `.claude-bx-selflearning/` facts into the
central UUID store additively (delete nothing). All content ASCII."""
import pytest

import memory_engine as E
import uuid_store as us
import migrate_to_uuid_store as M


def _tree(tmp_path):
    """anchor (CLAUDE.md + legacy store) -> proj (CLAUDE.md + legacy store). Returns (anchor, proj)."""
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (proj / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    # seed LEGACY-ONLY facts at two altitudes (suppress the capture->UUID mirror so these tests start
    # from the real migration scenario: pre-existing legacy facts, no UUID store yet). The mirror
    # itself is covered by test_memory_engine.py.
    _orig = E.add_uuid_entry
    E.add_uuid_entry = lambda *a, **k: None
    try:
        E.add_or_update_entry(str(anchor), "Global rule", "always", body="A" * 400, source=["g"], scope_default="anchor scope")
        E.add_or_update_entry(str(proj), "Tiny fact", "a hook", body="small body", source=["p"], pin=True, scope_default="proj scope")
    finally:
        E.add_uuid_entry = _orig
    return str(anchor), str(proj)


def test_find_legacy_stores_lists_both_altitudes(tmp_path):
    anchor, proj = _tree(tmp_path)
    stores = M.find_legacy_stores(str(tmp_path))
    assert sorted(stores) == sorted([anchor, proj])   # returns the OWNING dirs (store parents)


def test_migrate_writes_bodies_and_pointers_for_every_fact(tmp_path):
    anchor, proj = _tree(tmp_path)
    rep = M.migrate(str(tmp_path), dry_run=False)
    assert rep["facts"] == 2 and rep["written"] == 2
    # heavy anchor fact -> central body + pointer at the anchor altitude
    u_g = us.fact_uuid(anchor, "global-rule")
    assert us.body_path(anchor, u_g).read_text(encoding="utf-8") == "A" * 400 + "\n"
    # inline proj fact -> central body (in the SAME anchor store) + pointer at the proj altitude
    u_p = us.fact_uuid(proj, "tiny-fact")
    assert us.body_path(anchor, u_p).read_text(encoding="utf-8") == "small body\n"
    # pointers carry title/hook/provenance/pin
    _s, ptrs = us.parse_pointer_index((tmp_path / "tree" / "proj" / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert ptrs[0].uuid == u_p and ptrs[0].pin is True and ptrs[0].source == {"p"}


def test_migrate_leaves_the_legacy_store_untouched(tmp_path):
    anchor, proj = _tree(tmp_path)
    before = (tmp_path / "tree" / "proj" / ".claude-bx-selflearning" / "index.md").read_text(encoding="utf-8")
    M.migrate(str(tmp_path), dry_run=False)
    after = (tmp_path / "tree" / "proj" / ".claude-bx-selflearning" / "index.md").read_text(encoding="utf-8")
    assert before == after                            # nothing deleted or rewritten


def test_migrate_roundtrips_through_the_resolver(tmp_path):
    anchor, proj = _tree(tmp_path)
    M.migrate(str(tmp_path), dry_run=False)
    got = {r.title: r.body for r in us.resolve(proj)}
    assert got == {"Global rule": "A" * 400, "Tiny fact": "small body"}


def test_migrate_is_idempotent(tmp_path):
    anchor, proj = _tree(tmp_path)
    M.migrate(str(tmp_path), dry_run=False)
    rep2 = M.migrate(str(tmp_path), dry_run=False)    # re-run: same uuids, no dupes
    assert rep2["facts"] == 2
    _s, ptrs = us.parse_pointer_index((tmp_path / "tree" / "proj" / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert len(ptrs) == 1                             # one pointer, not two


def test_dry_run_writes_nothing(tmp_path):
    anchor, proj = _tree(tmp_path)
    rep = M.migrate(str(tmp_path), dry_run=True)
    assert rep["facts"] == 2 and rep["written"] == 0
    assert not (tmp_path / "tree" / ".claude-memory").exists()      # no central store created
    # the legacy seeding already made CLAUDE.local.md (its @import block); dry-run must not add a
    # uuid pointer block to it.
    local = (tmp_path / "tree" / "proj" / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert us.INDEX_BEGIN not in local


def test_cli_dry_run_is_the_default(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    rc = M.main(["--root", str(tmp_path)])            # no --apply -> dry-run
    assert rc == 0
    assert not (tmp_path / "tree" / ".claude-memory").exists()
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "2" in out


# ---- sync + prune: keep the UUID projection faithful as legacy facts are deleted ----------------

def _drop_legacy_fact(proj, slug):
    """Simulate a dream pruning one fact out of the legacy store."""
    scope, entries, bodies = E.read_store(proj)
    entries = [e for e in entries if e.slug != slug]
    E._commit_store(proj, scope, entries, bodies)


def test_sync_prunes_orphan_pointer_and_body_when_legacy_fact_is_gone(tmp_path):
    anchor, proj = _tree(tmp_path)
    M.migrate(str(tmp_path), dry_run=False)
    u_kept = us.fact_uuid(proj, "tiny-fact")
    u_gone = us.fact_uuid(anchor, "global-rule")
    _drop_legacy_fact(anchor, "global-rule")          # dream removed the anchor's heavy fact
    rep = M.sync(str(tmp_path), prune=True)
    assert rep["pruned"] == 1
    # orphan pointer gone from the anchor altitude, kept pointer still present at proj
    _s, ptrs = us.parse_pointer_index((tmp_path / "tree" / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert u_gone not in {p.uuid for p in ptrs}
    got = {r.uuid for r in us.resolve(proj)}
    assert u_kept in got and u_gone not in got
    # orphan body file deleted from the central store
    assert not us.body_path(anchor, u_gone).exists()
    assert us.body_path(anchor, u_kept).exists()


def test_sync_without_prune_leaves_orphans(tmp_path):
    anchor, proj = _tree(tmp_path)
    M.migrate(str(tmp_path), dry_run=False)
    u_gone = us.fact_uuid(anchor, "global-rule")
    _drop_legacy_fact(anchor, "global-rule")
    M.sync(str(tmp_path), prune=False)
    assert us.body_path(anchor, u_gone).exists()      # not pruned -> orphan remains
