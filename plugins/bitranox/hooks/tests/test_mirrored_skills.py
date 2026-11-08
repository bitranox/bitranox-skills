"""Tests for mirrored_skills: the shared twin table and the twin-to-marketplace-name lookup."""
import os
import subprocess

import pytest

import mirrored_skills as MS

TABLE = {"coding-python-gitignore": "libs/igittigitt/skills/python-gitignore"}


def _git(cwd, *args):
    subprocess.run(["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
                   cwd=str(cwd), check=True, capture_output=True)


@pytest.fixture
def bare_git_env(monkeypatch):
    """No inherited GIT_ variable may point git at another repository (a worktree push sets one)."""
    for key in list(os.environ):
        if key.startswith("GIT_") and not key.startswith("GIT_CONFIG_"):
            monkeypatch.delenv(key)


def test_a_twin_path_maps_to_its_marketplace_name(tmp_path):
    twin = tmp_path / "public" / "libs" / "igittigitt" / "skills" / "python-gitignore"
    assert MS.marketplace_name(twin, TABLE) == "coding-python-gitignore"


def test_the_same_skill_name_under_another_repo_is_no_twin(tmp_path):
    other = tmp_path / "public" / "libs" / "other" / "skills" / "python-gitignore"
    other.mkdir(parents=True)
    assert MS.marketplace_name(other, TABLE) is None


def test_a_suffix_match_respects_path_boundaries(tmp_path):
    """`xlibs/igittigitt/...` ends with the right characters but not the right components."""
    near = tmp_path / "xlibs" / "igittigitt" / "skills" / "python-gitignore"
    assert MS.marketplace_name(near, TABLE) is None


def test_an_ordinary_skill_is_no_twin_and_runs_no_git(tmp_path, monkeypatch):
    def no_git(*_a, **_k):
        raise AssertionError("git must not run for a dir whose name is no twin's")
    monkeypatch.setattr(MS.subprocess, "run", no_git)
    assert MS.marketplace_name(tmp_path / "skills" / "devops-bmk-other", TABLE) is None


@pytest.mark.usefixtures("bare_git_env")
def test_a_twin_in_a_linked_worktree_maps_through_its_main_checkout(tmp_path):
    repo = tmp_path / "public" / "libs" / "igittigitt"
    (repo / "skills" / "python-gitignore").mkdir(parents=True)
    (repo / "skills" / "python-gitignore" / "SKILL.md").write_text("x\n", encoding="utf-8")
    _git(repo, "init", "-q", ".")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    worktree = tmp_path / "scratch" / "wt-igittigitt"
    _git(repo, "worktree", "add", "-q", str(worktree))
    assert MS.marketplace_name(worktree / "skills" / "python-gitignore", TABLE) \
        == "coding-python-gitignore"
    # Control: the same layout outside any repo the table names stays unmatched.
    loose = tmp_path / "scratch" / "loose" / "skills" / "python-gitignore"
    loose.mkdir(parents=True)
    assert MS.marketplace_name(loose, TABLE) is None


def test_the_shared_table_is_the_one_repo_gate_reads():
    import repo_gate  # noqa: PLC0415 - the conftest registers the hyphenated hook under this alias
    assert repo_gate.MIRRORED_SKILLS is MS.MIRRORED_SKILLS


def test_every_twin_skill_dir_name_differs_from_every_marketplace_name():
    """A twin named like a marketplace skill would map a marketplace path to itself; only
    devops-bmk shares its name, and its marketplace path cannot end with the twin's."""
    for name, rel in MS.MIRRORED_SKILLS.items():
        market = "/x/plugins/bitranox/skills/%s" % name
        assert MS.marketplace_name(market) is None, (name, rel)
