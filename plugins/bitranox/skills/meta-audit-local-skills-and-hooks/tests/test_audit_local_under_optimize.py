"""audit_local.py runs under `python -OO`, which strips every docstring.

It built its argument parser's description from `__doc__.splitlines()[0]`, None under -OO, so
every invocation died with AttributeError. The test runs the real script in a child -OO
interpreter: --help, and `targets` over an empty fixture home.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "audit_local.py"


def _run_oo(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-OO", str(SCRIPT), *args], capture_output=True,
                          encoding="utf-8", env=env, cwd=str(tmp_path))


def test_help_works_under_oo(tmp_path: Path) -> None:
    r = _run_oo(tmp_path, "--help")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("usage: audit_local.py"), r.stdout


def test_targets_runs_under_oo(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    r = _run_oo(tmp_path, "targets", "--home", str(tmp_path / "home"), "--no-personal",
                "--root", str(root), "--json")
    assert r.returncode == 1, r.stderr          # 1: no target found, the empty fixture
    assert json.loads(r.stdout)["data"]["count"] == 0
