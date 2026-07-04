"""Tests for migrate_to_uuid_store.py - copy the legacy `.claude-bx-selflearning/` facts into the
central UUID store (delete nothing). The engine is UUID-native now, so these tests seed RAW legacy
stores (index.md + facts/) directly. All content ASCII."""
from pathlib import Path

import self_improve_signals as sig
import uuid_store as us
import migrate_to_uuid_store as M


def _write_legacy(store_dir, scope, facts):
    """Seed a raw legacy store. facts: list of (slug, title, hook, body, source_list, pin, heavy)."""
    store = Path(store_dir)
    (store / "facts").mkdir(parents=True, exist_ok=True)
    lines = ["<!-- bitranox:self-learning -->", scope, "<!-- /bitranox:self-learning -->",
             "", "# Memory index", ""]
    for slug, title, hook, body, source, pin, heavy in facts:
        meta = []
        if source:
            meta.append("bx:src=" + ",".join(source))
        if pin:
            meta.append("bx:pin")
        metac = (" <!-- %s -->" % " ".join(meta)) if meta else ""
        if heavy:
            lines.append("- [%s](facts/%s.md) - %s%s" % (title, slug, hook, metac))
            (store / "facts" / (slug + ".md")).write_text(body + "\n", encoding="utf-8")
        else:
            lines.append("- [%s](#%s) - %s%s" % (title, slug, hook, metac))
            lines.extend("  " + ln for ln in body.split("\n"))
    (store / sig.CURATED_INDEX).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _tree(tmp_path):
    """anchor (CLAUDE.md + legacy store) -> proj (CLAUDE.md + legacy store). Returns (anchor, proj)."""
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (proj / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    _write_legacy(anchor / sig.CURATED_DIRNAME, "anchor scope",
                  [("global-rule", "Global rule", "always", "A" * 400, ["g"], False, True)])
    _write_legacy(proj / sig.CURATED_DIRNAME, "proj scope",
                  [("tiny-fact", "Tiny fact", "a hook", "small body", ["p"], True, False)])
    return str(anchor), str(proj)


def _drop_legacy_fact(store_dir, slug):
    """Simulate a dream pruning one fact out of the legacy store (rewrite without it)."""
    scope, facts = M.read_legacy_store(store_dir)
    keep = [(f["slug"], f["title"], f["hook"], f["body"], sorted(f["source"]), f["pin"], f["heavy"])
            for f in facts if f["slug"] != slug]
    _write_legacy(store_dir, scope, keep)


def test_read_legacy_store_parses_inline_and_heavy(tmp_path):
    _write_legacy(tmp_path / "s", "the scope",
                  [("h", "Heavy", "hook", "H" * 20, ["z"], False, True),
                   ("i", "Inline", "ihook", "line1\nline2", ["a", "b"], True, False)])
    scope, facts = M.read_legacy_store(str(tmp_path / "s"))
    assert scope == "the scope"
    by = {f["slug"]: f for f in facts}
    assert by["h"]["body"] == "H" * 20 and by["h"]["source"] == {"z"}
    assert by["i"]["body"] == "line1\nline2" and by["i"]["pin"] is True


def test_find_legacy_stores_lists_both_altitudes(tmp_path):
    anchor, proj = _tree(tmp_path)
    assert sorted(M.find_legacy_stores(str(tmp_path))) == sorted([anchor, proj])


def test_migrate_writes_bodies_and_pointers_for_every_fact(tmp_path):
    anchor, proj = _tree(tmp_path)
    rep = M.migrate(str(tmp_path), dry_run=False)
    assert rep["facts"] == 2 and rep["written"] == 2
    u_g = us.fact_uuid(anchor, "global-rule")
    assert us.body_path(anchor, u_g).read_text(encoding="utf-8") == "A" * 400 + "\n"
    u_p = us.fact_uuid(proj, "tiny-fact")
    assert us.body_path(anchor, u_p).read_text(encoding="utf-8") == "small body\n"
    _s, ptrs = us.parse_pointer_index((tmp_path / "tree" / "proj" / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert ptrs[0].uuid == u_p and ptrs[0].pin is True and ptrs[0].source == {"p"} and ptrs[0].slug == "tiny-fact"


def test_migrate_leaves_the_legacy_store_untouched(tmp_path):
    anchor, proj = _tree(tmp_path)
    idx = tmp_path / "tree" / "proj" / sig.CURATED_DIRNAME / sig.CURATED_INDEX
    before = idx.read_text(encoding="utf-8")
    M.migrate(str(tmp_path), dry_run=False)
    assert idx.read_text(encoding="utf-8") == before          # nothing deleted or rewritten


def test_migrate_roundtrips_through_the_resolver(tmp_path):
    anchor, proj = _tree(tmp_path)
    M.migrate(str(tmp_path), dry_run=False)
    got = {r.title: (r.body, r.slug) for r in us.resolve(proj)}
    assert got == {"Global rule": ("A" * 400, "global-rule"), "Tiny fact": ("small body", "tiny-fact")}


def test_migrate_is_idempotent(tmp_path):
    anchor, proj = _tree(tmp_path)
    M.migrate(str(tmp_path), dry_run=False)
    M.migrate(str(tmp_path), dry_run=False)                   # re-run: same uuids, no dupes
    _s, ptrs = us.parse_pointer_index((tmp_path / "tree" / "proj" / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert len(ptrs) == 1


def test_dry_run_writes_nothing(tmp_path):
    anchor, proj = _tree(tmp_path)
    rep = M.migrate(str(tmp_path), dry_run=True)
    assert rep["facts"] == 2 and rep["written"] == 0
    assert not (tmp_path / "tree" / ".claude-memory").exists()
    assert not (tmp_path / "tree" / "proj" / "CLAUDE.local.md").exists()   # no pointer file created


def test_cli_dry_run_is_the_default(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    rc = M.main(["--root", str(tmp_path)])
    assert rc == 0
    assert not (tmp_path / "tree" / ".claude-memory").exists()
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "2" in out


def test_sync_prunes_orphan_pointer_and_body_when_legacy_fact_is_gone(tmp_path):
    anchor, proj = _tree(tmp_path)
    M.migrate(str(tmp_path), dry_run=False)
    u_kept = us.fact_uuid(proj, "tiny-fact")
    u_gone = us.fact_uuid(anchor, "global-rule")
    _drop_legacy_fact(str(Path(anchor) / sig.CURATED_DIRNAME), "global-rule")
    rep = M.sync(str(tmp_path), prune=True)
    assert rep["pruned"] == 1
    _s, ptrs = us.parse_pointer_index((tmp_path / "tree" / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert u_gone not in {p.uuid for p in ptrs}
    got = {r.uuid for r in us.resolve(proj)}
    assert u_kept in got and u_gone not in got
    assert not us.body_path(anchor, u_gone).exists()
    assert us.body_path(anchor, u_kept).exists()


def test_sync_without_prune_leaves_orphans(tmp_path):
    anchor, proj = _tree(tmp_path)
    M.migrate(str(tmp_path), dry_run=False)
    u_gone = us.fact_uuid(anchor, "global-rule")
    _drop_legacy_fact(str(Path(anchor) / sig.CURATED_DIRNAME), "global-rule")
    M.sync(str(tmp_path), prune=False)
    assert us.body_path(anchor, u_gone).exists()
