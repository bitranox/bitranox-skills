"""compare_performance end to end: a real git repository, a real pytest suite, the real script.

Each fixture repo has a branch ``main`` with two commits. ``version.txt`` holds the commit's
name, and every test in the fixture suite appends "<kind>:<version>" to a log OUTSIDE the
repo (PERF_LOG), so a test can see which code each run executed without leaving untracked
files behind in the repository under test.
"""
import os
import signal
import subprocess
import sys
import time

import pytest

SCRIPT = "compare_performance.py"

LOGGING_TEST = (
    "import os, pathlib\n\n\n"
    "def test_{kind}():\n"
    "    version = pathlib.Path('version.txt').read_text().strip()\n"
    "    with open(os.environ['PERF_LOG'], 'a') as log:\n"
    "        log.write('{kind}:' + version + '\\n')\n"
)


@pytest.fixture
def git_env(tmp_path, clean_env):
    home = tmp_path / "home"
    home.mkdir()
    return clean_env(HOME=str(home), PERF_LOG=str(tmp_path / "seen.log"),
                     GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                     GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
                     GIT_CONFIG_NOSYSTEM="1")


def _git_in(root, env):
    def git(*args, check=True):
        r = subprocess.run(["git", *args], cwd=str(root), env=env, capture_output=True,
                           text=True, check=False)
        if check and r.returncode != 0:
            raise AssertionError(f"git {args}: {r.stderr}")
        return r
    return git


@pytest.fixture
def make_repo(tmp_path, git_env):
    """Build a two-commit repo on branch main (plus *extra* files in both commits).

    Returns (path, env, git)."""
    def build(extra=None, name="repo", versions=("c1", "c2")):
        root = tmp_path / name
        (root / "tests").mkdir(parents=True)
        git = _git_in(root, git_env)
        git("init", "-q", "-b", "main")
        files = {"tests/test_tracked.py": LOGGING_TEST.format(kind="tracked"), "mod.py": "x = 1\n"}
        files.update(extra or {})
        for rel, text in files.items():
            (root / rel).write_text(text, encoding="utf-8")
        for version in versions:
            (root / "version.txt").write_text(version + "\n", encoding="utf-8")
            git("add", "-A")
            git("commit", "-q", "-m", version)
        return root, git_env, git
    return build


@pytest.fixture
def repo(make_repo):
    return make_repo()


def _seen(root):
    log = root.parent / "seen.log"
    return log.read_text(encoding="utf-8").split() if log.exists() else []


def _stash_list(git):
    return git("stash", "list", "--format=%gs").stdout.split("\n")[:-1]


