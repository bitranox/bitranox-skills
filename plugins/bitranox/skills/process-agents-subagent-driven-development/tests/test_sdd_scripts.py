"""Behavioral tests for the SDD helper scripts (task_brief, review_package, sdd_workspace).

Fixtures are tiny real artifacts: a plan file with fenced decoys for task_brief, a throwaway
git repo for review_package/sdd_workspace. ASCII only.
"""
import subprocess
import sys
from pathlib import Path

import pytest

import review_package as RP
import sdd_workspace as WS
import task_brief as TB

PLAN = """# My plan

Intro prose.

## Task 1: warm up

body one

## Task 2: the real work

body two, line 1

```
# Task 3 inside a fence must not end task 2
fence content
```

body two, line 2

## Task 20: decoy for boundary check

body twenty

## Task 3: wind down

body three
"""


@pytest.fixture
def repo(tmp_path):
    """A throwaway git repo with two commits on top of a base commit."""
    r = tmp_path / "repo"
    r.mkdir()
    env_args = ["-c", "user.name=t", "-c", "user.email=t@t"]

    def git(*args):
        return subprocess.run(["git", *env_args, *args], cwd=r, capture_output=True,
                              text=True, check=True).stdout.strip()

    git("init", "-q")
    (r / "a.txt").write_text("base\n", encoding="utf-8")
    git("add", "a.txt")
    git("commit", "-qm", "base commit")
    base = git("rev-parse", "HEAD")
    (r / "a.txt").write_text("change one\n", encoding="utf-8")
    git("add", "a.txt")
    git("commit", "-qm", "first change")
    (r / "b.txt").write_text("new file\n", encoding="utf-8")
    git("add", "b.txt")
    git("commit", "-qm", "second change")
    head = git("rev-parse", "HEAD")
    return r, base, head


# ---------------------------------------------------------------- task_brief

def test_extract_task_between_headings():
    text = TB.extract_task(PLAN, 2)
    assert "## Task 2: the real work" in text
    assert "body two, line 1" in text and "body two, line 2" in text
    assert "body twenty" not in text and "body three" not in text and "body one" not in text


def test_extract_task_boundary_regex_no_prefix_match():
    # n=2 must not swallow Task 20; n=20 must find its own section
    assert "body twenty" not in TB.extract_task(PLAN, 2)
    t20 = TB.extract_task(PLAN, 20)
    assert "body twenty" in t20 and "body two, line 1" not in t20


def test_extract_task_ignores_headings_inside_fences():
    t2 = TB.extract_task(PLAN, 2)
    assert "# Task 3 inside a fence must not end task 2" in t2
    t3 = TB.extract_task(PLAN, 3)
    assert "wind down" in t3 and "fence content" not in t3


def test_extract_task_heading_levels_and_tabs():
    plan = "#\tTask 7\nseven\n### Task 8\neight\n"
    assert "seven" in TB.extract_task(plan, 7)
    assert "eight" in TB.extract_task(plan, 8)


def test_task_brief_main_writes_outfile(tmp_path, capsys):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN, encoding="utf-8")
    out = tmp_path / "brief.md"
    assert TB.main([str(plan), "2", str(out)]) == 0
    assert "body two, line 1" in out.read_text(encoding="utf-8")
    assert str(out) in capsys.readouterr().out


def test_task_brief_main_task_not_found_exit_3(tmp_path, capsys):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN, encoding="utf-8")
    out = tmp_path / "brief.md"
    assert TB.main([str(plan), "99", str(out)]) == 3
    assert "not found" in capsys.readouterr().err
    assert not out.exists() or out.read_text(encoding="utf-8") == ""


def test_task_brief_main_bad_args_exit_2(capsys):
    assert TB.main(["only-one-arg"]) == 2
    assert "usage:" in capsys.readouterr().err


def test_task_brief_main_missing_plan_exit_2(tmp_path, capsys):
    assert TB.main([str(tmp_path / "nope.md"), "1"]) == 2
    assert "no such plan file" in capsys.readouterr().err


def test_task_brief_default_outfile_in_workspace(repo, capsys, monkeypatch):
    r, _base, _head = repo
    monkeypatch.chdir(r)
    plan = r / "plan.md"
    plan.write_text(PLAN, encoding="utf-8")
    assert TB.main([str(plan), "2"]) == 0
    expected = r / ".bitranox" / "sdd" / "task-2-brief.md"
    assert expected.is_file()
    assert "body two, line 1" in expected.read_text(encoding="utf-8")


# ------------------------------------------------------------ review_package

def test_review_package_contains_sections_and_all_commits(repo, tmp_path, capsys, monkeypatch):
    r, base, head = repo
    monkeypatch.chdir(r)
    out = tmp_path / "review.diff"
    assert RP.main([base, head, str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "## Commits" in text and "## Files changed" in text and "## Diff" in text
    assert "first change" in text and "second change" in text     # multi-commit preserved
    assert "2 commit(s)" in capsys.readouterr().out


def test_review_package_bad_refs_exit_2(repo, capsys, monkeypatch):
    r, base, _head = repo
    monkeypatch.chdir(r)
    assert RP.main(["deadbeef" * 5, "HEAD"]) == 2
    assert "bad BASE" in capsys.readouterr().err
    assert RP.main([base, "nope-ref"]) == 2
    assert "bad HEAD" in capsys.readouterr().err


def test_review_package_bad_args_exit_2(capsys):
    assert RP.main(["one"]) == 2
    assert "usage:" in capsys.readouterr().err


def test_review_package_default_outfile_named_by_range(repo, capsys, monkeypatch):
    r, base, head = repo
    monkeypatch.chdir(r)
    assert RP.main([base, head]) == 0
    ws = r / ".bitranox" / "sdd"
    matches = list(ws.glob("review-*..*.diff"))
    assert len(matches) == 1
    assert base[:7] in matches[0].name and head[:7] in matches[0].name


# ------------------------------------------------------------- sdd_workspace

def test_workspace_created_self_ignoring_and_idempotent(repo, monkeypatch):
    r, _base, _head = repo
    monkeypatch.chdir(r)
    d1 = WS.workspace_dir()
    assert d1 == (r / ".bitranox" / "sdd").resolve()
    assert (d1 / ".gitignore").read_text(encoding="utf-8") == "*\n"
    d2 = WS.workspace_dir()                     # second run: same result, no error
    assert d2 == d1


def test_workspace_resolves_root_from_subdir(repo, monkeypatch):
    r, _base, _head = repo
    sub = r / "deep" / "nested"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    assert WS.workspace_dir() == (r / ".bitranox" / "sdd").resolve()


def test_workspace_main_outside_repo_exit_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert WS.main([]) == 2
    assert capsys.readouterr().err != ""
