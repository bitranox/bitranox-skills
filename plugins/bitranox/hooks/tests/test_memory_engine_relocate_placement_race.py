"""A cross-tree relocate decides "is this fact placed by topic?" under the source tree's
placement lock, and keeps holding it until its writes are done.

Read without the lock, a set-topics binding the fact after that read met a relocate that carried
the fact out of its tree, leaving the binding (and any lines a render then placed) pointing at a
body that had left. Both sides run as real processes: a holder that takes the placement lock
through the engine's own `placement_lock` and binds the fact while holding it, and the relocate
CLI. The interleaving is chosen by events, never by a clock: the holder announces that it holds
the lock, and the test waits until the relocate has either finished or joined the lock's queue
(a waiter refused once leaves a place file beside the lock). All content ASCII.
"""

import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import memory_engine as E
import pytest
import self_improve_signals as sig
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
LIST = {"python": "Python code and its tooling", "rust": "Rust code"}
HOOKS = Path(E.__file__).resolve().parent
ENGINE = HOOKS / "memory_engine.py"
# Bound on every wait for an event or a process that is expected to come: a hang fails, never
# stalls. Not a window the result depends on.
FINISH_S = 90.0

# The holder: takes the placement lock through the engine, says so, waits to be told to go, then
# binds the fact to a topic (what a set-topics does while it holds the lock) and lets go.
HOLDER = textwrap.dedent("""
    import sys, time
    from pathlib import Path
    sys.path.insert(0, sys.argv[1])
    import memory_engine as E
    import uuid_store as us
    anchor, slug, barrier = sys.argv[2], sys.argv[3], Path(sys.argv[4])
    with E.placement_lock(anchor, "holder"):
        (barrier / "at").write_text("held\\n", encoding="utf-8")
        deadline = time.monotonic() + 60
        while not (barrier / "go").exists():
            if time.monotonic() > deadline:
                sys.exit("holder: no go within 60 s")
            time.sleep(0.02)
        body = us.body_path(anchor, slug)
        if body.is_file():
            text = body.read_text(encoding="utf-8")
            us.put_body(anchor, slug, E._with_topics(text.rstrip("\\n"), ("python",)))
            print("bound")
        else:
            print("body gone before the bind")
""")


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    return h


def _tree(root, with_list):
    root.mkdir()
    (root / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (root / us.STORE_DIRNAME).mkdir()
    if with_list:
        topic_store.save_list(root, LIST, "jev")
    assert E.main(["set-scope", "--proj", str(root), "--scope", "WHAT: the top\nSTACK: none"]) == 0
    return str(root)


def _level(anchor, rel):
    level = Path(anchor, rel)
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert E.main(["set-scope", "--proj", str(level), "--scope", "WHAT: a level\nSTACK: python"]) == 0
    return str(level)


def _slugs_at(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return {p.slug for p in us.parse_pointer_index(text)[1]}


def _queued(anchor):
    lock = E.placement_lock_path(anchor)
    return any(p.name.startswith(lock.name + ".q") for p in lock.parent.iterdir())


def _await(what, proc, done):
    """Wait until `done()` holds; fail (not hang) when `proc` ends first or nothing comes."""
    deadline = time.monotonic() + FINISH_S
    while not done():
        if proc is not None and proc.poll() is not None:
            pytest.fail("%s ended before %s: %s" % (proc.args, what, proc.communicate()[0]))
        assert time.monotonic() < deadline, "never saw " + what
        time.sleep(0.02)


def _popen(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8")


def test_a_cross_tree_relocate_waits_for_a_binding_and_then_refuses_the_placed_fact(tmp_path):
    src_anchor = _tree(tmp_path / "src", with_list=True)
    dst_anchor = _tree(tmp_path / "dst", with_list=False)
    src, dst = _level(src_anchor, "d"), _level(dst_anchor, "d")
    E.add_or_update_entry(src, title="T feedback-x", hook=HOOK, body="body of feedback-x",
                          type_="feedback", slug="feedback-x")
    barrier = tmp_path / "barrier"
    barrier.mkdir()
    holder = _popen([sys.executable, "-c", HOLDER, str(HOOKS), src_anchor, "feedback-x",
                     str(barrier)])
    _await("the holder taking the placement lock", holder, (barrier / "at").exists)
    relocate = _popen([sys.executable, str(ENGINE), "relocate", "--from-level", src,
                       "--to-level", dst, "--slug", "feedback-x"])
    # The event that decides the interleaving: the relocate either finishes (it never asked for
    # the lock) or queues behind the holder (it did).
    _await("the relocate finishing or queueing", None,
           lambda: relocate.poll() is not None or _queued(src_anchor))
    waited = relocate.poll() is None
    (barrier / "go").write_text("go\n", encoding="utf-8")
    holder_out = holder.communicate(timeout=FINISH_S)[0]
    relocate_out = relocate.communicate(timeout=FINISH_S)[0]
    assert holder.returncode == 0, holder_out
    assert waited, ("relocate ran while the source tree's placement lock was held: "
                    + relocate_out + holder_out)
    assert holder_out.strip() == "bound"
    assert relocate.returncode != 0 and "placed by topic" in relocate_out, relocate_out
    assert "feedback-x" in _slugs_at(src)
    assert us.body_path(src_anchor, "feedback-x").is_file()
    assert not us.body_path(dst_anchor, "feedback-x").exists()
    assert "feedback-x" not in _slugs_at(dst)


def test_a_cross_tree_relocate_out_of_a_tree_without_a_list_takes_no_placement_lock(tmp_path):
    """A tree with no topic list places nothing, so its relocates keep their own pace: a stray
    lock file there does not hold one back."""
    src_anchor = _tree(tmp_path / "src", with_list=False)
    dst_anchor = _tree(tmp_path / "dst", with_list=False)
    src, dst = _level(src_anchor, "d"), _level(dst_anchor, "d")
    E.add_or_update_entry(src, title="T feedback-y", hook=HOOK, body="body of feedback-y",
                          type_="feedback", slug="feedback-y")
    lock = E.placement_lock_path(src_anchor)
    lock.write_text("peer\n", encoding="utf-8")
    try:
        done = subprocess.run([sys.executable, str(ENGINE), "relocate", "--from-level", src,
                               "--to-level", dst, "--slug", "feedback-y"],
                              capture_output=True, text=True, encoding="utf-8", timeout=FINISH_S)
    finally:
        lock.unlink()
    assert done.returncode == 0, done.stdout + done.stderr
    assert "feedback-y" in _slugs_at(dst)
    assert os.path.isfile(us.body_path(dst_anchor, "feedback-y"))
