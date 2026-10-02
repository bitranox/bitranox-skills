"""The test session must never inherit a git repository from whoever launched it.

git reads GIT_DIR before it looks at its working directory. A pytest run that inherits one - a
push from a linked worktree hands the pre-push hook GIT_DIR, and `git rebase --exec` or any other
git-spawned runner can too - makes every fixture's `git init` / `git config` / `git commit` land in
THAT repository instead of the fixture. Measured 2026-08-31: fixture runs of
`git config user.name t` and `user.email t@example.com` were written into this repo's shared
`.git/config`, and 375 public commits carried `t <t@example.com>` as their author before anyone
looked. Every git call exited 0.

The pre-push hook unsets the variables for its own run; the root `conftest.py` makes the suite
itself immune, so no other launcher can reopen it. This drives the real conftest through a real
pytest with a sentinel repository as the leaked GIT_DIR, and asserts the sentinel is untouched.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
PROBE_FLAG = "BITRANOX_HERMETIC_GIT_PROBE"


def _clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(cwd), env=env or _clean_env(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


@pytest.mark.skipif(PROBE_FLAG not in os.environ, reason="probe, run only by the test below")
def test_probe_builds_a_fixture_repo(tmp_path):
    """What every fixture-building test in this suite does, run under the inherited environment."""
    subprocess.run(["git", "init", "-q", "."], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=str(tmp_path), check=True,
                   capture_output=True)


def test_a_leaked_git_dir_never_reaches_a_fixture(tmp_path):
    sentinel = tmp_path / "sentinel"
    sentinel.mkdir()
    assert _git(sentinel, "init", "-q", ".").returncode == 0
    before = (sentinel / ".git" / "config").read_bytes()

    env = {**_clean_env(), "GIT_DIR": str(sentinel / ".git"), PROBE_FLAG: "1"}
    probe = f"{Path(__file__).resolve()}::test_probe_builds_a_fixture_repo"
    run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "--import-mode=importlib", probe],
                         cwd=str(REPO), env=env, capture_output=True, text=True,
                         encoding="utf-8", errors="replace")

    # The probe must have RUN, or an unchanged sentinel proves nothing.
    assert run.returncode == 0 and "1 passed" in run.stdout, run.stdout + run.stderr
    assert (sentinel / ".git" / "config").read_bytes() == before, (
        "a test wrote into the repository named by an inherited GIT_DIR:\n"
        + _git(sentinel, "config", "--list", "--local").stdout
    )
