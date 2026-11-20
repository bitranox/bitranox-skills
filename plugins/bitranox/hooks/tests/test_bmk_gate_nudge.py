"""Tests for bmk-gate-nudge: name bitranox:devops-bmk the first time a session runs a bmk gate."""

import json
import os
import subprocess
import sys
from pathlib import Path

import bmk_gate_nudge as nudge
import pytest

HOOK = Path(__file__).resolve().parents[1] / "bmk-gate-nudge.py"


@pytest.fixture
def bmk_repo(tmp_path):
    repo = tmp_path / "proj"
    repo.mkdir()
    (repo / "Makefile").write_text("# BMK MAKEFILE 3.13.2\n.PHONY: test\n", encoding="utf-8")
    return repo


@pytest.fixture
def plain_repo(tmp_path):
    repo = tmp_path / "plain"
    repo.mkdir()
    (repo / "Makefile").write_text("all:\n\techo hi\n", encoding="utf-8")
    return repo


@pytest.mark.parametrize("command", [
    "make test",
    "make push",
    "make bump-patch",
    "make release",
    "make test-all",
    "env -u VIRTUAL_ENV BMK_PYTHON_CMD=.venv/bin/python make test",
    "timeout 900 make test > /tmp/x.log 2>&1",
    "git status && make test",
])
def test_a_bmk_target_in_a_bmk_repo_fires(bmk_repo, command):
    assert nudge.notice(command, str(bmk_repo)) is not None


# as_posix(): the Bash tool is POSIX even on Windows, so an unquoted C:\Users\... path loses its
# backslashes as escapes (C:Users...) exactly as Git Bash would; C:/Users/... is what a user types.
def test_make_dash_c_into_a_bmk_repo_fires(bmk_repo, tmp_path):
    assert nudge.notice(f"make -C {bmk_repo.as_posix()} test", str(tmp_path)) is not None


def test_a_leading_cd_into_the_bmk_repo_fires(bmk_repo, tmp_path):
    assert nudge.notice(f"cd {bmk_repo.as_posix()} && make test", str(tmp_path)) is not None


def _git_bash_spelling(path):
    """`C:\\x\\y` as Git Bash prints it, `/c/x/y`."""
    return "/" + path.drive[0].lower() + path.as_posix()[len(path.drive):]


# Only a Windows host has a drive for Git Bash to mount at `/c`; elsewhere `/c` is a directory.
_GIT_BASH_DRIVES = pytest.mark.skipif(os.name != "nt", reason="Git Bash drive paths exist on Windows only")


@_GIT_BASH_DRIVES
@pytest.mark.parametrize("template", ["make -C {} test", "make --directory={} test", "cd {} && make test"])
def test_a_git_bash_drive_path_into_a_bmk_repo_fires(bmk_repo, tmp_path, template):
    """`make -C /c/...` is drive C to Git Bash; read at the current drive's root it was C:\\c\\...,
    which holds no Makefile, so the gate went unnamed."""
    command = template.format(_git_bash_spelling(bmk_repo))
    assert nudge.notice(command, str(tmp_path), "Bash") is not None


@_GIT_BASH_DRIVES
def test_the_powershell_tool_keeps_a_slash_drive_path_at_the_current_drive_root(bmk_repo, tmp_path):
    """PowerShell passes `/c/...` on unchanged: it is not the drive there, so nothing fires."""
    command = f"make -C {_git_bash_spelling(bmk_repo)} test"
    assert nudge.notice(command, str(tmp_path), "PowerShell") is None


@pytest.mark.parametrize("template", ["make -C {} test", "cd {} && make test"])
def test_a_git_bash_mount_path_names_no_repo_on_windows(bmk_repo, tmp_path, monkeypatch, template):
    """A rooted path that is not a drive (`/opt/...` here) reaches Git Bash's mount table, not the
    current drive's root, so on Windows the hook cannot say which Makefile runs and stays silent;
    elsewhere it is the repo itself. The cwd is moved onto the repo's drive so the current-drive
    reading would find it on every Windows host."""
    monkeypatch.chdir(tmp_path)
    command = template.format(bmk_repo.as_posix()[len(bmk_repo.drive):])
    fired = nudge.notice(command, str(tmp_path), "Bash") is not None
    assert fired is (os.name != "nt")
    assert nudge.notice(command, str(tmp_path), "PowerShell") is not None


@pytest.mark.parametrize("command", ["bmk test", "uvx bmk@latest install", "uvx bmk deps --update"])
def test_running_bmk_itself_fires_anywhere(plain_repo, command):
    assert nudge.notice(command, str(plain_repo)) is not None


@pytest.mark.parametrize("command", [
    "make test",                 # a plain Makefile is not a bmk gate
    "make all",
])
def test_a_plain_makefile_stays_silent(plain_repo, command):
    assert nudge.notice(command, str(plain_repo)) is None


@pytest.mark.parametrize("command", [
    "make help",                 # not a gate target
    "make clean",
    "echo make test",            # mentions it, runs echo
    "grep -n 'make test' Makefile",
    "cat <<'EOF'\nmake test\nEOF",
    "git commit -m 'run make test before push'",
])
def test_not_running_a_bmk_gate_stays_silent(bmk_repo, command):
    assert nudge.notice(command, str(bmk_repo)) is None


def test_an_unknown_cwd_and_no_cd_stays_silent():
    assert nudge.notice("make test", None) is None


def test_the_notice_names_the_skill(bmk_repo):
    assert "bitranox:devops-bmk" in nudge.notice("make test", str(bmk_repo))


def _isolated_env(tmp_path):
    """HOME and USERPROFILE both: Path.home() reads USERPROFILE on Windows, and a session marker
    written to the real profile would silence the first call of the next run."""
    home = str(tmp_path / "home")
    return {**os.environ, "HOME": home, "USERPROFILE": home}


def _run(event, env):
    proc = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), text=True,
                          encoding="utf-8", errors="replace", capture_output=True, env=env, timeout=30)
    return proc.returncode, proc.stdout


def test_the_hook_says_it_once_per_session(bmk_repo, tmp_path):
    env = _isolated_env(tmp_path)
    event = {"tool_name": "Bash", "session_id": f"s-{tmp_path.name}", "cwd": str(bmk_repo),
             "tool_input": {"command": "make test"}}
    rc1, out1 = _run(event, env)
    rc2, out2 = _run(event, env)
    assert rc1 == 0 and rc2 == 0
    assert "bitranox:devops-bmk" in json.loads(out1)["hookSpecificOutput"]["additionalContext"]
    assert out2.strip() == ""


def test_the_hook_ignores_other_tools_and_bad_input(bmk_repo, tmp_path):
    env = _isolated_env(tmp_path)
    rc, out = _run({"tool_name": "Write", "cwd": str(bmk_repo), "tool_input": {"command": "make test"}}, env)
    assert (rc, out.strip()) == (0, "")
    proc = subprocess.run([sys.executable, str(HOOK)], input="not json", text=True, encoding="utf-8",
                          capture_output=True, env=env, timeout=30)
    assert (proc.returncode, proc.stdout.strip()) == (0, "")
