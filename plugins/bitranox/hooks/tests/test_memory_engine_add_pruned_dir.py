"""Tests that `add` refuses a level whose path below the tree's anchor crosses a directory every
level walk prunes (a virtualenv, a vendored, build or cache dir, the store): no walk would read
the line, and every check would call the body dangling. The refusal writes nothing, and the route
it names, run from a cwd outside the tree, writes a fact the walk finds. All content ASCII.
"""

import re
import subprocess
import sys
from pathlib import Path

import memory_engine as E
import mod_bridge
import pytest
import uuid_store as us

HOOK = "When a fact is written, write it where a walk reads it."
ENGINE_ROOT = Path(E.__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path, name="tree"):
    anchor = tmp_path / name
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top"]) == 0
    return anchor


def _snapshot(anchor):
    return {str(p): p.read_bytes() for p in sorted(Path(anchor).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


def _walked(anchor):
    return {Path(p).resolve() for p in E.curated_levels_under(str(anchor))}


@pytest.mark.parametrize("rel,crossed,outside", [
    (".venv-3.12/lib/pkg", ".venv-3.12", ""),
    ("venv-foo/pkg", "venv-foo", ""),
    ("a/node_modules/pkg", "node_modules", "a"),
    ("a/b/build", "build", "a/b"),
    ("target/doc", "target", ""),
    (us.STORE_DIRNAME + "/facts", us.STORE_DIRNAME, ""),
])
def test_add_under_a_pruned_dir_is_refused_and_its_route_works(tmp_path, capsys, rel, crossed,
                                                                outside):
    anchor = _tree(tmp_path)
    if outside:
        level = Path(anchor, *outside.split("/"))
        level.mkdir(parents=True)
        (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    target = Path(anchor, *rel.split("/"))
    target.mkdir(parents=True, exist_ok=True)
    (target / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    before = _snapshot(anchor)
    capsys.readouterr()
    rc = E.main(["add", "--proj", str(target), "--title", "T", "--slug", "feedback-where",
                 "--hook", HOOK, "--body", "body"])
    captured = capsys.readouterr()
    assert rc == 2 and captured.out.startswith("! refused: "), captured
    assert "its path crosses %r" % crossed in captured.out
    assert _snapshot(anchor) == before
    route = re.search(r"(hooks/memory_engine\.py add --proj \S+) \.\.\.", captured.out)
    expected = Path(anchor, *outside.split("/")) if outside else anchor
    assert route is not None and Path(route.group(1).split()[3]) == expected, captured.out
    done = subprocess.run([sys.executable, str(ENGINE_ROOT / route.group(1).split()[0]),
                           *route.group(1).split()[1:], "--title", "T", "--slug",
                           "feedback-where", "--hook", HOOK, "--body", "body"],
                          cwd=str(tmp_path / "home"), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert expected.resolve() in _walked(anchor)
    assert us.body_path(anchor, "feedback-where").is_file()


@pytest.mark.parametrize("name", ["venvnotes", "myvenv", "venv3", "builds", "docs.venv"])
def test_a_name_that_is_still_a_level_takes_an_add(tmp_path, name):
    anchor = _tree(tmp_path)
    level = anchor / name
    E.add_or_update_entry(str(level), title="T", hook=HOOK, body="b", slug="feedback-ok")
    assert level.resolve() in _walked(anchor)


def test_an_anchor_with_a_pruned_name_is_still_a_tree(tmp_path):
    """The walk starts at the anchor and never prunes it, so its own name does not matter."""
    anchor = _tree(tmp_path, name="build")
    E.add_or_update_entry(str(anchor), title="T", hook=HOOK, body="b", slug="feedback-top")
    E.add_or_update_entry(str(anchor / "sub"), title="T", hook=HOOK, body="b", slug="feedback-sub")
    assert _walked(anchor) == {anchor.resolve(), (anchor / "sub").resolve()}


def test_the_refusal_is_an_excluded_level_every_reporter_catches(tmp_path):
    anchor = _tree(tmp_path)
    with pytest.raises(E.ExcludedLevel) as exc:
        E.add_or_update_entry(str(anchor / "venv_bar" / "x"), title="T", hook=HOOK, body="b",
                              slug="feedback-nowhere")
    assert isinstance(exc.value, E.NonLevelDir) and exc.value.name == "venv_bar"
    assert issubclass(E.NonLevelDir, mod_bridge.REFUSALS)
    assert not (anchor / "venv_bar").exists()
