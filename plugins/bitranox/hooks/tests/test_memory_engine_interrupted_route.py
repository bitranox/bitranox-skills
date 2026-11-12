"""Tests that a render or a set-topics collapse stopped part-way by a level it cannot write says
what the stop left and that running the same verb again completes it, instead of a bare
`! error: Permission denied: <lock>`; and that the re-run, as a subprocess from outside the tree,
does complete it. The stop is a real one: a level directory made read-only, so its lock file
cannot be created (POSIX only, and not as root, who ignores the mode). All content ASCII.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import memory_engine as E
import pytest
import self_improve_signals as sig
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
ENGINE = Path(E.__file__).resolve()

pytestmark = pytest.mark.skipif(
    os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="a read-only directory stops a write only on POSIX and only for a non-root user")


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    return h


@pytest.fixture
def read_only():
    """Make directories read-only; every one is made writable again at teardown."""
    made = []

    def _make(path):
        os.chmod(path, 0o555)
        made.append(path)

    yield _make
    for path in made:
        os.chmod(path, 0o755)


def _main(*args):
    return E.main([str(a) for a in args])


def _tree(tmp_path):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    listing = tmp_path / "list.json"
    listing.write_text(json.dumps({"tagger": "jev", "topics": {"python": "about python"}}),
                       encoding="utf-8")
    assert _main("topics-set-list", "--proj", anchor, "--from-file", listing) == 0
    assert _main("set-scope", "--proj", anchor, "--scope", "WHAT: the top") == 0
    out = {"": str(anchor)}
    for rel, topics in (("a", None), ("a/py", "python"), ("b", None), ("b/py", "python")):
        level = Path(anchor, *rel.split("/"))
        level.mkdir(parents=True)
        (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        assert _main("set-scope", "--proj", level, "--scope", "WHAT: " + rel) == 0
        if topics:
            assert _main("set-level-topics", "--proj", level, "--topics", topics) == 0
        out[rel] = str(level)
    assert _main("add", "--proj", anchor, "--title", "T feedback-py", "--hook", HOOK, "--body",
                 "body", "--type", "feedback", "--slug", "feedback-py") == 0
    assert _main("set-topics", "--proj", anchor, "--slug", "feedback-py", "--topics",
                 "python") == 0
    return out


def _holding(anchor, slug):
    return sorted(str(level) for level, _ptr in E._copies_of(anchor, slug))


def _run(tmp_path, *args):
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    done = subprocess.run([sys.executable, str(ENGINE), *map(str, args)], cwd=str(outside),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          check=False)
    return done.returncode, done.stdout + done.stderr


def test_an_interrupted_render_names_the_render_that_completes_it(tmp_path, capsys, read_only):
    L = _tree(tmp_path)
    read_only(L["b/py"])                       # the ADD pass writes a/py, then stops at b/py
    capsys.readouterr()
    rc = _main("render-topics", "--proj", L[""], "--scope", "tree")
    err = capsys.readouterr().err
    assert rc == 2 and err.startswith("! error: render-topics stopped before it finished: "), err
    assert "Permission denied" in err and "surplus line, never a fact without one" in err, err
    assert _holding(L[""], "feedback-py") == [L[""], L["a/py"]]      # nothing dropped yet
    route = re.search(r"then run (hooks/memory_engine\.py render-topics --proj \S+ --scope \S+) "
                      r"again", err)
    assert route is not None, err
    os.chmod(L["b/py"], 0o755)
    rc, said = _run(tmp_path, *route.group(1).split()[1:])
    assert rc == 0, said
    assert _holding(L[""], "feedback-py") == [L["a/py"], L["b/py"]]


def test_an_interrupted_collapse_names_the_call_that_completes_it(tmp_path, capsys, read_only):
    L = _tree(tmp_path)
    assert _main("render-topics", "--proj", L[""], "--scope", "tree") == 0
    read_only(L["b/py"])                       # the top's line is written, a/py dropped, b/py not
    capsys.readouterr()
    args = ("set-topics", "--proj", L[""], "--slug", "feedback-py", "--clear")
    rc = _main(*args)
    err = capsys.readouterr().err
    assert rc == 2 and err.startswith("! error: set-topics stopped before it finished: "), err
    assert "run the same hooks/memory_engine.py set-topics call again" in err, err
    assert E.read_body_topics(us.body_path(L[""], "feedback-py")) == ("python",)
    assert _holding(L[""], "feedback-py") == [L[""], L["b/py"]]
    os.chmod(L["b/py"], 0o755)
    rc, said = _run(tmp_path, *args)
    assert rc == 0, said
    assert _holding(L[""], "feedback-py") == [L[""]]
    assert E.read_body_topics(us.body_path(L[""], "feedback-py")) is None
