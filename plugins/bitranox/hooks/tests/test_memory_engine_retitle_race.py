"""A retitle writes the pointer line and the body's `title:` in ONE hold of the level lock.

Three REAL processes share one scratch tree: one retitles a fact in a loop, one re-adds the same
fact with a new title in a loop (the per-turn capture path of another session), and an observer
takes the level lock - the same lock both writers use - and compares the line's title with the
body's. Any hold in which the two differ is a state another writer can build on: an `add` landing
there left the line with its title and the body with the retitle's until the next write.

Measured on the two-hold retitle (add_pointer's own hold, then a second one for the body): the
observer saw the titles differ in 3930 of 16159 holds over 10 seconds; with one hold, 0 of 14230.

The run ends on counts, not on a clock: the workers stop once each writer has written and the
observer has held the lock enough times, with a deadline as a safety net only. A 3 s window
ended Windows runs below the counts with no title differing (on one loaded CPU: 10 of 10, with
6 to 13 writes per writer): an add holds the lock for about 250 ms there. Each writer pauses
after each write, as a real session does, for up to a little more than one 50 ms poll of a lock
wait: an add that took the lock again within 5 ms left the retitle's 5 s wait no gap.

The pacing costs the race detection power: against the two-hold retitle it caught the gap in 4
of 6 runs. test_every_take_of_a_lock_by_retitle_finds_the_titles_equal checks the same property
with no timing in it and caught it in every run.
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

# The longest pause, in seconds, a writer takes after each write (see the module docstring).
_PACE = 0.06

# The observer polls the lock fast and comes back to it almost at once, so it is waiting when a
# writer lets go (the gap a two-hold retitle leaves is short). Once every _GAP_EVERY seconds it
# stays away for _GAP seconds, longer than the 50 ms a writer's lock wait polls at: back every time
# without that, it held the lock so often that a retitle's 5 s wait ran out on one loaded CPU.
# Spaced by the clock, not by a count of holds: a hold took 25 ms there and 0.5 ms unloaded.
_LOOK, _GAP, _GAP_EVERY = 0.0003, 0.06, 0.06

# Each writer's and the observer's count the run must reach before the workers are stopped;
# both multiples of 10, the step a worker reports its count in.
_WRITES, _HOLDS = 20, 200

_WORKER = r'''
import json, os, random, sys, time
from pathlib import Path
hooks, role, anchor, proj, stop, deadline, count = (sys.argv[1], sys.argv[2], sys.argv[3],
                                                    sys.argv[4], sys.argv[5], float(sys.argv[6]),
                                                    sys.argv[7])
sys.path.insert(0, hooks)
import memory_engine as E
import self_improve_signals as sig
import uuid_store as us

def titles():
    text = Path(proj, "CLAUDE.local.md").read_text(encoding="utf-8")
    ptr = next(p for p in us.parse_pointer_index(text)[1] if p.slug == "fact")
    body = us.body_path(anchor, "fact").read_text(encoding="utf-8").rstrip("\n")
    return ptr.title, E.body_title(body)

done = differ = 0
next_gap = time.time() + GAP_EVERY
while not os.path.exists(stop) and time.time() < deadline:
    if role == "retitle":
        done += bool(E.retitle_entry(proj, "fact", "A%d" % done).retitled)
        time.sleep(random.uniform(0.0, PACE))
    elif role == "add":
        E.add_or_update_entry(proj, "B%d" % done, "When racing, keep titles equal.", slug="fact")
        done += 1
        time.sleep(random.uniform(0.0, PACE))
    else:
        with sig.memory_lock(sig.claude_local_md_path(proj), timeout=30, poll=0.0002):
            line_title, body_title = titles()
        done += 1
        differ += line_title != body_title
        if time.time() >= next_gap:
            time.sleep(GAP)
            next_gap = time.time() + GAP_EVERY
        else:
            time.sleep(LOOK)
    if done % 10 == 0:                           # both counts the test waits for end in 0
        try:
            Path(count).write_text(str(done), encoding="utf-8")
        except OSError:
            pass                                 # the test is reading it; the next one lands
print(json.dumps({"role": role, "done": done, "differ": differ}))
'''


def _count(path):
    """The count a worker last wrote to `path`; 0 before its first, or mid-write."""
    try:
        return int(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0


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
    source = _WORKER
    for name, value in (("GAP_EVERY", _GAP_EVERY), ("PACE", _PACE), ("LOOK", _LOOK), ("GAP", _GAP)):
        source = source.replace(name, repr(value))
    worker.write_text(source, encoding="utf-8")
    stop = tmp_path / "stop"
    deadline = time.time() + 120.0                  # a safety net only: the counts end the run
    roles = {"retitle": _WRITES, "add": _WRITES, "observe": _HOLDS}
    counts = {role: tmp_path / (role + ".count") for role in roles}
    # A pipe nobody reads fills and stalls its writer, so stderr goes to a file read at the end.
    errs = {role: tmp_path / (role + ".err") for role in roles}
    procs = []
    try:
        for role in roles:
            with errs[role].open("w", encoding="utf-8") as err_fh:
                procs.append(subprocess.Popen(
                    [sys.executable, str(worker), str(HOOKS), role, anchor, proj, str(stop),
                     repr(deadline), str(counts[role])],
                    stdout=subprocess.PIPE, stderr=err_fh, encoding="utf-8"))
        while any(_count(counts[role]) < need for role, need in roles.items()):
            if time.time() > deadline or any(proc.poll() is not None for proc in procs):
                break
            time.sleep(0.05)
        stop.write_text("x", encoding="utf-8")
        results = {}
        for role, proc in zip(roles, procs, strict=True):
            out, _ = proc.communicate(timeout=60)
            assert proc.returncode == 0, errs[role].read_text(encoding="utf-8")
            row = json.loads(out.strip().splitlines()[-1])
            results[row["role"]] = row
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()

    # The race ran: each writer wrote many times and the observer held the lock many times.
    assert results["retitle"]["done"] >= _WRITES, results
    assert results["add"]["done"] >= _WRITES, results
    assert results["observe"]["done"] >= _HOLDS, results
    assert results["observe"]["differ"] == 0, results
    ptr = next(p for p in us.parse_pointer_index(
        (Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8"))[1] if p.slug == "fact")
    body = us.body_path(anchor, "fact").read_text(encoding="utf-8").rstrip("\n")
    assert ptr.title == E.body_title(body)
    assert "the body" in body, "neither writer may lose the prose"


def _titles(anchor, proj):
    """(the line's title, the body's title) as the files hold them now."""
    text = (Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8")
    ptr = next(p for p in us.parse_pointer_index(text)[1] if p.slug == "fact")
    return ptr.title, E.body_title(us.body_path(anchor, "fact").read_text(encoding="utf-8"))


def test_every_take_of_a_lock_by_retitle_finds_the_titles_equal(tmp_path, monkeypatch):
    """The race above with no timing in it: each time the retitle takes a lock, the moment
    another writer could take it instead, the line and the body carry one title. A retitle that
    wrote them in two holds arrives at its second take with the line retitled and the body not.
    The race test needs the observer to land in that gap; this sees every one."""
    monkeypatch.setenv("HOME", str(tmp_path))
    anchor, proj = _tree(tmp_path)
    seen = []

    def profile(frame, event, _arg):
        if event == "call" and frame.f_code.co_name == "memory_lock":
            seen.append(_titles(anchor, proj))

    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        rep = E.retitle_entry(proj, "fact", "New title")
    finally:
        sys.setprofile(previous)
    assert rep.retitled, rep
    assert seen, "the retitle took no lock"
    assert all(line == body for line, body in seen), seen
    assert _titles(anchor, proj) == ("New title", "New title")


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

    profile, fired = _between_read_and_write(lambda: E.drop_pointer(proj, "fact"))
    rep = _retitle_with(profile, proj, "New title")

    assert fired, "the interleaving was not exercised"
    assert rep.refused is not None
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
    assert rep.refused is not None
    assert rep.retitled is False and "amend-pinned" in rep.refused, rep
    line = _line(proj)
    assert line is not None and (line.title, line.pin) == ("T0", True)


def test_the_line_keeps_a_hook_written_meanwhile(tmp_path, monkeypatch):
    """Title only: the hook comes from the file under the lock, never from the earlier read."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _anchor, proj = _tree(tmp_path)

    def new_hook():
        E.add_or_update_entry(proj, "T0", "When racing, a newer hook.", slug="fact")

    profile, fired = _between_read_and_write(new_hook)
    rep = _retitle_with(profile, proj, "New title")

    assert fired and rep.retitled is True, rep
    line = _line(proj)
    assert line is not None
    assert (line.title, line.hook) == ("New title", "When racing, a newer hook.")
