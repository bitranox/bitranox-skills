"""move, relocate, rename and the inbound-ref rewrite of a rename never write back a copy of a
fact read before another session's `add` landed.

Each verb reads a fact's line (and, for relocate and rename, its body), then writes a line and a
body built from that read. An `add` from another session can land between the two: it updates
the line and the body under the level lock. A verb that writes what it read unlocked puts the
old hook, title and prose back over the add's, and both sides exit 0.

The second writer here is a REAL process. In each trial it updates the fact in a loop, the hook,
the title and the prose carrying its counter N, while this process runs the verb once; the loop
stops when the fact has left the level (the next `add` is refused, or creates a new fact). Every
`add` that returned an UPDATE of the fact happened before the verb took the fact away, so the
fact's new home must carry the counter of the last such update. A verb that copied an older read
leaves a smaller counter there.

The inbound-ref rewrite is checked by an observer process instead: a citing fact's counter only
ever grows, so any sample of it below one already seen is a stale copy written back.

All content ASCII.
"""

import json
import os
import random
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

import memory_engine as E
import uuid_store as us

if sys.platform == "win32":
    import _winapi

HOOKS = Path(E.__file__).resolve().parent

# The longest pause, in seconds, a worker takes after each of its writes. A real session pauses
# between its writes, and the pause spreads the adds over the verb's whole run so that they land
# many times per verb. (The level lock serves its waiters in arrival order, so an unpaced worker
# no longer keeps a waiting verb out; see `sig.memory_lock`.)
_PACE = 0.005

# Every _GAP_EVERY-th write the pause is _GAP instead, a little more than one poll. On Windows an
# add holds the lock for about 250 ms, and behind such holds 5 ms apart a relocate's 5 s wait
# still ran out (1 run in 3). Pausing that long after EVERY write let the stale copy the
# relocate test exists to catch slip through in 1 of 2 runs; the short pauses keep the adds dense.
_GAP, _GAP_EVERY = 0.06, 4


def _script(path, source):
    """Write a worker's source to `path`, its PACE, GAP and GAP_EVERY set to the constants."""
    for name, value in (("GAP_EVERY", _GAP_EVERY), ("GAP", _GAP), ("PACE", _PACE)):
        source = source.replace(name, repr(value))
    path.write_text(source, encoding="utf-8")

_UPDATER = r'''
import json, random, sys, time
from pathlib import Path
hooks, level, slug, ready, deadline = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
sys.path.insert(0, hooks)
import memory_engine as E
updated, ended = 0, "deadline"
n = 0
while time.time() < deadline:
    n += 1
    try:
        _slug, created = E.upsert_entry(
            level, "T%d" % n, "When racing %d, keep it." % n, body="prose %d" % n, slug=slug)
    except (E.SlugCollision, E.PinnedEntry) as exc:
        ended = type(exc).__name__
        break
    if created:
        ended = "created"
        break
    updated = n
    if n == 1:
        Path(ready).write_text("x", encoding="utf-8")
    time.sleep(GAP if n % GAP_EVERY == 0 else random.uniform(0.0, PACE))
print(json.dumps({"updated": updated, "ended": ended}))
'''

_NUM = re.compile(r"(\d+)")


