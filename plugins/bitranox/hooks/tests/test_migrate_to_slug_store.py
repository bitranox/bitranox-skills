"""Tests for migrate_to_slug_store.py (uuid-sharded -> slug-named store migration). ASCII."""
from pathlib import Path

import uuid_store as us
import migrate_to_slug_store as MS


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
