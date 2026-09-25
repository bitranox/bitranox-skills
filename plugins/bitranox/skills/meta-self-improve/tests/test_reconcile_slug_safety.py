"""reconcile builds a body path only from a slug that names a plain file.

Two paths reached a file from a slug nobody validated: `archive_entry` took the slug from a
POINTER line, so a hand-damaged `mem:../../CLAUDE` pointer archived the tree's CLAUDE.md; and
`rehome_dangling_bodies` passed a body's FILENAME to the engine, which now refuses a name that is
not a valid slug with InvalidSlug - so one badly named body crashed the whole re-home.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

import reconcile_memory_index as R

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))
import memory_engine as E  # noqa: E402
import uuid_store as US  # noqa: E402


@pytest.fixture
def proj(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    p = tmp_path / "proj"
    p.mkdir()
    return p


def _plant_pointer(level: Path, line: str) -> None:
    path = level / "CLAUDE.local.md"
    text = path.read_text(encoding="utf-8")
    assert text.count(US.INDEX_END) == 1
    path.write_text(text.replace(US.INDEX_END, line + "\n" + US.INDEX_END), encoding="utf-8")


def test_archiving_a_traversal_pointer_moves_no_file(proj):
    E.add_or_update_entry(str(proj), "Real", "When real, do real.", body="B", type_="reference")
    claude_md = proj / "CLAUDE.md"
    claude_md.write_text("# the tree's own instructions\n", encoding="utf-8")
    _plant_pointer(proj, "- [Bad](mem:../../CLAUDE) - When bad, a damaged pointer.")
    assert R.archive_entry(str(proj), "../../CLAUDE") is True        # the pointer is dropped
    assert claude_md.read_text(encoding="utf-8") == "# the tree's own instructions\n"
    assert not any(e.slug == "../../CLAUDE" for e in E.read_store(str(proj))[1])


def test_control_archiving_a_real_fact_still_moves_its_body(proj):
    slug = E.add_or_update_entry(str(proj), "Real", "When real, do real.", body="B",
                                 type_="reference")
    body = US.body_path(E._anchor(str(proj)), slug)
    assert body.is_file()
    assert R.archive_entry(str(proj), slug) is True
    assert not body.is_file()
    assert (body.parent.parent / ".archive" / body.name).is_file()


def _dangle(proj: Path, name: str) -> Path:
    facts = US.central_facts_dir(E._anchor(str(proj)))
    facts.mkdir(parents=True, exist_ok=True)
    path = facts / (name + ".md")
    path.write_text("---\nname: x\ndescription: When %s, do it.\n---\n\nbody\n" % name,
                    encoding="utf-8")
    return path


def test_a_badly_named_body_does_not_stop_the_rehome(proj):
    E.add_or_update_entry(str(proj), "Keep", "When keep, do keep.", body="B", type_="reference")
    _dangle(proj, "Bad_Name")
    _dangle(proj, "good-orphan")
    assert R.rehome_dangling_bodies(proj) == ["good-orphan"]
    assert any(e.slug == "good-orphan" for e in E.read_store(str(proj))[1])
    assert R.find_dangling_bodies(proj) == ["Bad_Name"]


def test_the_rehome_cli_names_the_body_it_cannot_rehome(proj, capsys):
    E.add_or_update_entry(str(proj), "Keep", "When keep, do keep.", body="B", type_="reference")
    _dangle(proj, "Bad_Name")
    assert R.main(["--rehome", str(proj)]) == 1
    out = capsys.readouterr().out
    assert "Bad_Name" in out and "not a valid slug" in out


def test_control_a_clean_rehome_still_exits_zero(proj, capsys):
    E.add_or_update_entry(str(proj), "Keep", "When keep, do keep.", body="B", type_="reference")
    _dangle(proj, "good-orphan")
    assert R.main(["--rehome", str(proj)]) == 0
    assert "re-homed: good-orphan" in capsys.readouterr().out


def test_archiving_keeps_an_earlier_archived_body_of_the_same_slug(proj):
    slug = E.add_or_update_entry(str(proj), "Real", "When real, do real.", body="LIVE",
                                 type_="reference")
    body = US.body_path(E._anchor(str(proj)), slug)
    archive = body.parent.parent / ".archive"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / body.name).write_text("EARLIER ARCHIVED FACT\n", encoding="utf-8")
    assert R.archive_entry(str(proj), slug) is True
    assert (archive / body.name).read_text(encoding="utf-8") == "EARLIER ARCHIVED FACT\n"
    assert any("LIVE" in p.read_text(encoding="utf-8") for p in archive.iterdir()
               if p.name != body.name)
