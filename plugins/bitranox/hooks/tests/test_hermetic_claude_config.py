"""The test session must never inherit CLAUDE_CONFIG_DIR from whoever launched it.

Every path inside Claude's config dir follows CLAUDE_CONFIG_DIR (`claude_paths.config_dir()`), and
the tests isolate that dir by pointing HOME at a temp dir. A suite launched where the variable is
set - an A/B arm sets it for the session it runs, and an agent there may run the suite - would
send every HOME-isolated test to the launcher's config dir instead. The root `conftest.py` drops
the variable at session start. This drives the real conftest through a real pytest with a
sentinel config dir in the environment and asserts the test session resolves under its own HOME.
"""

import os
import subprocess
import sys
from pathlib import Path

import claude_paths
import pytest

REPO = Path(__file__).resolve().parents[4]
PROBE_FLAG = "BITRANOX_HERMETIC_CLAUDE_CONFIG_PROBE"


@pytest.mark.skipif(PROBE_FLAG not in os.environ, reason="probe, run only by the test below")
def test_probe_resolves_the_config_dir_under_home(tmp_path, monkeypatch):
    """What a HOME-isolated test does, run under the inherited environment."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert "CLAUDE_CONFIG_DIR" not in os.environ
    assert claude_paths.config_dir() == tmp_path / ".claude"


def test_a_leaked_claude_config_dir_never_reaches_a_test(tmp_path):
    sentinel = tmp_path / "launcher-config"
    sentinel.mkdir()
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(sentinel), PROBE_FLAG: "1"}
    probe = f"{Path(__file__).resolve()}::test_probe_resolves_the_config_dir_under_home"
    run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "--import-mode=importlib", probe],
                         cwd=str(REPO), env=env, capture_output=True, text=True,
                         encoding="utf-8", errors="replace")

    # The probe must have RUN, or a pass proves nothing.
    assert run.returncode == 0 and "1 passed" in run.stdout, run.stdout + run.stderr
    assert list(sentinel.iterdir()) == []
