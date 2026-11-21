"""bump_version, skill_decisions and strip_typographic_tells run under `python -OO`.

-OO strips every docstring. The first two built their argument parser's description from
`__doc__`, and strip_typographic_tells sliced its USAGE out of the module docstring at import, so
under -OO each died with AttributeError before doing anything. Each test runs the real script in a
child interpreter with -OO.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent
REPO = HOOKS.parents[1]


def _run_oo(tmp_path: Path, script: str, *args: str, stdin: str | None = None,
            cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
               CLAUDE_CONFIG_DIR=str(home / ".claude"), PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-OO", str(HOOKS / script), *args], input=stdin,
                          capture_output=True, encoding="utf-8", env=env,
                          cwd=str(cwd or tmp_path))


@pytest.mark.parametrize("script", ["bump_version.py", "skill_decisions.py",
                                    "strip_typographic_tells.py"])
def test_help_works_under_oo(tmp_path: Path, script: str) -> None:
    r = _run_oo(tmp_path, script, "--help")
    assert r.returncode == 0, r.stderr
    assert r.stdout.lower().startswith("usage:"), r.stdout


def test_skill_decisions_show_runs_under_oo(tmp_path: Path) -> None:
    r = _run_oo(tmp_path, "skill_decisions.py", "show", "meta-dream-tree", cwd=REPO)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("d-"), r.stdout


def test_strip_typographic_tells_normalises_stdin_under_oo(tmp_path: Path) -> None:
    r = _run_oo(tmp_path, "strip_typographic_tells.py", "-", stdin="a" + chr(0x2014) + "b\n")
    assert r.returncode == 0, r.stderr
    assert r.stdout == "a - b\n"


def test_strip_typographic_tells_usage_names_every_form_and_the_exit_codes(tmp_path: Path) -> None:
    """USAGE is a constant now, no longer a slice of the docstring: it still carries the whole
    block an unknown option and --help print."""
    r = _run_oo(tmp_path, "strip_typographic_tells.py", "--bogus")
    assert r.returncode == 2
    for form in ("--check FILE", " - ", "-- -FILE", "-h | --help", "Exit 0 done or clean",
                 "2 wins over 1."):
        assert form in r.stderr, (form, r.stderr)
