"""The move, relocate, rename, retitle, heal and ensure-all-trees reports are typed records.

Pinned here: the record type each verb returns; `refused` as the text of a whole declined action
(str or None) on every report that has it, with the levels heal and a scaffold left while the rest
went ahead under `refused_levels`; the named fields of every per-level item; and the readers that
consume them, the CLI printers and SessionStart's self-heal line, run for real.
"""
from pathlib import Path

import pytest

import memory_engine as E
import self_improve_signals as sig
import session_start
import uuid_store as us

SCOPE = "WHAT: a level\nSTACK: python\nCHILDREN:\n- x/: y\nPLACE-HERE: a\nPLACE-ELSEWHERE: b"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


def _levels(root, *names):
    out = []
    for name in names:
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        out.append(str(d))
    (root / names[0] / us.STORE_DIRNAME).mkdir(exist_ok=True)
    return out


def _legacy_topics_md(level):
    """A CLAUDE.md whose legacy scope block has a TOPICS line that does not parse."""
    sig.claude_md_path(level).write_text(
        f"# L\n\n{sig.SCOPE_MARK_BEGIN}\n{SCOPE}\nTOPICS: Not A Tag!\n{sig.SCOPE_MARK_END}\n",
        encoding="utf-8")


# ---- move ----------------------------------------------------------------------------------------

def test_a_move_returns_a_move_report_with_its_direction_as_a_member(tmp_path):
    _anchor, mid, proj = _levels(tmp_path, "t", "t/m", "t/m/p")
    E.add_or_update_entry(proj, "Shared rule", "applies widely", body="B", scope_default="p")
    rep = E.move_entry(proj, mid, "shared-rule")
    assert type(rep) is E.MoveReport
    assert rep.moved is True and rep.refused is None
    assert rep.direction is E.MoveDirection.UP
    assert rep.slug == "shared-rule"
    assert rep.slugs == rep.moved_slugs == ["shared-rule"]
    assert (rep.from_level, rep.to_level) == (proj, mid)


def test_a_refused_move_carries_its_reason_as_text(tmp_path):
    _anchor, mid, proj = _levels(tmp_path, "t", "t/m", "t/m/p")
    rep = E.move_entry(proj, mid, "nope")
    assert type(rep) is E.MoveReport
    assert isinstance(rep.refused, str) and "not found" in rep.refused
    assert rep.moved is False and rep.moved_slugs == []


def test_a_set_move_names_the_set_comma_joined(tmp_path):
    anchor, _mid, proj = _levels(tmp_path, "t", "t/m", "t/m/p")
    for title in ("One", "Two"):
        E.add_or_update_entry(proj, title, "h " + title, body="B", scope_default="p")
    rep = E.move_entry(proj, anchor, ["one", "two"])
    assert rep.slug == "one, two" and rep.moved_slugs == ["one", "two"]


# ---- relocate ------------------------------------------------------------------------------------

def test_a_same_tree_relocate_carries_the_moves_outcome(tmp_path):
    anchor, proj = _levels(tmp_path, "t", "t/p")
    E.add_or_update_entry(proj, "Local", "loc", body="B", scope_default="p")
    rep = E.relocate_entry(proj, anchor, "local")
    assert type(rep) is E.RelocateReport
    assert (rep.relocated, rep.refused, rep.cross_tree, rep.notes) == (True, None, False, [])


def test_a_refused_same_tree_relocate_carries_the_moves_reason(tmp_path):
    anchor, proj = _levels(tmp_path, "t", "t/p")
    rep = E.relocate_entry(proj, anchor, "nope")
    assert rep.refused is not None
    assert rep.relocated is False and "not found" in rep.refused


def test_a_cross_tree_relocate_is_marked_cross_tree(tmp_path):
    _a1, p1 = _levels(tmp_path, "one", "one/p")
    _a2, p2 = _levels(tmp_path, "two", "two/p")
    E.add_or_update_entry(p1, "Oven rule", "ovens", body="B", scope_default="p")
    rep = E.relocate_entry(p1, p2, "oven-rule")
    assert type(rep) is E.RelocateReport
    assert (rep.cross_tree, rep.relocated, rep.refused) == (True, True, None)


# ---- rename and retitle --------------------------------------------------------------------------

def test_a_rename_lists_each_repointed_ref_as_a_named_record(tmp_path):
    anchor, proj = _levels(tmp_path, "t", "t/p")
    E.add_or_update_entry(proj, "Old name", "h", body="B", scope_default="p")
    E.add_or_update_entry(anchor, "Citer", "c", body="See [[old-name]]", scope_default="a")
    rep = E.rename_entry(proj, "old-name", "new-name")
    assert type(rep) is E.RenameReport and rep.renamed is True and rep.refused is None
    [ref] = rep.refs_rewritten
    assert type(ref) is E.RewrittenRef
    assert (ref.level, ref.citer, ref.site) == (anchor, "citer", E.RefSite.BODY)


def test_a_refused_rename_carries_its_reason_as_text(tmp_path):
    _anchor, proj = _levels(tmp_path, "t", "t/p")
    rep = E.rename_entry(proj, "nope", "other")
    assert rep.refused is not None
    assert type(rep) is E.RenameReport and "not found" in rep.refused and rep.renamed is False


