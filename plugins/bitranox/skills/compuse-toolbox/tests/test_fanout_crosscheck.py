"""Tests for fanout_crosscheck.py - after a per-target fan-out, find text that landed in the wrong
target. Every fixture is a real temporary git repo (or a real plain file): the tool's whole job is
reading what git says was ADDED, so a stubbed diff would test the wrong thing.
"""

import json
import subprocess
import sys
from pathlib import Path

import fanout_crosscheck as F
import pytest

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "fanout_crosscheck.py"


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=True).stdout.strip()


def make_repo(root: Path, name: str, files: dict[str, str]) -> Path:
    """A repo whose `files` are committed: the state before the fan-out."""
    repo = root / name
    repo.mkdir()
    for rel, text in files.items():
        (repo / rel).write_text(text, encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


def append(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def three_repos(tmp_path):
    """The 2026-10-05 shape: three sibling repos, one agent each, each documenting its own."""
    a = make_repo(tmp_path, "alpha_lib", {"README.md": "# alpha_lib\n\nParses things.\n"})
    b = make_repo(tmp_path, "beta-tool", {"README.md": "# beta-tool\n\nRuns things.\n"})
    c = make_repo(tmp_path, "gamma", {"README.md": "# gamma\n\nStores things.\n"})
    return a, b, c


def run(*args, cwd=None):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(cwd) if cwd else None,
                          check=False)


def targets(*repos):
    out = []
    for repo in repos:
        out += ["--target", f"{repo.name}={repo}"]
    return out


def test_a_siblings_name_on_an_added_line_is_found(tmp_path):
    a, b, c = three_repos(tmp_path)
    append(a, "README.md", "\nUsage: see the docs.\n")
    append(b, "README.md", "\nThis module wraps the alpha_lib parser.\n")
    append(c, "README.md", "\nStores what it is given.\n")
    proc = run(*targets(a, b, c), "--json")
    assert proc.returncode == 1, (proc.stdout, proc.stderr)
    data = json.loads(proc.stdout)["data"]
    assert [(f["target"], f["file"], f["line"], f["foreign"]) for f in data["findings"]] == [
        ("beta-tool", "README.md", 5, "alpha_lib")]
    assert data["examined"]["targets"] == 3
    assert data["examined"]["added_lines"] >= 6


@pytest.mark.parametrize("spelling", ["alpha-lib", "Alpha Lib", "ALPHA_LIB"])
def test_every_spelling_of_a_name_is_found(tmp_path, spelling):
    a, b, _ = three_repos(tmp_path)
    append(a, "README.md", "\nmore\n")
    append(b, "README.md", f"\nBorrowed from {spelling}.\n")
    proc = run(*targets(a, b))
    assert proc.returncode == 1, (spelling, proc.stdout, proc.stderr)


def test_a_longer_name_that_contains_a_siblings_name_is_not_it(tmp_path):
    a, b, _ = three_repos(tmp_path)
    append(a, "README.md", "\nmore\n")
    append(b, "README.md", "\nSee alpha_library and gamma_rays, both unrelated.\n")
    proc = run(*targets(a, b))
    assert proc.returncode == 0, (proc.stdout, proc.stderr)


def test_a_line_that_was_already_there_is_not_a_finding(tmp_path):
    a = make_repo(tmp_path, "alpha_lib", {"README.md": "# alpha_lib\n"})
    b = make_repo(tmp_path, "beta-tool", {"README.md": "# beta-tool\n\nOlder note on alpha_lib.\n"})
    append(a, "README.md", "\nnew text\n")
    append(b, "README.md", "\nnew text\n")
    proc = run(*targets(a, b))
    assert proc.returncode == 0, (proc.stdout, proc.stderr)


def test_a_declared_dependency_of_the_scanned_target_is_not_a_finding(tmp_path):
    a, b, _ = three_repos(tmp_path)
    (b / "pyproject.toml").write_text(
        '[project]\nname = "beta-tool"\ndependencies = ["alpha-lib>=1.0"]\n', encoding="utf-8")
    _git(b, "add", "pyproject.toml")
    _git(b, "commit", "-q", "-m", "deps")
    append(a, "README.md", "\nmore\n")
    append(b, "README.md", "\nimport alpha_lib\n")
    proc = run(*targets(a, b), "--json")
    data = json.loads(proc.stdout)["data"]
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert data["findings"] == []


def test_allow_suppresses_a_named_token_in_one_target(tmp_path):
    a, b, _ = three_repos(tmp_path)
    append(a, "README.md", "\nmore\n")
    append(b, "README.md", "\nCompare alpha_lib.\n")
    proc = run(*targets(a, b), "--allow", "beta-tool=alpha_lib")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)


