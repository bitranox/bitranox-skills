"""Behavioral tests for the SDD helper scripts (task_brief, review_package, sdd_workspace).

Fixtures are tiny real artifacts: a plan file with fenced decoys for task_brief, a throwaway
git repo for review_package/sdd_workspace. ASCII only.
"""
import os
import subprocess
import sys

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
    written = list((r / ".bitranox" / "sdd").glob("task-2-*-brief.md"))
    assert len(written) == 1
    assert "body two, line 1" in written[0].read_text(encoding="utf-8")


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
    assert "git working tree" in capsys.readouterr().err


def _git_init(path):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    return path


@pytest.mark.skipif(sys.platform == "win32", reason="Windows forbids a trailing space in a name")
def test_workspace_keeps_a_trailing_space_in_the_repo_root(tmp_path, monkeypatch):
    repo = _git_init(tmp_path / "proj ")
    monkeypatch.chdir(repo)
    assert WS.workspace_dir() == (repo / ".bitranox" / "sdd").resolve()
    assert not (tmp_path / "proj").exists(), "a sibling outside the repo was created"


def test_workspace_handles_a_non_ascii_repo_root(tmp_path, monkeypatch):
    """git prints the path as UTF-8; decoding it with a cp1252 locale lands in a sibling dir."""
    repo = _git_init(tmp_path / "proj-ä")
    monkeypatch.chdir(repo)
    assert WS.workspace_dir() == (repo / ".bitranox" / "sdd").resolve()


def test_workspace_main_rejects_arguments_and_creates_nothing(tmp_path, monkeypatch, capsys):
    repo = _git_init(tmp_path / "fresh")
    monkeypatch.chdir(repo)
    for argv in (["--help"], ["stray"]):
        assert WS.main(argv) == 2
    assert "usage" in capsys.readouterr().err.lower()
    assert not (repo / ".bitranox").exists()


def test_workspace_main_prints_the_workspace_on_success(tmp_path, monkeypatch, capsys):
    repo = _git_init(tmp_path / "ok")
    monkeypatch.chdir(repo)
    assert WS.main([]) == 0
    assert capsys.readouterr().out.strip() == str((repo / ".bitranox" / "sdd").resolve())


def test_workspace_main_names_a_mkdir_failure_as_such(tmp_path, monkeypatch, capsys):
    repo = _git_init(tmp_path / "blocked")
    (repo / ".bitranox").write_text("a file, not a dir", encoding="utf-8")
    monkeypatch.chdir(repo)
    assert WS.main([]) == 2
    err = capsys.readouterr().err
    assert "cannot create" in err and "git working tree" not in err


def test_workspace_cli_on_a_cp1252_console_fails_loudly_not_with_a_wrong_path(tmp_path):
    repo = _git_init(tmp_path / "proj-✓")
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    env.pop("PYTHONUTF8", None)
    done = subprocess.run([sys.executable, WS.__file__], cwd=repo, capture_output=True, env=env,
                          timeout=60)
    assert b"Traceback" not in done.stderr
    assert done.returncode in (0, 2)
    if done.returncode == 0:  # a console that CAN encode it must print the exact path
        assert done.stdout.decode("cp1252").strip() == str((repo / ".bitranox" / "sdd").resolve())


# ---------------------------- every caller of workspace_dir() fails with exit 2, never a traceback

SCRIPTS = os.path.dirname(os.path.abspath(WS.__file__))

# Each script that resolves the workspace, with arguments that reach that resolution. A new caller
# must be added here: test_every_workspace_caller_is_in_the_failure_matrix fails until it is.
_WORKSPACE_CALLERS = {
    "task_brief.py": ["plan.md", "1"],
    "review_package.py": ["HEAD~1", "HEAD"],
}


def _callers_of_workspace_dir():
    found = []
    for name in sorted(os.listdir(SCRIPTS)):
        if not name.endswith(".py") or name == "sdd_workspace.py":
            continue
        with open(os.path.join(SCRIPTS, name), encoding="utf-8") as handle:
            if "workspace_dir(" in handle.read():
                found.append(name)
    return found


def test_every_workspace_caller_is_in_the_failure_matrix():
    assert _callers_of_workspace_dir() == sorted(_WORKSPACE_CALLERS)


def _run_script(name, argv, cwd, ceiling):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CEILING_DIRECTORIES"] = str(ceiling)
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, name), *argv], cwd=cwd,
                          capture_output=True, env=env, timeout=60)


def _two_commit_repo(path):
    _git_init(path)
    for msg in ("one", "two"):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                        "--allow-empty", "-m", msg], cwd=path, check=True, capture_output=True)
    (path / "plan.md").write_text("## Task 1\nbody\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("name", sorted(_WORKSPACE_CALLERS))
def test_a_blocked_workspace_is_exit_2_not_a_traceback(tmp_path, name):
    repo = _two_commit_repo(tmp_path / "blocked")
    (repo / ".bitranox").write_text("a file, not a dir", encoding="utf-8")
    done = _run_script(name, _WORKSPACE_CALLERS[name], repo, tmp_path)
    assert b"Traceback" not in done.stderr, done.stderr.decode("utf-8", "replace")
    assert done.returncode == 2
    assert b"cannot create the workspace" in done.stderr


@pytest.mark.parametrize("name", sorted(_WORKSPACE_CALLERS))
def test_the_same_arguments_in_a_healthy_repo_write_the_artifact(tmp_path, name):
    """Control for the blocked case: nothing but the blocked workspace separates the two."""
    repo = _two_commit_repo(tmp_path / "ok")
    done = _run_script(name, _WORKSPACE_CALLERS[name], repo, tmp_path)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    written = [p for p in (repo / ".bitranox" / "sdd").iterdir() if p.name != ".gitignore"]
    assert len(written) == 1


def test_task_brief_outside_a_repo_is_exit_2_not_a_traceback(tmp_path):
    loose = tmp_path / "loose"
    loose.mkdir()
    (loose / "plan.md").write_text("## Task 1\nbody\n", encoding="utf-8")
    done = _run_script("task_brief.py", ["plan.md", "1"], loose, tmp_path)
    assert b"Traceback" not in done.stderr, done.stderr.decode("utf-8", "replace")
    assert done.returncode == 2
    assert b"git working tree" in done.stderr


@pytest.mark.parametrize("name,argv", [
    ("task_brief.py", ["plan.md", "1", "no-such-dir/brief.md"]),
    ("review_package.py", ["HEAD~1", "HEAD", "no-such-dir/pkg.diff"]),
])
def test_an_unwritable_outfile_is_exit_2_not_a_traceback(tmp_path, name, argv):
    repo = _two_commit_repo(tmp_path / "repo")
    done = _run_script(name, argv, repo, tmp_path)
    assert b"Traceback" not in done.stderr, done.stderr.decode("utf-8", "replace")
    assert done.returncode == 2
    assert b"cannot write" in done.stderr
