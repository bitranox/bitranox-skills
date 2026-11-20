"""`heal --backfill-titles` holds, for each fact, the lock of every level that carries its line.

A fact can have a line at more than one level: by design when it is placed by topic, and as a
duplicate otherwise. Each of those levels is a route an `add` writes the body through, under that
level's lock. A back-fill that held only the first level's lock read the body, let an `add`
through another level write new prose, and then wrote the old prose back with the title in it:
the new prose was gone, both sides exited 0. The second process here is a REAL one, started while
the back-fill sits between its read and its write. All content ASCII.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest

import memory_engine as E
import self_improve_signals as sig
import topic_store
import uuid_store as us

HOOKS = Path(E.__file__).resolve().parent

_ADD = r'''
import sys
sys.path.insert(0, sys.argv[1])
import memory_engine as E
E.add_or_update_entry(sys.argv[2], "Old fact title", "When x, do y.", body=sys.argv[4],
                      slug=sys.argv[3])
'''


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path):
    """anchor -> proj and anchor -> other, all CLAUDE.md-bearing; central store at the anchor."""
    anchor = tmp_path / "tree"
    for d in (anchor, anchor / "proj", anchor / "other"):
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return str(anchor), str(anchor / "proj"), str(anchor / "other")


def _untitled_fact(anchor, level, slug, prose):
    """A fact as engines before the title field left it: a framed body with no `title:`."""
    E.add_or_update_entry(level, "Old fact title", "When x, do y.", body="P.", slug=slug)
    us.body_path(anchor, slug).write_text(
        "---\nname: %s\ndescription: When x, do y.\nmetadata:\n  type: feedback\n---\n\n%s\n"
        % (slug, prose), encoding="utf-8")


def _while_backfill_holds_its_read(start):
    """A profile function that calls `start()` once, when the back-fill first reaches
    `_with_title`: after it read a body, before it writes it back. It replaces nothing."""
    fired = []

    def profile(frame, event, _arg):
        if fired or event != "call" or frame.f_code.co_name != "_with_title":
            return
        fired.append(start())

    return profile, fired


def _backfill_profiled(profile, proj):
    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        return E.backfill_titles(proj)
    finally:
        sys.setprofile(previous)


def _start_add(tmp_path, level, slug, prose):
    script = tmp_path / "add.py"
    script.write_text(_ADD, encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(script), str(HOOKS), level, slug, prose],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    # Long enough for the add to finish when nothing blocks it, well inside its 5 s lock wait
    # when the back-fill holds the lock it needs.
    deadline = time.time() + 3.0
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.05)
    return proc


def test_an_add_through_another_level_keeps_its_prose(tmp_path):
    anchor, proj, other = _tree(tmp_path)
    _untitled_fact(anchor, proj, "dup-fact", "Prose one.")
    us.add_pointer(other, "dup-fact", "Old fact title", "When x, do y.")   # the second line

    # The add goes through the carrier the walk meets SECOND: the back-fill reads the body while
    # holding the lock of the one it meets first.
    walk = [str(Path(level).resolve()) for level in E.curated_levels_under(anchor)]
    second = max((proj, other), key=lambda level: walk.index(str(Path(level).resolve())))
    profile, fired = _while_backfill_holds_its_read(
        lambda: _start_add(tmp_path, second, "dup-fact", "Prose two."))
    rep = _backfill_profiled(profile, proj)
    proc = fired[0]
    _out, err = proc.communicate(timeout=60)

    assert proc.returncode == 0, err
    assert rep.filled == ["dup-fact"]
    body = us.body_path(anchor, "dup-fact").read_text(encoding="utf-8")
    assert "Prose two." in body and "Prose one." not in body, body
    assert E._body_title(body.rstrip("\n")) == "Old fact title"


def test_an_add_of_another_fact_at_the_same_level_is_not_held_up(tmp_path):
    """One fact's locks at a time: a level's lock is not held across all of its facts, so an add
    of a fact the back-fill is not touching goes through while the back-fill is under way."""
    anchor, proj, _other = _tree(tmp_path)
    _untitled_fact(anchor, proj, "first-fact", "Prose one.")
    _untitled_fact(anchor, proj, "second-fact", "Prose two.")
    lock = Path(str(sig.claude_local_md_path(proj)) + ".lock")
    held_between = []

    def profile(frame, event, _arg):
        # On the second fact's lookup of its body path, before its locks are taken: is the
        # level lock still held from the first fact?
        if event == "call" and frame.f_code.co_name == "body_path" and not held_between \
                and frame.f_locals.get("slug") == "second-fact":
            held_between.append(lock.exists())

    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        rep = E.backfill_titles(proj)
    finally:
        sys.setprofile(previous)

    assert rep.filled == ["first-fact", "second-fact"]
    assert held_between == [False]


def test_a_fact_bound_to_a_topic_is_filled_under_the_placement_lock(tmp_path):
    """Every write to a fact placed by topic holds the tree's placement lock; so does the
    back-fill's, which then never interleaves with a render moving that fact's lines."""
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, {"python": "Python code and its tooling"}, "jev")
    level = anchor / "py"
    level.mkdir()
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert E.main(["set-scope", "--proj", str(level), "--scope", "WHAT: a level\nSTACK: python"]) == 0
    E.set_level_topics(str(level), ("python",))
    E.add_or_update_entry(str(level), "Bound fact", "When x, do y.", body="Prose.",
                          type_="feedback", slug="bound-fact")
    E.set_fact_topics(str(level), {"bound-fact": ("python",)})
    path = us.body_path(str(anchor), "bound-fact")
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    assert sum(line.startswith("title: ") for line in lines) == 1
    path.write_text("".join(line for line in lines if not line.startswith("title: ")),
                    encoding="utf-8")
    placement = E.placement_lock_path(str(anchor))
    held = []

    def profile(frame, event, _arg):
        if not held and event == "call" and frame.f_code.co_name == "_with_title":
            held.append(placement.exists())

    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        rep = E.backfill_titles(str(level))
    finally:
        sys.setprofile(previous)

    assert rep.filled == ["bound-fact"]
    assert held == [True]
