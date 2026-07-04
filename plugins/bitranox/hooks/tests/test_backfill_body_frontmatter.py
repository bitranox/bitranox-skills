"""Tests for backfill_body_frontmatter.py (frame bare bodies as native memory entries). ASCII."""
import backfill_body_frontmatter as BF
import memory_engine as E
import uuid_store as us


def _tree(tmp_path):
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (proj / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return anchor, proj


def test_dry_run_reports_and_writes_nothing(tmp_path):
    anchor, proj = _tree(tmp_path)
    E.add_or_update_entry(str(proj), "F", "When testing, do x.", body="B", scope_default="p")
    us.write_if_changed(us.body_path(anchor, "f"), "bare prose body\n")   # strip the frame
    rep = BF.backfill([str(tmp_path)], apply=False)
    assert rep["framed"] == 1 and rep["already"] == 0
    assert us.body_path(anchor, "f").read_text(encoding="utf-8") == "bare prose body\n"


def test_apply_frames_bare_and_keeps_framed(tmp_path):
    anchor, proj = _tree(tmp_path)
    E.add_or_update_entry(str(proj), "Framed", "When x, do y.", body="stays", scope_default="p")
    E.add_or_update_entry(str(proj), "Reference bare", "When z, read this.",
                          body="ignored", type_="reference")
    us.write_if_changed(us.body_path(anchor, "reference-bare"), "old prose\n")
    rep = BF.backfill([str(tmp_path)], apply=True)
    assert rep["framed"] == 1 and rep["already"] == 1
    framed = us.body_path(anchor, "reference-bare").read_text(encoding="utf-8")
    assert framed.startswith("---\nname: reference-bare\n")
    assert "  type: reference" in framed                 # type derived from the slug prefix
    assert framed.endswith("old prose\n")                # prose untouched, frame prepended
    rep2 = BF.backfill([str(tmp_path)], apply=True)
    assert rep2["framed"] == 0 and rep2["already"] == 2  # idempotent


def test_missing_body_reported_never_fabricated(tmp_path):
    anchor, proj = _tree(tmp_path)
    E.add_or_update_entry(str(proj), "Gone", "When g, h.", body="B", scope_default="p")
    us.body_path(anchor, "gone").unlink()
    rep = BF.backfill([str(tmp_path)], apply=True)
    assert rep["missing"] == 1 and rep["framed"] == 0
    assert not us.body_path(anchor, "gone").exists()
