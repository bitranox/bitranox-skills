"""grep_all and conflict_scan prune ONE set of vendored directories, through one shared module.

Two private copies of the set had to be kept in step by hand, and neither knew a virtualenv by
anything but its name, so `venv/` or `env/` (a venv by its `pyvenv.cfg`) was walked by both.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import _vendored_dirs as V

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
MARKER = "<<<<<<< ours\n"

#: Every directory a walk must prune, one per rule: a name, the .venv prefix, the pyvenv.cfg marker.
PRUNED = (".git", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
          ".venv", ".venv-3.12", ".venv-win", "venv", "env")
#: Look-alikes that are project content and must still be searched.
KEPT = ("src", "venvish", "environment", "node_module")


def _tree(root: Path) -> Path:
    root.mkdir(parents=True)
    # A real repository: a bare `.git` dir with no repo in it makes grep_all's gitignore question
    # fail, which is a different refusal from the one under test.
    subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=60)
    for name in PRUNED + KEPT:
        (root / name).mkdir(exist_ok=True)
        (root / name / "f.txt").write_text(MARKER, encoding="utf-8")
    for name in ("venv", "env"):
        (root / name / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    # A pyvenv.cfg FILE under a kept name proves nothing; only a dir holding it is a venv.
    (root / "venvish" / "pyvenv.cfg.bak").write_text("x\n", encoding="utf-8")
    return root


def _top_dirs(paths: list[str], root: Path) -> set[str]:
    return {Path(p).resolve().relative_to(root.resolve()).parts[0] for p in paths}


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True,
                          text=True, encoding="utf-8", check=False, timeout=60)


def _grep_all_dirs(root: Path) -> set[str]:
    proc = _run("grep_all.py", "<<<<<<<", str(root), "--json")
    assert proc.returncode == 0, proc.stderr
    return _top_dirs([m["path"] for m in json.loads(proc.stdout)["data"]["matches"]], root)


def _conflict_scan_dirs(root: Path) -> set[str]:
    proc = _run("conflict_scan.py", str(root))
    assert proc.returncode == 1, proc.stderr
    # Split at the line-number separator, never the first colon: on Windows that is the
    # drive letter's, and "C:\...\f.txt:1: ..." became the path "C".
    rows = [line.partition(":1: ")[0] for line in proc.stdout.splitlines() if ":1: " in line]
    return _top_dirs(rows, root)


def test_both_scripts_prune_the_same_set_suffixed_and_marked_venvs_included(tmp_path):
    root = _tree(tmp_path / "repo")
    assert _grep_all_dirs(root) == set(KEPT)
    assert _conflict_scan_dirs(root) == set(KEPT)


@pytest.mark.parametrize("name", PRUNED)
def test_every_pruned_name_is_judged_vendored(tmp_path, name):
    (tmp_path / name).mkdir()
    if name in ("venv", "env"):
        (tmp_path / name / "pyvenv.cfg").write_text("", encoding="utf-8")
    assert V.is_vendored_dir(str(tmp_path), name)


@pytest.mark.parametrize("name", KEPT)
def test_a_look_alike_is_not_vendored(tmp_path, name):
    (tmp_path / name).mkdir()
    assert not V.is_vendored_dir(str(tmp_path), name)


def test_prune_edits_the_walk_list_in_place(tmp_path):
    for name in ("src", ".venv-bmk", "node_modules"):
        (tmp_path / name).mkdir()
    dirnames = ["src", ".venv-bmk", "node_modules"]
    V.prune_vendored(str(tmp_path), dirnames)
    assert dirnames == ["src"]
