"""reconcile names what it could not read, and never reports a sharded body as absent.

Three defects of one shape - an answer that cannot be told apart from a clean one:

* The engine raises `TreeWalkError` for a level file it cannot decode, but reconcile's CLI let it
  escape as a traceback, exiting 1 - the code every mode uses for "problems found".
* Its own reads (`is_curated`, the frame-only scan, the re-home) decoded strictly behind an
  `except OSError` that a `UnicodeDecodeError` walks past.
* `find_dangling_bodies` listed only `facts/*.md`, so a pre-pivot body at `facts/<shard>/<uuid>.md`
  that no pointer names was never reported - the layout the engine itself still reads.

All content ASCII.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

import reconcile_memory_index as R

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))
import memory_engine as E  # noqa: E402
import uuid_store as US  # noqa: E402

BLOCK = """<!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->

## Memory index
%s
<!-- BITRANOX-MEMORY-INDEX:END -->
"""
BODY = ("---\nname: %s\ndescription: When something, do something.\nmetadata:\n  type: project\n"
        "---\n\nThe body.\n")
CP1252 = b"caf\xe9\n"
LEGACY_UUID = "ab" + "0" * 6 + "-0000-5000-8000-000000000000"


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """An anchor holding `a-fact`, plus a `sub` level holding `b-fact`; HOME kept in tmp_path."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    anchor = tmp_path / "tree"
    facts = anchor / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("# tree\n", encoding="utf-8")
    _level(anchor, "- [A fact](mem:a-fact) - When a, do a.")
    (facts / "a-fact.md").write_text(BODY % "a-fact", encoding="utf-8")
    sub = anchor / "sub"
    sub.mkdir()
    (sub / "CLAUDE.md").write_text("# sub\n", encoding="utf-8")
    _level(sub, "- [B fact](mem:b-fact) - When b, do b.")
    (facts / "b-fact.md").write_text(BODY % "b-fact", encoding="utf-8")
    return anchor


def _level(level, lines):
    (level / "CLAUDE.local.md").write_text(BLOCK % lines, encoding="utf-8")


def _spoil(path):
    path.write_bytes(path.read_bytes() + CP1252)
    return path


def _facts(anchor):
    return anchor / ".claude-memory" / "facts"


# ---- R1.1: every mode maps the typed error to exit 2 ---------------------------------------------

MODES = {
    "check": lambda a: ["--check", str(a)],
    "archive": lambda a: [str(a), "--archive", "a-fact"],
    "rehome": lambda a: [str(a), "--rehome", "--dry-run"],
    "check-misplaced": lambda a: [str(a), "--check-misplaced"],
}


@pytest.mark.parametrize("mode", sorted(MODES))
def test_an_undecodable_level_makes_the_mode_exit_two_naming_the_file(tree, mode, capsys):
    bad = _spoil(tree / "sub" / "CLAUDE.local.md")
    assert R.main(MODES[mode](tree)) == 2
    err = capsys.readouterr().err
    assert str(bad) in err and "UTF-8" in err


@pytest.mark.parametrize("mode", sorted(MODES))
def test_control_the_same_tree_saved_as_utf8_runs_the_mode(tree, mode, capsys):
    assert R.main(MODES[mode](tree)) == 0, capsys.readouterr()


def test_the_default_reconcile_of_an_undecodable_level_exits_two(tree, capsys):
    bad = _spoil(tree / "sub" / "CLAUDE.local.md")
    assert R.main([str(tree / "sub")]) == 2
    assert str(bad) in capsys.readouterr().err


# ---- R1.2: reconcile's own reads raise the named error ------------------------------------------

def test_is_curated_names_an_undecodable_level_file(tree):
    bad = _spoil(tree / "sub" / "CLAUDE.local.md")
    with pytest.raises(E.TreeWalkError) as info:
        R.is_curated(tree / "sub")
    assert info.value.path == str(bad)


def test_control_is_curated_on_a_plain_dir_is_false(tree):
    plain = tree / "plain"
    plain.mkdir()
    assert R.is_curated(plain) is False and R.is_curated(tree / "sub") is True


def test_other_levels_pointing_names_an_undecodable_level(tree):
    _spoil(tree / "sub" / "CLAUDE.local.md")
    with pytest.raises(E.TreeWalkError):
        R._other_levels_pointing(str(tree), str(tree), "a-fact")


