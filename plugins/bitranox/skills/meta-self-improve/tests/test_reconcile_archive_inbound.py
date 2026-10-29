"""--archive refuses while something still names the fact. ASCII only.

Archiving the last pointer of a fact that another fact links with `[[slug]]`, names in plain
prose, or a CLAUDE.md names, leaves a dangling ref or a stale name that only a later
`--check-tree` (refs) or nothing at all (prose, CLAUDE.md) reports. The archive now refuses and
lists them; `--force` archives anyway.
"""
from pathlib import Path

import reconcile_memory_index as R  # puts the plugin's hooks dir on sys.path first
import memory_engine as E


def _tree(tmp_path):
    top = tmp_path / "top"
    top.mkdir()
    (top / "CLAUDE.md").write_text("top\n", encoding="utf-8")
    proj = top / "proj"
    proj.mkdir()
    (proj / "CLAUDE.md").write_text("proj\n", encoding="utf-8")
    target = E.add_or_update_entry(str(proj), "Retire Me", "When x, do y.",
                                   body="Old lesson.", type_="reference")
    return top, proj, target


def _body(top, slug):
    return top / ".claude-memory" / "facts" / (slug + ".md")


def test_an_archive_with_a_linking_fact_is_refused_and_writes_nothing(tmp_path, capsys):
    top, proj, target = _tree(tmp_path)
    E.add_or_update_entry(str(proj), "Citer", "When z, do w.", body="See [[%s]]." % target,
                          type_="reference")
    assert R.main(["--archive", target, str(proj)]) == 1
    out = capsys.readouterr()
    assert "[[ref]]" in out.out + out.err and "reference-citer" in out.out + out.err
    assert _body(top, target).is_file()
    assert any(e.slug == target for e in E.read_store(str(proj))[1])


def test_a_prose_mention_in_another_fact_blocks_the_archive(tmp_path, capsys):
    top, proj, target = _tree(tmp_path)
    E.add_or_update_entry(str(top), "Namer", "When a, do b.",
                          body="Below sits %s, deliberately unlinked." % target, type_="reference")
    assert R.main(["--archive", target, str(proj)]) == 1
    assert "prose" in capsys.readouterr().out
    assert _body(top, target).is_file()


def test_a_claude_md_naming_the_slug_blocks_the_archive(tmp_path, capsys):
    top, proj, target = _tree(tmp_path)
    (top / "CLAUDE.md").write_text("Read %s before deploying.\n" % target, encoding="utf-8")
    assert R.main(["--archive", target, str(proj)]) == 1
    assert str(top / "CLAUDE.md") in capsys.readouterr().out


def test_force_archives_anyway_and_names_what_it_leaves(tmp_path, capsys):
    top, proj, target = _tree(tmp_path)
    E.add_or_update_entry(str(proj), "Citer", "When z, do w.", body="See [[%s]]." % target,
                          type_="reference")
    assert R.main(["--archive", target, "--force", str(proj)]) == 0
    assert "reference-citer" in capsys.readouterr().out
    assert not _body(top, target).is_file()


def test_control_an_unnamed_fact_archives_as_before(tmp_path):
    top, proj, target = _tree(tmp_path)
    assert R.main(["--archive", target, str(proj)]) == 0
    assert not _body(top, target).is_file()


def test_a_dry_run_reports_the_refusal_too(tmp_path, capsys):
    top, proj, target = _tree(tmp_path)
    E.add_or_update_entry(str(proj), "Citer", "When z, do w.", body="See [[%s]]." % target,
                          type_="reference")
    assert R.main(["--dry-run", "--archive", target, str(proj)]) == 1
    assert "reference-citer" in capsys.readouterr().out


def test_dropping_one_of_two_pointers_is_not_blocked_since_the_fact_stays(tmp_path):
    import shutil
    top, proj, target = _tree(tmp_path)
    sub = proj / "sub"
    sub.mkdir()
    (sub / "CLAUDE.md").write_text("sub\n", encoding="utf-8")
    shutil.copy(proj / "CLAUDE.local.md", sub / "CLAUDE.local.md")
    E.add_or_update_entry(str(top), "Citer", "When z, do w.", body="See [[%s]]." % target,
                          type_="reference")
    assert R.main(["--archive", target, str(sub)]) == 0
    assert _body(top, target).is_file()
    assert Path(proj / "CLAUDE.local.md").read_text(encoding="utf-8").count(target) == 1


def test_force_with_another_level_still_pointing_claims_nothing_dangles(tmp_path, capsys):
    # Dropping one of two pointers keeps the fact, so its mentions still resolve: saying they now
    # point at nothing would send the reader to repair refs that are fine.
    top, proj, target = _tree(tmp_path)
    E.add_or_update_entry(str(proj), "Citer", "When z, do w.", body="See [[%s]]." % target,
                          type_="reference")
    other = top / "other"
    other.mkdir()
    (other / "CLAUDE.local.md").write_text(
        (proj / "CLAUDE.local.md").read_text(encoding="utf-8"), encoding="utf-8")
    assert R.main(["--archive", target, "--force", str(proj)]) == 0
    assert "point at nothing" not in capsys.readouterr().out
    assert _body(top, target).is_file()
