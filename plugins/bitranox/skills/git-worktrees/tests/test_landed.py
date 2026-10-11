"""Tests for landed.py - did a leftover worktree or branch already land on the target branch?

Every case builds a real repository and drives the real CLI, because the questions this tool
answers (a squash merge, a cherry-pick, a file that master changed again afterwards) are shapes
of git history that a fake would only describe. ASCII only.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import landed as L
import pytest

GIT = shutil.which("git")
pytestmark = pytest.mark.skipif(GIT is None, reason="git is not installed")

CLI = str(Path(__file__).resolve().parent.parent / "scripts" / "landed.py")
TIMEOUT = 60


def _clean_env(root: Path) -> dict[str, str]:
    """An environment with no inherited repo scoping and a private git config.

    A push from a linked worktree exports GIT_DIR to the hooks that run this suite; inherited, it
    would point every fixture's git at the launching repository instead of the fixture.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_GLOBAL"] = str(root / "gitconfig")
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "t"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "t@example.invalid"
    return env


class Repo:
    """A real repository on branch `main`, with helpers to write, commit and branch."""

    def __init__(self, root: Path):
        self.root = root
        self.path = root / "main"
        self.path.mkdir()
        self.env = _clean_env(root)
        self.git("init", "-q", "-b", "main")

    def git(self, *args, cwd=None) -> str:
        done = subprocess.run(
            [GIT, *args], cwd=str(cwd or self.path), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=TIMEOUT, check=True, env=self.env,
        )
        return done.stdout

    def write(self, rel: str, text: str, where: Path | None = None) -> None:
        target = (where or self.path) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))

    def commit(self, message: str, where: Path | None = None) -> None:
        self.git("add", "-A", cwd=where)
        self.git("commit", "-q", "-m", message, cwd=where)

    def worktree(self, branch: str) -> Path:
        path = self.root / f"wt-{branch}"
        self.git("worktree", "add", "-q", str(path), "-b", branch)
        return path

    def run(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, CLI, *args], cwd=str(cwd or self.path), capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT, check=False,
            env=self.env,
        )

    def run_json(self, *args, cwd=None):
        done = self.run(*args, "--json", cwd=cwd)
        return done.returncode, json.loads(done.stdout)


@pytest.fixture
def repo(tmp_path):
    r = Repo(tmp_path)
    r.write("a.txt", "one\ntwo\nthree\n")
    r.commit("init")
    return r


# ---------------------------------------------------------------------------------------------
# Worktree mode: uncommitted files compared byte for byte
# ---------------------------------------------------------------------------------------------


def test_dirty_worktree_whose_edit_is_on_main_is_landed(repo):
    wt = repo.worktree("topic")
    repo.write("a.txt", "one\nTWO\nthree\n", where=wt)
    repo.write("a.txt", "one\nTWO\nthree\n")
    repo.commit("same edit made on main")

    rc, env = repo.run_json(str(wt), "--into", "main")

    assert rc == 0, env
    assert env["data"]["verdict"] == "landed"
    files = {f["path"]: f["status"] for f in env["data"]["files"]}
    assert files == {"a.txt": "in_target"}


def test_dirty_worktree_with_an_edit_main_lacks_is_not_landed(repo):
    wt = repo.worktree("topic")
    repo.write("a.txt", "one\nmine\nthree\n", where=wt)

    rc, env = repo.run_json(str(wt), "--into", "main")

    assert rc == 1, env
    assert env["ok"] is True
    assert env["data"]["verdict"] == "not_landed"
    assert {f["path"]: f["status"] for f in env["data"]["files"]} == {"a.txt": "differs"}


def test_edit_that_main_changed_again_afterwards_counts_as_landed(repo):
    """The bytes match an EARLIER commit on main, not main's tip - the work landed, then moved on."""
    wt = repo.worktree("topic")
    repo.write("a.txt", "one\nTWO\nthree\n", where=wt)
    repo.write("a.txt", "one\nTWO\nthree\n")
    repo.commit("landed")
    repo.write("a.txt", "one\nTWO\nthree\nfour\n")
    repo.commit("main moved on")

    rc, env = repo.run_json(str(wt), "--into", "main")

    assert rc == 0, env
    assert {f["path"]: f["status"] for f in env["data"]["files"]} == {"a.txt": "in_history"}


