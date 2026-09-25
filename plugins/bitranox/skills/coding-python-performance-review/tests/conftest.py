"""Put the skill directory on sys.path so tests can import the scripts by module name.

Also provides ``run_script``: runs one of the skill's scripts as a real subprocess, the way
SKILL.md invokes it, and returns the CompletedProcess with BYTES output so a test can check the
encoding the script actually wrote.
"""
import os
import subprocess
import sys

import pytest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SKILL_DIR)


def _clean_env(**extra):
    """The current environment minus anything that would scope git or pytest to another repo.

    A push from a linked worktree exports GIT_DIR to its hooks, and git reads it before the
    cwd, so a fixture repo built under it would write into the repo being pushed.
    """
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("GIT_") and k not in ("PYTEST_ADDOPTS", "PYTHONIOENCODING")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra)
    return env


@pytest.fixture
def clean_env():
    """The ``_clean_env`` builder, as a fixture (a test must never import conftest by name)."""
    return _clean_env


@pytest.fixture
def run_script():
    def _run(name, *args, cwd=None, env=None, timeout=120):
        script = os.path.join(SKILL_DIR, name)
        return subprocess.run([sys.executable, script, *args], cwd=cwd, env=env or _clean_env(),
                              capture_output=True, timeout=timeout, check=False)
    return _run
