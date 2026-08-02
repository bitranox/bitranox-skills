"""The tree walk must not re-discover the dream's own backups as live curated levels.

Backups are written under `~/.claude/self-improve-audit/backups/` expressly to keep them OUT of the
knowledge trees. That works for a tree on another mount, but `~/.claude` is ITSELF an anchor (it
carries a `CLAUDE.md`, and `~` is on the excluded-anchor list so the walk stops there), so the
backup root sits INSIDE that tree and every backed-up pointer block reads as a live level. Measured
before the fix: `--check-tree ~/.claude` reported 6028 problems, essentially all of them backups.
All content ASCII.
"""

from pathlib import Path

import pytest

import memory_engine as E


POINTER_BLOCK = """<!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->

## Memory index
- [A fact](mem:a-fact) - When something, do something.
<!-- BITRANOX-MEMORY-INDEX:END -->
"""


def _level(d: Path) -> Path:
    """Make `d` a curated level: a CLAUDE.local.md carrying a managed pointer block."""
    d.mkdir(parents=True, exist_ok=True)
    (d / "CLAUDE.local.md").write_text(POINTER_BLOCK, encoding="utf-8")
    return d


@pytest.fixture
def home_tree(tmp_path, monkeypatch):
    """A `~/.claude`-shaped anchor: a real level, plus a backup copy of one under the audit dir."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    anchor = tmp_path / ".claude"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("# home tree\n", encoding="utf-8")
    _level(anchor)
    _level(anchor / "skills" / "toolbox")
    # what a dream backup leaves behind, at the depth the real ones sit
    _level(anchor / "self-improve-audit" / "backups" / "crosstree-deep-20260802" / "levels")
    _level(anchor / "self-improve-audit" / "backups" / "crosstree-deep-20260802" / "levels" / "projects")
    return anchor


def test_backup_levels_are_not_walked_as_live_levels(home_tree):
    found = E.curated_levels_under(str(home_tree))
    inside_backups = [p for p in found if "self-improve-audit" in p]
    assert inside_backups == [], (
        "the dream's own backups were re-discovered as live curated levels: %r" % inside_backups
    )


def test_real_levels_are_still_found(home_tree):
    """The prune must not cost a genuine level - the anchor itself and a nested skills dir."""
    found = {Path(p).resolve() for p in E.curated_levels_under(str(home_tree))}
    assert home_tree.resolve() in found
    assert (home_tree / "skills" / "toolbox").resolve() in found


def test_a_project_named_like_the_audit_dir_elsewhere_is_untouched(tmp_path, monkeypatch):
    """The prune is anchored at the REAL audit dir, never a bare name match - a project that happens
    to contain a `self-improve-audit` dir of its own is a normal level and must still be walked."""
    monkeypatch.setenv("HOME", str(tmp_path / "elsewhere"))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "elsewhere"))
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "CLAUDE.md").write_text("# a project tree\n", encoding="utf-8")
    _level(tree)
    decoy = _level(tree / "self-improve-audit")
    found = {Path(p).resolve() for p in E.curated_levels_under(str(tree))}
    assert decoy.resolve() in found


def test_decoy_scan_skips_stores_inside_the_backup_root(home_tree):
    """`find_decoy_anchors` is a SECOND walker over the same tree; pruning only the level walk left
    every snapshotted store under the backup root reading as a decoy anchor."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "meta-self-improve"))
    import reconcile_memory_index as R
    import uuid_store as us

    (home_tree / us.STORE_DIRNAME / "facts").mkdir(parents=True)          # the real top store
    snapshot = home_tree / "self-improve-audit" / "backups" / "run-1" / "curated" / us.STORE_DIRNAME
    snapshot.mkdir(parents=True)                                          # a backed-up store
    assert R.find_decoy_anchors(str(home_tree)) == []