def test_untracked_file_main_does_not_have_is_not_landed(repo):
    wt = repo.worktree("topic")
    repo.write("new/b.txt", "fresh\n", where=wt)

    rc, env = repo.run_json(str(wt), "--into", "main")

    assert rc == 1, env
    assert {f["path"]: f["status"] for f in env["data"]["files"]} == {
        "new/b.txt": "absent_in_target"}


def test_local_deletion_that_main_also_made_is_landed(repo):
    wt = repo.worktree("topic")
    (wt / "a.txt").unlink()
    repo.git("rm", "-q", "a.txt")
    repo.git("commit", "-q", "-m", "drop a")

    rc, env = repo.run_json(str(wt), "--into", "main")

    assert rc == 0, env
    assert {f["path"]: f["status"] for f in env["data"]["files"]} == {"a.txt": "deleted_in_target"}


def test_local_deletion_main_did_not_make_is_not_landed(repo):
    wt = repo.worktree("topic")
    (wt / "a.txt").unlink()

    rc, env = repo.run_json(str(wt), "--into", "main")

    assert rc == 1, env
    assert {f["path"]: f["status"] for f in env["data"]["files"]} == {"a.txt": "deleted_here_only"}


def test_a_dirty_worktree_is_inspected_without_writing_the_index(repo):
    """A plain `git status` refreshes the index and rewrites it; the tool must leave it alone."""
    wt = repo.worktree("topic")
    repo.write("a.txt", "one\nmine\nthree\n", where=wt)
    os.utime(wt / "a.txt", (1_000_000_000, 1_000_000_000))
    gitdir = Path(repo.git("rev-parse", "--absolute-git-dir", cwd=wt).strip())
    index = gitdir / "index"
    before = (index.read_bytes(), index.stat().st_mtime_ns)

    repo.run_json(str(wt), "--into", "main")

    assert (index.read_bytes(), index.stat().st_mtime_ns) == before


# ---------------------------------------------------------------------------------------------
# Branch mode: committed work, including work that landed squashed or rewritten
# ---------------------------------------------------------------------------------------------


def _branch_with_two_commits(repo):
    repo.git("checkout", "-q", "-b", "feature")
    repo.write("a.txt", "one\ntwo\nthree\nfour\n")
    repo.commit("add four")
    repo.write("c.txt", "see\n")
    repo.commit("add c")
    repo.git("checkout", "-q", "main")


def test_squash_merged_branch_is_landed_although_git_cherry_says_otherwise(repo):
    _branch_with_two_commits(repo)
    repo.git("merge", "-q", "--squash", "feature")
    repo.git("commit", "-q", "-m", "squash feature")

    rc, env = repo.run_json("feature", "--into", "main")

    assert rc == 0, env
    data = env["data"]
    assert data["verdict"] == "landed"
    assert data["commits"]["total"] == 2
    # The premise behind the tool: patch-id equivalence (git cherry) finds NEITHER commit.
    assert data["commits"]["patch_equivalent"] == 0
    assert data["lines"]["added"] == 2
    assert data["lines"]["present"] == 2


def test_cherry_picked_branch_is_landed_by_patch_id(repo):
    _branch_with_two_commits(repo)
    # Diverge first: picked onto an unmoved main within the same second, git rebuilds the very
    # same commits (same tree, parent, message and timestamp), leaving the branch nothing to judge.
    repo.write("z.txt", "unrelated\n")
    repo.commit("main moves")
    for sha in repo.git("rev-list", "--reverse", "main..feature").split():
        repo.git("cherry-pick", sha)

    rc, env = repo.run_json("feature", "--into", "main")

    assert rc == 0, env
    assert env["data"]["commits"]["patch_equivalent"] == 2