def test_check_tree_reports_an_undecodable_body_instead_of_crashing(tree, capsys):
    bad = _spoil(_facts(tree) / "b-fact.md")
    assert R.main([str(tree), "--check-tree"]) == 1
    out = capsys.readouterr().out
    assert str(bad) in out and "unreadable" in out and "directory" not in out


def test_control_check_tree_on_the_utf8_tree_is_clean(tree, capsys):
    assert R.main([str(tree), "--check-tree"]) == 0, capsys.readouterr().out


def test_the_frame_only_scan_names_an_undecodable_body(tree):
    bad = _spoil(_facts(tree) / "b-fact.md")
    with pytest.raises(E.TreeWalkError) as info:
        R.find_frame_only_bodies(tree)
    assert info.value.path == str(bad)
    unreadable = []
    assert R.find_frame_only_bodies(tree, unreadable=unreadable) == []
    assert unreadable == [str(bad)]


# ---- R1.3: a sharded legacy body is a body --------------------------------------------------------

def _sharded(anchor, uuid=LEGACY_UUID, shard=None):
    d = _facts(anchor) / (shard or US.shard(uuid))
    d.mkdir(parents=True, exist_ok=True)
    path = d / (uuid + ".md")
    path.write_text("---\nname: old\ndescription: When old, do old.\n---\n\nold body\n",
                    encoding="utf-8")
    return path


def test_an_unpointed_sharded_body_is_reported_dangling(tree):
    _sharded(tree)
    assert R.find_dangling_bodies(tree) == ["ab/%s" % LEGACY_UUID]


def test_control_a_sharded_body_a_legacy_pointer_names_is_not_dangling(tree):
    _sharded(tree)
    _level(tree, "- [A fact](mem:a-fact) - When a, do a.\n"
                 "- [Old](uuid:%s) - When old, do old. <!-- bx:slug=old-fact -->" % LEGACY_UUID)
    assert R.find_dangling_bodies(tree) == []


def test_a_file_outside_its_own_shard_dir_is_not_a_body(tree):
    """`uuid_store.legacy_body_path` reads `facts/<shard(uuid)>/<uuid>.md` and nowhere else."""
    _sharded(tree, shard="zz")
    notes = _facts(tree) / "ab"
    notes.mkdir()
    (notes / "readme.txt").write_text("x\n", encoding="utf-8")
    assert R.find_dangling_bodies(tree) == []


def test_check_tree_lists_the_sharded_dangler(tree, capsys):
    _sharded(tree)
    R.main([str(tree), "--check-tree"])
    assert "dangling body (no pointer at any level): ab/%s" % LEGACY_UUID in capsys.readouterr().out


def test_rehome_reports_a_sharded_dangler_and_leaves_it_alone(tree, capsys):
    """A sharded body carries no slug a pointer could name, so re-home must not act on it."""
    body = _sharded(tree)
    before = body.read_bytes()
    assert R.main([str(tree), "--rehome"]) == 1
    out = capsys.readouterr().out
    assert "cannot re-home: ab/%s.md" % LEGACY_UUID in out and "sharded" in out
    assert "TOTAL re-homed: 0" in out
    assert body.read_bytes() == before
    assert not any("old" in e.slug for e in E.read_store(str(tree))[1])


def test_rehome_reports_an_undecodable_dangler_instead_of_skipping_it(tree, capsys):
    """An unreadable dangling body was dropped by `except OSError: continue` (and a non-UTF-8 one
    crashed the run); either way nobody was told it could not be re-homed."""
    orphan = _facts(tree) / "orphan.md"
    orphan.write_text(BODY % "orphan", encoding="utf-8")
    _spoil(orphan)
    assert R.main([str(tree), "--rehome"]) == 1
    out = capsys.readouterr().out
    assert "cannot re-home: orphan.md" in out and "UTF-8" in out
    assert not any(e.slug == "orphan" for e in E.read_store(str(tree))[1])


def test_control_rehome_still_reattaches_a_readable_flat_dangler(tree, capsys):
    (_facts(tree) / "orphan.md").write_text(BODY % "orphan", encoding="utf-8")
    assert R.main([str(tree), "--rehome"]) == 0
    assert "re-homed: orphan" in capsys.readouterr().out