def _counter(text):
    """The counter N in 'T<N>', 'When racing <N>, ...' or 'prose <N>'; None when absent."""
    m = _NUM.search(text or "")
    return int(m.group(1)) if m else None


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(root, *levels):
    """A tree at `root` with a CLAUDE.md at the root and at each of `levels` (relative paths),
    its central store at the root."""
    root.mkdir(parents=True)
    (root / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (root / us.STORE_DIRNAME).mkdir()
    out = []
    for rel in levels:
        d = root / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        out.append(str(d))
    return out


def _line(level, slug):
    text = (Path(level) / "CLAUDE.local.md").read_text(encoding="utf-8")
    return next((p for p in us.parse_pointer_index(text)[1] if p.slug == slug), None)


def _race(tmp, level, slug, verb):
    """Start the updater on `level`/`slug`, run `verb()` once it has updated the fact at least
    once, and return the updater's report."""
    ready = tmp / "ready"
    worker = tmp / "updater.py"
    _script(worker, _UPDATER)
    proc = subprocess.Popen([sys.executable, str(worker), str(HOOKS), level, slug, str(ready),
                             repr(time.time() + 20.0)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    try:
        start = time.time()
        while not ready.exists():
            assert proc.poll() is None, proc.communicate()
            assert time.time() - start < 15, "the updater never updated the fact"
            time.sleep(0.002)
        time.sleep(random.uniform(0.0, 0.02))
        verb()
        out, err = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()
    assert proc.returncode == 0, err
    return json.loads(out.strip().splitlines()[-1])


TRIALS = 12


def _assert_home_carries(rows):
    """Every trial's new home carries the counter of the updater's last update."""
    stale = [r for r in rows if r["home"] != (r["updated"],) * len(r["home"])]
    assert not stale, "a verb wrote back a copy read before an add landed: %s" % stale


def test_move_carries_the_last_concurrent_update(tmp_path):
    rows = []
    for i in range(TRIALS):
        sub, top = _tree(tmp_path / ("t%d" % i), "proj/sub", "proj")
        E.add_or_update_entry(sub, "T0", "When racing 0, keep it.", body="prose 0", slug="fact")
        moved = []
        res = _race(tmp_path / ("t%d" % i), sub, "fact",
                    lambda: moved.append(E.move_entry(sub, top, "fact")))
        assert moved[0].moved, moved[0].refused
        ptr = _line(top, "fact")
        body = us.body_path(str(tmp_path / ("t%d" % i)), "fact").read_text(encoding="utf-8")
        rows.append({"updated": res["updated"], "ended": res["ended"],
                     "home": (_counter(ptr.hook), _counter(ptr.title),
                              _counter(E.body_title(body)))})
    _assert_home_carries(rows)


def test_relocate_carries_the_last_concurrent_update(tmp_path):
    rows = []
    for i in range(TRIALS):
        (src,) = _tree(tmp_path / ("a%d" % i), "proj")
        (dst,) = _tree(tmp_path / ("b%d" % i), "proj")
        E.add_or_update_entry(src, "T0", "When racing 0, keep it.", body="prose 0", slug="fact")
        done = []
        res = _race(tmp_path / ("a%d" % i), src, "fact",
                    lambda: done.append(E.relocate_entry(src, dst, "fact")))
        assert done[0].relocated, done[0].refused
        ptr = _line(dst, "fact")
        body = us.body_path(str(tmp_path / ("b%d" % i)), "fact").read_text(encoding="utf-8")
        prose = body.split("---")[-1]
        rows.append({"updated": res["updated"], "ended": res["ended"],
                     "home": (_counter(ptr.hook), _counter(ptr.title), _counter(prose))})
    _assert_home_carries(rows)


def test_rename_carries_the_last_concurrent_update(tmp_path):
    rows = []
    for i in range(TRIALS):
        root = tmp_path / ("t%d" % i)
        (proj,) = _tree(root, "proj")
        E.add_or_update_entry(proj, "T0", "When racing 0, keep it.", body="prose 0", slug="fact")
        done = []
        res = _race(root, proj, "fact",
                    lambda: done.append(E.rename_entry(proj, "fact", "renamed")))
        assert done[0].renamed, done[0].refused
        ptr = _line(proj, "renamed")
        body = us.body_path(str(root), "renamed").read_text(encoding="utf-8")
        prose = body.split("---")[-1]
        rows.append({"updated": res["updated"], "ended": res["ended"],
                     "home": (_counter(ptr.hook), _counter(ptr.title), _counter(prose))})
    _assert_home_carries(rows)


class _HeldOpen:
    """The file at `path` held open for reading, the way another session's unlocked read of a
    body holds it (an `add`'s placement check, a recall hook), and closed `seconds` later from a
    second thread. Python opens without FILE_SHARE_DELETE, so on Windows a rename of the file
    fails with a sharing violation while it is held; on POSIX it does not."""

    def __init__(self, path, seconds):
        self.fd = os.open(str(path), os.O_RDONLY)
        self.timer = threading.Timer(seconds, os.close, args=(self.fd,))

    def __enter__(self):
        self.timer.start()
        return self

    def __exit__(self, *exc):
        self.timer.join()


class _HeldExclusive:
    """The file at `path` opened on Windows with no sharing at all, as a write replacing it or a
    scanner can hold it, and closed `seconds` later from a second thread: every other open of it
    is refused meanwhile with a PermissionError."""

    def __init__(self, path, seconds):
        self.handle = _winapi.CreateFile(str(path), _winapi.GENERIC_READ, 0, 0,
                                         _winapi.OPEN_EXISTING, 0, 0)
        self.timer = threading.Timer(seconds, _winapi.CloseHandle, args=(self.handle,))

    def __enter__(self):
        self.timer.start()
        return self

    def __exit__(self, *exc):
        self.timer.join()


@pytest.mark.skipif(sys.platform != "win32", reason="only Windows refuses an open by share mode")
def test_an_add_waits_out_a_body_another_handle_holds(tmp_path):
    """An `add` reads the body without the level lock to decide whether the fact is placed by
    topic. On Windows that read can meet the body held by another session's write (the instant
    of its replace) and be refused; the add waits it out instead of failing with "unreadable".
    Seen in test_memory_engine_retitle_race: an add's worker died on TreeWalkError there."""
    root = tmp_path / "tree"
    (proj,) = _tree(root, "proj")
    E.add_or_update_entry(proj, "T0", "When racing 0, keep it.", body="prose 0", slug="fact")
    with _HeldExclusive(us.body_path(str(root), "fact"), 0.3):
        result = E.upsert_entry(proj, "T1", "When racing 1, keep it.", body="prose 1", slug="fact")
    assert result == ("fact", False)
    assert _counter(_line(proj, "fact").title) == 1


def _old_slug_answers_again(level):
    """True when an `add` of the old slug updates a fact rather than creating one: the old name
    still resolves after the verb took the fact away."""
    _slug, created = E.upsert_entry(level, "New", "When reusing the old name, a new fact.",
                                    body="new prose", slug="fact")
    return not created


def test_rename_waits_out_a_reader_holding_the_old_body(tmp_path):
    """A rename that meets the old body held open by another reader archives it once the reader
    lets go, instead of leaving it in place. Left in place it is a body no level points at, and
    the next `add` of the old slug adopts it: the renamed fact comes back under its old name.
    This is the Windows failure of test_rename_carries_the_last_concurrent_update (an updater
    that kept UPDATING the old slug until its deadline)."""
    root = tmp_path / "tree"
    (proj,) = _tree(root, "proj")
    E.add_or_update_entry(proj, "T0", "When racing 0, keep it.", body="prose 0", slug="fact")
    with _HeldOpen(us.body_path(str(root), "fact"), 0.3):
        rep = E.rename_entry(proj, "fact", "renamed")
    assert rep.renamed, rep.refused
    assert rep.warnings == []
    assert not us.body_path(str(root), "fact").exists()
    assert not _old_slug_answers_again(proj)


def test_relocate_waits_out_a_reader_holding_the_source_body(tmp_path):
    """The same for a cross-tree relocate: the source body is archived once the reader lets go,
    so the source tree has no dangling copy for the next `add` of the slug to adopt."""
    (src,) = _tree(tmp_path / "a", "proj")
    (dst,) = _tree(tmp_path / "b", "proj")
    E.add_or_update_entry(src, "T0", "When racing 0, keep it.", body="prose 0", slug="fact")
    with _HeldOpen(us.body_path(str(tmp_path / "a"), "fact"), 0.3):
        rep = E.relocate_entry(src, dst, "fact")
    assert rep.relocated, rep.refused
    assert rep.warnings == []
    assert not us.body_path(str(tmp_path / "a"), "fact").exists()
    assert not _old_slug_answers_again(src)


_CITER = r'''
import json, os, random, sys, time
hooks, level, stop, deadline, progress = (sys.argv[1], sys.argv[2], sys.argv[3],
                                          float(sys.argv[4]), sys.argv[5])
sys.path.insert(0, hooks)
import memory_engine as E
n = 0
while not os.path.exists(stop) and time.time() < deadline:
    n += 1
    E.add_or_update_entry(level, "Citer", "When racing %d, see [[fact]] and [[renamed]]." % n,
                          body="prose %d cites [[fact]] and [[renamed]]." % n, slug="citer")
    try:
        with open(progress, "w", encoding="utf-8") as fh:
            fh.write(str(n))
    except OSError:
        pass                                     # the test is reading it; the next one lands
    time.sleep(GAP if n % GAP_EVERY == 0 else random.uniform(0.0, PACE))
print(json.dumps({"role": "citer", "done": n}))
'''

_OBSERVER = r'''
import json, os, re, sys, time
from pathlib import Path
hooks, root, level, stop, deadline = (sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
                                      float(sys.argv[5]))
sys.path.insert(0, hooks)
import uuid_store as us
num = re.compile(r"(\d+)")
seen = {"hook": 0, "body": 0}
samples = drops = 0
while not os.path.exists(stop) and time.time() < deadline:
    try:
        text = Path(level, "CLAUDE.local.md").read_text(encoding="utf-8")
        body = us.body_path(root, "citer").read_text(encoding="utf-8")
    except OSError:
        continue
    ptr = next((p for p in us.parse_pointer_index(text)[1] if p.slug == "citer"), None)
    for site, value in (("hook", ptr.hook if ptr else ""), ("body", body.split("---")[-1])):
        m = num.search(value)
        if not m:
            continue
        n = int(m.group(1))
        drops += n < seen[site]
        seen[site] = max(seen[site], n)
    samples += 1
    time.sleep(0.0002)
print(json.dumps({"role": "observer", "samples": samples, "drops": drops}))
'''


# The run ends once BOTH counts are reached: the renames the rewrite is tested on, and the
# citer's writes they must overlap. A fixed rename count alone let 12 renames finish while a
# paced citer on a slow macOS runner had written 16 times.
RENAMES, CITES = 12, 20


def _progress(path):
    """The count a worker last wrote to `path`; 0 before its first write, or mid-write."""
    try:
        return int(path.read_text(encoding="utf-8") or 0)
    except (OSError, ValueError):
        return 0


def test_the_inbound_ref_rewrite_never_writes_back_an_older_citer(tmp_path):
    """A rename back and forth while another process keeps updating a fact that cites it: the
    citer's counter, in its hook and its body, never goes down.

    The level holds facts of an ordinary count, so the rewrite reads each before it reaches the
    citer, and the renames are spaced at random, off the citer's rhythm: renamed back to back,
    the rename's own line swaps kept the citer waiting out a lock poll while the rewrite ran, and
    the two seldom overlapped. Against the engine that rewrote from an unlocked read this caught
    a stale citer in 6 of 6 runs; the deterministic case is in
    test_memory_engine_writer_interleavings.py."""
    root = tmp_path / "tree"
    (proj,) = _tree(root, "proj")
    E.add_or_update_entry(proj, "Fact", "When racing, the cited fact.", body="cited", slug="fact")
    for k in range(40):
        E.add_or_update_entry(proj, "Filler %d" % k, "When filling, fact %d." % k,
                              body="filler %d" % k, slug="filler-%d" % k)
    E.add_or_update_entry(proj, "Citer", "When racing 0, see [[fact]] and [[renamed]].",
                          body="prose 0 cites [[fact]] and [[renamed]].", slug="citer")
    citer, observer = tmp_path / "citer.py", tmp_path / "observer.py"
    _script(citer, _CITER)
    _script(observer, _OBSERVER)
    stop, progress = tmp_path / "stop", tmp_path / "citer.count"
    deadline = time.time() + 120.0              # a safety net only: the counts end the run
    procs = [subprocess.Popen([sys.executable, str(citer), str(HOOKS), proj, str(stop),
                               repr(deadline), str(progress)],
                              # it warns on stderr for each ref to the name the fact does not
                              # have now: a pipe nobody reads fills, and the citer then stalls
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              encoding="utf-8"),
             subprocess.Popen([sys.executable, str(observer), str(HOOKS), str(root), proj,
                               str(stop), repr(deadline)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")]
    renames, rewrote, names = 0, 0, ("fact", "renamed")
    try:
        time.sleep(0.5)                              # both workers imported and running
        # Counts, not a clock: a 4 s window held 9 renames on a slow macOS runner.
        while (renames < RENAMES or _progress(progress) < CITES) and time.time() < deadline:
            rep = E.rename_entry(proj, names[renames % 2], names[(renames + 1) % 2])
            assert rep.renamed, rep.refused
            rewrote += {r.citer for r in rep.refs_rewritten} == {"citer"}
            renames += 1
            time.sleep(random.uniform(0.0, 0.005))
        time.sleep(0.3)                              # the observer samples after the last one
        stop.write_text("x", encoding="utf-8")
        results = {}
        for proc in procs:
            out, err = proc.communicate(timeout=60)
            assert proc.returncode == 0, err
            row = json.loads(out.strip().splitlines()[-1])
            results[row["role"]] = row
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
    assert rewrote == renames, (renames, rewrote)
    assert renames >= RENAMES, (renames, results)
    assert results["citer"]["done"] >= CITES, results
    assert results["observer"]["samples"] >= 200, results
    assert results["observer"]["drops"] == 0, (renames, results)


_RETITLER = r'''
import json, os, random, sys, time
from pathlib import Path
hooks, level, progress, stop = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, hooks)
import memory_engine as E
import uuid_store as us


def title_now():
    text = Path(level, "CLAUDE.local.md").read_text(encoding="utf-8")
    return int(next(p for p in us.parse_pointer_index(text)[1] if p.slug == "pinned-fact").title[1:])


n = stale = 0
while not os.path.exists(stop):
    # nothing but this process writes a title, so a title below n, read before the next amend
    # or right after this one, is an older title another writer put back over this one
    stale += title_now() < n
    n += 1
    E.amend_pinned_entry(level, "pinned-fact", title="T%d" % n)
    stale += title_now() < n
    Path(progress).write_text(str(n), encoding="utf-8")
    time.sleep(random.uniform(0.0, PACE))
print(json.dumps({"amends": n, "stale": stale}))
'''

AMENDS_TO_MEET = 300
"""How many title amends the retitler makes before the body amends stop: counted, not timed."""


def test_an_amend_without_a_title_never_writes_back_an_older_title(tmp_path):
    """amend-pinned with no title read the stored title before the level lock and wrote that read
    back: a concurrent amend's new title landing in between was undone (both exit 0). A real
    process amends the title in a loop and reads each back; this one amends the body only, over
    and over. The retitler must never read a title older than the one it just wrote."""
    (proj,) = _tree(tmp_path / "tree", "proj")
    E.add_or_update_entry(proj, "T0", "When racing, keep the pin.", body="prose 0",
                          slug="pinned-fact", pin=True)
    worker, progress, stop = tmp_path / "retitler.py", tmp_path / "progress", tmp_path / "stop"
    _script(worker, _RETITLER)
    proc = subprocess.Popen([sys.executable, str(worker), str(HOOKS), proj, str(progress),
                             str(stop)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    body_amends = 0
    try:
        while _progress(progress) < 1:
            assert proc.poll() is None, proc.communicate()
            time.sleep(0.002)
        while _progress(progress) < AMENDS_TO_MEET and body_amends < 20000:
            body_amends += 1
            E.amend_pinned_entry(proj, "pinned-fact", body="prose %d" % body_amends)
            # paced like the worker, as a real session paces its writes
            time.sleep(random.uniform(0.0, _PACE))
        stop.write_text("x", encoding="utf-8")
        out, err = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()
    assert proc.returncode == 0, err
    res = json.loads(out.strip().splitlines()[-1])
    assert res["amends"] >= AMENDS_TO_MEET and body_amends >= 10, (res, body_amends)
    assert res["stale"] == 0, "%d of %d title amends were undone by %d body amends" % (
        res["stale"], res["amends"], body_amends)


def test_an_update_only_write_refuses_a_slug_the_level_holds_no_line_of(tmp_path):
    """`must_exist` (amend-pinned's write) decides presence under the level lock: a fact that left
    the level after the amend's own fast check is refused with UnknownSlug, never created anew
    and never re-adopted from its body, which an ordinary add does with a body no level points
    at."""
    root = tmp_path / "tree"
    (proj,) = _tree(root, "proj")
    E.add_or_update_entry(proj, "T0", "When racing, keep the pin.", body="prose 0",
                          slug="pinned-fact", pin=True)
    E.drop_pointer(proj, "pinned-fact")                # its body stays: a dangling body
    with pytest.raises(E.UnknownSlug):
        E.upsert_entry(proj, "", "", body="new prose", slug="pinned-fact",
                       allow_pinned_overwrite=True, must_exist=True)
    assert _line(proj, "pinned-fact") is None
    assert "prose 0" in us.body_path(str(root), "pinned-fact").read_text(encoding="utf-8")