def test_restores_branch_changes_and_untracked_files(repo, run_script):
    root, env, git = repo
    (root / "mod.py").write_text("x = 2\n", encoding="utf-8")                 # tracked edit
    (root / "tests" / "test_untracked.py").write_text(LOGGING_TEST.format(kind="untracked"),
                                                      encoding="utf-8")        # new, untracked
    r = run_script(SCRIPT, cwd=str(root), env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert b"Improvement:" in r.stdout
    assert git("symbolic-ref", "HEAD").stdout.strip() == "refs/heads/main"
    assert (root / "mod.py").read_text(encoding="utf-8") == "x = 2\n"
    assert (root / "tests" / "test_untracked.py").exists()
    assert _stash_list(git) == []
    # the untracked test did not exist in the BEFORE commit, so it must not run there
    assert sorted(_seen(root)) == ["tracked:c1", "tracked:c2", "untracked:c2"]


def test_a_second_run_restores_cleanly_too(repo, run_script):
    """No .pytest_cache or __pycache__ from one run may block the next stash pop."""
    root, env, git = repo
    (root / "mod.py").write_text("x = 2\n", encoding="utf-8")
    env = {k: v for k, v in env.items() if k != "PYTHONDONTWRITEBYTECODE"}
    for _ in range(2):
        r = run_script(SCRIPT, cwd=str(root), env=env)
        assert r.returncode == 0, r.stdout + r.stderr
    assert _stash_list(git) == []
    assert (root / "mod.py").read_text(encoding="utf-8") == "x = 2\n"


def test_clean_tree_leaves_an_existing_user_stash_alone_in_any_locale(repo, run_script):
    root, env, git = repo
    (root / "other.py").write_text("saved = True\n", encoding="utf-8")
    git("add", "other.py")
    git("stash", "push", "-m", "USER-SAVED-WORK")
    env = dict(env, LC_ALL="de_DE.UTF-8", LANGUAGE="de", LANG="de_DE.UTF-8")
    r = run_script(SCRIPT, cwd=str(root), env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _stash_list(git) == ["On main: USER-SAVED-WORK"]
    assert git("status", "--porcelain").stdout == ""


def test_no_commits_exits_2(tmp_path, git_env, run_script):
    empty = tmp_path / "empty"
    empty.mkdir()
    _git_in(empty, git_env)("init", "-q")
    r = run_script(SCRIPT, cwd=str(empty), env=git_env)
    assert r.returncode == 2
    assert b"no commits" in r.stderr
    assert b"Improvement" not in r.stdout


def test_not_a_repository_exits_2(tmp_path, git_env, run_script):
    env = dict(git_env, GIT_CEILING_DIRECTORIES=str(tmp_path.parent))
    r = run_script(SCRIPT, cwd=str(tmp_path), env=env)
    assert r.returncode == 2 and b"git repository" in r.stderr.lower()


def test_single_commit_exits_2_and_touches_nothing(make_repo, run_script):
    root, env, git = make_repo(versions=("only",))
    (root / "mod.py").write_text("x = 2\n", encoding="utf-8")
    r = run_script(SCRIPT, cwd=str(root), env=env)
    assert r.returncode == 2
    assert b"no parent commit" in r.stderr
    assert b"Improvement" not in r.stdout
    assert _stash_list(git) == []
    assert (root / "mod.py").read_text(encoding="utf-8") == "x = 2\n"


def test_a_failing_suite_exits_2_without_an_improvement(repo, run_script):
    root, env, git = repo
    (root / "tests" / "test_tracked.py").write_text("import missing_module_xyz\n", encoding="utf-8")
    r = run_script(SCRIPT, cwd=str(root), env=env)
    assert r.returncode == 2, r.stdout + r.stderr
    assert b"test suite failed" in r.stdout
    assert b"Improvement" not in r.stdout
    assert git("symbolic-ref", "HEAD").stdout.strip() == "refs/heads/main"
    assert "missing_module_xyz" in (root / "tests" / "test_tracked.py").read_text(encoding="utf-8")


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal delivery; Ctrl-C on Windows is a console event")
def test_ctrl_c_during_before_run_restores_branch_and_changes(tmp_path, make_repo):
    started = tmp_path / "before_started"
    # c1's suite signals that it is running, then blocks until interrupted
    slow_test = ("import pathlib, time\n\n\ndef test_slow():\n"
                 "    if pathlib.Path('version.txt').read_text().strip() == 'c1':\n"
                 f"        pathlib.Path({str(started)!r}).write_text('x')\n"
                 "        time.sleep(60)\n")
    root, env, git = make_repo({"tests/test_slow.py": slow_test})
    (root / "mod.py").write_text("x = 2\n", encoding="utf-8")

    script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), SCRIPT)
    proc = subprocess.Popen([sys.executable, script], cwd=str(root), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 60
        while not started.exists():
            assert proc.poll() is None, proc.communicate()
            assert time.monotonic() < deadline, "the BEFORE run never started"
            time.sleep(0.1)
        proc.send_signal(signal.SIGINT)
        proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode != 0
    assert git("symbolic-ref", "HEAD").stdout.strip() == "refs/heads/main"
    assert (root / "mod.py").read_text(encoding="utf-8") == "x = 2\n"
    assert _stash_list(git) == []
