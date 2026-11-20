"""A retitle writes the pointer line and the body's `title:` in ONE hold of the level lock.

Three REAL processes share one scratch tree: one retitles a fact in a loop, one re-adds the same
fact with a new title in a loop (the per-turn capture path of another session), and an observer
takes the level lock - the same lock both writers use - and compares the line's title with the
body's. Any hold in which the two differ is a state another writer can build on: an `add` landing
there left the line with its title and the body with the retitle's until the next write.

Measured on the two-hold retitle (add_pointer's own hold, then a second one for the body): the
observer saw the titles differ in 3930 of 16159 holds over 10 seconds; with one hold, 0 of 14230.
All content ASCII.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import memory_engine as E
import uuid_store as us

HOOKS = Path(E.__file__).resolve().parent

_WORKER = r'''
import json, os, sys, time
from pathlib import Path
hooks, role, anchor, proj, stop = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
sys.path.insert(0, hooks)
import memory_engine as E
import self_improve_signals as sig
import uuid_store as us

def titles():
    text = Path(proj, "CLAUDE.local.md").read_text(encoding="utf-8")
    ptr = next(p for p in us.parse_pointer_index(text)[1] if p.slug == "fact")
    body = us.body_path(anchor, "fact").read_text(encoding="utf-8").rstrip("\n")
    return ptr.title, E._body_title(body)

done = differ = 0
while time.time() < stop:
    if role == "retitle":
        done += bool(E.retitle_entry(proj, "fact", "A%d" % done).retitled)
    elif role == "add":
        E.add_or_update_entry(proj, "B%d" % done, "When racing, keep titles equal.", slug="fact")
        done += 1
    else:
        with sig.memory_lock(sig.claude_local_md_path(proj), timeout=30, poll=0.0002):
            line_title, body_title = titles()
        done += 1
        differ += line_title != body_title
        time.sleep(0.0003)
print(json.dumps({"role": role, "done": done, "differ": differ}))
'''


def _tree(tmp_path):
    """anchor -> proj, both CLAUDE.md-bearing, so the pair is one tree with its store at the
    anchor; one fact, `fact`, at proj."""
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    E.add_or_update_entry(str(proj), "T0", "When racing, keep titles equal.", body="the body",
                          slug="fact")
    return str(anchor), str(proj)


def test_no_hold_of_the_level_lock_sees_the_line_and_body_titles_differ(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    anchor, proj = _tree(tmp_path)
    worker = tmp_path / "worker.py"
    worker.write_text(_WORKER, encoding="utf-8")
    stop = time.time() + 3.0
    procs = [subprocess.Popen([sys.executable, str(worker), str(HOOKS), role, anchor, proj,
                               repr(stop)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              encoding="utf-8")
             for role in ("retitle", "add", "observe")]
    results = {}
    for proc in procs:
        out, err = proc.communicate(timeout=120)
        assert proc.returncode == 0, err
        row = json.loads(out.strip().splitlines()[-1])
        results[row["role"]] = row

    # The race ran: each writer wrote many times and the observer held the lock many times.
    assert results["retitle"]["done"] >= 20, results
    assert results["add"]["done"] >= 20, results
    assert results["observe"]["done"] >= 200, results
    assert results["observe"]["differ"] == 0, results
    ptr = next(p for p in us.parse_pointer_index(
        (Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8"))[1] if p.slug == "fact")
    body = us.body_path(anchor, "fact").read_text(encoding="utf-8").rstrip("\n")
    assert ptr.title == E._body_title(body)
    assert "the body" in body, "neither writer may lose the prose"



def _between_read_and_write(action):
    """A profile function that runs `action()` once, when the retitle first calls
    `_line_growth_refusal`: after its unlocked read of the store, before its locked write. It
    replaces nothing; it only places another session's write at that point."""
    fired = []

    def profile(frame, event, _arg):
        if fired or event != "call" or frame.f_code.co_name != "_line_growth_refusal":
            return
        fired.append(True)
        action()

    return profile, fired


def _retitle_with(profile, proj, title):
    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        return E.retitle_entry(proj, "fact", title)
    finally:
        sys.setprofile(previous)


def _line(proj):
    text = (Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8")
    return next((p for p in us.parse_pointer_index(text)[1] if p.slug == "fact"), None)


def test_a_line_dropped_meanwhile_is_not_put_back(tmp_path, monkeypatch):
    """The line is re-read under the lock: one a concurrent `move` dropped after the retitle's
    unlocked read stays dropped, the retitle is refused, and the body keeps its title."""
    monkeypatch.setenv("HOME", str(tmp_path))
    anchor, proj = _tree(tmp_path)
    body_before = us.body_path(anchor, "fact").read_bytes()

    profile, fired = _between_read_and_write(lambda: E._drop_pointer(proj, "fact"))
    rep = _retitle_with(profile, proj, "New title")

    assert fired, "the interleaving was not exercised"
    assert rep.retitled is False and "left" in rep.refused, rep
    assert _line(proj) is None
    assert us.body_path(anchor, "fact").read_bytes() == body_before


def test_a_fact_pinned_meanwhile_is_refused_and_left_alone(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    anchor, proj = _tree(tmp_path)

    def pin_it():
        E.add_or_update_entry(proj, "T0", "When racing, keep titles equal.", slug="fact", pin=True)

    profile, fired = _between_read_and_write(pin_it)
    rep = _retitle_with(profile, proj, "New title")

    assert fired, "the interleaving was not exercised"
    assert rep.retitled is False and "amend-pinned" in rep.refused, rep
    assert (_line(proj).title, _line(proj).pin) == ("T0", True)


def test_the_line_keeps_a_hook_written_meanwhile(tmp_path, monkeypatch):
    """Title only: the hook comes from the file under the lock, never from the earlier read."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _anchor, proj = _tree(tmp_path)

    def new_hook():
        E.add_or_update_entry(proj, "T0", "When racing, a newer hook.", slug="fact")

    profile, fired = _between_read_and_write(new_hook)
    rep = _retitle_with(profile, proj, "New title")

    assert fired and rep.retitled is True, rep
    assert (_line(proj).title, _line(proj).hook) == ("New title", "When racing, a newer hook.")
