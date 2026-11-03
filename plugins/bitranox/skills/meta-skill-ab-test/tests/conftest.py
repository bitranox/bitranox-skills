"""Put scripts/ on sys.path; provide the fake claude binary, a scratch workpiece and a skills repo."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

FIXTURES = HERE / "fixtures"
FIXTURE_SUFFIX = ".fixture"

# The three seams below need POSIX: an extensionless executable found on PATH through its
# shebang (Windows runs neither), and a workpiece whose gate is a /bin/sh script. CI runs every
# plugin test on Windows too, so they skip there by name rather than fail; the pure _ablib tests
# need none of them and still run on every platform.
WINDOWS_SKIP_REASON = "the A/B harness is Linux only (POSIX fake claude binary, gate.sh); Windows is unsupported"


def _skip_on_windows() -> None:
    if sys.platform == "win32":
        pytest.skip(WINDOWS_SKIP_REASON)


def _git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@x"})
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,  # nosec B603
                          encoding="utf-8", env=env, check=False)
    assert proc.returncode == 0, f"git {' '.join(args)}: {proc.stderr}"
    return proc.stdout.strip()


@pytest.fixture
def fake_claude_path(tmp_path):
    """A dir holding an executable `claude` that replays fixtures; prepend it to PATH."""
    _skip_on_windows()
    d = tmp_path / "fakebin"
    d.mkdir()
    target = d / "claude"
    shutil.copyfile(HERE / "fakes" / "claude", target)
    target.chmod(0o755)
    return d


@pytest.fixture
def scratch_repo(tmp_path):
    """A workpiece: one commit, a CLAUDE.local.md, a gate that fails when BROKEN exists."""
    _skip_on_windows()
    repo = tmp_path / "workpiece"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "CLAUDE.md").write_text("# workpiece\n", encoding="utf-8")
    (repo / "CLAUDE.local.md").write_text("WHAT: scratch workpiece\n", encoding="utf-8")
    (repo / "gate.sh").write_text("#!/bin/sh\ntest ! -e BROKEN\n", encoding="utf-8")
    (repo / "gate.sh").chmod(0o755)
    (repo / ".gitignore").write_text("CLAUDE.local.md\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    (repo / ".base").write_text(_git(repo, "rev-parse", "HEAD"), encoding="utf-8")
    return repo


@pytest.fixture
def skills_repo(tmp_path):
    """A git repo made from fixtures/skills-repo: the two-file plugin a frozen checkout is cut from."""
    _skip_on_windows()
    repo = tmp_path / "skills"
    shutil.copytree(FIXTURES / "skills-repo", repo)
    # The fixture's hook is stored as .py.fixture and renamed here: tracked as .py it would share
    # a basename with the plugin's real hooks/self_improve_signals.py, which the repo gate refuses.
    for stored in repo.rglob(f"*.py{FIXTURE_SUFFIX}"):
        stored.rename(stored.with_suffix(""))
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "plugin")
    (repo / ".ref").write_text(_git(repo, "rev-parse", "HEAD"), encoding="utf-8")
    return repo


@pytest.fixture
def arm_env_base(fake_claude_path):
    """The PATH an arm sees under test: the fake claude first, then the real PATH (for git)."""
    return {"PATH": f"{fake_claude_path}{os.pathsep}{os.environ['PATH']}"}
