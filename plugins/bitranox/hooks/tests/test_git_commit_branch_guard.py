"""Tests for git-commit-branch-guard.py (warn-only PreToolUse commit-state guard). ASCII.

The hyphenated module is loaded + aliased as `git_commit_branch_guard` by conftest.py.
"""
import io
import json
import sys

import git_commit_branch_guard as G


def test_is_git_commit():
    assert G._is_git_commit('git commit -m "x"')
    assert G._is_git_commit("git -C /repo commit -m x")
    assert G._is_git_commit("ls && git commit -F -")
    assert not G._is_git_commit("git status")
    assert not G._is_git_commit("git log --oneline -1")
    assert not G._is_git_commit("echo commit")


def _fake_git(returns):
    def _f(cwd, *a):
        if a[0] == "rev-parse" and "--show-toplevel" in a:
            return returns.get("toplevel")
        if a[0] == "rev-list":
            return returns.get("ahead_behind")
        if a[0] == "symbolic-ref" and "refs/remotes/origin/HEAD" in a:
            return returns.get("origin_head")
        if a[0] == "symbolic-ref":
            return returns.get("branch")
        return None
    return _f


def _run(monkeypatch, capsys, command, returns, strict_repos=None):
    monkeypatch.setattr(G, "_git", _fake_git(returns))
    if strict_repos is None:
        monkeypatch.delenv("GIT_GUARD_STRICT_REPOS", raising=False)
    else:
        monkeypatch.setenv("GIT_GUARD_STRICT_REPOS", strict_repos)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": command}, "cwd": "/x"})))
    rc = G.main()
    return rc, capsys.readouterr().err


# toplevel + on a feature branch + default 'main'
BASE = {"toplevel": "/p/myrepo", "branch": "feature", "origin_head": "origin/main"}


def test_silent_when_ahead_only(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind="2\t0"))
    assert rc == 0 and err == ""


def test_silent_when_no_upstream(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind=None))
    assert rc == 0 and err == ""


def test_warns_when_behind_any_repo(monkeypatch, capsys):
    # the always-on safe check: fires in any repo, no strict config needed
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind="0\t3"))
    assert rc == 0 and "3 commit(s) behind/diverged" in err


def test_branch_check_off_by_default(monkeypatch, capsys):
    # on a feature branch, up to date: silent unless the repo is in GIT_GUARD_STRICT_REPOS
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind="0\t0"))
    assert rc == 0 and err == ""


def test_branch_check_warns_for_strict_repo(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind="0\t0"),
                   strict_repos="other,myrepo")
    assert rc == 0 and "not the default 'main'" in err and "feature" in err


def test_branch_check_detached_for_strict_repo(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, branch=None, ahead_behind="0\t0"),
                   strict_repos="myrepo")
    assert rc == 0 and "DETACHED" in err


def test_strict_repo_not_matched_is_silent(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind="0\t0"),
                   strict_repos="some-other-repo")
    assert rc == 0 and err == ""


def test_silent_not_a_git_repo(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, toplevel=None, ahead_behind="0\t9"))
    assert rc == 0 and err == ""


def test_silent_non_commit(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git status", dict(BASE, ahead_behind="0\t9"))
    assert rc == 0 and err == ""


def test_bad_stdin_safe(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert G.main() == 0
