"""Tests that a long holder of the placement lock never looks stale to a waiter: a render
refreshes the lock file's mtime once per level it walks in each pass, and set-topics once per
row, so the 120 s reclaim (`sig._LOCK_STALE_S`, judged by the lock file's mtime) only ever takes
the lock of a holder that stopped.

The only thing faked is the clock at its external edge: through the documented `write` port,
each level write sets the lock file's mtime 200 s into the past, as if that long had passed since
the holder last touched it. At the next level (render) or row (set-topics) the lock must read
fresh again. Nothing in the engine is patched. All content ASCII.
"""

import os
import time
from pathlib import Path

import memory_engine as E
import pytest
import self_improve_signals as sig
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
LIST = {"python": "Python code", "rust": "Rust code"}
AGED_S = 200.0


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    return h


def _tree(tmp_path):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top"]) == 0
    levels = {"": str(anchor)}
    for rel, topics in (("a", ("rust",)), ("a/py", ("python",)), ("b", None),
                        ("b/py", ("python",))):
        level = Path(anchor, *rel.split("/"))
        level.mkdir(parents=True)
        (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        assert E.main(["set-scope", "--proj", str(level), "--scope", "WHAT: " + rel]) == 0
        if topics:
            E.set_level_topics(str(level), topics)
        levels[rel] = str(level)
    return levels


def _fact(level, slug, topics=None):
    E.add_or_update_entry(level, title="T " + slug, hook=HOOK, body="body of " + slug,
                          type_="feedback", slug=slug)
    if topics is not None:
        E.set_fact_topics(level, {slug: topics})


class _AgingPort:
    """The `write` port: writes through, records whether the placement lock looked fresh at each
    write it was asked to check, then ages the lock file by AGED_S."""

    def __init__(self, anchor, check):
        self.lock = E.placement_lock_path(anchor)
        self.check = check
        self.seen = []

    def __call__(self, path, text):
        done = us.write_if_changed(path, text)
        if self.seen or self.check(path):
            age = time.time() - self.lock.stat().st_mtime
            self.seen.append((str(path), age < sig._LOCK_STALE_S))
        aged = time.time() - AGED_S
        os.utime(self.lock, (aged, aged))
        return done


def test_a_tree_render_refreshes_the_lock_at_every_level_of_both_passes(tmp_path):
    L = _tree(tmp_path)
    _fact(L[""], "feedback-py", ("python",))        # added at a/py and b/py, dropped at the top
    port = _AgingPort(L[""], lambda path: True)
    E.render_topics(L[""], scope="tree", write=port)
    written = [path for path, _fresh in port.seen]
    assert len(written) == 3, written                  # two ADD writes, one REMOVE write
    assert written[-1] == str(sig.claude_local_md_path(L[""]))
    # every write after the first came after the lock was aged by the one before it
    assert [fresh for _path, fresh in port.seen[1:]] == [True, True], port.seen


def test_a_chain_render_refreshes_the_lock_at_every_level_of_both_passes(tmp_path):
    L = _tree(tmp_path)
    _fact(L["b"], "feedback-rs", ("rust",))           # placed at a, held off the chain
    _fact(L["b"], "feedback-py", ("python",))         # placed at a/py and b/py
    _fact(L[""], "feedback-dup", ("python",))         # held at the top: a copy at a/py drops
    local = sig.claude_local_md_path(L["a/py"])
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    local.write_text(us.upsert_pointer_block(text, scope, pointers + [us.Pointer(
        slug="feedback-dup", title="T feedback-dup", hook=HOOK)]), encoding="utf-8")
    port = _AgingPort(L[""], lambda path: True)
    E.render_topics(L["a/py"], scope="chain", write=port)
    written = [path for path, _fresh in port.seen]
    a_py = str(sig.claude_local_md_path(L["a/py"]))
    assert written == [str(sig.claude_local_md_path(L["a"])), a_py, a_py], written
    assert [fresh for _path, fresh in port.seen[1:]] == [True, True], port.seen


def test_a_set_topics_batch_refreshes_the_lock_at_every_row(tmp_path):
    L = _tree(tmp_path)
    for slug in ("feedback-py1", "feedback-py2"):
        _fact(L[""], slug, ("python",))
    E.render_topics(L[""], scope="tree")
    top = str(sig.claude_local_md_path(L[""]))
    # each un-bind collapses: the line at the top first, then the drops below; only the top
    # write starts a row, so only it must find the lock fresh
    port = _AgingPort(L[""], lambda path: str(path) == top)
    rep = E.set_fact_topics(L[""], {"feedback-py1": None, "feedback-py2": None}, write=port)
    assert sorted(rep["collapsed"]) == ["feedback-py1", "feedback-py2"]
    at_top = [fresh for path, fresh in port.seen if path == top]
    assert len(at_top) == 2 and at_top[1] is True, port.seen


def test_a_fresh_lock_is_not_touched(tmp_path):
    """A beat only refreshes a lock older than the heartbeat age: one stat, no write, otherwise."""
    L = _tree(tmp_path)
    with E.placement_lock(L[""], "render-topics"):
        lock = E.placement_lock_path(L[""])
        recent = time.time() - 5
        os.utime(lock, (recent, recent))
        E._placement_heartbeat()
        assert abs(lock.stat().st_mtime - recent) < 1
        aged = time.time() - AGED_S
        os.utime(lock, (aged, aged))
        E._placement_heartbeat()
        assert time.time() - lock.stat().st_mtime < sig._LOCK_STALE_S
    assert not lock.exists()
