"""The migration's backup covers everything the migration WRITES, and restores it byte for byte.
ASCII only.

The backup used to copy the native store (which the migration only reads) and the retired
`.claude-bx-selflearning` dir (which it never touches), and nothing it actually mutates: the
anchor's central store, the level's CLAUDE.local.md, the CLAUDE.md a legacy scope block is moved
out of, and the repo .gitignore. A backup that misses what the migration mutates is not a backup.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import migrate_memory as M
import self_improve_signals as sig

HAVE_GIT = shutil.which("git") is not None


@pytest.fixture
def env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(M, "_EXCLUDE_PREFIXES", ())   # tmp_path sits under /tmp
    return tmp_path, home


def _slug(path):
    return re.sub(r"[^a-zA-Z0-9]", "-", str(path))


def _native(home, slug, topics):
    d = home / ".claude" / "projects" / slug / "memory"
    d.mkdir(parents=True, exist_ok=True)
    (d / "MEMORY.md").write_text("# Memory index\n", encoding="utf-8")
    for name, body in topics.items():
        (d / (name + ".md")).write_text(
            "---\nname: %s\ndescription: the %s fact\nmetadata:\n  type: project\n---\n%s\n"
            % (name, name, body), encoding="utf-8")
    return d


def _tree(tmp_path, git=True):
    """A knowledge tree that already holds state the migration will touch: a tree-top store with
    another level's fact, a level whose CLAUDE.md still carries a legacy scope block, a hand-written
    CLAUDE.local.md, and (optionally) a git repo with its own .gitignore."""
    top = tmp_path / "tree"
    proj = top / "sub"
    proj.mkdir(parents=True)
    (top / "CLAUDE.md").write_text("# tree top\n", encoding="utf-8")
    facts = top / sig.MEMORY_DIRNAME / "facts"
    facts.mkdir(parents=True)
    (facts / "other-fact.md").write_text("---\nname: other-fact\n---\nkept\n", encoding="utf-8")
    (proj / "CLAUDE.md").write_bytes(
        b"# sub\r\n\r\n<!-- bitranox:self-learning -->\r\nWHAT: the sub project\r\n"
        b"<!-- /bitranox:self-learning -->\r\n\r\nmore text\r\n")
    (proj / "CLAUDE.local.md").write_text("my own notes\n", encoding="utf-8")
    if git and HAVE_GIT:
        subprocess.run(["git", "init", "-q", str(top)], check=True, capture_output=True)
        (top / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    return top, proj


def _snapshot(root):
    """{relative path: bytes or None for a dir} of everything under `root` except git's own dir."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        rel = os.path.relpath(dirpath, root)
        out[rel] = None
        for name in filenames:
            out[os.path.join(rel, name)] = (Path(dirpath) / name).read_bytes()
    return out


def _changed(before, after):
    return sorted(k for k in set(before) | set(after) if before.get(k, 0) != after.get(k, 0))


# ---- the backup holds the pre-migration bytes of every path the migration changed --------------

def test_every_path_the_migration_changes_is_in_the_backup(env):
    tmp_path, home = env
    top, proj = _tree(tmp_path)
    slug = _slug(proj)
    _native(home, slug, {"project-alpha": "Alpha body.", "project-beta": "Beta body."})
    before = _snapshot(top)
    rep = M.migrate_store(slug, dry_run=False)
    assert rep["error"] is None and rep["placed"] == 2
    after = _snapshot(top)
    changed = _changed(before, after)
    assert changed, "control: the migration must change something for this test to mean anything"
    backup_bytes = {p.read_bytes() for p in M._backups_dir().rglob("*") if p.is_file()}
    lost = [k for k in changed if before.get(k) is not None and before[k] not in backup_bytes]
    assert lost == [], "pre-migration bytes missing from the backup: %s" % lost


def test_a_restore_puts_the_tree_back_byte_for_byte(env):
    tmp_path, home = env
    top, proj = _tree(tmp_path)
    slug = _slug(proj)
    _native(home, slug, {"project-alpha": "Alpha body.", "project-beta": "Beta body."})
    before = _snapshot(top)
    rep = M.migrate_store(slug, dry_run=False)
    assert _snapshot(top) != before
    problems = M.restore_backup(rep["backup"])
    assert problems == []
    assert _snapshot(top) == before


def test_a_restore_removes_what_the_migration_created(env):
    # nothing existed yet: no store, no CLAUDE.local.md, no .gitignore - all must go again
    tmp_path, home = env
    proj = tmp_path / "bare"
    proj.mkdir()
    (proj / "CLAUDE.md").write_text("# bare\n", encoding="utf-8")
    slug = _slug(proj)
    _native(home, slug, {"project-a": "Body A."})
    before = _snapshot(proj)
    rep = M.migrate_store(slug, dry_run=False)
    assert (proj / "CLAUDE.local.md").exists() and (proj / sig.MEMORY_DIRNAME).is_dir()
    assert M.restore_backup(rep["backup"]) == []
    assert _snapshot(proj) == before


def test_one_run_backs_up_a_shared_store_once_and_restores_every_level(env, capsys):
    tmp_path, home = env
    top, proj = _tree(tmp_path)
    proj2 = top / "sub2"
    proj2.mkdir()
    (proj2 / "CLAUDE.md").write_text("# sub2\n", encoding="utf-8")
    s1, s2 = _slug(proj), _slug(proj2)
    _native(home, s1, {"project-alpha": "Alpha body."})
    _native(home, s2, {"project-gamma": "Gamma body."})
    before = _snapshot(top)
    assert M.main(["--apply", "--slug=" + s1, "--slug=" + s2]) == 0
    runs = [p for p in M._backups_dir().iterdir() if p.is_dir()]
    assert len(runs) == 1, runs
    manifest = json.loads((runs[0] / "manifest.json").read_text(encoding="utf-8"))
    stores = [i for i in manifest["items"] if i["path"] == str(top / sig.MEMORY_DIRNAME)]
    assert len(stores) == 1                                   # copied once, not once per level
    assert "--restore" in capsys.readouterr().out
    assert M.main(["--restore", str(runs[0])]) == 0
    assert _snapshot(top) == before


# ---- the restore CLI refuses what it cannot trust ----------------------------------------------

def test_restore_of_a_dir_without_a_manifest_is_a_usage_error(env, capsys):
    tmp_path, _home = env
    bogus = tmp_path / "not-a-backup"
    bogus.mkdir()
    assert M.main(["--restore", str(bogus)]) == 2
    assert "manifest" in capsys.readouterr().err


def test_restore_cannot_be_combined_with_apply(env, capsys):
    tmp_path, _home = env
    with pytest.raises(SystemExit) as exc:
        M.main(["--apply", "--restore", str(tmp_path)])
    assert exc.value.code == 2


def test_a_dry_run_writes_no_backup(env):
    tmp_path, home = env
    _top, proj = _tree(tmp_path, git=False)
    slug = _slug(proj)
    _native(home, slug, {"project-alpha": "Alpha body."})
    M.migrate_store(slug, dry_run=True)
    assert not M._backups_dir().exists()
