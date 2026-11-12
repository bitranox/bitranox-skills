"""Tests for the tree's placement lock: a render, a set-topics and every write to a fact placed by
topic hold it, so none of them changes placement while another is between its passes.

Each race test runs both sides as real processes. One side is held at a chosen point by a
barrier file the engine cannot see (`placement_actor.py`, through the `write` port every level
file is written through), so the interleaving is the same on every run; the other side is
started while it is held. "Still running after a short wait" is the only timed check, and it can
only fail the GREEN direction if the lock is missing. All content ASCII.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import memory_engine as E
import self_improve_signals as sig
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python"
LIST = {"python": "Python code and its tooling", "rust": "Rust code", "git": "git and GitHub"}
HOOKS = Path(E.__file__).resolve().parent
ENGINE = HOOKS / "memory_engine.py"
ACTOR = Path(__file__).resolve().parent / "placement_actor.py"

# How long a process the lock must hold back is given to finish anyway. Without the lock it
# finishes well inside this; with it, it cannot finish at all until the holder lets go.
HELD_BACK_S = 1.5
# Bound on every wait for a process that is expected to finish: a hang fails, never stalls.
FINISH_S = 90.0


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
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top\nSTACK: none"]) == 0
    return str(anchor)


def _level(anchor, rel, topics=None):
    level = Path(anchor, *rel.split("/"))
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert E.main(["set-scope", "--proj", str(level), "--scope", SCOPE]) == 0
    if topics is not None:
        E.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, topics=None):
    E.add_or_update_entry(level, title="T " + slug, hook=HOOK, body="body of " + slug,
                          type_="feedback", slug=slug)
    if topics is not None:
        E.set_fact_topics(level, {slug: topics})


def _example(tmp_path):
    """The reviewer's tree: python under a and b, rust at c, nothing at d; one python rule placed."""
    anchor = _tree(tmp_path)
    levels = {rel: _level(anchor, rel, topics) for rel, topics in (
        ("a", ()), ("a/py", ("python",)), ("b", ()), ("b/py", ("python",)), ("c", ("rust",)),
        ("d", ()))}
    _fact(anchor, "feedback-py", ("python",))
    E.render_topics(anchor)
    assert _where(anchor, "feedback-py") == [levels["a/py"], levels["b/py"]]
    return anchor, levels


def _where(anchor, slug):
    return sorted(level for level in E.curated_levels_under(anchor)
                  if slug in {p.slug for p in us.parse_pointer_index(
                      sig.claude_local_md_path(level).read_text(encoding="utf-8"))[1]})


def _broken_invariants(anchor):
    """What the reviewer's checker reports: a body with no line anywhere (orphan), an unplaced
    fact with other than exactly one line, a line that says something else than its body, and a
    line with no body."""
    lines = {}
    for level in E.curated_levels_under(anchor):
        text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
        for ptr in us.parse_pointer_index(text)[1]:
            lines.setdefault(ptr.slug, []).append((level, ptr.index_line()))
    bad = []
    bodies = sorted(p.stem for p in us.central_facts_dir(anchor).glob("*.md"))
    for slug in bodies:
        held = lines.get(slug, [])
        head = E._read_body_head(us.body_path(anchor, slug))
        topics = E._body_topics(head)
        if not held:
            bad.append("orphan %s (topics %r)" % (slug, topics))
        elif not topics and len(held) != 1:
            bad.append("unplaced %s has %d lines" % (slug, len(held)))
        want = E._line_from_head(slug, head)
        for level, line in held:
            if want is not None and line != want.index_line():
                bad.append("line of %s at %s differs from its body" % (slug, level))
    bad.extend("line with no body: %s" % slug for slug in sorted(set(lines) - set(bodies)))
    return bad


def _lock_file(anchor):
    return Path(anchor) / us.STORE_DIRNAME / "placement.lock"


def _engine(*args):
    return [sys.executable, str(ENGINE), *map(str, args)]


