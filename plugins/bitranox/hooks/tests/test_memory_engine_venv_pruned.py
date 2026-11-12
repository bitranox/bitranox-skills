"""The level walk must not read a virtualenv as a level, whatever suffix its name carries.

A project often keeps one virtualenv per interpreter or platform beside the default `.venv`
(`.venv-3.12`, `.venv-win`, `.venv-bmk`). Installed packages ship their own CLAUDE.md files, so a
walk that enters such a dir can find a pointer block there and treat it as a curated level: a
render then writes lines into the virtualenv. All content ASCII.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

import memory_engine as E
import self_improve_signals as sig
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python"
VENVS = (".venv-3.12", ".venv-win", ".venv-bmk")


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


@pytest.mark.parametrize("name", [".venv", ".venv-3.12", ".venv-win", ".venv-bmk", ".venv_x",
                                  "venv", "venv-notes", "venv-foo", "venv_bar", "node_modules",
                                  "site-packages", "target", us.STORE_DIRNAME])
def test_a_virtualenv_or_vendor_name_is_never_a_level(name):
    assert us.is_non_level_dirname(name)


@pytest.mark.parametrize("name", ["venvnotes", "venv3", "myvenv", "src", "docs.venv"])
def test_a_name_that_only_mentions_venv_is_still_walked(name):
    assert not us.is_non_level_dirname(name)


def _level(path, topics=("python",)):
    path.mkdir(parents=True, exist_ok=True)
    (path / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert E.main(["set-scope", "--proj", str(path), "--scope", SCOPE]) == 0
    E.set_level_topics(str(path), topics)
    return path


def _planted_tree(tmp_path):
    """A python level `a`, and the same kind of level inside each suffixed virtualenv."""
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, {"python": "Python code"}, "jev")
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top"]) == 0
    live = _level(anchor / "a")
    inside = [_level(anchor / name / "lib" / "pkg") for name in VENVS]
    return anchor, live, inside


def test_the_level_walk_does_not_enter_a_suffixed_virtualenv(tmp_path):
    anchor, live, _inside = _planted_tree(tmp_path)
    found = {Path(p).resolve() for p in E.curated_levels_under(str(anchor))}
    # Control: both live levels are found, so a prune that dropped everything fails.
    assert found == {anchor.resolve(), live.resolve()}


def test_render_topics_writes_nothing_inside_a_suffixed_virtualenv(tmp_path):
    anchor, live, inside = _planted_tree(tmp_path)
    E.add_or_update_entry(str(anchor), title="T feedback-py-rule", hook=HOOK, body="b",
                          type_="feedback", slug="feedback-py-rule")
    E.set_fact_topics(str(anchor), {"feedback-py-rule": ("python",)})
    before = {path: sig.claude_local_md_path(path).read_bytes() for path in inside}
    E.render_topics(str(anchor))
    assert {path: sig.claude_local_md_path(path).read_bytes() for path in inside} == before
    placed = us.parse_pointer_index(sig.claude_local_md_path(live).read_text(encoding="utf-8"))[1]
    assert [p.slug for p in placed] == ["feedback-py-rule"]


PLUGIN = Path(E.__file__).resolve().parents[1]
LEVEL_WALKS = {
    "mem_levels": PLUGIN / "skills" / "compuse-toolbox" / "scripts" / "mem_levels.py",
    "reconcile": PLUGIN / "skills" / "meta-self-improve" / "reconcile_memory_index.py",
}
EVERY_SHAPE = (".venv-3.12", "venv-foo", "venv_bar", "target", "node_modules", "build")
DREAM = PLUGIN / "skills" / "meta-dream-tree"


def _pointing_level(anchor, path, slug):
    """A level at `path` whose block points at `slug` (body written at the tree's store)."""
    _level(path)
    E.add_or_update_entry(str(path), title="T " + slug, hook=HOOK, body="b", type_="feedback",
                          slug=slug)
    return path


def _run(script, *args):
    done = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False)
    return done.returncode, done.stdout + done.stderr


def test_every_level_walk_reports_one_level_set_whatever_the_virtualenv_is_called(tmp_path):
    """One tree, a live level `venvnotes` (no separator after `venv`: a project dir, not a
    virtualenv) and a level inside each virtualenv shape and each vendored or build dir. Every
    walk over the tree's levels - the engine's, reconcile --check-tree, mem_levels, the dream's
    store_manifest and dedup_scan, and factedit's owner search - must report the same two levels.
    Each pruned level points at the slug `venvnotes` points at, so a walk that entered one would
    also report a duplicate (or a second owner)."""
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, {"python": "Python code"}, "jev")
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top"]) == 0
    live = _pointing_level(anchor, anchor / "venvnotes", "feedback-shared")
    for name in EVERY_SHAPE:
        inside = anchor / name / "lib" / "pkg"
        _level(inside)
        local = sig.claude_local_md_path(inside)
        text = local.read_text(encoding="utf-8")
        local.write_text(us.upsert_pointer_block(text, us.parse_pointer_index(text)[0],
                                                 [us.Pointer(slug="feedback-shared", title="T",
                                                             hook=HOOK)]), encoding="utf-8")
    engine = {Path(p).resolve() for p in E.curated_levels_under(str(anchor))}
    assert engine == {anchor.resolve(), live.resolve()}
    rc, out = _run(LEVEL_WALKS["mem_levels"], "--root", str(anchor), "--json")
    assert rc == 0, out
    data = json.loads(out)["data"]
    assert sorted(data["levels"]) == [".", "venvnotes"] and data["duplicates"] == {}, out
    rc, out = _run(LEVEL_WALKS["reconcile"], "--check-tree", str(anchor))
    assert "tree integrity: 2 curated level(s)" in out and "duplicate pointer" not in out, out
    want = {anchor.resolve(), live.resolve()}
    manifest = _load(DREAM / "store_manifest.py", "store_manifest_walk_probe")
    assert {p.resolve() for p in manifest.levels_under(anchor)} == want
    dedup = _load(DREAM / "dedup_scan.py", "dedup_scan_walk_probe")
    skipped = []
    assert {p.resolve() for p in dedup._levels(anchor, skipped)} == want and skipped == []
    factedit = _load(DREAM / "factedit.py", "factedit_walk_probe")
    owners, complete = factedit.find_pointer_owners(anchor, "feedback-shared",
                                                    us.parse_pointer_index)
    assert complete and owners == [live.resolve()]


def _load(path, name):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", [".venv", ".venv-3.12", "venv", "venv-foo", "venv_bar",
                                  "venvnotes", "myvenv", "target", "site-packages", "src",
                                  us.STORE_DIRNAME, us.STORE_DIRNAME + "-migration-backup-1"])
def test_the_dream_s_level_walks_prune_by_the_engine_s_rule(name):
    manifest = _load(DREAM / "store_manifest.py", "store_manifest_venv_probe")
    dedup = _load(DREAM / "dedup_scan.py", "dedup_scan_venv_probe")
    want = us.is_non_level_dirname(name)
    assert manifest.is_pruned_dir(name) is want and dedup._is_pruned(name) is want