def test_a_retitle_returns_a_retitle_report(tmp_path):
    _anchor, proj = _levels(tmp_path, "t", "t/p")
    E.add_or_update_entry(proj, "Old", "h", body="B", scope_default="p")
    rep = E.retitle_entry(proj, "old", "Better")
    assert type(rep) is E.RetitleReport
    assert (rep.retitled, rep.refused, rep.to_title, rep.levels) == (True, None, "Better", [proj])


# ---- heal ----------------------------------------------------------------------------------------

def test_heal_returns_named_per_level_items(tmp_path):
    anchor, proj, legacy = _levels(tmp_path, "t", "t/p", "t/p/q")
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="p")
    us.body_path(anchor, "f").unlink()
    local = sig.claude_local_md_path(proj)
    local.write_text(local.read_text(encoding="utf-8").replace(
        "- [F](mem:f)", "- [Bad](mem:../x) - When bad\n- [F](mem:f)"), encoding="utf-8")
    _legacy_topics_md(legacy)
    rep = E.heal(legacy)
    assert type(rep) is E.HealReport and rep.skipped is None and rep.levels == 3
    [orphan] = rep.orphans
    assert type(orphan) is E.LevelSlug and (orphan.level, orphan.slug) == (proj, "f")
    [bad] = rep.invalid_pointers
    assert type(bad) is E.LevelLine and bad.level == proj and "mem:../x" in bad.line
    [left] = rep.refused_levels
    assert type(left) is E.LevelReason and left.level == legacy and "does not parse" in left.reason
    assert rep.unreadable == []


def test_heal_reports_an_unreadable_level_as_a_level_reason(tmp_path):
    _anchor, proj = _levels(tmp_path, "t", "t/p")
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="p")
    local = sig.claude_local_md_path(proj)
    local.write_bytes(local.read_bytes() + b"caf\xe9\n")
    [bad] = E.heal(proj).unreadable
    assert type(bad) is E.LevelReason and bad.level == proj and str(local) in bad.reason


def test_heal_under_writes_off_is_skipped_with_every_list_empty(tmp_path, monkeypatch):
    _anchor, proj = _levels(tmp_path, "t", "t/p")
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    rep = E.heal(proj)
    assert rep == E.HealReport(skipped=sig.MEMORY_WRITES_OFF_LINE)


# ---- ensure-all-trees and scaffold ---------------------------------------------------------------

def test_ensure_all_trees_returns_a_tree_report_per_tree(tmp_path):
    work = tmp_path / "work"
    for name in ("mk", "bk"):
        top = work / name
        (top / "c").mkdir(parents=True)
        (top / "CLAUDE.md").write_text("top\n", encoding="utf-8")
        (top / us.STORE_DIRNAME).mkdir()
        (top / "c" / "CLAUDE.md").write_text("c\n", encoding="utf-8")
    (work / "CLAUDE.md").write_text("stray\n", encoding="utf-8")
    _legacy_topics_md(str(work / "mk" / "c"))
    rep = E.ensure_all_trees(roots=[str(work)], apply=True)
    assert type(rep) is E.TreesReport and rep.roots == [str(work)]
    by_top = {Path(tr.top).name: tr for tr in rep.trees}
    assert all(type(tr) is E.TreeReport for tr in rep.trees)
    assert by_top["work"].why is not None
    assert by_top["work"].status is E.TreeStatus.AMBIGUOUS and "stray" in by_top["work"].why
    assert by_top["bk"].status is E.TreeStatus.OK and by_top["bk"].why is None
    [left] = by_top["mk"].refused_levels
    assert type(left) is E.LevelReason and left.level == str(work / "mk" / "c")


def test_scaffold_hands_a_refused_level_back_as_a_level_reason(tmp_path):
    _anchor, proj = _levels(tmp_path, "t", "t/p")
    _legacy_topics_md(proj)
    refused = []
    E.scaffold(proj, refused_levels=refused)
    [left] = refused
    assert type(left) is E.LevelReason and left.level == proj


# ---- the readers ---------------------------------------------------------------------------------

def test_the_heal_cli_prints_each_named_item(tmp_path, capsys):
    anchor, proj, legacy = _levels(tmp_path, "t", "t/p", "t/p/q")
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="p")
    us.body_path(anchor, "f").unlink()
    _legacy_topics_md(legacy)
    assert E.main(["heal", "--proj", legacy]) == 0
    out = capsys.readouterr().out
    assert f"! missing central body (not fabricated): f [{proj}]" in out
    assert out.rstrip("\n").endswith(f"[{legacy}]")


def test_the_move_cli_prints_the_direction_value(tmp_path, capsys):
    _anchor, mid, proj = _levels(tmp_path, "t", "t/m", "t/m/p")
    E.add_or_update_entry(proj, "Shared rule", "applies widely", body="B", scope_default="p")
    assert E.main(["move", "--from-level", proj, "--to-level", mid, "--slug", "shared-rule"]) == 0
    assert capsys.readouterr().out == f"moved shared-rule: {proj} -> {mid} (up)\n"


def test_session_start_names_the_levels_the_real_heal_refused_and_could_not_read(tmp_path):
    _anchor, proj, legacy = _levels(tmp_path, "t", "t/p", "t/p/q")
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="p")
    local = sig.claude_local_md_path(proj)
    local.write_bytes(local.read_bytes() + b"caf\xe9\n")
    _legacy_topics_md(legacy)
    text = session_start._self_heal(legacy)
    assert f"refused 1 level(s) and left them untouched: {legacy}." in text
    assert f"could not read 1 level(s) and left them untouched: {proj}." in text