def test_branch_with_lines_main_lacks_is_not_landed_and_names_them(repo):
    _branch_with_two_commits(repo)
    repo.write("c.txt", "see\n")
    repo.commit("only c landed")

    rc, env = repo.run_json("feature", "--into", "main")

    assert rc == 1, env
    data = env["data"]
    assert data["verdict"] == "not_landed"
    assert data["lines"] == {"added": 2, "present": 1, "share": 0.5}
    missing = {f["path"]: f["missing"] for f in data["branch_files"] if f["missing"]}
    assert missing == {"a.txt": ["four"]}


def test_a_line_present_once_on_main_covers_only_one_added_copy(repo):
    """Lines are matched as a multiset: two added copies need two copies on main."""
    repo.git("checkout", "-q", "-b", "feature")
    repo.write("a.txt", "one\ntwo\nthree\nx\nx\n")
    repo.commit("two x")
    repo.git("checkout", "-q", "main")
    repo.write("a.txt", "one\ntwo\nthree\nx\n")
    repo.commit("one x")

    rc, env = repo.run_json("feature", "--into", "main")

    assert rc == 1, env
    assert env["data"]["lines"]["present"] == 1


def test_version_named_in_a_subject_is_checked_against_the_changelog(repo):
    repo.git("checkout", "-q", "-b", "feature")
    repo.write("a.txt", "one\ntwo\nthree\nfour\n")
    repo.commit("add four; 1.2.3")
    repo.git("checkout", "-q", "main")
    repo.write("CHANGELOG.md", "# Changelog\n\n## [1.2.3]\n\n- four\n")
    repo.write("a.txt", "one\ntwo\nthree\nfour\n")
    repo.commit("release 1.2.3")

    rc, env = repo.run_json("feature", "--into", "main")

    assert rc == 0, env
    assert env["data"]["versions"] == [{"version": "1.2.3", "in_changelog": True}]


def test_a_worktree_also_reports_its_branch_commits(repo):
    wt = repo.worktree("topic")
    repo.write("b.txt", "bee\n", where=wt)
    repo.commit("add b", where=wt)

    rc, env = repo.run_json(str(wt), "--into", "main")

    assert rc == 1, env
    assert env["data"]["commits"]["total"] == 1
    assert env["data"]["lines"]["present"] == 0


# ---------------------------------------------------------------------------------------------
# Could not run: exit 2 with a JSON envelope
# ---------------------------------------------------------------------------------------------


def test_unknown_target_is_exit_2_with_an_envelope(repo):
    rc, env = repo.run_json("no-such-branch", "--into", "main")

    assert rc == 2
    assert env["ok"] is False
    assert "no-such-branch" in env["data"]["error"]


def test_unknown_into_ref_is_exit_2(repo):
    _branch_with_two_commits(repo)
    rc, env = repo.run_json("feature", "--into", "nope")

    assert rc == 2
    assert env["ok"] is False


def test_default_into_falls_back_to_a_local_main(repo):
    _branch_with_two_commits(repo)
    rc, env = repo.run_json("feature")

    assert rc == 1, env
    assert env["data"]["into"] == "main"


def test_text_output_names_the_verdict_and_each_unlanded_file(repo):
    wt = repo.worktree("topic")
    repo.write("a.txt", "one\nmine\nthree\n", where=wt)

    done = repo.run(str(wt), "--into", "main")

    assert done.returncode == 1
    assert "NOT LANDED" in done.stdout
    assert "a.txt" in done.stdout


# ---------------------------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------------------------


def test_added_lines_skip_headers_and_blank_lines():
    diff = (
        "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1,3 @@\n+kept\n+\n+   \n-gone\n+also"
    )
    assert L.added_lines(diff) == ["kept", "also"]


def test_versions_in_subjects_are_unique_and_ordered():
    assert L.versions_in(["fix x; 8.10.3", "more 8.10.3 and 1.0.0", "none"]) == ["8.10.3", "1.0.0"]
