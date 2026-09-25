"""review_package.py against real throwaway git repos: failures, line endings, argument order.

Every repo here is built with plain git in tmp_path. Repo-scoping GIT_ variables are cleared so a
run from a linked worktree or a git hook cannot point these fixtures at the repository under
test.
"""
import os
import subprocess
import sys

import pytest

import review_package as RP

_GIT_ID = ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false"]


@pytest.fixture(autouse=True)
def _hermetic_git(monkeypatch):
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                 "GIT_COMMON_DIR"):
        monkeypatch.delenv(name, raising=False)


def _git(repo, *args):
    return subprocess.run(["git", *_GIT_ID, *args], cwd=repo, capture_output=True,
                          check=True).stdout.decode("utf-8").strip()


def _commit(repo, name, data, message):
    (repo / name).write_bytes(data)
    _git(repo, "add", name)
    _git(repo, "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    base = _commit(r, "a.txt", b"a\nb\n", "base")
    monkeypatch.chdir(r)
    return r, base


def _package(tmp_path, base, head):
    out = tmp_path / "pkg.diff"
    rc = RP.main([base, head, str(out)])
    return rc, (out.read_bytes() if out.exists() else b"")


# ---- git failures inside build() ----------------------------------------------------------------
def test_a_git_failure_while_building_is_exit_2_not_an_empty_package(repo, tmp_path, capsys):
    """A missing blob makes `git diff` fail; the package used to come out empty with exit 0."""
    r, base = repo
    head = _commit(r, "a.txt", b"a\nc\n", "change")
    blob = _git(r, "rev-parse", "HEAD:a.txt")
    (r / ".git" / "objects" / blob[:2] / blob[2:]).unlink()
    rc, data = _package(tmp_path, base, head)
    assert rc == 2
    assert data == b""
    assert "git" in capsys.readouterr().err


def test_an_intact_repo_still_packages(repo, tmp_path):
    r, base = repo
    head = _commit(r, "a.txt", b"a\nc\n", "change")
    rc, data = _package(tmp_path, base, head)
    assert rc == 0
    assert b"-b\n" in data and b"+c\n" in data


# ---- line endings survive -----------------------------------------------------------------------
def test_a_line_ending_change_is_visible_in_the_package(repo, tmp_path):
    """Text-mode capture turned +a\\r\\n into +a\\n, so LF->CRLF showed identical -/+ lines."""
    r, base = repo
    head = _commit(r, "a.txt", b"a\r\nb\r\n", "crlf")
    rc, data = _package(tmp_path, base, head)
    assert rc == 0
    assert b"+a\r\n" in data and b"+b\r\n" in data


def test_a_lone_carriage_return_is_not_turned_into_a_line_break(repo, tmp_path):
    r, base = repo
    head = _commit(r, "a.txt", b"a\nx\ry\n", "lone cr")
    _rc, data = _package(tmp_path, base, head)
    assert b"+x\ry\n" in data


# ---- BASE must be an ancestor of HEAD -----------------------------------------------------------
def test_swapped_base_and_head_are_refused(repo, tmp_path, capsys):
    """Swapped, the package read "0 commits" and a reversed diff, exit 0."""
    r, base = repo
    head = _commit(r, "a.txt", b"a\nchanged\n", "change")
    rc, data = _package(tmp_path, head, base)
    assert rc == 2
    assert data == b""
    assert "ancestor" in capsys.readouterr().err


def test_a_base_rewritten_away_is_refused(repo, tmp_path):
    """A BASE amended after it was recorded is no longer on HEAD's history."""
    r, base = repo
    _git(r, "commit", "-q", "--amend", "-m", "base, reworded")
    head = _commit(r, "a.txt", b"a\nchanged\n", "change")
    rc, _data = _package(tmp_path, base, head)
    assert rc == 2


def test_base_equal_to_head_is_an_empty_but_valid_range(repo, tmp_path, capsys):
    _r, base = repo
    rc, _data = _package(tmp_path, base, base)
    assert rc == 0
    assert "0 commit(s)" in capsys.readouterr().out


# ---- arguments ----------------------------------------------------------------------------------
def test_more_than_three_arguments_is_a_usage_error(repo, capsys):
    _r, base = repo
    assert RP.main([base, base, "out.diff", "extra"]) == 2
    assert "usage:" in capsys.readouterr().err


# ---- a cp1252 console ---------------------------------------------------------------------------
def test_a_non_cp1252_output_path_does_not_crash_the_report(repo, tmp_path):
    r, base = repo
    head = _commit(r, "a.txt", b"a\nc\n", "change")
    out = tmp_path / ("pkg-" + chr(0x0141) + ".diff")
    script = os.path.join(os.path.dirname(RP.__file__), "review_package.py")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "PYTHONUTF8"}
    env["PYTHONIOENCODING"] = "cp1252"
    proc = subprocess.run([sys.executable, script, base, head, str(out)], cwd=r, env=env,
                          capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert out.exists()
