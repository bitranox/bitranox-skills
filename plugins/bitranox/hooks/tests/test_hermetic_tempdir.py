"""The test session must leave nothing behind in the launcher's temp directory.

Hooks keep per-project state in `tempfile.gettempdir()`, keyed by a hash of the project path, and
every test hands them its own `tmp_path` as the project. So every run of the suite wrote a few
hundred state files that nothing removed. Measured 2026-10-06 on a shared host whose /tmp is a
tmpfs with a fixed inode count: 57,653 `claude-ci-watch-*.json` sat directly in /tmp, at least
44,084 of them holding this suite's fixture values, and the tmpfs ran out of inodes - every tool
on the host that writes to /tmp then failed with ENOSPC while 41 GB were free.

The root `conftest.py` points the whole session (TMPDIR, TEMP, TMP and `tempfile.tempdir`) at one
directory of its own and removes it when the session ends. This drives the real conftest through a
real pytest with a sentinel directory as the inherited TMPDIR, and asserts the sentinel is empty
afterwards.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
PROBE_FLAG = "BITRANOX_HERMETIC_TEMPDIR_PROBE"


@pytest.mark.skipif(PROBE_FLAG not in os.environ, reason="probe, run only by the test below")
def test_probe_leaves_a_temp_file_behind():
    """What a hook's state write looks like from the suite: a temp file nobody removes."""
    fd, _ = tempfile.mkstemp(prefix="claude-probe-", suffix=".json")
    os.close(fd)


def test_a_session_leaves_nothing_in_the_launchers_temp_dir(tmp_path):
    sentinel = tmp_path / "launcher-tmp"
    sentinel.mkdir()
    env = {**os.environ, PROBE_FLAG: "1", "TMPDIR": str(sentinel), "TEMP": str(sentinel),
           "TMP": str(sentinel)}
    node = "%s::test_probe_leaves_a_temp_file_behind" % Path(__file__).relative_to(REPO).as_posix()
    run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", node],
                         cwd=str(REPO), env=env, capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    assert run.returncode == 0, run.stdout + run.stderr
    assert "1 passed" in run.stdout, run.stdout
    assert sorted(p.name for p in sentinel.iterdir()) == [], run.stdout


def test_the_session_temp_dir_is_the_one_every_temp_api_sees():
    """A subprocess reads TMPDIR (TEMP/TMP on Windows), this process reads tempfile.tempdir: a
    redirect of only one of them leaves the other writing into the launcher's directory."""
    session_dir = tempfile.gettempdir()
    assert Path(session_dir).name.startswith("bitranox-tests-"), session_dir
    for name in ("TMPDIR", "TEMP", "TMP"):
        assert os.environ[name] == session_dir, name
