"""Test for the message factedit gives when several levels hold a line of the fact: a fact placed
by topic has one line per level its topics place it at, so the message does not call that a
defect, and the retry it names works when run as given from a cwd outside the tree. ASCII."""

import os
import re
import subprocess
import sys
from pathlib import Path

import factedit as FE
import memory_engine as ME
import pytest
import topic_store
import uuid_store as us

TOOL = Path(FE.__file__).resolve()
RECONCILE = TOOL.parents[1] / "meta-self-improve" / "reconcile_memory_index.py"
HOOK = "When a rule is about one stack, bind it to that stack's topic."


def test_several_owners_are_named_without_calling_them_a_defect(tmp_path):
    owners = [tmp_path / "a", tmp_path / "b"]
    text = FE.unknown_fact_message("feedback-x", tmp_path, tmp_path, owners, True)
    assert "2 levels point at it (placed by topic, or a duplicate pointer that --check-tree names)" in text
    assert "--level %s" % owners[0] in text and str(Path(owners[1])) in text


@pytest.fixture
def placed(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    anchor = tmp_path / "tree"
    (anchor / us.STORE_DIRNAME).mkdir(parents=True)
    topic_store.save_list(anchor, {"python": "Python code", "rust": "Rust code"}, "jev")
    levels = {}
    for rel, topics in (("", None), ("a", ("python",)), ("b", ("python",)), ("c", ("rust",))):
        level = anchor / rel if rel else anchor
        level.mkdir(exist_ok=True)
        (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        assert ME.main(["set-scope", "--proj", str(level), "--scope", "WHAT: a level"]) == 0
        if topics:
            ME.set_level_topics(str(level), topics)
        levels[rel] = str(level)
    ME.add_or_update_entry(levels[""], title="T feedback-py-rule", hook=HOOK, body="body",
                           type_="feedback", slug="feedback-py-rule")
    ME.set_fact_topics(levels[""], {"feedback-py-rule": ("python",)})
    ME.render_topics(levels[""])
    return levels


def _run(argv, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    env = dict(os.environ)
    env.pop("BITRANOX_MEMORY_ENGINE", None)
    return subprocess.run([sys.executable, *argv], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False, env=env,
                          cwd=str(outside))


def test_a_placed_fact_read_from_another_level_names_its_levels_and_the_retry_runs(placed, tmp_path):
    done = _run([str(TOOL), "show", "--slug", "feedback-py-rule", "--from", placed["c"]], tmp_path)
    assert done.returncode == 1, done.stdout + done.stderr
    msg = done.stdout + done.stderr
    assert "2 levels point at it (placed by topic, or a duplicate pointer that --check-tree names)" in msg
    retry = re.search(r"e\.g\. --level (\S+)", msg)
    assert retry and retry.group(1) in (placed["a"], placed["b"]), msg
    done = _run([str(TOOL), "show", "--slug", "feedback-py-rule", "--from", placed["c"],
                 "--level", retry.group(1)], tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    # the check the message names: two lines of a placed fact are no duplicate pointer
    done = _run([str(RECONCILE), "--check-tree", placed[""]], tmp_path)
    assert done.returncode == 0 and "duplicate pointer" not in done.stdout, done.stdout + done.stderr
