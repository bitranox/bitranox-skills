"""Tests for git_state.py - parse `git status --porcelain=v2 --branch` output, walk for repos,
and the error / None-branch behaviour. ASCII only."""
import os

import git_state as G


def test_parse_clean_in_sync():
    out = (
        "# branch.oid abc123\n"
        "# branch.head master\n"
        "# branch.upstream origin/master\n"
        "# branch.ab +0 -0\n"
    )
    s = G.parse_branch_status(out)
    assert s["branch"] == "master"
    assert s["upstream"] == "origin/master"
    assert s["ahead"] == 0 and s["behind"] == 0
    assert s["dirty"] == 0 and s["staged"] == []
    assert s["in_sync"] is True


def test_parse_dirty_ahead_and_staged():
    out = (
        "# branch.head feature\n"
        "# branch.upstream origin/feature\n"
        "# branch.ab +2 -1\n"
        "1 M. N... 100644 100644 100644 aa bb tools/x.py\n"   # staged (index modified)
        "1 .M N... 100644 100644 100644 aa bb tools/y.py\n"   # worktree-modified, not staged
        "? untracked.txt\n"
    )
    s = G.parse_branch_status(out)
    assert s["branch"] == "feature"
    assert s["ahead"] == 2 and s["behind"] == 1
    assert s["in_sync"] is False
    assert s["dirty"] == 3            # 2 tracked changes + 1 untracked
    assert "tools/x.py" in s["staged"] and "tools/y.py" not in s["staged"]


def test_parse_detached_no_upstream():
    out = "# branch.head (detached)\n"
    s = G.parse_branch_status(out)
    assert s["branch"] == "(detached)"
    assert s["upstream"] is None
    assert s["in_sync"] is False      # no upstream -> not verifiably in sync


def test_git_state_on_non_repo_returns_error(tmp_path):
    s = G.git_state(str(tmp_path))     # a plain dir, not a git repo
    assert "error" in s
    assert s["repo"] == str(tmp_path)


def test_find_repos_discovers_git_dirs_and_skips_nested_git(tmp_path):
    (tmp_path / "a" / ".git").mkdir(parents=True)
    (tmp_path / "b" / "sub" / ".git").mkdir(parents=True)
    (tmp_path / "b" / "sub" / ".git" / "modules").mkdir()   # must NOT be walked into
    (tmp_path / "plain").mkdir()                             # no .git -> not a repo
    found = G.find_repos(str(tmp_path))
    assert os.path.join(str(tmp_path), "a") in found
    assert os.path.join(str(tmp_path), "b", "sub") in found
    assert not any("plain" in p for p in found)
    assert not any(".git" in p for p in found)              # never reports a .git internal dir


def test_main_error_path_exits_nonzero_and_does_not_crash(tmp_path, capsys):
    rc = G.main([str(tmp_path)])       # not a git repo -> error path -> rc 1, no crash
    assert rc == 1
    assert "ERROR" in capsys.readouterr().out


def test_main_survives_none_branch(monkeypatch, capsys):
    # regression: a repo whose parsed branch is None must not crash the f-string formatting
    monkeypatch.setattr(G, "git_state", lambda repo: {
        "repo": repo, "branch": None, "upstream": None, "ahead": 0, "behind": 0,
        "dirty": 0, "staged": [], "in_sync": False,
    })
    rc = G.main(["somerepo"])
    assert rc == 1                     # no-upstream -> out of sync
    assert "None" in capsys.readouterr().out   # printed, did not raise
