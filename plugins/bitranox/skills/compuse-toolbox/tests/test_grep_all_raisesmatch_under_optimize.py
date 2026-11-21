"""grep_all and raisesmatch run under `python -OO`, which strips every docstring.

Both built their argument parser's description from `__doc__.splitlines()[0]`, None under -OO, so
every invocation died with AttributeError. Each test runs the real script in a child -OO
interpreter: --help, and one real scan.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _run_oo(tmp_path: Path, script: str, *args: str) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-OO", str(SCRIPTS / script), *args],
                          capture_output=True, encoding="utf-8", env=env, cwd=str(tmp_path))


@pytest.mark.parametrize("script", ["grep_all.py", "raisesmatch.py"])
def test_help_works_under_oo(tmp_path: Path, script: str) -> None:
    r = _run_oo(tmp_path, script, "--help")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("usage: %s" % script), r.stdout


def test_grep_all_scans_under_oo(tmp_path: Path) -> None:
    src = tmp_path / "a.py"
    src.write_text("x = 1\n", encoding="utf-8")
    r = _run_oo(tmp_path, "grep_all.py", "--json", "x =", str(src))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["data"]["files_scanned"] == 1


def test_raisesmatch_scans_under_oo(tmp_path: Path) -> None:
    src = tmp_path / "a.py"
    src.write_text("x = 1\n", encoding="utf-8")
    r = _run_oo(tmp_path, "raisesmatch.py", "--json", str(src))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["data"]["files"] == 1
