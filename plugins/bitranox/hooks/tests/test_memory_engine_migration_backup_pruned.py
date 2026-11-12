"""The level walk must not read a slug-store migration's backup as live levels.

`migrate_to_slug_store.py --apply` copies the store and every pointer file it touches into
`<anchor>/.claude-memory-migration-backup-<stamp>/` and leaves that directory in the tree. The
copies carry managed pointer blocks, legacy lines included, so a walk that enters the backup
reports each copy as a curated level: the tree-wide check then sees every migrated slug pointed at
from two levels, and a verb that writes levels would write into the backup. All content ASCII.
"""

import sys
from pathlib import Path

import pytest

import memory_engine as E
import migrate_to_slug_store as mig
import self_improve_signals as sig
import uuid_store as us

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "meta-self-improve"))
import reconcile_memory_index as R  # noqa: E402 - lives beside a skill, not on the hooks path

HOOK = "When a rule is about one stack, bind it to that stack's topic."
BLOCK = """<!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->

## Memory index
- [A fact](mem:feedback-a) - When something, do something.
<!-- BITRANOX-MEMORY-INDEX:END -->
"""


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _level_file(d: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "CLAUDE.local.md").write_text(BLOCK, encoding="utf-8")
    return d


def _planted_tree(tmp_path):
    """An anchor with a live level below it and a backup copying both, as the migration lays it out."""
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME / "facts").mkdir(parents=True)
    _level_file(anchor)
    live = _level_file(anchor / "sub")
    backup = anchor / (mig.BACKUP_PREFIX + "20261112T000000")
    (backup / us.STORE_DIRNAME / "facts").mkdir(parents=True)
    _level_file(backup / "levels")
    _level_file(backup / "levels" / "sub")
    return anchor, live, backup


def test_a_migration_backup_is_not_walked_as_live_levels(tmp_path):
    anchor, live, backup = _planted_tree(tmp_path)
    found = {Path(p).resolve() for p in E.curated_levels_under(str(anchor))}
    assert [p for p in found if backup.resolve() in p.parents] == []
    # Control: the walk still finds both live levels, so a prune that dropped everything fails.
    assert found == {anchor.resolve(), live.resolve()}


def test_the_decoy_scan_and_the_level_walk_skip_the_same_backup(tmp_path):
    anchor, _live, _backup = _planted_tree(tmp_path)
    assert R.find_decoy_anchors(str(anchor)) == []


def _legacy_tree(tmp_path):
    """A tree whose top level holds one legacy uuid pointer, ready for the migration."""
    anchor = tmp_path / "legacy"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top"]) == 0
    uuid = us.fact_uuid(str(anchor), "feedback-l")
    body = us.legacy_body_path(str(anchor), uuid)
    body.parent.mkdir(parents=True, exist_ok=True)
    body.write_text("---\nname: feedback-l\ndescription: %s\ntitle: T feedback-l\nmetadata:\n"
                    "  type: feedback\n---\n\nbody\n" % HOOK, encoding="utf-8")
    local = sig.claude_local_md_path(str(anchor))
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers.append(us.Pointer(slug="feedback-l", title="T feedback-l", hook=HOOK, uuid=uuid,
                               legacy=True))
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")
    return anchor


def test_check_tree_after_a_real_migration_sees_one_level_per_slug(tmp_path, capsys):
    anchor = _legacy_tree(tmp_path)
    assert mig.main(["--root", str(anchor), "--apply"]) == 0
    backups = list(anchor.glob(mig.BACKUP_PREFIX + "*"))
    assert len(backups) == 1                         # the backup really is inside the tree
    capsys.readouterr()
    rc = R.main(["--check-tree", str(anchor)])
    out = capsys.readouterr().out
    assert backups[0].name not in out, out
    assert rc == 0, out