def test_an_extra_ident_is_looked_for_too(tmp_path):
    a, b, _ = three_repos(tmp_path)
    append(a, "README.md", "\nmore\n")
    append(b, "README.md", "\nThe AlphaParser class does it.\n")
    proc = run(*targets(a, b), "--ident", "alpha_lib=AlphaParser")
    assert proc.returncode == 1, (proc.stdout, proc.stderr)


def test_an_untracked_new_file_counts_as_added(tmp_path):
    """git diff never shows an untracked file, and a file CREATED in the wrong repo is exactly
    the misdirected write this exists to catch."""
    a, b, _ = three_repos(tmp_path)
    append(a, "README.md", "\nmore\n")
    (b / "NOTES.md").write_text("Copied from gamma.\n", encoding="utf-8")
    proc = run(*targets(a, b, tmp_path / "gamma"), "--json")
    assert proc.returncode == 1, (proc.stdout, proc.stderr)
    found = json.loads(proc.stdout)["data"]["findings"]
    assert [(f["target"], f["file"], f["line"]) for f in found] == [("beta-tool", "NOTES.md", 1)]


def test_since_counts_commits_made_after_rev(tmp_path):
    a, b, _ = three_repos(tmp_path)
    base = _git(b, "rev-parse", "HEAD")
    append(a, "README.md", "\nmore\n")
    append(b, "README.md", "\nPorted from alpha_lib.\n")
    _git(b, "commit", "-q", "-am", "agent work")
    assert run(*targets(a, b)).returncode != 1  # committed, so not uncommitted work
    # Per target: a sha from beta-tool does not exist in alpha_lib.
    proc = run(*targets(a, b), "--since", f"beta-tool={base}")
    assert proc.returncode == 1, (proc.stdout, proc.stderr)


def test_a_since_rev_that_does_not_resolve_is_refused(tmp_path):
    a, b, _ = three_repos(tmp_path)
    append(a, "README.md", "\nmore\n")
    proc = run(*targets(a, b), "--since", "no-such-rev")
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "no-such-rev" in proc.stderr


def test_plain_file_targets_count_every_line_as_added(tmp_path):
    one = tmp_path / "levels" / "projects-public"
    two = tmp_path / "levels" / "bitranox-systems"
    for d in (one, two):
        d.mkdir(parents=True)
    (one / "CLAUDE.local.md").write_text("WHAT: public repos\n", encoding="utf-8")
    (two / "CLAUDE.local.md").write_text("WHAT: projects public descriptor, wrong level\n",
                                         encoding="utf-8")
    proc = run("--target", f"projects-public={one / 'CLAUDE.local.md'}",
               "--target", f"bitranox-systems={two / 'CLAUDE.local.md'}",
               "--ident", "projects-public=projects public", "--json")
    assert proc.returncode == 1, (proc.stdout, proc.stderr)
    found = json.loads(proc.stdout)["data"]["findings"]
    assert [(f["target"], f["line"]) for f in found] == [("bitranox-systems", 1)]


def test_zero_added_lines_is_a_refusal_not_a_clean_pass(tmp_path):
    """A wrong --since or a target with no work prints a green that means nothing."""
    a, b, _ = three_repos(tmp_path)
    proc = run(*targets(a, b), "--json")
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    env = json.loads(proc.stdout)
    assert env["ok"] is False
    assert "0 added lines" in env["error"]


@pytest.mark.parametrize("args, needle", [
    (["--target", "only=."], "at least two"),
    (["--target", "a=.", "--target", "a=.."], "twice"),
    (["--target", "noequals"], "NAME=PATH"),
])
def test_bad_target_lists_are_usage_errors(tmp_path, args, needle):
    proc = run(*args, cwd=tmp_path)
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert needle in proc.stderr


def test_a_directory_that_is_not_a_work_tree_is_refused(tmp_path):
    a, _, _ = three_repos(tmp_path)
    loose = tmp_path / "loose"
    loose.mkdir()
    proc = run(*targets(a), "--target", f"loose={loose}")
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert "not a git work tree" in proc.stderr


def test_added_lines_parses_hunk_line_numbers():
    diff = ("diff --git a/x.md b/x.md\n--- a/x.md\n+++ b/x.md\n"
            "@@ -3,0 +4,2 @@\n+first\n+second\n@@ -9 +11 @@\n-old\n+third\n")
    assert list(F.added_lines_from_diff(diff)) == [
        ("x.md", 4, "first"), ("x.md", 5, "second"), ("x.md", 11, "third")]


def test_a_deleted_file_adds_nothing():
    diff = "diff --git a/x.md b/x.md\n--- a/x.md\n+++ /dev/null\n@@ -1 +0,0 @@\n-gone\n"
    assert list(F.added_lines_from_diff(diff)) == []
