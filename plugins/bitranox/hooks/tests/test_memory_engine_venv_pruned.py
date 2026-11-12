"""The level walk must not read a virtualenv as a level, whatever suffix its name carries.

A project often keeps one virtualenv per interpreter or platform beside the default `.venv`
(`.venv-3.12`, `.venv-win`, `.venv-bmk`). Installed packages ship their own CLAUDE.md files, so a
walk that enters such a dir can find a pointer block there and treat it as a curated level: a
render then writes lines into the virtualenv. All content ASCII.
"""

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
                                  "venv", "node_modules", us.STORE_DIRNAME])
def test_a_virtualenv_or_vendor_name_is_never_a_level(name):
    assert us.is_non_level_dirname(name)


@pytest.mark.parametrize("name", ["venv-notes", "venv3", "myvenv", "src", "docs.venv"])
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
