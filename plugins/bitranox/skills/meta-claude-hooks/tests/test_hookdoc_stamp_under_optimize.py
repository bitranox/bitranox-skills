"""hookdoc_stamp.py runs under `python -OO`, which strips every docstring.

It built its argument parser's description from `__doc__`, None under -OO, so every invocation
died with AttributeError. The test runs the real script in a child -OO interpreter: --help, and
the offline `selftest` over the bundled fixtures.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "hookdoc_stamp.py"


def _run_oo(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-OO", str(SCRIPT), *args], capture_output=True,
                          encoding="utf-8", env=env, cwd=str(tmp_path), timeout=120)


def test_help_works_under_oo(tmp_path: Path) -> None:
    r = _run_oo(tmp_path, "--help")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("usage: hookdoc_stamp"), r.stdout


def test_selftest_runs_under_oo(tmp_path: Path) -> None:
    r = _run_oo(tmp_path, "--json", "selftest")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["ok"] is True