def _actor(verb, proj, arg, barrier, pause_after):
    return subprocess.Popen([sys.executable, str(ACTOR), verb, str(proj), arg, str(barrier),
                             str(pause_after)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8")


def _start(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8")


def _wait_for_barrier(barrier, proc):
    deadline = time.monotonic() + FINISH_S
    while not (barrier / "at").exists():
        if proc.poll() is not None:
            pytest.fail("the held side ended before its barrier: %s" % proc.communicate()[0])
        assert time.monotonic() < deadline, "the held side never reached its barrier"
        time.sleep(0.02)


def _held_back(proc):
    """True when `proc` is still running after HELD_BACK_S."""
    try:
        proc.wait(timeout=HELD_BACK_S)
    except subprocess.TimeoutExpired:
        return True
    return False


def _finish(proc):
    out = proc.communicate(timeout=FINISH_S)[0]
    return proc.returncode, out


def _barrier(tmp_path):
    barrier = tmp_path / "barrier"
    barrier.mkdir()
    return barrier


# ---- the two races the review found ---------------------------------------------------------

def test_a_rebind_during_a_tree_render_leaves_no_fact_without_a_line(tmp_path):
    """s8: a set-topics landing between the render's ADD and REMOVE passes made REMOVE drop every
    line of a fact ADD never placed again (an orphan, both exiting 0). The render is held right
    after its ADD pass wrote c (its last add); the rebind is started then and must wait."""
    anchor, levels = _example(tmp_path)
    _fact(anchor, "feedback-rs", ("rust",))          # gives the render an ADD write at c
    barrier = _barrier(tmp_path)
    render = _actor("render", levels["d"], "tree", barrier, sig.claude_local_md_path(levels["c"]))
    _wait_for_barrier(barrier, render)
    rebind = _start(_engine("set-topics", "--proj", levels["d"], "--slug", "feedback-py",
                            "--topics", "rust"))
    waited = _held_back(rebind)
    (barrier / "go").write_text("go\n", encoding="utf-8")
    render_rc, render_out = _finish(render)
    rebind_rc, rebind_out = _finish(rebind)
    assert (render_rc, rebind_rc) == (0, 0), (render_out, rebind_out)
    assert _broken_invariants(anchor) == []
    assert waited, "set-topics ran while the render held the placement lock"
    E.render_topics(anchor)
    assert _where(anchor, "feedback-py") == [levels["c"]] and _broken_invariants(anchor) == []


def test_a_render_during_a_clear_collapse_leaves_no_stuck_duplicates(tmp_path):
    """s4: set-topics --clear wrote the top line and dropped the placed ones, then a render
    (wanted lines computed from the still-bound body) put them back before the un-bind: an
    unplaced fact with several lines that no verb repairs. The collapse is held after its third
    level write (top added, a/py and b/py dropped), before the body is un-bound."""
    anchor, levels = _example(tmp_path)
    barrier = _barrier(tmp_path)
    collapse = _actor("set-topics", anchor, json.dumps({"feedback-py": None}), barrier, 3)
    _wait_for_barrier(barrier, collapse)
    render = _start(_engine("render-topics", "--proj", levels["d"], "--scope", "tree"))
    waited = _held_back(render)
    (barrier / "go").write_text("go\n", encoding="utf-8")
    collapse_rc, collapse_out = _finish(collapse)
    render_rc, render_out = _finish(render)
    assert (collapse_rc, render_rc) == (0, 0), (collapse_out, render_out)
    assert _broken_invariants(anchor) == []
    assert _where(anchor, "feedback-py") == [anchor]
    assert waited, "the render ran while set-topics held the placement lock"


def test_a_render_waits_for_a_held_placement_lock_then_renders_the_new_state(tmp_path):
    """The lock file is the lock: held here, as a set-topics holds it while it rebinds. The
    render must wait, and once it is let go it must place what the body says THEN."""
    anchor, levels = _example(tmp_path)
    lock = _lock_file(anchor)
    lock.write_text("peer\n", encoding="utf-8")
    render = _start(_engine("render-topics", "--proj", anchor, "--scope", "tree"))
    waited = _held_back(render)
    # the holder's write: the rebind a set-topics makes while it holds the lock
    body = us.body_path(anchor, "feedback-py").read_text(encoding="utf-8")
    us.put_body(anchor, "feedback-py", E._with_topics(body.rstrip("\n"), ("rust",)))
    lock.unlink()
    rc, out = _finish(render)
    assert rc == 0, out
    assert _where(anchor, "feedback-py") == [levels["c"]]
    assert waited, "the render did not wait for the placement lock"


def test_a_chain_render_takes_the_placement_lock_too(tmp_path):
    anchor, levels = _example(tmp_path)
    lock = _lock_file(anchor)
    lock.write_text("peer\n", encoding="utf-8")
    render = _start(_engine("render-topics", "--proj", levels["a/py"], "--scope", "chain"))
    waited = _held_back(render)
    lock.unlink()
    rc, out = _finish(render)
    assert rc == 0, out
    assert waited, "a chain render did not wait for the placement lock"


@pytest.mark.parametrize("rows", [{"feedback-py": ("rust",)}, {"feedback-py": None}],
                         ids=["rebind", "clear"])
def test_set_topics_waits_for_a_held_placement_lock(tmp_path, rows):
    anchor, levels = _example(tmp_path)
    batch = tmp_path / "rows.jsonl"
    batch.write_text("".join(json.dumps({"slug": slug, "topics": None if t is None else list(t)})
                             + "\n" for slug, t in rows.items()), encoding="utf-8")
    lock = _lock_file(anchor)
    lock.write_text("peer\n", encoding="utf-8")
    proc = _start(_engine("set-topics", "--proj", anchor, "--batch", batch))
    waited = _held_back(proc)
    lock.unlink()
    rc, out = _finish(proc)
    assert rc == 0, out
    assert waited, "set-topics did not wait for the placement lock"
    assert _broken_invariants(anchor) == []


# ---- the write verbs that rewrite a placed fact's lines -------------------------------------

def _placed_writes(anchor, levels):
    return {
        "add": _engine("add", "--proj", levels["a/py"], "--title", "T feedback-py", "--hook",
                       HOOK + " Changed.", "--slug", "feedback-py"),
        "retitle": _engine("retitle", "--level", levels["a/py"], "--slug", "feedback-py",
                           "--to-title", "A new title"),
        "rename": _engine("rename", "--level", levels["a/py"], "--slug", "feedback-py",
                          "--to-slug", "feedback-py-renamed"),
    }


@pytest.mark.parametrize("verb", ["add", "retitle", "rename"])
def test_a_write_to_a_placed_fact_waits_for_the_placement_lock(tmp_path, verb):
    anchor, levels = _example(tmp_path)
    lock = _lock_file(anchor)
    lock.write_text("peer\n", encoding="utf-8")
    proc = _start(_placed_writes(anchor, levels)[verb])
    waited = _held_back(proc)
    lock.unlink()
    rc, out = _finish(proc)
    assert rc == 0, out
    assert waited, "%s of a placed fact did not wait for the placement lock" % verb
    assert _broken_invariants(anchor) == []


@pytest.mark.parametrize("verb", ["retitle", "rename"])
def test_a_walk_over_every_level_waits_whatever_the_fact_in_a_tree_with_a_list(tmp_path, verb):
    """rename and retitle read and write level after level: a fact bound, placed and un-bound by
    peers between two of those steps would get a line put back, so they hold the lock for an
    unbound fact too."""
    anchor, levels = _example(tmp_path)
    _fact(levels["d"], "feedback-plain")
    cmd = {"retitle": _engine("retitle", "--level", levels["d"], "--slug", "feedback-plain",
                              "--to-title", "A new title"),
           "rename": _engine("rename", "--level", levels["d"], "--slug", "feedback-plain",
                             "--to-slug", "feedback-plain-renamed")}[verb]
    lock = _lock_file(anchor)
    lock.write_text("peer\n", encoding="utf-8")
    proc = _start(cmd)
    waited = _held_back(proc)
    lock.unlink()
    rc, out = _finish(proc)
    assert rc == 0, out
    assert waited, "%s did not wait for the placement lock" % verb


def test_an_add_of_an_unbound_fact_does_not_wait_for_the_placement_lock(tmp_path):
    """add writes one level under that level's lock, and is the per-turn capture path: for a fact
    no render manages it keeps its own pace."""
    anchor, levels = _example(tmp_path)
    _fact(levels["d"], "feedback-plain")
    lock = _lock_file(anchor)
    lock.write_text("peer\n", encoding="utf-8")
    try:
        done = subprocess.run(_engine("add", "--proj", levels["d"], "--title", "T plain", "--hook",
                                      HOOK, "--slug", "feedback-plain"),
                              capture_output=True, text=True, encoding="utf-8", timeout=FINISH_S)
    finally:
        lock.unlink()
    assert done.returncode == 0, done.stdout + done.stderr


# ---- the timeout, the stale lock, the dry runs ----------------------------------------------

def test_a_held_placement_lock_times_out_with_a_message_naming_the_route(tmp_path):
    anchor, _levels = _example(tmp_path)
    lock = _lock_file(anchor)
    lock.write_text("peer\n", encoding="utf-8")
    with pytest.raises(TimeoutError) as exc:
        E.render_topics(anchor, lock_timeout=0.3)
    text = str(exc.value)
    assert "render-topics" in text and str(lock) in text and "again" in text
    assert "reclaimed" in text
    with pytest.raises(TimeoutError) as exc:
        E.set_fact_topics(anchor, {"feedback-py": ("rust",)}, lock_timeout=0.3)
    assert "set-topics" in str(exc.value) and str(lock) in str(exc.value)
    assert lock.read_text(encoding="utf-8") == "peer\n"


def test_a_stale_placement_lock_is_reclaimed_by_the_level_locks_rule(tmp_path):
    anchor, levels = _example(tmp_path)
    lock = _lock_file(anchor)
    lock.write_text("crashed holder\n", encoding="utf-8")
    stamp = time.time() - 3600
    os.utime(lock, (stamp, stamp))
    E.set_fact_topics(anchor, {"feedback-py": ("rust",)}, lock_timeout=2.0)
    E.render_topics(anchor, lock_timeout=2.0)
    assert _where(anchor, "feedback-py") == [levels["c"]] and not lock.exists()


@pytest.mark.parametrize("call", ["render", "set-topics"])
def test_a_dry_run_neither_waits_for_nor_touches_the_placement_lock(tmp_path, call):
    anchor, _levels = _example(tmp_path)
    lock = _lock_file(anchor)
    lock.write_text("peer\n", encoding="utf-8")
    started = time.monotonic()
    if call == "render":
        E.render_topics(anchor, dry_run=True)
    else:
        E.set_fact_topics(anchor, {"feedback-py": ("rust",)}, dry_run=True)
    assert time.monotonic() - started < 2.0
    assert lock.read_text(encoding="utf-8") == "peer\n"


# ---- belt and braces: REMOVE never drops the last line of a fact ----------------------------

def test_remove_keeps_the_last_line_of_a_fact_and_reports_it(tmp_path, capsys):
    """A body rebound by a writer that ignores the lock (a hand edit, an older engine) after ADD
    placed it: REMOVE finds its lines misplaced while its new level has none. It keeps them and
    says so; the next render places it."""
    anchor, levels = _example(tmp_path)
    c_file = sig.claude_local_md_path(levels["c"])
    _fact(anchor, "feedback-rs", ("rust",))          # gives the render an ADD write at c

    def write(path, text):
        changed = us.write_if_changed(path, text)
        if os.path.abspath(str(path)) == os.path.abspath(str(c_file)):
            body = us.body_path(anchor, "feedback-py").read_text(encoding="utf-8")
            us.put_body(anchor, "feedback-py", E._with_topics(body.rstrip("\n"), ("rust",)))
        return changed

    rep = E.render_topics(anchor, write=write)
    assert _where(anchor, "feedback-py") == [levels["a/py"], levels["b/py"]]
    kept = {level: row.get("kept", 0) for level, row in rep["levels"].items()}
    assert kept[levels["a/py"]] == kept[levels["b/py"]] == 1
    assert rep["levels"][levels["a/py"]]["examples"]["kept"] == ["feedback-py"]
    E._print_render(rep, as_json=False)
    out = capsys.readouterr().out
    assert "kept 2 line(s)" in out and "feedback-py" in out and "render-topics" in out
    E.render_topics(anchor)
    assert _where(anchor, "feedback-py") == [levels["c"]] and _broken_invariants(anchor) == []
