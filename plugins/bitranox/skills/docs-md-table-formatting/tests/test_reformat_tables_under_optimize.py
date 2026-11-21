"""reformat_tables.py runs under `python -OO`, which strips every docstring.

Its --help printed `__doc__.strip()`, None under -OO, so --help died with AttributeError. The
test runs the real script in a child -OO interpreter: --help, and one real --check.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "reformat_tables.py"


def _run_oo(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-OO", str(SCRIPT), *args], capture_output=True,
                          encoding="utf-8", env=env, cwd=str(tmp_path))


def test_help_works_under_oo(tmp_path: Path) -> None:
    r = _run_oo(tmp_path, "--help")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("Usage: python3 reformat_tables.py"), r.stdout


def test_check_runs_under_oo(tmp_path: Path) -> None:
    doc = tmp_path / "t.md"
    doc.write_text("| a | b |\n|---|---|\n| 1 | 22 |\n", encoding="utf-8")
    r = _run_oo(tmp_path, "--check", str(doc))
    assert r.returncode in (0, 1), r.stderr
    assert "Traceback" not in r.stderr
