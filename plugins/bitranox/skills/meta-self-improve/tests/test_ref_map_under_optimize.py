"""ref_map.py runs under `python -OO`, which strips every docstring.

It built its argument parser's description from `__doc__.splitlines()[0]`; under -OO `__doc__` is
None, so every invocation, `--help` included, died with AttributeError before parsing an argument.
Both tests run the real script in a child interpreter with -OO.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import ref_map

import memory_engine as ME  # ref_map put hooks/ on sys.path at import
import uuid_store as us

SCRIPT = Path(ref_map.__file__).resolve()


def _run_oo(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
               CLAUDE_CONFIG_DIR=str(home / ".claude"), PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-OO", str(SCRIPT), *args], capture_output=True,
                          encoding="utf-8", env=env, cwd=str(tmp_path))


def test_help_works_under_oo(tmp_path: Path) -> None:
    r = _run_oo(tmp_path, "--help")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("usage: ref_map.py"), r.stdout


def test_a_ref_map_runs_under_oo(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    (root / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (root / us.STORE_DIRNAME).mkdir()
    ME.add_or_update_entry(str(root), "Beta rule", "When beta, do beta.", body="Beta prose.",
                           slug="beta-rule")
    ME.add_or_update_entry(str(root), "Alpha rule", "When alpha, do alpha.",
                           body="Alpha prose, see [[beta-rule]].", slug="alpha-rule")
    r = _run_oo(tmp_path, "--root", str(root), "--json", "beta-rule")
    assert r.returncode == 0, r.stderr
    assert "alpha-rule" in json.dumps(json.loads(r.stdout))
