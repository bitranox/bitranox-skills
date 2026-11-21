"""No git subprocess runs while a level lock is held, for the callers that set a level up under
their own hold of its lock: `add` (upsert_entry), `heal` (_heal_level) and `set-scope`; nor while
an `add` of a fact bound to a topic holds the tree's placement lock. A level outside any git
repo asks git once per process, not on every call.

ensure_level asks git whether the level's private files are ignored. Its unlocked path asks
after releasing the lock; the callers that already held the lock asked under it, so the first
add, heal or set-scope of every process spent its git round trips (about 250 ms on Windows)
holding the lock every other writer of that level waits on.

The observer is a `git` stand-in first on PATH, the one real edge the engine reaches git
through: on every call it records whether the level's lock file exists at that moment, then runs
the real git. Each verb runs in a fresh process, so its git check is the process's first (the
answer is cached per process afterwards). All content ASCII.
"""

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import memory_engine as E
import pytest
import self_improve_signals as sig
import topic_store
import uuid_store as us

pytestmark = pytest.mark.skipif(os.name == "nt",
                                reason="the recording git stand-in is a POSIX shell script")

ENGINE = Path(E.__file__).resolve()
HOOK = "When a level is set up under its own lock, ask git before taking the lock."


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    return h


@pytest.fixture
def tree(tmp_path):
    """A git repo that is a memory tree, its top already a level (set up with the real git)."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (root / us.STORE_DIRNAME).mkdir()
    assert E.main(["set-scope", "--proj", str(root), "--scope", "WHAT: the top"]) == 0
    return root


def _recording_git(tmp_path):
    """A git stand-in that logs `held` or `free` (the lock file named by $WATCHED_LOCK exists or
    not) and its arguments, one line per call, then runs the real git. Returns its dir."""
    shim = tmp_path / "bin" / "git"
    if shim.exists():
        return shim.parent
    real = shutil.which("git")
    assert real is not None
    shim.parent.mkdir()
    shim.write_text('#!/bin/sh\n'
                    'if [ -e "$WATCHED_LOCK" ]; then s=held; else s=free; fi\n'
                    'echo "$s $*" >> "$GIT_CALL_LOG"\n'
                    f'exec {shlex.quote(real)} "$@"\n', encoding="utf-8")
    shim.chmod(0o755)
    return shim.parent


def _run_watched(tmp_path, level, args, watched=None, program=None):
    """Run the engine CLI (or the Python source `program`, with argv `args`) with the recording
    git first on PATH, watching `watched` (default: `level`'s lock file); return the logged
    calls."""
    log = tmp_path / ("git-calls-%d.log" % len(list(tmp_path.glob("git-calls-*.log"))))
    env = dict(os.environ)
    env["PATH"] = str(_recording_git(tmp_path)) + os.pathsep + env.get("PATH", "")
    env["WATCHED_LOCK"] = str(watched or str(sig.claude_local_md_path(level)) + ".lock")
    env["GIT_CALL_LOG"] = str(log)
    cmd = [sys.executable, "-c", program] if program else [sys.executable, str(ENGINE)]
    done = subprocess.run([*cmd, *map(str, args)], env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def _new_level(tree, name):
    level = tree / name
    level.mkdir()
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    return level


def _assert_git_asked_only_outside_the_lock(calls):
    assert any("check-ignore" in c for c in calls), calls     # the check did run (liveness)
    assert [c for c in calls if c.startswith("held ")] == [], calls


def test_add_asks_git_before_it_takes_the_level_lock(tmp_path, tree):
    level = _new_level(tree, "sub")
    calls = _run_watched(tmp_path, level, ["add", "--proj", level, "--title", "T git-first",
                                           "--hook", HOOK, "--slug", "feedback-git-first",
                                           "--body", "body"])
    _assert_git_asked_only_outside_the_lock(calls)
    assert "feedback-git-first" in sig.claude_local_md_path(level).read_text(encoding="utf-8")


def test_set_scope_asks_git_before_it_takes_the_level_lock(tmp_path, tree):
    level = _new_level(tree, "sub")
    calls = _run_watched(tmp_path, level, ["set-scope", "--proj", level, "--scope",
                                           "WHAT: a level set up by set-scope"])
    _assert_git_asked_only_outside_the_lock(calls)
    assert "set up by set-scope" in sig.claude_local_md_path(level).read_text(encoding="utf-8")


def test_heal_asks_git_before_it_takes_the_level_lock(tmp_path, tree):
    level = _new_level(tree, "sub")          # a CLAUDE.md rung with no CLAUDE.local.md: healed
    calls = _run_watched(tmp_path, level, ["heal", "--proj", level])
    _assert_git_asked_only_outside_the_lock(calls)
    assert sig.claude_local_md_path(level).is_file()


def test_the_recording_git_sees_a_held_lock(tmp_path, tree):
    """Control: the observer can answer `held`. A peer's lock file present for the whole call is
    seen by every git call the verb makes (the add itself would wait on it, so the control runs
    a read-only git command through the same stand-in)."""
    level = _new_level(tree, "sub")
    lock = Path(str(sig.claude_local_md_path(level)) + ".lock")
    lock.write_text("peer\n", encoding="utf-8")
    log = tmp_path / "control.log"
    env = dict(os.environ, PATH=str(_recording_git(tmp_path)) + os.pathsep
               + os.environ.get("PATH", ""), WATCHED_LOCK=str(lock), GIT_CALL_LOG=str(log))
    subprocess.run(["git", "-C", str(level), "check-ignore", "-q", "--no-index", "x"], env=env,
                   check=False)
    assert log.read_text(encoding="utf-8").splitlines()[0].startswith("held ")


def test_an_add_of_a_bound_fact_asks_git_before_it_takes_the_placement_lock(tmp_path, tree):
    """An add of a fact bound to a topic holds the tree's placement lock (every render and
    set-topics waits on it) from its placed checks to its write: git is asked before that too."""
    topic_store.save_list(tree, {"python": "Python code", "rust": "Rust code"}, "jev")
    py = _new_level(tree, "py")
    assert E.main(["set-scope", "--proj", str(py), "--scope", "WHAT: py\nSTACK: python"]) == 0
    E.set_level_topics(str(py), ("python",))
    E.add_or_update_entry(str(tree), title="T bound", hook=HOOK, body="body", slug="feedback-bound")
    E.set_fact_topics(str(tree), {"feedback-bound": ("python",)})
    E.render_topics(str(tree))
    assert "feedback-bound" in sig.claude_local_md_path(py).read_text(encoding="utf-8")
    calls = _run_watched(tmp_path, py, ["add", "--proj", py, "--title", "T bound", "--hook",
                                        HOOK + " Changed.", "--slug", "feedback-bound"],
                         watched=E.placement_lock_path(tree))
    _assert_git_asked_only_outside_the_lock(calls)
    assert "Changed." in sig.claude_local_md_path(py).read_text(encoding="utf-8")


_ENSURE_TWICE = """
import sys
sys.path.insert(0, sys.argv[1])
import memory_engine as E
E.ensure_level(sys.argv[2], scope_default="WHAT: a level outside git")
E.ensure_level(sys.argv[2], scope_default="WHAT: a level outside git")
"""


def test_a_level_outside_git_asks_git_once_per_process(tmp_path):
    """Outside a git repo there is nothing to ignore. The answer was not remembered, so every
    add at such a level spawned `git rev-parse` again (about 50 ms each on Windows)."""
    root = tmp_path / "plain"
    root.mkdir()
    (root / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (root / us.STORE_DIRNAME).mkdir()
    probe = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                           capture_output=True, check=False)
    if probe.returncode == 0:
        pytest.skip("the test dir sits inside a git repo")
    calls = _run_watched(tmp_path, root, [Path(E.__file__).resolve().parent, root],
                         program=_ENSURE_TWICE)
    asked = [c for c in calls if "rev-parse --show-toplevel" in c]
    # the level is its own anchor: the first ensure_level asks once for both of its patterns,
    # the second asks nothing
    assert len(asked) == 1, calls
